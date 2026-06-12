"use client";

import { useCallback, useEffect, useState } from "react";
import GpuConsentModal, { GpuStatus } from "@/components/GpuConsentModal";
import ResultsPanel from "@/components/ResultsPanel";
import LiveInterview from "@/components/LiveInterview";
import VideoRecorder from "@/components/VideoRecorder";
import {
  ApiError,
  fetchJson,
  hasApiBackend,
  loadDemoEvaluation,
  postEvaluate,
} from "@/lib/api";
import {
  GpuConsent,
  resolveConsentForRequest,
  setStoredGpuConsent,
} from "@/lib/gpuConsent";

type Role = { id: string; label: string };
type Question = { question_id: string; question: string };

export default function Home() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [role, setRole] = useState("");
  const [questionId, setQuestionId] = useState("");
  const [videoBlob, setVideoBlob] = useState<Blob | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [demoMode, setDemoMode] = useState(false);
  const [gpuStatus, setGpuStatus] = useState<GpuStatus | null>(null);
  const [consentModalOpen, setConsentModalOpen] = useState(false);
  const [pendingConsent, setPendingConsent] = useState<GpuConsent | null>(null);
  const [mode, setMode] = useState<"record" | "live">("record");

  useEffect(() => {
    setLoadingCatalog(true);
    const loadCatalog = async () => {
      try {
        if (!hasApiBackend()) throw new Error("no-api");
        const d = await fetchJson<{ roles: Role[] }>("/roles");
        const loaded = d.roles || [];
        setRoles(loaded);
        if (loaded.length > 0) setRole(loaded[0].id);
      } catch {
        const c = await fetch("/catalog.json").then((r) => r.json());
        setRoles(c.roles || []);
        if (c.roles?.[0]) setRole(c.roles[0].id);
      } finally {
        setLoadingCatalog(false);
      }
    };
    loadCatalog();

    if (hasApiBackend()) {
      fetchJson<GpuStatus>("/gpu/status")
        .then((d) => setGpuStatus(d))
        .catch(() => null);
    }
  }, []);

  useEffect(() => {
    if (!role) return;
    const loadQuestions = async () => {
      try {
        if (!hasApiBackend()) throw new Error("no-api");
        const d = await fetchJson<{ questions: Question[] }>(`/questions/${role}`);
        setQuestions(d.questions || []);
        setQuestionId(d.questions?.[0]?.question_id || "");
      } catch {
        const c = await fetch("/catalog.json").then((r) => r.json());
        const qs = c.questions?.[role] || [];
        setQuestions(qs);
        setQuestionId(qs[0]?.question_id || "");
      }
    };
    loadQuestions();
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
    setDemoMode(false);

    if (!hasApiBackend()) {
      try {
        const demo = await loadDemoEvaluation();
        setResult(demo);
        setDemoMode(true);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Demo evaluation unavailable");
      } finally {
        setLoading(false);
      }
      return;
    }

    const form = new FormData();
    form.append("role", role);
    form.append("question", q.question);
    form.append("question_id", questionId);
    form.append("gpu_consent", consent);
    form.append("video", videoBlob, "recording.webm");

    try {
      if (consent === "always" || consent === "never") {
        setStoredGpuConsent(consent);
        await fetchJson("/gpu/consent", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ choice: consent }),
        });
      }

      try {
        const data = await postEvaluate(form);
        setResult(data);
      } catch (e) {
        if (e instanceof ApiError && e.status === 428) {
          setConsentModalOpen(true);
          return;
        }
        throw e;
      }
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
        {!hasApiBackend() && (
          <p className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
            Demo mode (no API backend). Submit shows sample scores — run{" "}
            <code className="text-amber-100">setup.cmd</code> locally for real analysis.
          </p>
        )}
        {gpuStatus?.gpu_available && (
          <p className="mt-2 text-xs text-slate-500">
            GPU detected: {gpuStatus.gpu_name}. You will be asked before GPU acceleration is used.
          </p>
        )}
      </header>

      <div className="mb-6 flex gap-2 rounded-xl border border-slate-800 bg-slate-900/50 p-1">
        <button
          type="button"
          onClick={() => setMode("record")}
          className={`flex-1 rounded-lg py-2 text-sm font-medium ${
            mode === "record" ? "bg-emerald-500 text-black" : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Record &amp; evaluate
        </button>
        <button
          type="button"
          onClick={() => setMode("live")}
          className={`flex-1 rounded-lg py-2 text-sm font-medium ${
            mode === "live" ? "bg-indigo-500 text-white" : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Live interview (LangGraph)
        </button>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        <section className="space-y-5">
          <div>
            <label className="mb-1 block text-sm text-slate-400">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              disabled={loadingCatalog}
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 disabled:opacity-50"
            >
              <option value="">
                {loadingCatalog ? "Loading roles..." : "Select role..."}
              </option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          {mode === "record" ? (
            <>
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
            </>
          ) : (
            <LiveInterview role={role} disabled={loading || !role} />
          )}

          {error && mode === "record" && <p className="text-sm text-red-400">{error}</p>}
        </section>

        <section>
          {demoMode && (
            <p className="mb-3 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm text-amber-100">
              Sample results only — your recording was not sent to the API.
            </p>
          )}
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
