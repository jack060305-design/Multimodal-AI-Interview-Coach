"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TOOLS = [
  {
    href: "/",
    label: "About",
    description: "What this coach does",
  },
  {
    href: "/practice",
    label: "Practice Interview",
    description: "Grounded rubric scoring",
  },
] as const;

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col border-r border-coach-mist/70 bg-coach-sidebar backdrop-blur-md lg:w-64">
        <div className="border-b border-coach-mist/70 px-4 py-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-coach-violet">
            Multimodal AI
          </p>
          <p className="mt-1 text-sm font-semibold text-slate-900">Interview Coach</p>
        </div>

        <nav className="flex flex-1 flex-col gap-1 p-3">
          <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            AI tools
          </p>
          {TOOLS.map((tool) => {
            const active = pathname === tool.href;
            return (
              <Link
                key={tool.href}
                href={tool.href}
                className={`rounded-xl px-3 py-2.5 transition-colors ${
                  active
                    ? "bg-coach-blue/10 text-coach-blue ring-1 ring-coach-mist"
                    : "text-slate-600 hover:bg-coach-sky/15 hover:text-slate-900"
                }`}
              >
                <p className="text-sm font-medium">{tool.label}</p>
                <p className="mt-0.5 text-xs text-slate-500">{tool.description}</p>
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="min-w-0 flex-1 bg-coach-page">{children}</div>
    </div>
  );
}
