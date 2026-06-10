"use client";

type PerformanceCategory = {
  score: number;
  label: string;
  summary: string;
  signals: string[];
};

type EvaluationResult = {
  evaluation_id?: string;
  overall_score: number;
  transcript: string;
  performance: {
    delivery: PerformanceCategory;
    communication: PerformanceCategory;
    technical_depth: PerformanceCategory;
  };
  metrics: {
    eye_contact: { score: number; percentage: number; comment: string };
    filler_words: {
      score: number;
      count: number;
      rate: number;
      top_fillers: string[];
      wpm: number;
    };
    confidence: { score: number };
    technical_depth: { score: number; comment: string };
    response_quality: { score: number; comment: string };
  };
  improvement_suggestions: string[];
  video_storage_key?: string | null;
};

export default function ResultsPanel({ result }: { result: EvaluationResult }) {
  const m = result.metrics;
  const p = result.performance;

  return (
    <div className="space-y-6 rounded-2xl border border-slate-700 bg-slate-900/60 p-6">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-sm text-slate-400">Overall Score</p>
          <p className="text-5xl font-bold text-emerald-400">{result.overall_score}</p>
        </div>
      </div>

      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-indigo-400">
          Performance Pillars
        </h3>
        <div className="grid gap-4 sm:grid-cols-3">
          <PillarCard category={p.delivery} accent="bg-sky-500" />
          <PillarCard category={p.communication} accent="bg-violet-500" />
          <PillarCard category={p.technical_depth} accent="bg-emerald-500" />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Signal Breakdown
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <MetricCard title="Eye Contact" score={m.eye_contact.score} detail={`${m.eye_contact.percentage}%`} />
          <MetricCard title="Confidence" score={m.confidence.score} />
          <MetricCard title="Filler Words" score={m.filler_words.score} detail={`${m.filler_words.rate}% (${m.filler_words.count})`} />
          <MetricCard title="Speaking Pace" score={0} detail={`${m.filler_words.wpm} WPM`} hideBar />
          <MetricCard title="Response Quality" score={m.response_quality.score} />
          <MetricCard title="Technical Depth" score={m.technical_depth.score} />
        </div>
      </section>

      <section>
        <h3 className="mb-2 font-semibold text-slate-200">Comments</h3>
        <ul className="space-y-1 text-sm text-slate-400">
          <li>{m.eye_contact.comment}</li>
          <li>{m.technical_depth.comment}</li>
          <li>{m.response_quality.comment}</li>
        </ul>
      </section>

      <section>
        <h3 className="mb-2 font-semibold text-slate-200">Coaching Suggestions</h3>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          {result.improvement_suggestions.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className="mb-2 font-semibold text-slate-200">Transcript</h3>
        <p className="rounded-xl bg-slate-950 p-4 text-sm leading-relaxed text-slate-400">
          {result.transcript || "(empty)"}
        </p>
      </section>
    </div>
  );
}

function PillarCard({
  category,
  accent,
}: {
  category: PerformanceCategory;
  accent: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
      <div className="flex items-center justify-between">
        <span className="font-medium text-slate-200">{category.label}</span>
        <span className="text-2xl font-bold text-white">{category.score}</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full ${accent} transition-all`}
          style={{ width: `${Math.min(100, category.score)}%` }}
        />
      </div>
      <p className="mt-2 text-xs leading-relaxed text-slate-500">{category.summary}</p>
    </div>
  );
}

function MetricCard({
  title,
  score,
  detail,
  hideBar,
}: {
  title: string;
  score: number;
  detail?: string;
  hideBar?: boolean;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
      <div className="flex justify-between text-sm">
        <span className="text-slate-400">{title}</span>
        <span className="font-semibold">{hideBar ? detail : score}</span>
      </div>
      {!hideBar && (
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-indigo-500 transition-all"
            style={{ width: `${Math.min(100, score)}%` }}
          />
        </div>
      )}
      {detail && !hideBar && <p className="mt-1 text-xs text-slate-500">{detail}</p>}
    </div>
  );
}
