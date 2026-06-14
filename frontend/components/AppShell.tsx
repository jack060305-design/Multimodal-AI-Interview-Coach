"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getCurrentUser, signOutAuth, type AuthUser } from "@/lib/auth";
import { getSupabase } from "@/lib/supabase/client";
import type { AuthChangeEvent, Session } from "@supabase/supabase-js";
import UserAccountButton from "@/components/UserAccountButton";

const TOOLS = [
  {
    href: "/practice",
    label: "Practice",
    description: "Grounded rubric scoring",
    icon: PracticeIcon,
  },
  {
    href: "/history",
    label: "History",
    description: "Saved evaluations",
    icon: HistoryIcon,
  },
] as const;

const SIDEBAR_KEY = "ic-sidebar-collapsed";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(SIDEBAR_KEY);
    if (stored === "1") setCollapsed(true);
  }, []);

  useEffect(() => {
    void getCurrentUser().then(setUser);
    const sb = getSupabase();
    if (!sb) return;
    const { data: sub } = sb.auth.onAuthStateChange((_event: AuthChangeEvent, session: Session | null) => {
      if (session?.user) {
        const meta = session.user.user_metadata || {};
        setUser({
          id: session.user.id,
          email: session.user.email ?? null,
          name: meta.full_name || meta.name || session.user.email?.split("@")[0] || "User",
          avatar_url: meta.avatar_url || meta.picture || null,
          provider: session.user.app_metadata?.provider,
        });
      } else {
        setUser(null);
      }
    });
    return () => sub.subscription.unsubscribe();
  }, [pathname]);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(SIDEBAR_KEY, next ? "1" : "0");
      return next;
    });
  };

  const logout = async () => {
    await signOutAuth();
    setUser(null);
    router.push("/login");
  };

  return (
    <div className="flex min-h-screen">
      <aside
        className={`flex shrink-0 flex-col border-r border-coach-mist/70 bg-coach-sidebar backdrop-blur-md transition-[width] duration-200 ${
          collapsed ? "w-[4.25rem]" : "w-60 lg:w-64"
        }`}
      >
        <div
          className={`flex items-center border-b border-coach-mist/70 ${
            collapsed ? "justify-center px-2 py-4" : "justify-between gap-2 px-4 py-4"
          }`}
        >
          {!collapsed && (
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wider text-coach-violet">
                Multimodal AI
              </p>
              <p className="mt-0.5 truncate text-sm font-semibold text-slate-900">Interview Coach</p>
            </div>
          )}
          <button
            type="button"
            onClick={toggleCollapsed}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <SidebarToggleIcon collapsed={collapsed} />
          </button>
        </div>

        <nav className={`flex flex-1 flex-col gap-1 ${collapsed ? "items-center p-2" : "p-3"}`}>
          {!collapsed && (
            <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              AI tools
            </p>
          )}
          {TOOLS.map((tool) => {
            const active = pathname === tool.href;
            const Icon = tool.icon;
            if (collapsed) {
              return (
                <Link
                  key={tool.href}
                  href={tool.href}
                  title={tool.label}
                  className={`flex h-10 w-10 items-center justify-center rounded-xl transition-colors ${
                    active
                      ? "bg-coach-blue/10 text-coach-blue"
                      : "text-slate-600 hover:bg-coach-sky/15"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                </Link>
              );
            }
            return (
              <Link
                key={tool.href}
                href={tool.href}
                className={`flex gap-3 rounded-xl px-3 py-2.5 transition-colors ${
                  active
                    ? "bg-coach-blue/10 text-coach-blue ring-1 ring-coach-mist"
                    : "text-slate-600 hover:bg-coach-sky/15 hover:text-slate-900"
                }`}
              >
                <Icon className="mt-0.5 h-5 w-5 shrink-0" />
                <span className="min-w-0">
                  <p className="text-sm font-medium">{tool.label}</p>
                  <p className="mt-0.5 text-xs text-slate-500">{tool.description}</p>
                </span>
              </Link>
            );
          })}
        </nav>

        <div className={`border-t border-coach-mist/70 ${collapsed ? "p-2" : "p-3"}`}>
          {user ? (
            <UserAccountButton user={user} compact={collapsed} onSignOut={() => void logout()} />
          ) : collapsed ? (
            <Link
              href="/login"
              title="Sign in"
              className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-coach-blue text-xs font-semibold text-white hover:bg-coach-cyan"
            >
              In
            </Link>
          ) : (
            <div className="flex flex-col gap-2">
              <Link
                href="/login"
                className="rounded-lg bg-coach-blue px-3 py-2 text-center text-sm font-medium text-white hover:bg-coach-cyan"
              >
                Sign in
              </Link>
              <Link
                href="/signup"
                className="rounded-lg border border-coach-mist px-3 py-2 text-center text-sm text-slate-700 hover:bg-slate-50"
              >
                Sign up
              </Link>
            </div>
          )}
        </div>
      </aside>

      <div className="min-w-0 flex-1 bg-coach-page">{children}</div>
    </div>
  );
}

function SidebarToggleIcon({ collapsed }: { collapsed: boolean }) {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d={collapsed ? "M9 4v16" : "M8 4v16"} />
      {collapsed ? <path d="M11 12h6M13 9l3 3-3 3" /> : null}
    </svg>
  );
}

function PracticeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 6h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2z" />
    </svg>
  );
}

function HistoryIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}
