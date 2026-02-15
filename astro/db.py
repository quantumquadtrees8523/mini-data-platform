"""DataLayer – DuckDB wrapper enriched with semantic metadata.

The DataLayer is the single interface that the Astro agent (and any other
consumer) uses to explore and query the warehouse.  Every exploration
method merges live schema information from DuckDB with semantic context
from the manifest so that an LLM can understand *what the data means*,
not just what columns exist.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from astro.semantic import SemanticManifest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = _PROJECT_ROOT / "warehouse" / "data.duckdb"
_MAX_QUERY_ROWS = 100
_MAX_SAMPLE_ROWS = 10


class DataLayer:
    """Semantic-aware DuckDB data layer.

    Parameters
    ----------
    db_path : str | Path | None
        Path to the DuckDB file.  Defaults to ``warehouse/data.duckdb``
        relative to the project root.
    manifest_path : str | Path | None
        Path to the semantic manifest YAML.  Defaults to the bundled
        ``astro/semantic/manifest.yml``.
    read_only : bool
        Open the database in read-only mode (default True).
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        manifest_path: str | Path | None = None,
        read_only: bool = True,
    ):
        db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._conn = duckdb.connect(str(db_path), read_only=read_only)
        self._manifest = SemanticManifest(manifest_path)

    # ── Public API (matches the agent's tool declarations) ────────

    def list_schemas(self) -> list[dict]:
        """List all user-created schemas with semantic annotations."""
        rows = self._conn.execute(
            """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE catalog_name = current_database()
              AND schema_name NOT IN ('information_schema', 'pg_catalog')
            ORDER BY schema_name
            """
        ).fetchall()

        results = []
        for (schema_name,) in rows:
            entities = self._manifest.entities_in_schema(schema_name)
            results.append(
                {
                    "schema": schema_name,
                    "entity_count": len(entities),
                    "entities": [
                        {
                            "name": e.name,
                            "table": e.table,
                            "type": e.entity_type,
                            "description": e.description,
                        }
                        for e in entities
                    ],
                }
            )
        return results

    def list_tables(self, schema: str) -> list[dict]:
        """List tables in *schema* with row counts and semantic context."""
        rows = self._conn.execute(
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
            # Row count
            try:
                ((count,),) = self._conn.execute(
                    f'SELECT COUNT(*) FROM "{schema}"."{table_name}"'
                ).fetchall()
            except Exception:
                count = None

            entity = self._manifest.entity_for_table(schema, table_name)
            entry: dict = {
                "table": table_name,
                "table_type": table_type,
                "row_count": count,
            }
            if entity:
                entry["entity_name"] = entity.name
                entry["entity_type"] = entity.entity_type
                entry["description"] = entity.description
                entry["grain"] = entity.grain
                # Summarize available metrics
                metrics = self._manifest.metrics_for(entity.name)
                if metrics:
                    entry["available_metrics"] = [
                        {"name": m.name, "description": m.description}
                        for m in metrics
                    ]
                # Summarize relationships
                rels = self._manifest.relationships_for(entity.name)
                if rels:
                    entry["relationships"] = [
                        {
                            "name": r.name,
                            "related_entity": (
                                r.to_entity if r.from_entity == entity.name else r.from_entity
                            ),
                            "cardinality": r.cardinality,
                            "description": r.description,
                        }
                        for r in rels
                    ]
            results.append(entry)
        return results

    def describe_table(self, schema: str, table: str) -> list[dict]:
        """Describe columns with DuckDB types and semantic metadata."""
        rows = self._conn.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = ? AND table_name = ?
            ORDER BY ordinal_position
            """,
            [schema, table],
        ).fetchall()

        entity = self._manifest.entity_for_table(schema, table)
        results = []
        for col_name, data_type, is_nullable in rows:
            entry: dict = {
                "column": col_name,
                "data_type": data_type,
                "nullable": is_nullable == "YES",
            }
            if entity:
                col_meta = entity.columns.get(col_name)
                if col_meta:
                    entry["semantic_type"] = col_meta.semantic_type
                    entry["description"] = col_meta.description
                    if col_meta.format:
                        entry["format"] = col_meta.format
            results.append(entry)

        # Append entity-level context if available
        if entity:
            results = {
                "table": f"{schema}.{table}",
                "entity_name": entity.name,
                "entity_type": entity.entity_type,
                "description": entity.description,
                "grain": entity.grain,
                "primary_key": entity.primary_key,
                "columns": results,
            }
        return results

    def sample_data(self, schema: str, table: str, limit: int = 5) -> dict:
        """Return sample rows with column names."""
        limit = min(max(1, limit), _MAX_SAMPLE_ROWS)
        result = self._conn.execute(
            f'SELECT * FROM "{schema}"."{table}" LIMIT {limit}'
        )
        columns = [desc[0] for desc in result.description]
        rows = [list(row) for row in result.fetchall()]
        return {"columns": columns, "rows": rows}

    def execute_query(self, sql: str) -> dict:
        """Execute a read-only SQL query.  Results capped at 100 rows."""
        try:
            result = self._conn.execute(sql)
            columns = [desc[0] for desc in result.description]
            rows = [list(row) for row in result.fetchmany(_MAX_QUERY_ROWS)]
            row_count = len(rows)
            return {"columns": columns, "rows": rows, "row_count": row_count}
        except Exception as e:
            return {"error": str(e)}

    # ── Semantic helpers (not used by agent tools, but available) ──

    @property
    def manifest(self) -> SemanticManifest:
        """Direct access to the semantic manifest for advanced use."""
        return self._manifest

    def semantic_summary(self) -> dict:
        """Return the full semantic summary (useful for LLM context)."""
        return self._manifest.summary()

    def close(self):
        """Close the underlying DuckDB connection."""
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
