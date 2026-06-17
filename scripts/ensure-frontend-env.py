"""Merge missing frontend env keys from .env.local.example (idempotent)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "frontend" / ".env.local"
EXAMPLE = ROOT / "frontend" / ".env.local.example"

KEYS_FROM_EXAMPLE = (
    "NEXT_PUBLIC_GOOGLE_CLIENT_ID",
    "NEXT_PUBLIC_BACKEND_FACEBOOK_OAUTH",
    "NEXT_PUBLIC_API_URL",
)


def parse_env(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, val = s.partition("=")
        out[key.strip()] = val.strip()
    return out


def main() -> int:
    if not EXAMPLE.exists():
        return 0
    if not ENV.exists():
        ENV.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Created {ENV.name} from .env.local.example")
        return 0

    example = parse_env(EXAMPLE.read_text(encoding="utf-8"))
    current = parse_env(ENV.read_text(encoding="utf-8"))
    lines = ENV.read_text(encoding="utf-8").splitlines()
    changed: list[str] = []

    for key in KEYS_FROM_EXAMPLE:
        if current.get(key) or not example.get(key):
            continue
        lines.append(f"{key}={example[key]}")
        changed.append(key)

    if not changed:
        return 0

    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Updated frontend/.env.local:", ", ".join(changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
