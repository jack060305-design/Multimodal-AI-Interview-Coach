"use client";

import { useCallback, useEffect, useState } from "react";
import GpuConsentModal, { GpuStatus } from "@/components/GpuConsentModal";
import ResultsPanel from "@/components/ResultsPanel";
import VideoRecorder from "@/components/VideoRecorder";
import {
  ApiError,
  fetchJson,
  fetchRandomQuestion,
  fetchQuestionFeedStatus,
  fetchDailyQuestionStatus,
  fetchHealth,
  getApiBaseUrl,
  hasApiBackend,
  HealthStatus,
  loadDemoEvaluation,
  postInterviewVideoTurn,
} from "@/lib/api";
import {
  GpuConsent,
  resolveConsentForRequest,
  setStoredGpuConsent,
} from "@/lib/gpuConsent";
import { BankQuestion, pickRandomQuestion } from "@/lib/questions";
import type { ClientDeliveryMetrics } from "@/lib/faceHud";
import { useAuthSession } from "@/lib/useAuthSession";

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

export default function PracticeInterview() {
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
  const [clientMetrics, setClientMetrics] = useState<Record<string, unknown> | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [agentTrace, setAgentTrace] = useState<AgentTrace[]>([]);
  const [turnGrading, setTurnGrading] = useState<Record<string, unknown> | null>(null);

  const [gpuStatus, setGpuStatus] = useState<GpuStatus | null>(null);
  const [feedStatus, setFeedStatus] = useState<{
    total: number;
    bank_counts: Record<string, number>;
    synced_at: string | null;
  } | null>(null);
  const [dailyStatus, setDailyStatus] = useState<{
    theme_today: string;
    total: number;
    generated_at: string | null;
    mode: string;
    llm_calls_last_run?: number | null;
    agent_trace?: Array<{ node: string; decision: string }> | null;
  } | null>(null);
  const [apiHealth, setApiHealth] = useState<HealthStatus | null>(null);
  const [consentModalOpen, setConsentModalOpen] = useState(false);
  const [pendingConsent, setPendingConsent] = useState<GpuConsent | null>(null);
  const [signedIn, setSignedIn] = useState(false);
  const { signedIn: sessionSignedIn, ready: authReady } = useAuthSession();

  useEffect(() => {
    if (authReady) setSignedIn(sessionSignedIn);
  }, [authReady, sessionSignedIn]);

  const clearTurnState = useCallback(() => {
    setSessionId(null);
    setInterviewStarted(false);
    setSessionComplete(false);
    setCurrentQuestion(null);
    setVideoBlob(null);
    setClientMetrics(null);
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
        setQuestionCatalog(Object.fromEntries(entries));
      } catch {
        const c = await fetch("/catalog.json").then((r) => r.json());
        setRoles(c.roles || []);
        setQuestionCatalog((c.questions || {}) as Record<string, BankQuestion[]>);
      } finally {
        setLoadingCatalog(false);
      }
    };
    void loadCatalog();

    if (hasApiBackend()) {
      fetchHealth()
        .then((h) => setApiHealth(h))
        .catch(() => setApiHealth(null));
      fetchJson<GpuStatus>("/gpu/status")
        .then((d) => setGpuStatus(d))
        .catch(() => null);
      fetchQuestionFeedStatus()
        .then((d) =>
          setFeedStatus({
            total: d.total,
            bank_counts: d.bank_counts,
            synced_at: d.synced_at,
          })
        )
        .catch(() => null);
      fetchDailyQuestionStatus()
        .then((d) =>
          setDailyStatus({
            theme_today: d.theme_today,
            total: d.total,
            generated_at: d.generated_at,
            mode: d.mode,
            llm_calls_last_run: d.llm_calls_last_run,
            agent_trace: d.agent_trace,
          })
        )
        .catch(() => null);
    }
  }, []);

  const onRecorded = useCallback((blob: Blob, metrics?: ClientDeliveryMetrics) => {
    setVideoBlob(blob);
    setClientMetrics(metrics ?? null);
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
    if (newRole === role) return;

    if (!newRole) {
      setRole("");
      setPreviewQuestion(null);
      if (interviewStarted || sessionComplete) clearTurnState();
      return;
    }

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
    if (clientMetrics) {
      form.append("client_metrics", JSON.stringify(clientMetrics));
    }

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
    setClientMetrics(null);
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
    <div className="mx-auto max-w-7xl px-4 py-8 lg:px-8 lg:py-10">
      <GpuConsentModal
        open={consentModalOpen}
        gpu={gpuStatus}
        onChoice={handleConsentChoice}
        onClose={() => setConsentModalOpen(false)}
      />

      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
          Practice interviews with grounded rubric scoring
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          LangGraph picks questions from the role bank — shuffle for a new prompt, then start when
          you are ready. After each answer the graph advances to the next question.
        </p>
        {feedStatus && role && feedStatus.bank_counts[role] != null && (
          <p className="mt-2 text-xs text-slate-500">
            Question bank: {feedStatus.bank_counts[role]} prompts for this role
            {feedStatus.synced_at
              ? ` · external feed synced ${new Date(feedStatus.synced_at).toLocaleDateString()}`
              : ""}
            {dailyStatus?.theme_today
              ? ` · daily theme: ${dailyStatus.theme_today}`
              : ""}
            {dailyStatus?.mode === "agentic"
              ? ` · LangGraph agents (${dailyStatus.llm_calls_last_run ?? "?"} LLM calls)`
              : dailyStatus?.total
                ? ` · ${dailyStatus.total} LLM questions cached`
                : ""}
          </p>
        )}
        {!hasApiBackend() && (
          <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            Demo mode — connect a backend API for full Whisper + LangGraph scoring.
          </p>
        )}
        {hasApiBackend() && !signedIn && (
          <p className="mt-2 rounded-lg border border-coach-mist bg-coach-sky/20 px-3 py-2 text-xs text-slate-700">
            <a href="/login" className="font-medium text-coach-blue hover:underline">
              Sign in
            </a>{" "}
            with Google, Facebook, or email — history saved in Supabase Postgres.
          </p>
        )}
        {hasApiBackend() && apiHealth?.status === "ok" && (
          <p className="mt-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900">
            API connected ({getApiBaseUrl().replace(/^https?:\/\//, "")}) · {apiHealth.deploy_profile}{" "}
            · LLM {apiHealth.llm_provider} · Whisper {apiHealth.whisper_backend}
            {apiHealth.langsmith ? " · LangSmith on" : ""}
          </p>
        )}
      </header>

      <div className="grid gap-8 lg:grid-cols-12 lg:items-start">
        <section className="space-y-5 lg:col-span-5 xl:col-span-4">
          <div>
            <label className="mb-1 block text-sm text-slate-600">Role</label>
            <select
              value={role}
              onChange={(e) => void handleRoleChange(e.target.value)}
              disabled={loadingCatalog || loading}
              className="w-full rounded-xl border border-coach-mist bg-white/90 px-4 py-2.5 text-slate-800 disabled:opacity-50"
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
            {role && !interviewStarted && (
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
              {role && (
                <div className="rounded-xl border border-coach-mist/80 bg-white/80 p-4 shadow-sm backdrop-blur-sm">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Up next</p>
                    <button
                      type="button"
                      onClick={shufflePreview}
                      disabled={previewLoading || loading}
                      className="shrink-0 rounded-lg border border-coach-mist px-2.5 py-1 text-xs text-coach-blue hover:bg-coach-sky/15 disabled:opacity-50"
                    >
                      {previewLoading ? "Loading..." : "Shuffle"}
                    </button>
                  </div>
                  {previewQuestion ? (
                    <>
                      <p className="mt-2 text-slate-800">{previewQuestion.question}</p>
                      {previewQuestion.competency && (
                        <p className="mt-2 text-xs text-slate-500">
                          {previewQuestion.competency.replace(/_/g, " ")}
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="mt-2 text-sm text-slate-500">
                      {previewLoading ? "Drawing from question bank..." : "Loading question..."}
                    </p>
                  )}
                </div>
              )}
              <button
                type="button"
                onClick={startInterview}
                disabled={loading || previewLoading || !role || !previewQuestion}
                className="w-full rounded-xl bg-coach-blue py-3 font-semibold text-white shadow-sm hover:bg-coach-cyan disabled:opacity-50"
              >
                {loading ? "Starting..." : "Start interview"}
              </button>
            </>
          ) : (
            <>
              {displayedQuestion && !sessionComplete && (
                <div className="rounded-xl border border-coach-blue/25 bg-coach-blue/5 p-4">
                  <p className="text-xs uppercase tracking-wide text-coach-violet">
                    Question {displayedQuestion.turn_number}
                    {displayedQuestion.competency
                      ? ` · ${displayedQuestion.competency.replace(/_/g, " ")}`
                      : ""}
                  </p>
                  <p className="mt-2 text-slate-800">{displayedQuestion.question}</p>
                </div>
              )}

              {sessionComplete ? (
                <p className="rounded-xl border border-coach-cyan/30 bg-coach-cyan/10 px-4 py-3 text-sm text-coach-blue">
                  Interview complete. Change role or shuffle for a new practice question.
                </p>
              ) : (
                <>
                  <VideoRecorder onRecorded={onRecorded} disabled={loading} />

                  {videoBlob && (
                    <p className="text-sm text-coach-cyan">
                      Recording ready ({Math.round(videoBlob.size / 1024)} KB)
                    </p>
                  )}

                  <button
                    type="button"
                    onClick={submitAnswer}
                    disabled={loading || !videoBlob}
                    className="w-full rounded-xl bg-coach-violet py-3 font-semibold text-white shadow-sm hover:bg-coach-blue disabled:opacity-50"
                  >
                    {loading ? "Transcribing & grading..." : "Submit video answer"}
                  </button>
                </>
              )}

              {transcript && (
                <div className="rounded-xl border border-coach-mist/70 bg-coach-sky/10 p-4">
                  <p className="text-xs uppercase text-slate-500">Your answer (transcript)</p>
                  <p className="mt-2 text-sm text-slate-700">{transcript}</p>
                </div>
              )}

              {turnGrading && (
                <div className="rounded-xl border border-coach-mist/70 bg-white/80 p-3 text-sm shadow-sm">
                  <p className="font-medium text-coach-violet">
                    Agent score: {String((turnGrading as { score?: number }).score ?? "?")}/5
                  </p>
                  <p className="mt-1 text-slate-600">
                    {(turnGrading as { feedback?: string }).feedback}
                  </p>
                </div>
              )}

              {agentTrace.length > 0 && (
                <div className="text-xs text-slate-500">
                  <p className="mb-1 font-medium text-slate-600">LangGraph trace</p>
                  <ul className="space-y-0.5">
                    {agentTrace.map((t, i) => (
                      <li key={`${t.node}-${i}`}>
                        <span className="text-coach-blue">{t.node}</span>: {t.decision}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}
        </section>

        <section className="w-full min-w-0 lg:col-span-7 xl:col-span-8 lg:sticky lg:top-6">
          {demoMode && result && (
            <p className="mb-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
              Sample rubric scores — not from your recording.
            </p>
          )}
          {result ? (
            <ResultsPanel result={result as never} />
          ) : (
            <div className="flex min-h-[240px] w-full items-center justify-center rounded-2xl border border-dashed border-coach-mist bg-coach-sky/10 px-8 py-10 text-center lg:min-h-[360px]">
              <p className="max-w-lg text-base leading-relaxed text-slate-500">
                Rubric-grounded scores appear here after you submit a video answer
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
