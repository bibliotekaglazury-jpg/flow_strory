import type { Page } from "@playwright/test";
import { createMockServices } from "../services/mock";

/** Per-test API boundary: browser tests can never reach paid providers. */
export async function mockApi(page: Page) {
  const s = createMockServices(false);
  await page.route("**/api/**", async (route) => {
    const request = route.request(),
      url = new URL(request.url());
    const path = url.pathname.replace(/^\/api/, ""),
      method = request.method();
    const body = request.headers()["content-type"]?.includes("application/json")
      ? request.postDataJSON()
      : {};
    try {
      let data: unknown;
      if (path === "/templates")
        data = await s.templates.list(Object.fromEntries(url.searchParams));
      else if (path === "/models") data = await s.models.list();
      else if (path === "/assets" && method === "GET")
        data = await s.assets.list(
          url.searchParams.get("role") as "person",
          url.searchParams.get("source") as "try_on",
        );
      else if (path === "/assets") {
        data = await s.assets.upload(
          new File([new Uint8Array(20)], "product.png", { type: "image/png" }),
          request.postData()?.includes('name="role"\r\n\r\nperson')
            ? "person"
            : "product",
          request.postData()?.includes('name="source"\r\n\r\ntry_on')
            ? "try_on"
            : undefined,
        );
        (data as { asset: { url: string } }).asset.url =
          "/template-styles/ugc-review.webp";
      } else if (path === "/assets/bulk") {
        const count = (request.postData()?.match(/name="files"/g) || []).length;
        const uploaded = await s.assets.uploadMany(
          Array.from(
            { length: count },
            (_, i) =>
              new File([new Uint8Array(20)], `piece-${i}.png`, { type: "image/png" }),
          ),
        );
        for (const asset of uploaded.assets)
          asset.url = "/template-styles/ugc-review.webp";
        data = uploaded;
      } else if (path === "/assets/catalog-import") {
        // A real file upload from disk (via setInputFiles) never exposes its bytes through
        // postData() here - Chromium's request interception only preserves the multipart
        // structure, not file part content, same reason /assets/bulk below fabricates its
        // file bytes instead of reading the real upload. Tests use a fixed fixture (two good
        // rows, one row missing both url and imageUrl), so the mock replays that content.
        const csvText = "imageUrl,name\nhttps://cdn.example/shirt.png,Shirt\nhttps://cdn.example/hat.png,Hat\n,Broken row\n";
        const imported = await s.assets.importCatalogCsv(
          new File([csvText], "catalog.csv", { type: "text/csv" }),
        );
        for (const asset of imported.created) asset.url = "/template-styles/ugc-review.webp";
        data = imported;
      } else if (path === "/try-on") {
        data = await s.tryOn.preview(body);
        (data as { asset: { url: string } }).asset.url =
          "/template-styles/ugc-review.webp";
      } else if (path === "/look-projects")
        data =
          method === "POST"
            ? await s.lookProjects.create(body)
            : await s.lookProjects.list();
      else if (/^\/look-projects\/[^/]+$/.test(path))
        data = await s.lookProjects.get(path.split("/")[2]);
      else if (path === "/product/resolve")
        data = await s.products.resolve(body.url);
      else if (path === "/credits")
        data = await s.credits.get(
          url.searchParams.has("estimate")
            ? JSON.parse(url.searchParams.get("estimate")!)
            : undefined,
        );
      else if (path === "/prompts/generate")
        data = await s.prompts.generate(body);
      else if (path === "/generations")
        data =
          method === "POST"
            ? await s.generations.create(
                body,
                request.headers()["idempotency-key"],
              )
            : await s.generations.list();
      else if (/^\/generations\/[^/]+$/.test(path))
        data = await s.generations.get(path.split("/")[2]);
      else if (path === "/chat/sessions") data = await s.chat.create();
      else if (/^\/chat\/sessions\/[^/]+\/messages$/.test(path))
        data =
          method === "POST"
            ? await s.chat.send(path.split("/")[3], body)
            : await s.chat.messages(path.split("/")[3]);
      else if (/^\/chat\/sessions\/[^/]+\/apply$/.test(path))
        data = await s.chat.apply(path.split("/")[3], body);
      else if (/^\/chat\/sessions\/[^/]+$/.test(path))
        data =
          method === "DELETE"
            ? await s.chat.delete(path.split("/")[3])
            : await s.chat.get(path.split("/")[3]);
      else throw new Error("Unmocked API operation");
      await route.fulfill({ status: 200, json: data });
    } catch (e) {
      await route.fulfill({
        status: 422,
        json: {
          error: {
            code: "MOCK_ERROR",
            message: (e as Error).message,
            retryable: false,
          },
          requestId: "test",
        },
      });
    }
  });
}
