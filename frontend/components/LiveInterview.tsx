"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchJson, getApiBaseUrl, hasApiBackend } from "@/lib/api";

type AgentTrace = { node: string; decision: string };

type Props = {
  role: string;
  disabled?: boolean;
  onSessionEnd?: (summary: Record<string, unknown>) => void;
};

export default function LiveInterview({ role, disabled, onSessionEnd }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [grading, setGrading] = useState<Record<string, unknown> | null>(null);
  const [trace, setTrace] = useState<AgentTrace[]>([]);
  const [status, setStatus] = useState<"idle" | "connecting" | "live" | "done">("idle");
  const [error, setError] = useState<string | null>(null);
  const [turnNumber, setTurnNumber] = useState(0);

  useEffect(() => {
    let active = true;
    navigator.mediaDevices
      .getUserMedia({ video: true, audio: true })
      .then((s) => {
        if (!active) {
          s.getTracks().forEach((t) => t.stop());
          return;
        }
        setStream(s);
        if (videoRef.current) videoRef.current.srcObject = s;
      })
      .catch(() => setError("Camera/microphone required for live interview."));
    return () => {
      active = false;
      stream?.getTracks().forEach((t) => t.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const closeWs = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  useEffect(() => () => closeWs(), [closeWs]);

  const connectWs = useCallback(
    (sid: string) => {
      if (!hasApiBackend()) return;
      const base = getApiBaseUrl().replace(/^http/, "ws");
      const ws = new WebSocket(`${base}/ws/interview/${sid}`);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: "start" }));
      };

      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data);
        if (msg.type === "question") {
          setQuestion(msg.question || "");
          setTurnNumber(msg.turn_number || 0);
          setTrace(msg.agent_trace || []);
          setStatus("live");
          setAnswer("");
          setGrading(null);
        }
        if (msg.type === "turn_result") {
          setGrading(msg.grading || null);
          setTrace(msg.agent_trace || []);
          setTurnNumber(msg.turn_number || 0);
        }
        if (msg.type === "session_complete") {
          setStatus("done");
          onSessionEnd?.(msg.summary || {});
        }
        if (msg.type === "error") {
          setError(msg.message || "WebSocket error");
        }
      };

      ws.onerror = () => setError("Live stream connection failed.");
    },
    [onSessionEnd]
  );

  const startSession = async () => {
    if (!role || !hasApiBackend()) {
      setError("Live interview requires the FastAPI backend (setup.cmd).");
      return;
    }
    setError(null);
    setStatus("connecting");

    try {
      const created = await fetchJson<{ session_id: string }>("/interview/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role, max_turns: 5, difficulty: 3 }),
      });
      setSessionId(created.session_id);
      connectWs(created.session_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start session");
      setStatus("idle");
    }
  };

  const submitAnswer = () => {
    if (!answer.trim() || !wsRef.current) return;
    wsRef.current.send(JSON.stringify({ type: "answer", answer: answer.trim() }));
  };

  return (
    <div className="space-y-4 rounded-2xl border border-indigo-500/30 bg-indigo-500/5 p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-indigo-300">Live Interview (LangGraph 5-agent)</h3>
        <span className="text-xs text-slate-500">
          Friday-style · WebSocket stream
        </span>
      </div>

      <div className="overflow-hidden rounded-xl bg-black/40">
        <video ref={videoRef} autoPlay muted playsInline className="aspect-video w-full object-cover" />
      </div>

      {status === "idle" && (
        <button
          type="button"
          disabled={disabled || !role}
          onClick={startSession}
          className="w-full rounded-xl bg-indigo-500 py-2.5 font-medium hover:bg-indigo-400 disabled:opacity-50"
        >
          Start live interview
        </button>
      )}

      {status !== "idle" && question && (
        <div className="rounded-xl border border-slate-700 bg-slate-900/80 p-4">
          <p className="text-xs uppercase text-slate-500">Turn {turnNumber}</p>
          <p className="mt-1 text-slate-100">{question}</p>
        </div>
      )}

      {status === "live" && (
        <>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Type or paste your answer (voice → text coming soon)..."
            rows={4}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={submitAnswer}
            disabled={!answer.trim()}
            className="w-full rounded-xl bg-emerald-500 py-2.5 font-medium hover:bg-emerald-400 disabled:opacity-50"
          >
            Submit answer
          </button>
        </>
      )}

      {grading && (
        <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-3 text-sm">
          <p className="font-medium text-emerald-400">
            Score: {String((grading as { score?: number }).score ?? "?")}/5
          </p>
          <p className="mt-1 text-slate-400">
            {(grading as { feedback?: string }).feedback}
          </p>
        </div>
      )}

      {trace.length > 0 && (
        <div className="text-xs text-slate-500">
          <p className="mb-1 font-medium text-slate-400">Agent trace</p>
          <ul className="space-y-0.5">
            {trace.map((t, i) => (
              <li key={`${t.node}-${i}`}>
                <span className="text-indigo-400">{t.node}</span>: {t.decision}
              </li>
            ))}
          </ul>
        </div>
      )}

      {sessionId && (
        <p className="text-xs text-slate-600">Session: {sessionId.slice(0, 8)}…</p>
      )}

      {status === "done" && (
        <p className="text-sm text-emerald-400">Session complete. Switch to Record mode for video rubric scoring.</p>
      )}

      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  );
}
