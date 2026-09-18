"use client";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  CirclePlus,
  Captions,
  Shirt,
  LayoutGrid,
  Folder,
  Palette,
  ChartNoAxesCombined,
  CreditCard,
  Settings,
  ArrowUpRight,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { getAuthClient, mockMode } from "@/lib/auth";
const items = [
  ["Create", "/", CirclePlus],
  ["Try On", "/try-on", Shirt],
  ["Subtitles", "/subtitles", Captions],
  ["Templates", "/templates", LayoutGrid],
  ["Library", "/library", Folder],
  ["Brand Kit", "/brand-kit", Palette],
  ["Analytics", "/analytics", ChartNoAxesCombined],
  ["Billing", "/billing", CreditCard],
  ["Settings", "/settings", Settings],
] as const;
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  return (
    <>
      <a href="#create" className="skip-link">
        Skip to creation
      </a>
      <aside
        className={`sidebar${sidebarCollapsed ? " sidebar-collapsed" : ""}`}
        data-state={sidebarCollapsed ? "collapsed" : "expanded"}
        data-testid="sidebar"
      >
        <div className="sidebar-header">
          <button
            type="button"
            className="sidebar-toggle"
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!sidebarCollapsed}
            aria-controls="main-navigation"
            onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
          >
            {sidebarCollapsed ? (
              <PanelLeftOpen size={18} strokeWidth={1.7} />
            ) : (
              <PanelLeftClose size={18} strokeWidth={1.7} />
            )}
          </button>
          <Link href="/" className="wordmark">
            Forma<span>REAL PRODUCTS. REAL STORIES.</span>
          </Link>
        </div>
        <nav aria-label="Main navigation" id="main-navigation">
          {items.map(([label, href, Icon]) => (
            <Link
              key={label}
              href={href}
              className={pathname === href ? "nav-active" : ""}
              aria-current={pathname === href ? "page" : undefined}
              aria-label={label}
              onMouseEnter={() => setSidebarCollapsed(false)}
              onFocus={() => setSidebarCollapsed(false)}
            >
              <Icon size={18} strokeWidth={1.7} />
              <span className="nav-label">{label}</span>
            </Link>
          ))}
        </nav>
        <div
          className="sidebar-silver-ribbon"
          data-testid="sidebar-silver-ribbon"
          aria-hidden="true"
        >
          <Image
            src="/sidebar-silver-ribbon.webp"
            alt=""
            width={600}
            height={200}
            sizes="260px"
          />
        </div>
        <div className="sidebar-bottom">
          <div className="plan-box">
            <strong>
              {mockMode ? "Your creative space" : "Ready for your next story?"}
            </strong>
            <p>
              {mockMode
                ? "Explore the workflow with demo credits."
                : "Manage your plan and credits."}
            </p>
            <Link href="/billing" className="button button-primary">
              {mockMode ? "Demo plan" : "View plan"}
              <ArrowUpRight size={13} />
            </Link>
          </div>
          <div className="account">
            <span className="avatar">{mockMode ? "D" : "U"}</span>
            <span className="account-copy">
              <strong>{mockMode ? "Demo workspace" : "Your account"}</strong>
              <small>{mockMode ? "No real charges" : "Secure workspace"}</small>
            </span>
            {!mockMode && (
              <button
                aria-label="Sign out"
                onClick={async () => {
                  await getAuthClient()?.auth.signOut();
                  router.replace("/login");
                  router.refresh();
                }}
              >
                <LogOut size={14} />
              </button>
            )}
          </div>
        </div>
      </aside>
      <main
        className={`main-content${
          sidebarCollapsed ? " main-content-sidebar-collapsed" : ""
        }`}
      >
        {children}
      </main>
    </>
  );
}
