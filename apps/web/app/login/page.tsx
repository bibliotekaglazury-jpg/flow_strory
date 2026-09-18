"use client";
import { useEffect, useSyncExternalStore } from "react";
import type { AuthChangeEvent, Session } from "@supabase/supabase-js";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";
import { getAuthClient, mockMode } from "@/lib/auth";
const subscribeLocation = (onChange: () => void) => {
  window.addEventListener("popstate", onChange);
  return () => window.removeEventListener("popstate", onChange);
};
const appearance = {
  theme: ThemeSupa,
  variables: {
    default: {
      colors: {
        brand: "#D5FF32",
        brandAccent: "#C5EF26",
        brandButtonText: "#071117",
      },
    },
  },
};
export default function Login() {
  const client = getAuthClient(),
    router = useRouter();
  const authError = useSyncExternalStore(
    subscribeLocation,
    () => new URLSearchParams(window.location.search).has("auth_error"),
    () => false,
  );
  useEffect(() => {
    if (!client) return;
    const { data } = client.auth.onAuthStateChange(
      (event: AuthChangeEvent, session: Session | null) => {
        if (session && (event === "SIGNED_IN" || event === "INITIAL_SESSION")) {
          router.replace("/");
          router.refresh();
        }
      },
    );
    return () => data.subscription.unsubscribe();
  }, [client, router]);
  return (
    <main className="auth-page">
      <div className="auth-panel">
        <h1>Welcome to Forma</h1>
        <p>Your next product story starts here.</p>
        {authError && (
          <p role="alert">Sign-in could not be completed. Please try again.</p>
        )}
        {mockMode ? (
          <Link className="button button-primary" href="/">
            Open demo workspace
          </Link>
        ) : client ? (
          <Auth
            supabaseClient={client}
            providers={["google"]}
            appearance={appearance}
            redirectTo={
              typeof window !== "undefined"
                ? `${window.location.origin}/auth/callback`
                : undefined
            }
          />
        ) : (
          <p role="status">
            Authentication is not configured. Set the public Supabase URL and
            anonymous key to enable sign-in.
          </p>
        )}
      </div>
    </main>
  );
}
