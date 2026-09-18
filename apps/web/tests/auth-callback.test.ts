import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
const { exchange } = vi.hoisted(() => ({ exchange: vi.fn() }));
vi.mock("@supabase/ssr", () => ({
  createServerClient: (
    _url: string,
    _key: string,
    options: { cookies: { setAll: (values: unknown[]) => void } },
  ) => ({
    auth: {
      exchangeCodeForSession: async (code: string) => {
        const result = await exchange(code);
        if (!result.error)
          options.cookies.setAll([
            { name: "session", value: "test", options: { httpOnly: true } },
          ]);
        return result;
      },
    },
  }),
}));
import { GET } from "../app/auth/callback/route";
beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://auth.example.com");
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "public-key");
  exchange.mockReset();
});
afterEach(() => vi.unstubAllEnvs());
describe("PKCE callback", () => {
  it("exchanges the code and carries session cookies onto the workspace redirect", async () => {
    exchange.mockResolvedValue({ error: null });
    const response = await GET(
      new NextRequest("http://localhost:3000/auth/callback?code=one-time"),
    );
    expect(exchange).toHaveBeenCalledWith("one-time");
    expect(response.headers.get("location")).toBe("http://localhost:3000/");
    expect(response.cookies.get("session")?.value).toBe("test");
  });
  it("redirects failed exchanges to a recoverable login error", async () => {
    exchange.mockResolvedValue({ error: { message: "Expired" } });
    const response = await GET(
      new NextRequest("http://localhost:3000/auth/callback?code=expired"),
    );
    expect(response.headers.get("location")).toBe(
      "http://localhost:3000/login?auth_error=1",
    );
    expect(response.cookies.get("session")).toBeUndefined();
  });
});
