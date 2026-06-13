"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ClientDeliveryMetrics, FaceHudTracker } from "@/lib/faceHud";

type Props = {
  onRecorded: (blob: Blob, metrics?: ClientDeliveryMetrics) => void;
  disabled?: boolean;
};

export default function VideoRecorder({ onRecorded, disabled }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const hudRef = useRef<FaceHudTracker | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveEyePct, setLiveEyePct] = useState<number | null>(null);

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
        if (videoRef.current) {
          videoRef.current.srcObject = s;
        }
      })
      .catch(() => setError("Camera/microphone permission denied."));

    return () => {
      active = false;
      stream?.getTracks().forEach((t) => t.stop());
      hudRef.current?.stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startRecording = useCallback(async () => {
    if (!stream || !videoRef.current) return;
    chunksRef.current = [];
    setLiveEyePct(null);
    const hud = new FaceHudTracker();
    hudRef.current = hud;
    await hud.start(videoRef.current, setLiveEyePct);

    const recorder = new MediaRecorder(stream, { mimeType: "video/webm" });
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.onstop = () => {
      const metrics = hudRef.current?.stop();
      hudRef.current = null;
      setLiveEyePct(null);
      const blob = new Blob(chunksRef.current, { type: "video/webm" });
      onRecorded(blob, metrics);
    };
    recorder.start();
    mediaRecorderRef.current = recorder;
    setRecording(true);
  }, [stream, onRecorded]);

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  }, []);

  return (
    <div className="space-y-3">
      <div className="relative overflow-hidden rounded-2xl border border-coach-mist bg-black aspect-video shadow-sm">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="h-full w-full object-cover"
        />
        {recording && (
          <>
            <span className="absolute top-3 left-3 flex items-center gap-2 rounded-full bg-red-600/90 px-3 py-1 text-xs font-medium text-white">
              <span className="h-2 w-2 animate-pulse rounded-full bg-white" />
              REC
            </span>
            {liveEyePct !== null && (
              <span className="absolute top-3 right-3 rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-emerald-300">
                Eye contact ~{Math.round(liveEyePct)}%
              </span>
            )}
          </>
        )}
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {recording && (
        <p className="text-xs text-slate-500">
          Live behavioral HUD runs in your browser (no extra API cost).
        </p>
      )}
      <div className="flex gap-3">
        {!recording ? (
          <button
            type="button"
            onClick={startRecording}
            disabled={disabled || !stream}
            className="rounded-xl bg-coach-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-coach-cyan disabled:opacity-50"
          >
            Start Recording
          </button>
        ) : (
          <button
            type="button"
            onClick={stopRecording}
            className="rounded-xl bg-red-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-400"
          >
            Stop & Use Recording
          </button>
        )}
      </div>
    </div>
  );
}
