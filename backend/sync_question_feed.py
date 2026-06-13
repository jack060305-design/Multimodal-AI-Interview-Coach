"""CLI: sync external interview question feeds."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.question_feed_sync import sync_question_feed


def main() -> None:
    force = "--force" in sys.argv
    result = sync_question_feed(force=force)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
