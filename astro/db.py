"""Data layer for DuckDB warehouse access.

Fully generic — discovers schemas, tables, and columns dynamically
so it works with any DuckDB warehouse, not just this e-commerce one.
"""

import math
import re

import duckdb
from pathlib import Path


class DataLayer:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        self.conn = duckdb.connect(str(self.db_path), read_only=True)

    def close(self):
        self.conn.close()

    def list_schemas(self) -> list[str]:
        """List all user-created schemas in the database."""
        rows = self.conn.execute(
            """
            SELECT DISTINCT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
            ORDER BY schema_name
            """
        ).fetchall()
        return [r[0] for r in rows]

    def list_tables(self, schema: str) -> list[dict]:
        """List tables/views in a schema with row counts."""
        rows = self.conn.execute(
            """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = ?
            ORDER BY table_name
            """,
            [schema],
        ).fetchall()

        results = []
        for table_name, table_type in rows:
            try:
                count = self.conn.execute(
                    f'SELECT COUNT(*) FROM "{schema}"."{table_name}"'
                ).fetchone()[0]
            except Exception:
                count = None
            results.append({
                "name": table_name,
                "type": table_type,
                "row_count": count,
            })
        return results

    def describe_table(self, schema: str, table: str) -> list[dict]:
        """Get column names, types, and nullability for a table."""
        rows = self.conn.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = ? AND table_name = ?
            ORDER BY ordinal_position
            """,
            [schema, table],
        ).fetchall()
        return [{"column": r[0], "type": r[1], "nullable": r[2]} for r in rows]

    def sample_data(self, schema: str, table: str, limit: int = 5) -> dict:
        """Get sample rows from a table."""
        limit = min(max(1, limit), 10)
        if not _valid_identifier(schema) or not _valid_identifier(table):
            raise ValueError(f"Invalid identifier: {schema}.{table}")

        result = self.conn.execute(
            f'SELECT * FROM "{schema}"."{table}" LIMIT {limit}'
        )
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return {
            "columns": columns,
            "rows": [[_serialize(v) for v in row] for row in rows],
        }

    def execute_query(self, sql: str) -> dict:
        """Execute a read-only SQL query. Results capped at 100 rows."""
        result = self.conn.execute(sql.rstrip(';'))
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        
        total = len(rows)
        truncated = total > 100
        
        if truncated:
            rows = rows[:100]
        
        output = {
            "columns": columns,
            "rows": [[_serialize(v) for v in row] for row in rows],
            "row_count": total,
        }
        if truncated:
            output["note"] = f"Showing 100 of {total} rows. Refine your query for full results."
        return output


def _valid_identifier(name: str) -> bool:
    return all(c.isalnum() or c == '_' for c in name) and len(name) > 0


def _serialize(value):
    """Convert a value to a JSON-safe type."""
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, (int, str, bool)):
        return value
    return str(value)
