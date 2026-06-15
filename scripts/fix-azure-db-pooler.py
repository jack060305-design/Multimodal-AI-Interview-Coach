"""Update GitHub DATABASE_URL to Supabase pooler (IPv4-friendly for Azure)."""
from __future__ import annotations

import secrets
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

PROJECT_REF = "ttgdcomdfqmbqqiywoxw"
REPO = "jack060305-design/Multimodal-AI-Interview-Coach"
ROLE = "interview_coach_app"
POOLER_HOST = "aws-1-us-west-2.pooler.supabase.com"
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
    password = secrets.token_urlsafe(24)
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
            ]
        )
    )

    user = f"{ROLE}.{PROJECT_REF}"
    encoded = urllib.parse.quote(password, safe="")
    database_url = (
        f"postgresql+psycopg2://{user}:{encoded}@{POOLER_HOST}:6543/postgres"
        "?sslmode=require"
    )

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

    print("DATABASE_URL updated to Supabase pooler (port 6543).")
    subprocess.run(
        ["gh", "workflow", "run", "Deploy to Azure Container Apps", "--repo", REPO],
        check=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
