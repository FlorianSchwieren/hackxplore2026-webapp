#!/usr/bin/env python3
"""Run layered E2E validation (unit + API + optional live stack)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], env: dict | None = None) -> int:
    print(f"\n$ {' '.join(cmd)}")
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.call(cmd, cwd=ROOT, env=merged)


def main() -> int:
    parser = argparse.ArgumentParser(description="Baumpate E2E validation runner")
    parser.add_argument("--with-db", action="store_true", help="Require DATABASE_URL and run DB tests")
    args = parser.parse_args()

    code = run(["uv", "run", "pytest", "tests/", "-q", "--tb=short"])
    if code != 0:
        return code

    if args.with_db and not os.getenv("DATABASE_URL"):
        print("ERROR: --with-db set but DATABASE_URL is missing", file=sys.stderr)
        return 2

    if os.getenv("DATABASE_URL"):
        print("\nDATABASE_URL present — DB integration tests included in pytest run above.")
    else:
        print("\nDATABASE_URL not set — DB integration tests were skipped.")

    print("\nNext manual steps for full browser E2E:")
    print("  1. cp .env.example .env  # add DATABASE_URL + Supabase keys")
    print("  2. make migrate && make seed")
    print("  3. DEV_AUTH_DISABLED=true make run")
    print("  4. cd hackxplore2026-webapp && npm i && VITE_USE_MOCK_DATA=false npm run dev")
    print("  5. agent-browser open http://localhost:5173")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
