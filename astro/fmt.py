"""Terminal formatting helpers for the Astro agent."""

from __future__ import annotations

# ANSI colour codes (gracefully degrade on dumb terminals)
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"


def bold(text: str) -> str:
    return f"{_BOLD}{text}{_RESET}"


def dim(text: str) -> str:
    return f"{_DIM}{text}{_RESET}"


def cyan(text: str) -> str:
    return f"{_CYAN}{text}{_RESET}"


def yellow(text: str) -> str:
    return f"{_YELLOW}{text}{_RESET}"


def red(text: str) -> str:
    return f"{_RED}{text}{_RESET}"


def green(text: str) -> str:
    return f"{_GREEN}{text}{_RESET}"


def blue(text: str) -> str:
    return f"{_BLUE}{text}{_RESET}"


def magenta(text: str) -> str:
    return f"{_MAGENTA}{text}{_RESET}"


# ── Semantic labels ───────────────────────────────────────────────


def step(label: str, detail: str = "") -> str:
    """Format an agent step indicator."""
    s = f"{_CYAN}▸ {label}{_RESET}"
    if detail:
        s += f"  {_DIM}{detail}{_RESET}"
    return s


def step_sql(sql: str) -> str:
    """Format a SQL execution step."""
    # Compact multi-line SQL for display
    compact = " ".join(sql.split())
    if len(compact) > 200:
        compact = compact[:197] + "..."
    return f"{_CYAN}▸ execute_query{_RESET}  {_DIM}{compact}{_RESET}"


def warning(msg: str) -> str:
    return f"{_YELLOW}⚠ {msg}{_RESET}"


def error(msg: str) -> str:
    return f"{_RED}✖ {msg}{_RESET}"


def success(msg: str) -> str:
    return f"{_GREEN}✔ {msg}{_RESET}"


def heading(text: str) -> str:
    return f"\n{_BOLD}{_BLUE}{text}{_RESET}\n"


def entity_type_badge(entity_type: str) -> str:
    """Colour-coded badge for entity types."""
    match entity_type:
        case "fact":
            return f"{_MAGENTA}[fact]{_RESET}"
        case "dimension":
            return f"{_BLUE}[dim]{_RESET}"
        case _:
            return f"{_DIM}[{entity_type}]{_RESET}"


def semantic_type_badge(semantic_type: str) -> str:
    """Colour-coded badge for column semantic types."""
    match semantic_type:
        case "key":
            return f"{_YELLOW}key{_RESET}"
        case "dimension":
            return f"{_BLUE}dim{_RESET}"
        case "measure":
            return f"{_GREEN}msr{_RESET}"
        case "timestamp":
            return f"{_CYAN}ts{_RESET}"
        case _:
            return semantic_type
