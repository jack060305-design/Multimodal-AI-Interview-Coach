"""Ensure backend/.env has Supabase auth + DB_ENABLED for local login (idempotent)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "backend" / ".env"
EXAMPLE = ROOT / "backend" / ".env.example"

REQUIRED = {
    "DB_ENABLED": "true",
    "DEPLOY_PROFILE": "local",
    "SUPABASE_URL": "https://ttgdcomdfqmbqqiywoxw.supabase.co",
    "SUPABASE_ANON_KEY": "sb_publishable_oAWTc_IxskWk11vaU7JzOg_74RccE7t",
    "DATA_DIR": "./data",
}


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
    if not ENV.exists():
        if EXAMPLE.exists():
            ENV.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Created {ENV.name} from .env.example")
        else:
            ENV.write_text("", encoding="utf-8")

    lines = ENV.read_text(encoding="utf-8").splitlines()
    current = parse_env("\n".join(lines))
    changed: list[str] = []

    for key, val in REQUIRED.items():
        if current.get(key) != val:
            changed.append(key)

    if not changed:
        return 0

    for key, val in REQUIRED.items():
        found = False
        new_lines: list[str] = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={val}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"{key}={val}")
        lines = new_lines

    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Updated backend/.env:", ", ".join(changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
