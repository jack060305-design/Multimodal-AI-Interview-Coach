import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center px-6 text-center">
      <h2 className="text-xl font-semibold text-slate-900">Page not found</h2>
      <p className="mt-2 text-sm text-slate-600">This page does not exist in the interview coach app.</p>
      <div className="mt-5 flex gap-3">
        <Link
          href="/"
          className="rounded-xl border border-coach-mist bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-coach-sky/10"
        >
          About
        </Link>
        <Link
          href="/practice"
          className="rounded-xl bg-coach-blue px-4 py-2 text-sm font-semibold text-white hover:bg-coach-cyan"
        >
          Practice interview
        </Link>
      </div>
    </div>
  );
}
