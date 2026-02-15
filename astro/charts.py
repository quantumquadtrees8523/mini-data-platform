"""Simple terminal chart rendering for the Astro agent.

Produces basic text-based charts on stderr so the user can see
visualizations inline without leaving the terminal.  This keeps the
dependency footprint minimal — no matplotlib or plotext required.
"""

from __future__ import annotations

import sys

from astro import fmt

_BAR_CHAR = "█"
_MAX_BAR_WIDTH = 50
_CHART_HEIGHT = 15  # rows for scatter/line


def render_chart(
    chart_type: str = "bar",
    x_data: list[str] | None = None,
    y_data: list[float | int] | None = None,
    x_label: str = "",
    y_label: str = "",
    title: str = "",
) -> None:
    """Render a chart to stderr.

    Parameters match the agent's ``create_chart`` tool declaration.
    """
    x_data = x_data or []
    y_data = y_data or []

    if not y_data:
        _print(fmt.dim("  (no data to chart)"))
        return

    match chart_type:
        case "bar":
            _bar_chart(x_data, y_data, x_label, y_label, title)
        case "histogram":
            _bar_chart(x_data, y_data, x_label, y_label, title)
        case "line":
            _line_chart(x_data, y_data, x_label, y_label, title)
        case "scatter":
            _scatter_chart(x_data, y_data, x_label, y_label, title)
        case _:
            _bar_chart(x_data, y_data, x_label, y_label, title)


# ── Chart implementations ─────────────────────────────────────────


def _bar_chart(
    x_data: list[str],
    y_data: list[float | int],
    x_label: str,
    y_label: str,
    title: str,
) -> None:
    if title:
        _print(fmt.heading(title))

    max_val = max(abs(v) for v in y_data) if y_data else 1
    max_label_len = max((len(str(x)) for x in x_data), default=0) if x_data else 0
    max_label_len = min(max_label_len, 25)

    for i, val in enumerate(y_data):
        label = str(x_data[i]) if i < len(x_data) else str(i)
        if len(label) > 25:
            label = label[:22] + "..."
        label = label.rjust(max_label_len)

        bar_len = int(abs(val) / max_val * _MAX_BAR_WIDTH) if max_val else 0
        bar = _BAR_CHAR * bar_len
        formatted = _format_number(val)
        _print(f"  {label} │{fmt.cyan(bar)} {formatted}")

    if x_label or y_label:
        axis_info = []
        if x_label:
            axis_info.append(f"x: {x_label}")
        if y_label:
            axis_info.append(f"y: {y_label}")
        _print(f"  {fmt.dim(' | '.join(axis_info))}")
    _print()


def _line_chart(
    x_data: list[str],
    y_data: list[float | int],
    x_label: str,
    y_label: str,
    title: str,
) -> None:
    if title:
        _print(fmt.heading(title))

    if len(y_data) < 2:
        _bar_chart(x_data, y_data, x_label, y_label, "")
        return

    min_val = min(y_data)
    max_val = max(y_data)
    val_range = max_val - min_val if max_val != min_val else 1
    width = min(len(y_data), 60)

    # Build a character grid
    grid = [[" "] * width for _ in range(_CHART_HEIGHT)]
    for col, val in enumerate(y_data[:width]):
        row = _CHART_HEIGHT - 1 - int((val - min_val) / val_range * (_CHART_HEIGHT - 1))
        row = max(0, min(_CHART_HEIGHT - 1, row))
        grid[row][col] = fmt.cyan("•")

    # Y-axis labels
    for r in range(_CHART_HEIGHT):
        y_val = max_val - (r / (_CHART_HEIGHT - 1)) * val_range
        label = _format_number(y_val).rjust(10)
        if r == 0 or r == _CHART_HEIGHT - 1 or r == _CHART_HEIGHT // 2:
            _print(f"  {fmt.dim(label)} │{''.join(grid[r])}")
        else:
            _print(f"  {'':>10} │{''.join(grid[r])}")

    # X-axis
    _print(f"  {'':>10} └{'─' * width}")
    if x_data:
        first = str(x_data[0])[:10]
        last = str(x_data[-1])[:10] if len(x_data) > 1 else ""
        _print(f"  {'':>10}  {first}{'':>{max(0, width - len(first) - len(last))}}{last}")

    if x_label or y_label:
        axis_info = []
        if x_label:
            axis_info.append(f"x: {x_label}")
        if y_label:
            axis_info.append(f"y: {y_label}")
        _print(f"  {fmt.dim(' | '.join(axis_info))}")
    _print()


def _scatter_chart(
    x_data: list[str],
    y_data: list[float | int],
    x_label: str,
    y_label: str,
    title: str,
) -> None:
    """Scatter plot — same as line but with isolated dots."""
    # Reuse line chart rendering (dots without connections look like scatter)
    _line_chart(x_data, y_data, x_label, y_label, title)


# ── Helpers ───────────────────────────────────────────────────────


def _format_number(val: float | int) -> str:
    if isinstance(val, int):
        return f"{val:,}"
    if abs(val) >= 1000:
        return f"{val:,.0f}"
    return f"{val:,.2f}"


def _print(msg: str = "") -> None:
    print(msg, file=sys.stderr)
