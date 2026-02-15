"""Terminal colors and formatting — ANSI escape codes, no dependencies."""

import sys

# Detect whether stderr supports color
_COLOR = hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


def _esc(code: str) -> str:
    return f"\033[{code}m" if _COLOR else ""


RESET = _esc("0")
BOLD = _esc("1")
DIM = _esc("2")
CYAN = _esc("36")
GREEN = _esc("32")
YELLOW = _esc("33")
RED = _esc("31")
MAGENTA = _esc("35")
BOLD_CYAN = _esc("1;36")
BOLD_GREEN = _esc("1;32")
BOLD_YELLOW = _esc("1;33")
BOLD_RED = _esc("1;31")


def banner(db_path: str, model: str) -> str:
    line = f"{BOLD_CYAN}astro{RESET} {DIM}~ natural language data warehouse agent{RESET}"
    info = f"{DIM}db: {db_path}  |  model: {model}{RESET}"
    sep = f"{DIM}{'─' * 52}{RESET}"
    return f"\n{sep}\n  {line}\n  {info}\n{sep}"


def step(icon: str, msg: str) -> str:
    return f"  {CYAN}{icon}{RESET} {DIM}{msg}{RESET}"


def step_sql(sql: str) -> str:
    display = sql if len(sql) <= 100 else sql[:97] + "..."
    return f"  {CYAN}>{RESET} {DIM}Executing:{RESET} {DIM}{CYAN}{display}{RESET}"


def error(msg: str) -> str:
    return f"  {BOLD_RED}error:{RESET} {msg}"


def warning(msg: str) -> str:
    return f"  {BOLD_YELLOW}warn:{RESET} {msg}"


def success(msg: str) -> str:
    return f"  {GREEN}{msg}{RESET}"


def answer_header() -> str:
    return f"\n{BOLD_GREEN}Answer{RESET}\n"


def prompt() -> str:
    """Return the styled prompt string for input()."""
    if _COLOR:
        return f"{BOLD_CYAN}astro>{RESET} "
    return "astro> "


def sources_section(sources: list[dict]) -> str:
    """Format a Sources footer from collected tool-call metadata."""
    if not sources:
        return ""

    tables = sorted(
        {s["table"] for s in sources if "table" in s},
    )
    queries = [s for s in sources if s.get("type") == "query"]

    lines = [f"{DIM}{'─' * 52}{RESET}", f"{BOLD}Sources{RESET}"]

    if tables:
        lines.append(f"  {DIM}Tables:{RESET} {', '.join(tables)}")

    if queries:
        lines.append(f"  {DIM}Queries:{RESET}")
        for i, q in enumerate(queries, 1):
            sql = q.get("sql", "")
            preview = sql if len(sql) <= 80 else sql[:77] + "..."
            rows = q.get("row_count", "?")
            lines.append(f"    {DIM}{i}. {CYAN}{preview}{RESET}")
            lines.append(f"       {DIM}{rows} row(s){RESET}")

    return "\n".join(lines)


def bye() -> str:
    return f"\n{DIM}Bye!{RESET}"
