"use client";

import { useCallback, useEffect, useState } from "react";
import GpuConsentModal, { GpuStatus } from "@/components/GpuConsentModal";
import ResultsPanel from "@/components/ResultsPanel";
import VideoRecorder from "@/components/VideoRecorder";
import {
  GpuConsent,
  resolveConsentForRequest,
  setStoredGpuConsent,
} from "@/lib/gpuConsent";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Role = { id: string; label: string };
type Question = { question_id: string; question: string };

export default function Home() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [role, setRole] = useState("");
  const [questionId, setQuestionId] = useState("");
  const [videoBlob, setVideoBlob] = useState<Blob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [gpuStatus, setGpuStatus] = useState<GpuStatus | null>(null);
  const [consentModalOpen, setConsentModalOpen] = useState(false);
  const [pendingConsent, setPendingConsent] = useState<GpuConsent | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/roles`)
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load roles");
        return r.json();
      })
      .then((d) => setRoles(d.roles || []))
      .catch(() => setError("Cannot reach backend API."));

    fetch(`${API_URL}/gpu/status`)
      .then((r) => r.json())
      .then((d) => setGpuStatus(d))
      .catch(() => null);
  }, []);

  useEffect(() => {
    if (!role) return;
    fetch(`${API_URL}/questions/${role}`)
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load questions");
        return r.json();
      })
      .then((d) => {
        setQuestions(d.questions || []);
        setQuestionId(d.questions?.[0]?.question_id || "");
      })
      .catch(() => setError("Cannot reach backend API."));
  }, [role]);

  const onRecorded = useCallback((blob: Blob) => {
    setVideoBlob(blob);
    setResult(null);
  }, []);

  const runEvaluation = async (consent: GpuConsent) => {
    if (!videoBlob || !role || !questionId) return;
    const q = questions.find((x) => x.question_id === questionId);
    if (!q) return;

    setLoading(true);
    setError(null);

    const form = new FormData();
    form.append("role", role);
    form.append("question", q.question);
    form.append("question_id", questionId);
    form.append("gpu_consent", consent);
    form.append("video", videoBlob, "recording.webm");

    try {
      if (consent === "always" || consent === "never") {
        setStoredGpuConsent(consent);
        await fetch(`${API_URL}/gpu/consent`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ choice: consent }),
        });
      }

      const res = await fetch(`${API_URL}/evaluate`, { method: "POST", body: form });
      const data = await res.json();
      if (res.status === 428) {
        setConsentModalOpen(true);
        return;
      }
      if (!res.ok) throw new Error(data.detail?.message || data.detail || "Evaluation failed");
      setResult(data);
      setPendingConsent(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const submit = () => {
    const consent = resolveConsentForRequest(gpuStatus, pendingConsent);

    if (gpuStatus?.gpu_available && !consent) {
      setConsentModalOpen(true);
      return;
    }

    runEvaluation(consent || "never");
  };

  const handleConsentChoice = (choice: GpuConsent) => {
    setConsentModalOpen(false);
    if (choice === "once") {
      setPendingConsent("once");
      runEvaluation("once");
      return;
    }
    setPendingConsent(null);
    runEvaluation(choice);
  };

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-4 py-10">
      <GpuConsentModal
        open={consentModalOpen}
        gpu={gpuStatus}
        onChoice={handleConsentChoice}
        onClose={() => setConsentModalOpen(false)}
      />

      <header className="mb-10">
        <p className="text-sm font-medium text-indigo-400">Multimodal AI Interview Coach</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
          Practice interviews with grounded rubric scoring
        </h1>
        <p className="mt-3 max-w-2xl text-slate-400">
          Record your answer, get eye contact, filler word, confidence analytics, and
          RAG-grounded technical depth evaluation.
        </p>
        {gpuStatus?.gpu_available && (
          <p className="mt-2 text-xs text-slate-500">
            GPU detected: {gpuStatus.gpu_name}. You will be asked before GPU acceleration is used.
          </p>
        )}
      </header>

      <div className="grid gap-8 lg:grid-cols-2">
        <section className="space-y-5">
          <div>
            <label className="mb-1 block text-sm text-slate-400">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5"
            >
              <option value="">Select role...</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm text-slate-400">Question</label>
            <select
              value={questionId}
              onChange={(e) => setQuestionId(e.target.value)}
              disabled={!role}
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 disabled:opacity-50"
            >
              {questions.map((q) => (
                <option key={q.question_id} value={q.question_id}>
                  {q.question}
                </option>
              ))}
            </select>
          </div>

          <VideoRecorder onRecorded={onRecorded} disabled={loading} />

          {videoBlob && (
            <p className="text-sm text-emerald-400">
              Recording ready ({Math.round(videoBlob.size / 1024)} KB)
            </p>
          )}

          <button
            type="button"
            onClick={submit}
            disabled={loading || !videoBlob || !role || !questionId}
            className="w-full rounded-xl bg-emerald-500 py-3 font-semibold hover:bg-emerald-400 disabled:opacity-50"
          >
            {loading ? "Analyzing..." : "Submit for Evaluation"}
          </button>

          {error && <p className="text-sm text-red-400">{error}</p>}
        </section>

        <section>
          {result ? (
            <ResultsPanel result={result as never} />
          ) : (
            <div className="flex h-full min-h-[320px] items-center justify-center rounded-2xl border border-dashed border-slate-700 text-slate-500">
              Results will appear here after submission
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
