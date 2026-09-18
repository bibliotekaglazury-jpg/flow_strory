import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from app.errors import DomainError


def public_target(url):
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise DomainError("INVALID_PRODUCT_URL", "Use a valid public HTTPS URL.", 422) from None
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or port not in (None, 443)
    ):
        raise DomainError("INVALID_PRODUCT_URL", "Use a public HTTPS product URL.", 422) from None
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)}
        if not addresses or any(
            (
                not ipaddress.ip_address(a).is_global
                or ipaddress.ip_address(a).is_multicast
                or ipaddress.ip_address(a).is_reserved
            )
            for a in addresses
        ):
            raise ValueError()
    except (socket.gaierror, ValueError):
        raise DomainError(
            "INVALID_PRODUCT_URL", "Product URL must resolve to a public address.", 422
        ) from None
    return parts, next(iter(sorted(addresses)))


async def download_public(url, max_bytes=2 * 1024 * 1024, accept="text/html"):
    # Pin the connection to the validated IP; TLS SNI and Host preserve certificate checks.
    for _ in range(4):
        parts, ip = public_target(url)
        host = f"[{ip}]" if ":" in ip else ip
        target = parts._replace(netloc=host).geturl()
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False) as client:
                async with client.stream(
                    "GET",
                    target,
                    headers={"Host": parts.hostname, "Accept": accept},
                    extensions={"sni_hostname": parts.hostname},
                ) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        url = urljoin(url, response.headers.get("location", ""))
                        continue
                    response.raise_for_status()
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > max_bytes:
                            raise DomainError(
                                "REMOTE_TOO_LARGE", "Remote content exceeds the size limit.", 413
                            ) from None
                    return bytes(content), response.headers.get("content-type", ""), url
        except httpx.HTTPError:
            raise DomainError(
                "PRODUCT_UNAVAILABLE", "Remote content could not be retrieved.", 503, True
            ) from None
    raise DomainError("INVALID_PRODUCT_URL", "Too many redirects.", 422) from None


async def resolve_product(url):
    data, mime, final = await download_public(url)
    if "text/html" not in mime:
        raise DomainError("INVALID_PRODUCT_URL", "URL must point to a product page.", 422) from None
    soup = BeautifulSoup(data, "html.parser")

    def meta(name):
        el = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        return str(el.get("content", "")).strip() if el else ""

    title = meta("og:title") or (soup.title.get_text(" ", strip=True) if soup.title else "")
    image = meta("og:image")
    if image:
        image = urljoin(final, image)
        try:
            public_target(image)
        except DomainError:
            image = None
    return {
        "url": final,
        "title": title[:500],
        "description": (meta("og:description") or meta("description"))[:4000],
        "imageUrl": image or None,
    }
