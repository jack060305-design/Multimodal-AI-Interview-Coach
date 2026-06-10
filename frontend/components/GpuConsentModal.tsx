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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div
        className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-xl"
        role="dialog"
        aria-labelledby="gpu-consent-title"
      >
        <h2 id="gpu-consent-title" className="text-lg font-semibold text-white">
          Use GPU for faster analysis?
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-400">
          Detected: <span className="text-slate-200">{gpu.gpu_name || gpu.vendor}</span>.
          Whisper transcription and embeddings can run on your graphics card for better speed.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          Choose CPU only if you prefer lower GPU usage or are on battery.
        </p>

        <div className="mt-6 flex flex-col gap-2">
          <button
            type="button"
            onClick={() => onChoice("once")}
            className="rounded-xl bg-indigo-500 py-2.5 text-sm font-semibold hover:bg-indigo-400"
          >
            Just this once
          </button>
          <button
            type="button"
            onClick={() => onChoice("always")}
            className="rounded-xl border border-indigo-500/50 bg-indigo-500/10 py-2.5 text-sm font-semibold text-indigo-300 hover:bg-indigo-500/20"
          >
            Always allow GPU
          </button>
          <button
            type="button"
            onClick={() => onChoice("never")}
            className="rounded-xl border border-slate-600 py-2.5 text-sm text-slate-300 hover:bg-slate-800"
          >
            CPU only — don&apos;t use GPU
          </button>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="mt-4 w-full text-center text-xs text-slate-500 hover:text-slate-400"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

export type { GpuStatus };
