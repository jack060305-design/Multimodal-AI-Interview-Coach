"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchMyEvaluations } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";

type Row = {
  evaluation_id: string;
  role: string;
  question: string;
  overall_score: number;
  created_at: string;
};

export default function HistoryPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      const token = await getAccessToken();
      if (!token) {
        setError("Sign in to view your evaluation history.");
        setLoading(false);
        return;
      }
      try {
        setRows(await fetchMyEvaluations());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load history");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-lg px-6 py-16 text-center">
        <p className="text-slate-600">{error}</p>
        <Link href="/login" className="mt-4 inline-block text-coach-blue hover:underline">
          Sign in
        </Link>
      </div>
    );
  }

  if (loading) {
    return <div className="px-6 py-16 text-center text-slate-500">Loading history…</div>;
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-900">My evaluations</h1>
      <p className="mt-1 text-sm text-slate-600">Stored in Postgres when signed in.</p>

      {rows.length === 0 ? (
        <p className="mt-8 text-slate-500">No saved evaluations yet.</p>
      ) : (
        <ul className="mt-8 space-y-3">
          {rows.map((r) => (
            <li
              key={r.evaluation_id}
              className="rounded-xl border border-coach-mist bg-white px-4 py-3"
            >
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm font-medium text-coach-blue">{r.role}</span>
                <span className="text-sm font-semibold text-slate-900">{r.overall_score}/100</span>
              </div>
              <p className="mt-1 text-sm text-slate-700">{r.question}</p>
              <p className="mt-1 text-xs text-slate-500">{new Date(r.created_at).toLocaleString()}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
