import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
export async function proxy(request: NextRequest) {
  if (
    process.env.NEXT_PUBLIC_USE_MOCK_API === "true" ||
    process.env.AUTH_MODE === "mock"
  )
    return NextResponse.next();
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL,
    key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key)
    return NextResponse.redirect(new URL("/login", request.url));
  let response = NextResponse.next({ request });
  const client = createServerClient(url, key, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll(values) {
        values.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        values.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options),
        );
      },
    },
  });
  const { data, error } = await client.auth.getUser();
  if (error || !data.user)
    return NextResponse.redirect(new URL("/login", request.url));
  return response;
}
export const config = {
  matcher: [
    "/",
    "/billing",
    "/library",
    "/brand-kit",
    "/analytics",
    "/settings",
  ],
};
