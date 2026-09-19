import hashlib
import json
import requests
import os

# ─── Konfiguracja ────────────────────────────────────────────────
MERCHANT_ID = 0          # ← Wstaw swój Merchant ID z panelu P24
POS_ID      = 0          # ← Zazwyczaj = MERCHANT_ID
CRC         = ""         # ← Klucz CRC z panelu P24 → Moje dane → Dane API
API_KEY     = ""         # ← Klucz do raportów (secretId) z panelu P24
SANDBOX     = True       # ← True = środowisko testowe, False = produkcja

# ─── Plany subskrypcji ────────────────────────────────────────────
PLAN_MONTHLY = 10000     # 100.00 PLN w groszach
PLAN_YEARLY  = 60000     # 600.00 PLN w groszach
VAT_RATE = 0.23
PLAN_MONTHLY_BRUTTO = int(PLAN_MONTHLY * (1 + VAT_RATE))  # 12300 = 123.00 PLN
PLAN_YEARLY_BRUTTO  = int(PLAN_YEARLY * (1 + VAT_RATE))   # 73800 = 738.00 PLN

# ─── URL-e ───────────────────────────────────────────────────────
BASE_URL = "https://sandbox.przelewy24.pl/api/v1" if SANDBOX else "https://secure.przelewy24.pl/api/v1"
PANEL_URL = "https://sandbox.przelewy24.pl" if SANDBOX else "https://secure.przelewy24.pl"


def calculate_sign(params: dict) -> str:
    """Oblicz podpis SHA384 dla parametrów transakcji."""
    combined = json.dumps(params, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha384(combined.encode('utf-8')).hexdigest()


def create_transaction(email: str, amount: int, description: str, session_id: str, return_url: str, status_url: str) -> dict:
    """
    Zarejestruj transakcję w P24.
    Zwraca {'success': True, 'token': '...', 'redirect_url': '...'} lub {'success': False, 'error': '...'}.
    """
    sign_params = {
        "sessionId": session_id,
        "merchantId": MERCHANT_ID,
        "amount": amount,
        "currency": "PLN",
        "crc": CRC
    }
    sign = calculate_sign(sign_params)

    payload = {
        "merchantId": MERCHANT_ID,
        "posId": POS_ID,
        "sessionId": session_id,
        "amount": amount,
        "currency": "PLN",
        "description": description,
        "email": email,
        "country": "PL",
        "language": "pl",
        "urlReturn": return_url,
        "urlStatus": status_url,
        "sign": sign
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/transaction/register",
            json=payload,
            auth=(str(POS_ID), API_KEY),
            timeout=15
        )
        data = resp.json()
        if resp.status_code == 200 and data.get("data", {}).get("token"):
            token = data["data"]["token"]
            redirect_url = f"{PANEL_URL}/trnRequest/{token}"
            return {"success": True, "token": token, "redirect_url": redirect_url}
        else:
            return {"success": False, "error": str(data)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def verify_transaction(session_id: str, order_id: int, amount: int) -> bool:
    """Zweryfikuj transakcję po otrzymaniu webhooka z P24."""
    sign_params = {
        "sessionId": session_id,
        "orderId": order_id,
        "amount": amount,
        "currency": "PLN",
        "crc": CRC
    }
    sign = calculate_sign(sign_params)

    payload = {
        "merchantId": MERCHANT_ID,
        "posId": POS_ID,
        "sessionId": session_id,
        "amount": amount,
        "currency": "PLN",
        "orderId": order_id,
        "sign": sign
    }

    try:
        resp = requests.put(
            f"{BASE_URL}/transaction/verify",
            json=payload,
            auth=(str(POS_ID), API_KEY),
            timeout=15
        )
        data = resp.json()
        return resp.status_code == 200 and data.get("data", {}).get("status") == "success"
    except Exception:
        return False
