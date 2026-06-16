"""Update GitHub DATABASE_URL to Supabase pooler (IPv4-friendly for Azure)."""
from __future__ import annotations

import secrets
import string
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

PROJECT_REF = "ttgdcomdfqmbqqiywoxw"
REPO = "jack060305-design/Multimodal-AI-Interview-Coach"
ROLE = "interview_coach_app"
POOLER_HOST = "aws-1-us-west-2.pooler.supabase.com"
# Session mode (5432) also works; transaction mode (6543) needs NullPool in database.py.
POOLER_PORT = 6543
ROOT = Path(__file__).resolve().parents[1]


def run_sql(sql: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as tmp:
        tmp.write(sql)
        tmp_path = tmp.name
    try:
        proc = subprocess.run(
            f'npx supabase db query --linked -f "{tmp_path}"',
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
            shell=True,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    combined = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0 and "already exists" not in combined.lower():
        print(combined, file=sys.stderr)
        raise SystemExit(proc.returncode)


def main() -> int:
    password = "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(32)
    )
    safe_pw = password.replace("'", "''")

    create = subprocess.run(
        f'npx supabase db query --linked "CREATE ROLE {ROLE} WITH LOGIN PASSWORD \'{safe_pw}\';"',
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        shell=True,
    )
    combined = (create.stdout or "") + (create.stderr or "")
    if create.returncode != 0 and "already exists" not in combined.lower():
        run_sql(f"ALTER ROLE {ROLE} WITH PASSWORD '{safe_pw}';")
    elif "already exists" in combined.lower():
        run_sql(f"ALTER ROLE {ROLE} WITH PASSWORD '{safe_pw}';")

    run_sql(
        "\n".join(
            [
                f"GRANT CONNECT ON DATABASE postgres TO {ROLE};",
                f"GRANT USAGE ON SCHEMA public TO {ROLE};",
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {ROLE};",
                f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {ROLE};",
                f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {ROLE};",
                f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                f"GRANT USAGE, SELECT ON SEQUENCES TO {ROLE};",
                f"ALTER ROLE {ROLE} BYPASSRLS;",
                "ALTER TABLE users DISABLE ROW LEVEL SECURITY;",
                "ALTER TABLE evaluations DISABLE ROW LEVEL SECURITY;",
            ]
        )
    )

    user = f"{ROLE}.{PROJECT_REF}"
    encoded = urllib.parse.quote(password, safe="")
    # Use postgresql:// (not postgresql+psycopg2://) — Azure env vars break on '+' in values.
    database_url = (
        f"postgresql://{user}:{encoded}@{POOLER_HOST}:{POOLER_PORT}/postgres"
        "?sslmode=require"
    )

    test_script = ROOT / "scripts" / "_test_pooler_conn.py"
    test_proc = subprocess.run(
        [sys.executable, str(test_script), database_url],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if test_proc.returncode != 0:
        print(test_proc.stderr or test_proc.stdout, file=sys.stderr)
        return test_proc.returncode

    proc = subprocess.run(
        ["gh", "secret", "set", "DATABASE_URL", "--repo", REPO],
        input=database_url,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode

    print(f"DATABASE_URL updated to Supabase pooler (port {POOLER_PORT}).")
    subprocess.run(
        ["gh", "workflow", "run", "Deploy to Azure Container Apps", "--repo", REPO],
        check=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
