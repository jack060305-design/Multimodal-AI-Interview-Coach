"""Preview auth/database fix locally — no git push, no OpenAI key required."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

os.environ.setdefault("DB_ENABLED", "false")
os.environ.setdefault("DEPLOY_PROFILE", "local")
os.environ.setdefault("LLM_PROVIDER", "local")
os.environ.setdefault("VECTOR_STORE", "memory")
os.environ.setdefault("DAILY_QUESTIONS_ENABLED", "false")

from fastapi.testclient import TestClient  # noqa: E402


def main() -> int:
    patches = [
        patch("main.init_db"),
        patch("main.ensure_s3_bucket"),
        patch("main.bootstrap_vector_index"),
        patch("main.maybe_sync_on_startup"),
        patch("main.start_daily_scheduler"),
        patch("main.stop_daily_scheduler"),
        patch("main.EvaluationOrchestrator", return_value=MagicMock()),
        patch("main.InterviewSessionService", return_value=MagicMock()),
    ]
    for p in patches:
        p.start()
    try:
        import importlib
        import config

        importlib.reload(config)
        config.get_settings.cache_clear()

        import main as main_mod

        importlib.reload(main_mod)
        client = TestClient(main_mod.app)

        print("=== Local preview (fixed code, no deploy) ===\n")

        health = client.get("/health").json()
        print("/health:")
        print(json.dumps(health, indent=2))

        checks: list[str] = []
        if health.get("db_connected") is False:
            checks.append("OK  db_connected=false (DB off)")
        if health.get("auth_enabled") is False:
            checks.append("OK  auth_enabled=false (no false promise)")
        if "db_error" in health:
            checks.append("OK  db_error field present")

        me = client.get("/auth/me")
        if me.status_code == 401:
            checks.append("OK  /auth/me -> 401 without token")
        else:
            checks.append(f"FAIL /auth/me -> {me.status_code}")

        print("\nChecks:")
        for c in checks:
            print(" ", c)

        # Scenario: DB enabled but bad URL
        os.environ["DB_ENABLED"] = "true"
        os.environ["DATABASE_URL"] = "postgresql://bad:bad@127.0.0.1:1/none"
        importlib.reload(config)
        config.get_settings.cache_clear()
        import db.database as db_mod

        importlib.reload(db_mod)
        db_mod.init_db()
        status = db_mod.db_status()
        print("\nDB fail scenario (bad DATABASE_URL):")
        print(json.dumps(status, indent=2))
        if status["configured"] and not status["connected"] and status["error"]:
            print(" OK  captures connection error:", status["error"][:80])

        print("\n--- Next: full UI test (no git) ---")
        print("  1. setup.cmd")
        print("  2. http://localhost:3000/login")
        print("  3. For history: set real DATABASE_URL in backend/.env, DB_ENABLED=true")
        return 0
    finally:
        for p in reversed(patches):
            p.stop()


if __name__ == "__main__":
    raise SystemExit(main())
