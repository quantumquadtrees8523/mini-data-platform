"""Display intermediate tool results to the user on stderr."""

import sys

from astro import fmt


def show_schemas(schemas: list[str]) -> None:
    if not schemas:
        return
    print(f"  {fmt.DIM}Found {len(schemas)} schema(s){fmt.RESET}", file=sys.stderr)


def show_tables(tables: list[dict], schema: str) -> None:
    if not tables:
        return
    print(
        f"  {fmt.DIM}Found {len(tables)} table(s) in {schema}{fmt.RESET}",
        file=sys.stderr,
    )


def show_columns(columns: list[dict], schema: str, table: str) -> None:
    if not columns:
        return
    print(
        f"  {fmt.DIM}Table {schema}.{table} has {len(columns)} column(s){fmt.RESET}",
        file=sys.stderr,
    )


def show_data(columns: list[str], rows: list[list], limit: int = 10) -> None:
    if not rows:
        return
    print(f"  {fmt.DIM}Sampled {len(rows)} row(s){fmt.RESET}", file=sys.stderr)


def show_query_result(result: dict) -> None:
    if "error" in result:
        return  # errors are already shown by agent
    row_count = result.get("row_count", len(result.get("rows", [])))
    print(
        f"  {fmt.DIM}Query returned {row_count} row(s){fmt.RESET}",
        file=sys.stderr,
    )
