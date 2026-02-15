"""CLI entry point: astro --ask '<question>'"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from astro.db import DataLayer
from astro.agent import Agent


def _find_env() -> Path | None:
    """Walk up from CWD looking for .env."""
    current = Path.cwd()
    for _ in range(6):
        candidate = current / ".env"
        if candidate.exists():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return None


def _find_warehouse() -> Path | None:
    """Walk up from CWD looking for warehouse/data.duckdb."""
    current = Path.cwd()
    for _ in range(6):
        candidate = current / "warehouse" / "data.duckdb"
        if candidate.exists():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return None


def main():
    parser = argparse.ArgumentParser(
        prog="astro",
        description="Query your data warehouse using natural language.",
    )
    parser.add_argument(
        "--ask",
        required=True,
        help="Question to ask about your data.",
    )
    parser.add_argument(
        "--db",
        help="Path to DuckDB file (default: auto-detect warehouse/data.duckdb).",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.0-flash",
        help="Gemini model to use (default: gemini-2.0-flash).",
    )
    args = parser.parse_args()

    # --- load .env from project root ---
    env_path = _find_env()
    if env_path:
        load_dotenv(env_path)

    # --- resolve database ---
    if args.db:
        db_path = Path(args.db)
    else:
        db_path = _find_warehouse()
    if not db_path or not db_path.exists():
        print("Error: Could not find DuckDB database.", file=sys.stderr)
        print("  Run from the project root or pass --db <path>.", file=sys.stderr)
        sys.exit(1)

    # --- resolve API key ---
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: Set GEMINI_API_KEY or GOOGLE_API_KEY.", file=sys.stderr)
        sys.exit(1)
    api_key = api_key.strip()
    key_source = "GEMINI_API_KEY" if os.environ.get("GEMINI_API_KEY") else "GOOGLE_API_KEY"
    print(f"  Using key from ${key_source}: {api_key[:8]}...{api_key[-4:]}", file=sys.stderr)

    # --- run ---
    dl = DataLayer(db_path)
    try:
        agent = Agent(dl, api_key, model=args.model)
        print(f"\n  Analyzing: {args.ask}\n", file=sys.stderr)
        answer = agent.ask(args.ask)
        print(f"\n{answer}")
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        dl.close()


if __name__ == "__main__":
    main()
