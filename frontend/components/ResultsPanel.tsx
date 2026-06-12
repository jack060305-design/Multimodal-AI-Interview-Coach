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
    <div className="w-full space-y-5 rounded-2xl border border-coach-mist/80 bg-white/80 p-5 shadow-sm backdrop-blur-sm sm:p-6 lg:p-7">
      <div className="flex w-full flex-col gap-4 rounded-xl border border-coach-cyan/30 bg-gradient-to-r from-coach-sky/25 via-white to-coach-violet/15 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
            Overall Score
          </p>
          <p className="text-5xl font-bold tabular-nums text-coach-violet sm:text-6xl">
            {result.overall_score}
          </p>
        </div>
        <div className="grid flex-1 grid-cols-3 gap-3 sm:max-w-md sm:ml-auto">
          <ScoreChip label="Delivery" score={p.delivery.score} />
          <ScoreChip label="Comm." score={p.communication.score} />
          <ScoreChip label="Technical" score={p.technical_depth.score} accent />
        </div>
      </div>

      <section className="w-full rounded-xl border border-coach-cyan/25 bg-coach-sky/10 p-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-coach-blue">
            Rubric-Grounded Technical Depth
          </h3>
          <span className="text-3xl font-bold tabular-nums text-slate-900">
            {p.technical_depth.score}
          </span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-coach-mist/50">
          <div
            className="h-full rounded-full bg-gradient-to-r from-coach-blue to-coach-cyan transition-all"
            style={{ width: `${Math.min(100, p.technical_depth.score)}%` }}
          />
        </div>
        <p className="mt-3 text-sm leading-relaxed text-slate-600">{p.technical_depth.summary}</p>
        {m.technical_depth.comment && (
          <p className="mt-2 rounded-lg bg-white/80 px-3 py-2 text-sm text-slate-700 ring-1 ring-coach-mist/60">
            {m.technical_depth.comment}
          </p>
        )}
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-coach-violet">
          Performance Pillars
        </h3>
        <div className="grid w-full gap-4 sm:grid-cols-3">
          <PillarCard category={p.delivery} accent="bg-coach-sky" />
          <PillarCard category={p.communication} accent="bg-coach-violet" />
          <PillarCard category={p.technical_depth} accent="bg-coach-cyan" />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Signal Breakdown
        </h3>
        <div className="grid w-full gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <MetricCard title="Eye Contact" score={m.eye_contact.score} detail={`${m.eye_contact.percentage}%`} />
          <MetricCard title="Confidence" score={m.confidence.score} />
          <MetricCard
            title="Filler Words"
            score={m.filler_words.score}
            detail={`${m.filler_words.rate}% (${m.filler_words.count})`}
          />
          <MetricCard title="Speaking Pace" score={0} detail={`${m.filler_words.wpm} WPM`} hideBar />
          <MetricCard title="Response Quality" score={m.response_quality.score} />
          <MetricCard title="Technical Depth" score={m.technical_depth.score} />
        </div>
      </section>

      <div className="grid w-full gap-5 lg:grid-cols-2">
        <section className="rounded-xl border border-coach-mist/70 bg-coach-sky/10 p-4">
          <h3 className="mb-2 font-semibold text-slate-800">Comments</h3>
          <ul className="space-y-2 text-sm leading-relaxed text-slate-600">
            <li>{m.eye_contact.comment}</li>
            <li>{m.response_quality.comment}</li>
          </ul>
        </section>

        <section className="rounded-xl border border-coach-mist/70 bg-coach-violet/5 p-4">
          <h3 className="mb-2 font-semibold text-slate-800">Coaching Suggestions</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-slate-700">
            {result.improvement_suggestions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </section>
      </div>

      <section className="w-full">
        <h3 className="mb-2 font-semibold text-slate-800">Transcript</h3>
        <p className="w-full rounded-xl bg-coach-mist/20 p-4 text-sm leading-relaxed text-slate-600 ring-1 ring-coach-mist/50">
          {result.transcript || "(empty)"}
        </p>
      </section>
    </div>
  );
}

function ScoreChip({
  label,
  score,
  accent,
}: {
  label: string;
  score: number;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border px-3 py-2 text-center ${
        accent
          ? "border-coach-cyan/40 bg-coach-cyan/10"
          : "border-coach-mist/70 bg-white/60"
      }`}
    >
      <p className="text-[10px] font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`text-xl font-bold tabular-nums ${accent ? "text-coach-blue" : "text-slate-900"}`}>
        {score}
      </p>
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
    <div className="rounded-xl border border-coach-mist/70 bg-white/70 p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-slate-800">{category.label}</span>
        <span className="text-2xl font-bold tabular-nums text-slate-900">{category.score}</span>
      </div>
      <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-coach-mist/50">
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
    <div className="rounded-xl border border-coach-mist/70 bg-white/70 p-4 shadow-sm">
      <div className="flex justify-between gap-2 text-sm">
        <span className="text-slate-600">{title}</span>
        <span className="shrink-0 font-semibold tabular-nums text-slate-900">{hideBar ? detail : score}</span>
      </div>
      {!hideBar && (
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-coach-mist/50">
          <div
            className="h-full rounded-full bg-gradient-to-r from-coach-blue to-coach-violet transition-all"
            style={{ width: `${Math.min(100, score)}%` }}
          />
        </div>
      )}
      {detail && !hideBar && <p className="mt-1 text-xs text-slate-500">{detail}</p>}
    </div>
  );
}
