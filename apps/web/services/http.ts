import type { Asset, Services } from "@ugc/contracts";
export class ServiceError extends Error {
  constructor(
    public code: string,
    message: string,
    public retryable = false,
  ) {
    super(message);
    this.name = "ServiceError";
  }
}
export function createHttpServices(
  getToken: () => Promise<string | null>,
): Services {
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const token = await getToken();
    const headers = new Headers(init.headers);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (init.body && !(init.body instanceof FormData))
      headers.set("Content-Type", "application/json");
    let response: Response;
    try {
      response = await fetch(`/api${path}`, {
        ...init,
        headers,
        cache: "no-store",
      });
    } catch {
      throw new ServiceError(
        "NETWORK_ERROR",
        "Connection interrupted. Please try again.",
        true,
      );
    }
    const data = await response.json().catch(() => null);
    if (!response.ok)
      throw new ServiceError(
        data?.error?.code || "REQUEST_FAILED",
        data?.error?.message || "The request could not be completed.",
        data?.error?.retryable || false,
      );
    return data as T;
  }
  const post = <T>(path: string, body: unknown, headers?: HeadersInit) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body), headers });
  return {
    chat: {
      create: () => post("/chat/sessions", {}),
      get: (id) => request(`/chat/sessions/${encodeURIComponent(id)}`),
      messages: (id) =>
        request(`/chat/sessions/${encodeURIComponent(id)}/messages`),
      send: (id, input) =>
        post(`/chat/sessions/${encodeURIComponent(id)}/messages`, input),
      delete: (id) =>
        request(`/chat/sessions/${encodeURIComponent(id)}`, {
          method: "DELETE",
        }),
      apply: (id, input) =>
        post(`/chat/sessions/${encodeURIComponent(id)}/apply`, input),
    },
    assets: {
      async upload(file, role, source, onProgress) {
        const form = new FormData();
        form.set("file", file);
        form.set("role", role);
        if (source) form.set("source", source);
        const token = await getToken();
        // XMLHttpRequest, not fetch: only it reports upload progress, and a dropped
        // connection must surface as an error instead of an endless "Uploading…".
        return new Promise<{ asset: Asset }>((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          xhr.open("POST", "/api/assets");
          if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
          xhr.upload.onprogress = (event) => {
            if (event.lengthComputable)
              onProgress?.(Math.min(99, Math.round((event.loaded / event.total) * 100)));
          };
          xhr.onerror = () =>
            reject(
              new ServiceError(
                "NETWORK_ERROR",
                "The upload was interrupted. Check your connection and try again.",
                true,
              ),
            );
          xhr.onload = () => {
            let data: { asset?: Asset; error?: { code?: string; message?: string; retryable?: boolean } } | null = null;
            try {
              data = JSON.parse(xhr.responseText);
            } catch {
              data = null;
            }
            if (xhr.status >= 200 && xhr.status < 300 && data?.asset) {
              onProgress?.(100);
              resolve({ asset: data.asset });
              return;
            }
            reject(
              new ServiceError(
                data?.error?.code || "UPLOAD_FAILED",
                data?.error?.message || "The upload could not be completed. Try again.",
                data?.error?.retryable ?? true,
              ),
            );
          };
          xhr.send(form);
        });
      },
      uploadMany(files) {
        const form = new FormData();
        for (const file of files) form.append("files", file);
        return request("/assets/bulk", { method: "POST", body: form });
      },
      list: (role, source) =>
        request(
          `/assets?role=${encodeURIComponent(role)}&source=${encodeURIComponent(source)}`,
        ),
      importCatalogCsv(file) {
        const form = new FormData();
        form.append("file", file);
        return request("/assets/catalog-import", { method: "POST", body: form });
      },
    },
    tryOn: { preview: (input) => post("/try-on", input) },
    lookProjects: {
      create: (input) => post("/look-projects", input),
      list: () => request("/look-projects"),
      get: (id) => request(`/look-projects/${encodeURIComponent(id)}`),
      remove: (id) => request(`/look-projects/${encodeURIComponent(id)}`, { method: "DELETE" }),
    },
    subtitleProjects: {
      create: (input, key) =>
        post("/subtitle-projects", input, { "Idempotency-Key": key }),
      list: (cursor) =>
        request(
          `/subtitle-projects${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`,
        ),
      get: (id) => request(`/subtitle-projects/${encodeURIComponent(id)}`),
      remove: (id) =>
        request(`/subtitle-projects/${encodeURIComponent(id)}`, { method: "DELETE" }),
      update: (id, input) =>
        request(`/subtitle-projects/${encodeURIComponent(id)}`, {
          method: "PATCH",
          body: JSON.stringify(input),
        }),
      export: (id, input, key) =>
        post(`/subtitle-projects/${encodeURIComponent(id)}/exports`, input, {
          "Idempotency-Key": key,
        }),
      getExport: (id, exportId) =>
        request(
          `/subtitle-projects/${encodeURIComponent(id)}/exports/${encodeURIComponent(exportId)}`,
        ),
      share: (id, exportId) =>
        request(
          `/subtitle-projects/${encodeURIComponent(id)}/exports/${encodeURIComponent(exportId)}/share`,
          { method: "POST" },
        ),
      unshare: (id, exportId) =>
        request(
          `/subtitle-projects/${encodeURIComponent(id)}/exports/${encodeURIComponent(exportId)}/share`,
          { method: "DELETE" },
        ),
      getShared: (token) => request(`/subtitle-shares/${encodeURIComponent(token)}`),
    },
    products: { resolve: (url) => post("/product/resolve", { url }) },
    templates: {
      list: (filters = {}) =>
        request(
          `/templates?${new URLSearchParams(
            Object.entries(filters)
              .filter(([, value]) => value !== undefined)
              .map(([key, value]) => [key, String(value)]),
          ).toString()}`,
        ),
    },
    models: { list: () => request("/models") },
    prompts: { generate: (input) => post("/prompts/generate", input) },
    generations: {
      create: (input, key) =>
        post("/generations", input, { "Idempotency-Key": key }),
      get: (id) => request(`/generations/${encodeURIComponent(id)}`),
      list: (cursor) =>
        request(
          `/generations${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`,
        ),
      cancel: (id) => post(`/generations/${encodeURIComponent(id)}/cancel`, {}),
      remove: (id) => request(`/generations/${encodeURIComponent(id)}`, { method: "DELETE" }),
    },
    credits: {
      get: (estimate) =>
        request(
          `/credits${estimate ? `?estimate=${encodeURIComponent(JSON.stringify(estimate))}` : ""}`,
        ),
    },
    billing: {
      summary: () => request("/billing/summary"),
      checkout: (priceId) => post("/billing/checkout", { priceId }),
      portal: () => post("/billing/portal", {}),
    },
  };
}
