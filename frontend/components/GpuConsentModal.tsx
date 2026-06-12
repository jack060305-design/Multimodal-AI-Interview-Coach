"use client";

type GpuStatus = {
  gpu_available: boolean;
  gpu_name: string | null;
  vendor: string;
  requires_prompt: boolean;
  stored_consent: string | null;
  resolved_consent: string;
};

type Props = {
  open: boolean;
  gpu: GpuStatus | null;
  onChoice: (choice: "once" | "always" | "never") => void;
  onClose: () => void;
};

export default function GpuConsentModal({ open, gpu, onChoice, onClose }: Props) {
  if (!open || !gpu?.gpu_available) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-coach-violet/20 p-4 backdrop-blur-sm">
      <div
        className="w-full max-w-md rounded-2xl border border-coach-mist bg-white p-6 shadow-xl"
        role="dialog"
        aria-labelledby="gpu-consent-title"
      >
        <h2 id="gpu-consent-title" className="text-lg font-semibold text-slate-900">
          Use GPU for faster analysis?
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          Detected: <span className="font-medium text-slate-800">{gpu.gpu_name || gpu.vendor}</span>.
          Whisper transcription and embeddings can run on your graphics card for better speed.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          Choose CPU only if you prefer lower GPU usage or are on battery.
        </p>

        <div className="mt-6 flex flex-col gap-2">
          <button
            type="button"
            onClick={() => onChoice("once")}
            className="rounded-xl bg-coach-blue py-2.5 text-sm font-semibold text-white hover:bg-coach-cyan"
          >
            Just this once
          </button>
          <button
            type="button"
            onClick={() => onChoice("always")}
            className="rounded-xl border border-coach-violet/30 bg-coach-violet/10 py-2.5 text-sm font-semibold text-coach-violet hover:bg-coach-violet/15"
          >
            Always allow GPU
          </button>
          <button
            type="button"
            onClick={() => onChoice("never")}
            className="rounded-xl border border-coach-mist py-2.5 text-sm text-slate-700 hover:bg-coach-sky/10"
          >
            CPU only — don&apos;t use GPU
          </button>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="mt-4 w-full text-center text-xs text-slate-500 hover:text-slate-700"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

export type { GpuStatus };
