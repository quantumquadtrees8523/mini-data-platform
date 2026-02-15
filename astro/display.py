"""Terminal display helpers for agent tool results.

Each ``show_*`` function prints a human-friendly representation of the
data returned by a DataLayer method so that the user can follow along
as the agent explores the warehouse.
"""

from __future__ import annotations

import sys
from typing import Any

from astro import fmt


def _print(msg: str = "") -> None:
    """Print to stderr so stdout stays clean for the agent's final answer."""
    print(msg, file=sys.stderr)


# ── Schema / table exploration ────────────────────────────────────


def show_schemas(schemas: list[dict]) -> None:
    """Display schemas returned by DataLayer.list_schemas()."""
    _print(fmt.heading("Schemas"))
    for s in schemas:
        name = fmt.bold(s["schema"])
        entity_count = s.get("entity_count", 0)
        _print(f"  {name}  ({entity_count} entities)")
        for e in s.get("entities", []):
            badge = fmt.entity_type_badge(e.get("type", ""))
            _print(f"    {badge} {e['name']}  →  {e['table']}")
            if e.get("description"):
                # First line of description only
                desc = e["description"].split("\n")[0].strip()
                if len(desc) > 100:
                    desc = desc[:97] + "..."
                _print(f"         {fmt.dim(desc)}")
    _print()


def show_tables(tables: list[dict], schema: str) -> None:
    """Display tables returned by DataLayer.list_tables()."""
    _print(fmt.heading(f"Tables in {schema}"))
    for t in tables:
        name = fmt.bold(t["table"])
        row_count = f"{t['row_count']:,}" if t.get("row_count") is not None else "?"
        table_type = fmt.dim(t.get("table_type", ""))
        _print(f"  {name}  {table_type}  ({row_count} rows)")

        if t.get("description"):
            desc = t["description"].split("\n")[0].strip()
            if len(desc) > 100:
                desc = desc[:97] + "..."
            _print(f"    {fmt.dim(desc)}")

        if t.get("entity_type"):
            badge = fmt.entity_type_badge(t["entity_type"])
            grain = fmt.dim(t.get("grain", ""))
            _print(f"    {badge} {grain}")

        if t.get("available_metrics"):
            metric_names = [m["name"] for m in t["available_metrics"][:5]]
            _print(f"    metrics: {fmt.cyan(', '.join(metric_names))}")

        if t.get("relationships"):
            for r in t["relationships"]:
                _print(
                    f"    → {r['related_entity']} ({r['cardinality']})"
                )
    _print()


def show_columns(columns: Any, schema: str, table: str) -> None:
    """Display column info returned by DataLayer.describe_table().

    Accepts either a plain list of column dicts or the enriched dict
    format with entity-level context.
    """
    # Enriched format wraps columns inside an outer dict
    if isinstance(columns, dict):
        entity_name = columns.get("entity_name", "")
        entity_type = columns.get("entity_type", "")
        description = columns.get("description", "")
        grain = columns.get("grain", "")
        col_list = columns.get("columns", [])

        _print(fmt.heading(f"{schema}.{table}"))
        if entity_name:
            badge = fmt.entity_type_badge(entity_type)
            _print(f"  Entity: {fmt.bold(entity_name)} {badge}")
        if description:
            _print(f"  {fmt.dim(description)}")
        if grain:
            _print(f"  Grain: {fmt.dim(grain)}")
        _print()
    else:
        col_list = columns
        _print(fmt.heading(f"{schema}.{table}"))

    # Column table
    for c in col_list:
        name = c["column"]
        dtype = fmt.dim(c["data_type"])
        nullable = "?" if c.get("nullable") else ""

        parts = [f"  {name:<30} {dtype:<15} {nullable}"]

        if c.get("semantic_type"):
            parts.append(fmt.semantic_type_badge(c["semantic_type"]))
        if c.get("description"):
            desc = c["description"].split("\n")[0].strip()
            if len(desc) > 60:
                desc = desc[:57] + "..."
            parts.append(fmt.dim(desc))

        _print("  ".join(parts))
    _print()


# ── Data display ──────────────────────────────────────────────────


def show_data(columns: list[str], rows: list[list]) -> None:
    """Display tabular data (sample_data or query results)."""
    if not columns or not rows:
        _print(fmt.dim("  (no data)"))
        return

    # Compute column widths
    widths = [len(str(c)) for c in columns]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(_format_cell(val)))

    # Cap widths at 40 chars
    widths = [min(w, 40) for w in widths]

    # Header
    header = "  ".join(
        fmt.bold(str(c).ljust(w)) for c, w in zip(columns, widths)
    )
    _print(f"  {header}")
    _print(f"  {'  '.join('─' * w for w in widths)}")

    # Rows
    for row in rows:
        cells = []
        for val, w in zip(row, widths):
            cell = _format_cell(val)
            if len(cell) > w:
                cell = cell[: w - 1] + "…"
            cells.append(cell.ljust(w))
        _print(f"  {'  '.join(cells)}")
    _print()


def show_query_result(result: dict) -> None:
    """Display the result of DataLayer.execute_query()."""
    if "error" in result:
        _print(fmt.error(result["error"]))
        return
    columns = result.get("columns", [])
    rows = result.get("rows", [])
    row_count = result.get("row_count", len(rows))
    _print(fmt.dim(f"  ({row_count} row{'s' if row_count != 1 else ''})"))
    show_data(columns, rows)


# ── Helpers ───────────────────────────────────────────────────────


def _format_cell(val: Any) -> str:
    """Format a single cell value for display."""
    if val is None:
        return fmt.dim("NULL")
    if isinstance(val, float):
        # Two decimal places for floats, add commas
        return f"{val:,.2f}"
    if isinstance(val, int):
        return f"{val:,}"
    return str(val)
