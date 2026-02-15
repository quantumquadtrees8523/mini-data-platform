"""CLI entry point: astro --ask '<question>' or interactive chat."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import ANSI

from astro.db import DataLayer
from astro.agent import Agent
from astro import fmt


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


def _chat_loop(agent: Agent):
    """Interactive REPL — read questions from stdin until quit or EOF."""
    print(
        f"\n  {fmt.DIM}Type a question, or 'quit' to exit.{fmt.RESET}\n",
        file=sys.stderr,
    )

    session = PromptSession()

    while True:
        try:
            question = session.prompt(ANSI(fmt.prompt())).strip()
        except (EOFError, KeyboardInterrupt):
            print(fmt.bye(), file=sys.stderr)
            break
        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print(fmt.bye(), file=sys.stderr)
            break
        print(file=sys.stderr)
        try:
            answer = agent.ask(question)
            print(fmt.answer_box(answer))
            print(fmt.sources_section(agent.get_sources()))
            print()
        except KeyboardInterrupt:
            print(
                f"\n  {fmt.DIM}(interrupted — ask another question or 'quit'){fmt.RESET}\n",
                file=sys.stderr,
            )
        except Exception as e:
            print(fmt.error(str(e)), file=sys.stderr)
            print(file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        prog="astro",
        description="Query your data warehouse using natural language.",
    )
    parser.parse_args()

    # --- load .env from project root ---
    env_path = _find_env()
    if env_path:
        load_dotenv(env_path)

    # --- resolve database ---
    db_path = _find_warehouse()
    if not db_path or not db_path.exists():
        print(fmt.error("Could not find DuckDB database."), file=sys.stderr)
        print(
            f"  {fmt.DIM}Run from a directory with warehouse/data.duckdb{fmt.RESET}",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- resolve API key ---
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print(fmt.error("Set GEMINI_API_KEY or GOOGLE_API_KEY."), file=sys.stderr)
        sys.exit(1)
    api_key = api_key.strip()

    # --- run ---
    model = "gemini-2.0-flash"
    dl = DataLayer(db_path)
    try:
        print(fmt.banner(str(db_path), model), file=sys.stderr)
        agent = Agent(dl, api_key, model=model)
        print(fmt.success("Connected."), file=sys.stderr)

        # Drop into interactive chat
        _chat_loop(agent)
    except KeyboardInterrupt:
        print(fmt.bye(), file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n{fmt.error(str(e))}", file=sys.stderr)
        sys.exit(1)
    finally:
        dl.close()


if __name__ == "__main__":
    main()
