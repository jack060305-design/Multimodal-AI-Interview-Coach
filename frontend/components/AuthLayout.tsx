export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="auth-shell min-h-screen bg-coach-page bg-fixed px-4 py-10 sm:py-16">
      <div className="mx-auto w-full max-w-md">
        <header className="mb-8 text-center">
          <p className="auth-title-violet text-xs font-semibold uppercase tracking-wider text-coach-violet">
            Multimodal AI
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Interview Coach
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Sign in to practice interviews and save your scores.
          </p>
        </header>
        <div className="auth-card rounded-2xl border border-coach-mist/80 bg-white/95 p-6 shadow-xl shadow-coach-blue/5 backdrop-blur-sm sm:p-8">
          {children}
        </div>
      </div>
    </div>
  );
}
