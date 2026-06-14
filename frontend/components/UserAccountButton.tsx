"use client";

import { useEffect, useRef, useState } from "react";
import type { AuthUser } from "@/lib/auth";

export function userInitials(name: string, email: string | null): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0] ?? ""}${parts[parts.length - 1][0] ?? ""}`.toUpperCase();
  }
  if (parts[0] && parts[0].length >= 2) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  if (email && email.length >= 2) {
    return email.slice(0, 2).toUpperCase();
  }
  return "U";
}

type Props = {
  user: AuthUser;
  compact?: boolean;
  onSignOut: () => void;
};

export default function UserAccountButton({ user, compact = false, onSignOut }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const initials = userInitials(user.name, user.email);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`flex w-full items-center gap-2.5 rounded-xl transition-colors hover:bg-slate-100/80 ${
          compact ? "justify-center p-1.5" : "px-2 py-2"
        }`}
        aria-expanded={open}
        aria-haspopup="menu"
        title={compact ? user.name : undefined}
      >
        <span className="relative flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full bg-coach-blue text-sm font-semibold text-white ring-2 ring-white">
          {user.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={user.avatar_url}
              alt=""
              className="h-full w-full object-cover"
              referrerPolicy="no-referrer"
            />
          ) : (
            initials
          )}
        </span>
        {!compact && (
          <>
            <span className="min-w-0 flex-1 text-left">
              <span className="block truncate text-sm font-medium text-slate-800">{user.name}</span>
              {user.email && (
                <span className="block truncate text-xs text-slate-500">{user.email}</span>
              )}
            </span>
            <ChevronIcon className="h-4 w-4 shrink-0 text-slate-400" />
          </>
        )}
      </button>

      {open && (
        <div
          role="menu"
          className={`absolute z-50 min-w-[11rem] rounded-xl border border-coach-mist/80 bg-white py-1 shadow-lg ${
            compact ? "bottom-full left-0 mb-2" : "bottom-full left-0 right-0 mb-2"
          }`}
        >
          {!compact && (
            <div className="border-b border-coach-mist/60 px-3 py-2">
              <p className="truncate text-sm font-medium text-slate-800">{user.name}</p>
              {user.email && <p className="truncate text-xs text-slate-500">{user.email}</p>}
            </div>
          )}
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              onSignOut();
            }}
            className="w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.25a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z"
        clipRule="evenodd"
      />
    </svg>
  );
}
