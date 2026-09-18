"use client";
import type { Services } from "@ugc/contracts";
import { getAuthClient, mockMode } from "@/lib/auth";
import { createHttpServices } from "./http";
import { createMockServices } from "./mock";
let instance: Services | undefined;
export function getServices(): Services {
  return (instance ??= mockMode
    ? createMockServices(true)
    : createHttpServices(async () => {
        const c = getAuthClient();
        if (!c) return null;
        const { data } = await c.auth.getSession();
        return data.session?.access_token || null;
      }));
}
