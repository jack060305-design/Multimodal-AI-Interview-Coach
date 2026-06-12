"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="bg-coach-page text-slate-800 antialiased">
        <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
          <h2 className="text-xl font-semibold text-slate-900">Application error</h2>
          <p className="mt-2 max-w-md text-sm text-slate-600">{error.message}</p>
          <button
            type="button"
            onClick={() => reset()}
            className="mt-5 rounded-xl bg-coach-blue px-4 py-2 text-sm font-semibold text-white hover:bg-coach-cyan"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
