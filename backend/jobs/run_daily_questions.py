"""CLI entry for Azure Container Apps Job / manual cron — runs daily question pipeline."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logging.basicConfig(level=logging.INFO)

from services.daily_question_pipeline import run_daily_question_pipeline  # noqa: E402


def main() -> int:
    force = "--force" in sys.argv
    result = run_daily_question_pipeline(force=force)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
