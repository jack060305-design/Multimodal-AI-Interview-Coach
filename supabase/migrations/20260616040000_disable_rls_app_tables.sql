-- Backend API uses interview_coach_app (pooler) — not Supabase client RLS.
ALTER ROLE interview_coach_app BYPASSRLS;

ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE evaluations DISABLE ROW LEVEL SECURITY;
