import Link from "next/link";

const FEATURES = [
  {
    title: "LangGraph question flow",
    body: "An agent graph picks role-based questions, grades your answer, and advances through a question bank.",
  },
  {
    title: "Multimodal analysis",
    body: "Video answers are transcribed with Whisper while delivery signals come from audio, gaze, and pacing.",
  },
  {
    title: "Rubric-grounded scoring",
    body: "Each prompt is graded against a structured rubric so feedback is specific, not generic.",
  },
];

const ROLES = ["SWE Intern", "Data Analyst", "Finance Analyst", "Product Manager"];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-10 lg:px-10 lg:py-14">
      <p className="text-sm font-medium text-coach-violet">Multimodal AI Interview Coach</p>
      <h1 className="mt-3 text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
        Practice real interviews with AI that watches, listens, and scores.
      </h1>
      <p className="mt-5 max-w-2xl text-lg leading-relaxed text-slate-600">
        A coaching workspace for job seekers. Pick a tool from the left sidebar — start with
        grounded rubric practice, with more AI interview tools coming over time.
      </p>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/practice"
          className="rounded-xl bg-coach-blue px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-coach-cyan"
        >
          Start practice interview
        </Link>
        <a
          href="#how-it-works"
          className="rounded-xl border border-coach-mist bg-white/80 px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-coach-sky/10"
        >
          How it works
        </a>
      </div>

      <section id="how-it-works" className="mt-14 grid gap-4 sm:grid-cols-3">
        {FEATURES.map((f) => (
          <div
            key={f.title}
            className="rounded-2xl border border-coach-mist/80 bg-white/70 p-5 shadow-sm backdrop-blur-sm"
          >
            <h2 className="font-semibold text-slate-900">{f.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">{f.body}</p>
          </div>
        ))}
      </section>

      <section className="mt-10 rounded-2xl border border-coach-mist/80 bg-white/70 p-6 shadow-sm backdrop-blur-sm">
        <h2 className="text-lg font-semibold text-slate-900">Supported roles</h2>
        <p className="mt-2 text-sm text-slate-600">
          Each role has its own question bank and rubric criteria.
        </p>
        <ul className="mt-4 flex flex-wrap gap-2">
          {ROLES.map((r) => (
            <li
              key={r}
              className="rounded-lg border border-coach-mist bg-coach-sky/20 px-3 py-1.5 text-sm text-slate-700"
            >
              {r}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-10 rounded-2xl border border-coach-violet/25 bg-coach-card p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-coach-violet">AI tools in this workspace</h2>
        <ul className="mt-4 space-y-3">
          <li className="flex items-start justify-between gap-4 rounded-xl border border-coach-mist/60 bg-white/80 px-4 py-3 shadow-sm">
            <div>
              <p className="font-medium text-slate-900">Practice Interview</p>
              <p className="mt-1 text-sm text-slate-600">
                Record video answers, get rubric-grounded scores, and advance through LangGraph
                questions.
              </p>
            </div>
            <Link
              href="/practice"
              className="shrink-0 text-sm font-medium text-coach-blue hover:text-coach-cyan"
            >
              Open →
            </Link>
          </li>
        </ul>
      </section>
    </div>
  );
}
