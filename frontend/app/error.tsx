"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center px-6 text-center">
      <h2 className="text-xl font-semibold text-slate-900">Something went wrong</h2>
      <p className="mt-2 max-w-md text-sm text-slate-600">{error.message}</p>
      <button
        type="button"
        onClick={() => reset()}
        className="mt-5 rounded-xl bg-coach-blue px-4 py-2 text-sm font-semibold text-white hover:bg-coach-cyan"
      >
        Try again
      </button>
    </div>
  );
}
