"""Display intermediate tool results to the user on stderr."""

import os
import sys

from astro import fmt


def _term_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80


def show_schemas(schemas: list[str]) -> None:
    if not schemas:
        return
    for s in schemas:
        print(f"  {fmt.DIM}  {fmt.CYAN}{s}{fmt.RESET}", file=sys.stderr)
    print(file=sys.stderr)


def show_tables(tables: list[dict], schema: str) -> None:
    if not tables:
        return
    for t in tables:
        count = t.get("row_count")
        count_str = f"{count:,} rows" if count is not None else ""
        print(
            f"  {fmt.DIM}  {fmt.CYAN}{t['name']:<30}{fmt.RESET}"
            f" {fmt.DIM}{count_str}{fmt.RESET}",
            file=sys.stderr,
        )
    print(file=sys.stderr)


def show_columns(columns: list[dict], schema: str, table: str) -> None:
    if not columns:
        return
    for col in columns:
        nullable = " (nullable)" if col.get("nullable") == "YES" else ""
        print(
            f"  {fmt.DIM}  {fmt.CYAN}{col['column']:<25}{fmt.RESET}"
            f" {fmt.DIM}{col['type']}{nullable}{fmt.RESET}",
            file=sys.stderr,
        )
    print(file=sys.stderr)


def show_data(columns: list[str], rows: list[list], limit: int = 10) -> None:
    if not rows:
        print(f"  {fmt.DIM}  (no data){fmt.RESET}", file=sys.stderr)
        return

    display_rows = rows[:limit]
    max_col = min(30, max(1, (_term_width() - 10) // max(len(columns), 1) - 3))

    def _trunc(val: object, width: int) -> str:
        s = str(val)
        return s[:width] if len(s) <= width else s[: width - 1] + "\u2026"

    # Column widths: fit header and data
    widths = []
    for i, col in enumerate(columns):
        w = len(_trunc(col, max_col))
        for row in display_rows:
            w = max(w, len(_trunc(row[i] if i < len(row) else "", max_col)))
        widths.append(min(w, max_col))

    def _row_str(vals: list) -> str:
        cells = []
        for i, v in enumerate(vals):
            cells.append(f"{_trunc(v, widths[i]):<{widths[i]}}")
        return " | ".join(cells)

    header = _row_str(columns)
    sep = "-+-".join("-" * w for w in widths)
    print(f"  {fmt.DIM}  {header}{fmt.RESET}", file=sys.stderr)
    print(f"  {fmt.DIM}  {sep}{fmt.RESET}", file=sys.stderr)
    for row in display_rows:
        print(f"  {fmt.DIM}  {_row_str(row)}{fmt.RESET}", file=sys.stderr)

    if len(rows) > limit:
        print(
            f"  {fmt.DIM}  ... ({len(rows) - limit} more rows){fmt.RESET}",
            file=sys.stderr,
        )
    print(file=sys.stderr)


def show_query_result(result: dict) -> None:
    if "error" in result:
        return  # errors are already shown by agent
    row_count = result.get("row_count", len(result.get("rows", [])))
    print(
        f"  {fmt.DIM}  {row_count} row(s) returned{fmt.RESET}",
        file=sys.stderr,
    )
    show_data(result.get("columns", []), result.get("rows", []))
