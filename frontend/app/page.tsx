"use client";

import { useCallback, useEffect, useState } from "react";
import GpuConsentModal, { GpuStatus } from "@/components/GpuConsentModal";
import ResultsPanel from "@/components/ResultsPanel";
import VideoRecorder from "@/components/VideoRecorder";
import {
  ApiError,
  fetchJson,
  fetchRandomQuestion,
  hasApiBackend,
  loadDemoEvaluation,
  postInterviewVideoTurn,
} from "@/lib/api";
import {
  GpuConsent,
  resolveConsentForRequest,
  setStoredGpuConsent,
} from "@/lib/gpuConsent";
import { BankQuestion, pickRandomQuestion } from "@/lib/questions";

type Role = { id: string; label: string };
type AgentTrace = { node: string; decision: string };

type InterviewQuestion = {
  session_id: string;
  question: string;
  question_id?: string;
  competency?: string;
  turn_number: number;
  agent_trace?: AgentTrace[];
};

export default function Home() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [role, setRole] = useState("");
  const [questionCatalog, setQuestionCatalog] = useState<Record<string, BankQuestion[]>>({});
  const [previewQuestion, setPreviewQuestion] = useState<BankQuestion | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [demoMode, setDemoMode] = useState(false);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [interviewStarted, setInterviewStarted] = useState(false);
  const [sessionComplete, setSessionComplete] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState<InterviewQuestion | null>(null);
  const [videoBlob, setVideoBlob] = useState<Blob | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [agentTrace, setAgentTrace] = useState<AgentTrace[]>([]);
  const [turnGrading, setTurnGrading] = useState<Record<string, unknown> | null>(null);

  const [gpuStatus, setGpuStatus] = useState<GpuStatus | null>(null);
  const [consentModalOpen, setConsentModalOpen] = useState(false);
  const [pendingConsent, setPendingConsent] = useState<GpuConsent | null>(null);

  const clearTurnState = useCallback(() => {
    setSessionId(null);
    setInterviewStarted(false);
    setSessionComplete(false);
    setCurrentQuestion(null);
    setVideoBlob(null);
    setTranscript(null);
    setResult(null);
    setAgentTrace([]);
    setTurnGrading(null);
    setError(null);
    setDemoMode(false);
  }, []);

  const loadRandomPreview = useCallback(
    async (roleId: string, catalog: Record<string, BankQuestion[]>) => {
      if (!roleId) {
        setPreviewQuestion(null);
        return null;
      }

      setPreviewLoading(true);
      try {
        if (hasApiBackend()) {
          const picked = await fetchRandomQuestion(roleId);
          const preview: BankQuestion = {
            question_id: picked.question_id,
            question: picked.question,
            competency: picked.competency,
          };
          setPreviewQuestion(preview);
          return preview;
        }

        const picked = pickRandomQuestion(catalog[roleId] || []);
        setPreviewQuestion(picked);
        return picked;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not load a practice question");
        return null;
      } finally {
        setPreviewLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    setLoadingCatalog(true);
    const loadCatalog = async () => {
      try {
        if (!hasApiBackend()) throw new Error("no-api");
        const d = await fetchJson<{ roles: Role[] }>("/roles");
        const loaded = d.roles || [];
        setRoles(loaded);

        const entries = await Promise.all(
          loaded.map(async (r) => {
            const qd = await fetchJson<{ questions: BankQuestion[] }>(`/questions/${r.id}`);
            return [r.id, qd.questions || []] as const;
          })
        );
        const catalog = Object.fromEntries(entries);
        setQuestionCatalog(catalog);

        const defaultRole = loaded[0]?.id || "";
        setRole((prev) => prev || defaultRole);
        const initialRole = defaultRole;
        if (initialRole) await loadRandomPreview(initialRole, catalog);
      } catch {
        const c = await fetch("/catalog.json").then((r) => r.json());
        const loaded = c.roles || [];
        const catalog = (c.questions || {}) as Record<string, BankQuestion[]>;
        setRoles(loaded);
        setQuestionCatalog(catalog);
        const defaultRole = loaded[0]?.id || "";
        setRole((prev) => prev || defaultRole);
        if (defaultRole) await loadRandomPreview(defaultRole, catalog);
      } finally {
        setLoadingCatalog(false);
      }
    };
    void loadCatalog();

    if (hasApiBackend()) {
      fetchJson<GpuStatus>("/gpu/status")
        .then((d) => setGpuStatus(d))
        .catch(() => null);
    }
  }, [loadRandomPreview]);

  const onRecorded = useCallback((blob: Blob) => {
    setVideoBlob(blob);
    setTranscript(null);
    setResult(null);
    setTurnGrading(null);
  }, []);

  const startInterviewForRole = useCallback(
    async (activeRole: string, lockedPreview?: BankQuestion | null) => {
      if (!activeRole) return;

      const preview = lockedPreview ?? previewQuestion;
      setLoading(true);
      setError(null);
      clearTurnState();

      if (!hasApiBackend()) {
        const picked = preview || pickRandomQuestion(questionCatalog[activeRole] || []);
        if (!picked) {
          setError("No questions available for this role.");
          setLoading(false);
          return;
        }
        setDemoMode(true);
        setInterviewStarted(true);
        setCurrentQuestion({
          session_id: "demo",
          question: picked.question,
          question_id: picked.question_id,
          competency: picked.competency,
          turn_number: 1,
        });
        setLoading(false);
        return;
      }

      try {
        const created = await fetchJson<{ session_id: string }>("/interview/sessions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            role: activeRole,
            max_turns: 5,
            difficulty: 3,
            first_question_id: preview?.question_id ?? null,
          }),
        });
        const first = await fetchJson<InterviewQuestion>(
          `/interview/sessions/${created.session_id}/start`,
          { method: "POST" }
        );
        setSessionId(created.session_id);
        setInterviewStarted(true);
        setCurrentQuestion(first);
        setAgentTrace(first.agent_trace || []);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not start interview");
      } finally {
        setLoading(false);
      }
    },
    [clearTurnState, previewQuestion, questionCatalog]
  );

  const startInterview = () => startInterviewForRole(role, previewQuestion);

  const shufflePreview = () => {
    if (!role || interviewStarted) return;
    void loadRandomPreview(role, questionCatalog);
  };

  const handleRoleChange = async (newRole: string) => {
    if (!newRole || newRole === role) return;

    const wasActive = interviewStarted && !sessionComplete;
    setRole(newRole);
    const picked = await loadRandomPreview(newRole, questionCatalog);

    if (wasActive) {
      clearTurnState();
      if (picked) await startInterviewForRole(newRole, picked);
      return;
    }

    if (sessionComplete) {
      clearTurnState();
    }
  };

  const runVideoTurn = async (consent: GpuConsent) => {
    if (!videoBlob || !currentQuestion) return;

    setLoading(true);
    setError(null);

    if (demoMode) {
      try {
        const demo = await loadDemoEvaluation();
        setResult(demo);
        setTranscript(String(demo.transcript || ""));
        setSessionComplete(true);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Demo unavailable");
      } finally {
        setLoading(false);
      }
      return;
    }

    if (!sessionId) return;

    const form = new FormData();
    form.append("video", videoBlob, "recording.webm");
    form.append("gpu_consent", consent);

    try {
      if (consent === "always" || consent === "never") {
        setStoredGpuConsent(consent);
        await fetchJson("/gpu/consent", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ choice: consent }),
        });
      }

      const data = await postInterviewVideoTurn(sessionId, form);
      setTranscript(String(data.transcript || ""));
      setResult((data.evaluation as Record<string, unknown>) || null);
      setTurnGrading((data.grading as Record<string, unknown>) || null);
      setAgentTrace((data.agent_trace as AgentTrace[]) || []);

      if (data.session_complete) {
        setSessionComplete(true);
      } else if (data.next_question) {
        setCurrentQuestion({
          session_id: sessionId,
          question: String(data.next_question),
          question_id: data.next_question_id as string | undefined,
          competency: data.competency as string | undefined,
          turn_number: Number(data.turn_number || 0),
          agent_trace: (data.agent_trace as AgentTrace[]) || [],
        });
        setVideoBlob(null);
        setTranscript(null);
      }
      setPendingConsent(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 428) {
        setConsentModalOpen(true);
        return;
      }
      setError(e instanceof Error ? e.message : "Submission failed");
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = () => {
    const consent = resolveConsentForRequest(gpuStatus, pendingConsent);
    if (gpuStatus?.gpu_available && !consent) {
      setConsentModalOpen(true);
      return;
    }
    runVideoTurn(consent || "never");
  };

  const handleConsentChoice = (choice: GpuConsent) => {
    setConsentModalOpen(false);
    if (choice === "once") {
      setPendingConsent("once");
      runVideoTurn("once");
      return;
    }
    setPendingConsent(null);
    runVideoTurn(choice);
  };

  const displayedQuestion = interviewStarted ? currentQuestion : null;

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
          LangGraph picks questions from the role bank — shuffle for a new prompt, then start when
          you are ready. After each answer the graph advances to the next question.
        </p>
        {!hasApiBackend() && (
          <p className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
            Demo mode — deploy the API with <code className="text-amber-100">render.yaml</code>{" "}
            (cloud profile), then set{" "}
            <code className="text-amber-100">NEXT_PUBLIC_API_URL</code> on Vercel for full Whisper +
            LangGraph scoring.
          </p>
        )}
      </header>

      <div className="grid gap-8 lg:grid-cols-2">
        <section className="space-y-5">
          <div>
            <label className="mb-1 block text-sm text-slate-400">Role</label>
            <select
              value={role}
              onChange={(e) => void handleRoleChange(e.target.value)}
              disabled={loadingCatalog || loading}
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
            {!interviewStarted && (
              <p className="mt-1.5 text-xs text-slate-500">
                {hasApiBackend()
                  ? "Up next is pulled randomly from the LangGraph question bank API."
                  : "Up next is a random pick from the demo question bank."}{" "}
                Shuffle or change role for another prompt.
              </p>
            )}
            {interviewStarted && !sessionComplete && (
              <p className="mt-1.5 text-xs text-slate-500">
                Wrong role? Pick another to restart with a new random question.
              </p>
            )}
          </div>

          {!interviewStarted ? (
            <>
              <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Up next</p>
                  <button
                    type="button"
                    onClick={shufflePreview}
                    disabled={!role || previewLoading || loading}
                    className="shrink-0 rounded-lg border border-slate-600 px-2.5 py-1 text-xs text-slate-300 hover:bg-slate-800 disabled:opacity-50"
                  >
                    {previewLoading ? "Loading..." : "Shuffle"}
                  </button>
                </div>
                {previewQuestion ? (
                  <>
                    <p className="mt-2 text-slate-200">{previewQuestion.question}</p>
                    {previewQuestion.competency && (
                      <p className="mt-2 text-xs text-slate-500">
                        {previewQuestion.competency.replace(/_/g, " ")}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="mt-2 text-sm text-slate-500">
                    {previewLoading ? "Drawing from question bank..." : "Select a role to preview."}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={startInterview}
                disabled={loading || previewLoading || !role || !previewQuestion}
                className="w-full rounded-xl bg-indigo-500 py-3 font-semibold hover:bg-indigo-400 disabled:opacity-50"
              >
                {loading ? "Starting..." : "Start interview"}
              </button>
            </>
          ) : (
            <>
              {displayedQuestion && !sessionComplete && (
                <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-4">
                  <p className="text-xs uppercase tracking-wide text-indigo-300">
                    Question {displayedQuestion.turn_number}
                    {displayedQuestion.competency
                      ? ` · ${displayedQuestion.competency.replace(/_/g, " ")}`
                      : ""}
                  </p>
                  <p className="mt-2 text-slate-100">{displayedQuestion.question}</p>
                </div>
              )}

              {sessionComplete ? (
                <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
                  Interview complete. Change role or shuffle for a new practice question.
                </p>
              ) : (
                <>
                  <VideoRecorder onRecorded={onRecorded} disabled={loading} />

                  {videoBlob && (
                    <p className="text-sm text-emerald-400">
                      Recording ready ({Math.round(videoBlob.size / 1024)} KB)
                    </p>
                  )}

                  <button
                    type="button"
                    onClick={submitAnswer}
                    disabled={loading || !videoBlob}
                    className="w-full rounded-xl bg-emerald-500 py-3 font-semibold hover:bg-emerald-400 disabled:opacity-50"
                  >
                    {loading ? "Transcribing & grading..." : "Submit video answer"}
                  </button>
                </>
              )}

              {transcript && (
                <div className="rounded-xl border border-slate-700 bg-slate-900/80 p-4">
                  <p className="text-xs uppercase text-slate-500">Your answer (transcript)</p>
                  <p className="mt-2 text-sm text-slate-300">{transcript}</p>
                </div>
              )}

              {turnGrading && (
                <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-3 text-sm">
                  <p className="font-medium text-indigo-300">
                    Agent score: {String((turnGrading as { score?: number }).score ?? "?")}/5
                  </p>
                  <p className="mt-1 text-slate-400">
                    {(turnGrading as { feedback?: string }).feedback}
                  </p>
                </div>
              )}

              {agentTrace.length > 0 && (
                <div className="text-xs text-slate-500">
                  <p className="mb-1 font-medium text-slate-400">LangGraph trace</p>
                  <ul className="space-y-0.5">
                    {agentTrace.map((t, i) => (
                      <li key={`${t.node}-${i}`}>
                        <span className="text-indigo-400">{t.node}</span>: {t.decision}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}

          {error && <p className="text-sm text-red-400">{error}</p>}
        </section>

        <section>
          {demoMode && result && (
            <p className="mb-3 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm text-amber-100">
              Sample rubric scores — not from your recording.
            </p>
          )}
          {result ? (
            <ResultsPanel result={result as never} />
          ) : (
            <div className="flex h-full min-h-[320px] items-center justify-center rounded-2xl border border-dashed border-slate-700 p-6 text-center text-slate-500">
              Rubric-grounded scores appear here after you submit a video answer
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
