"""Load and query the semantic manifest."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

_MANIFEST_PATH = Path(__file__).parent / "manifest.yml"

SemanticType = Literal["key", "dimension", "measure", "timestamp"]
EntityType = Literal["dimension", "fact"]
Cardinality = Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many"]


# ── Dataclasses ───────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ColumnMeta:
    """Semantic metadata for a single column."""

    name: str
    semantic_type: SemanticType
    description: str = ""
    format: str | None = None


@dataclass(frozen=True, slots=True)
class EntityMeta:
    """Semantic metadata for a table / entity."""

    name: str
    schema: str
    table: str
    description: str
    grain: str
    primary_key: str | None
    entity_type: EntityType
    columns: dict[str, ColumnMeta] = field(default_factory=dict)

    @property
    def qualified_table(self) -> str:
        return f"{self.schema}.{self.table}"


@dataclass(frozen=True, slots=True)
class Relationship:
    """A foreign-key relationship between two entities."""

    name: str
    from_entity: str
    from_column: str
    to_entity: str
    to_column: str
    cardinality: Cardinality
    description: str = ""


@dataclass(frozen=True, slots=True)
class Metric:
    """A pre-defined calculation on an entity."""

    name: str
    entity: str
    description: str
    sql: str
    format: str | None = None


@dataclass(frozen=True, slots=True)
class SuggestedAnalysis:
    """A suggested analytical question with relevant entities and metrics."""

    question: str
    entities: list[str]
    dimensions: list[str]
    metrics: list[str]


# ── Manifest ──────────────────────────────────────────────────────────


class SemanticManifest:
    """In-memory representation of the semantic manifest.

    Provides lookup helpers that the DataLayer uses to enrich schema
    exploration results.
    """

    def __init__(self, path: str | Path | None = None):
        path = Path(path) if path else _MANIFEST_PATH
        raw = yaml.safe_load(path.read_text())

        self.entities: dict[str, EntityMeta] = {}
        self.relationships: list[Relationship] = []
        self.metrics: list[Metric] = []
        self.suggested_analyses: list[SuggestedAnalysis] = []

        self._load_entities(raw.get("entities", []))
        self._load_relationships(raw.get("relationships", []))
        self._load_metrics(raw.get("metrics", []))
        self._load_suggested_analyses(raw.get("suggested_analyses", []))

        # Reverse lookups: schema.table → entity name
        self._table_to_entity: dict[str, str] = {
            e.qualified_table: e.name for e in self.entities.values()
        }

    # ── Loading ───────────────────────────────────────────────────

    def _load_entities(self, raw_entities: list[dict]) -> None:
        for e in raw_entities:
            cols = {
                c["name"]: ColumnMeta(
                    name=c["name"],
                    semantic_type=c.get("semantic_type", "dimension"),
                    description=c.get("description", ""),
                    format=c.get("format"),
                )
                for c in e.get("columns", [])
            }
            entity = EntityMeta(
                name=e["name"],
                schema=e["schema"],
                table=e["table"],
                description=e.get("description", "").strip(),
                grain=e.get("grain", ""),
                primary_key=e.get("primary_key"),
                entity_type=e.get("entity_type", "dimension"),
                columns=cols,
            )
            self.entities[entity.name] = entity

    def _load_relationships(self, raw_rels: list[dict]) -> None:
        for r in raw_rels:
            self.relationships.append(
                Relationship(
                    name=r["name"],
                    from_entity=r["from_entity"],
                    from_column=r["from_column"],
                    to_entity=r["to_entity"],
                    to_column=r["to_column"],
                    cardinality=r.get("cardinality", "many_to_one"),
                    description=r.get("description", ""),
                )
            )

    def _load_metrics(self, raw_metrics: list[dict]) -> None:
        for m in raw_metrics:
            self.metrics.append(
                Metric(
                    name=m["name"],
                    entity=m["entity"],
                    description=m.get("description", "").strip(),
                    sql=m.get("sql", "").strip(),
                    format=m.get("format"),
                )
            )

    def _load_suggested_analyses(self, raw_analyses: list[dict]) -> None:
        for a in raw_analyses:
            self.suggested_analyses.append(
                SuggestedAnalysis(
                    question=a["question"],
                    entities=a.get("entities", []),
                    dimensions=a.get("dimensions", []),
                    metrics=a.get("metrics", []),
                )
            )

    # ── Lookups ───────────────────────────────────────────────────

    def entity_for_table(self, schema: str, table: str) -> EntityMeta | None:
        """Return the entity metadata for a given schema.table, or None."""
        key = f"{schema}.{table}"
        name = self._table_to_entity.get(key)
        return self.entities.get(name) if name else None

    def entities_in_schema(self, schema: str) -> list[EntityMeta]:
        """Return all entities whose tables live in *schema*."""
        return [e for e in self.entities.values() if e.schema == schema]

    def relationships_for(self, entity_name: str) -> list[Relationship]:
        """Return relationships where *entity_name* is on either side."""
        return [
            r
            for r in self.relationships
            if r.from_entity == entity_name or r.to_entity == entity_name
        ]

    def metrics_for(self, entity_name: str) -> list[Metric]:
        """Return metrics defined on *entity_name*."""
        return [m for m in self.metrics if m.entity == entity_name]

    def column_meta(self, schema: str, table: str, column: str) -> ColumnMeta | None:
        """Return column-level metadata, or None if not in manifest."""
        entity = self.entity_for_table(schema, table)
        if entity is None:
            return None
        return entity.columns.get(column)

    def summary(self) -> dict:
        """Return a high-level summary suitable for an LLM system prompt."""
        entities_summary = []
        for e in self.entities.values():
            dims = [c.name for c in e.columns.values() if c.semantic_type == "dimension"]
            measures = [c.name for c in e.columns.values() if c.semantic_type == "measure"]
            entities_summary.append(
                {
                    "name": e.name,
                    "table": e.qualified_table,
                    "type": e.entity_type,
                    "description": e.description,
                    "grain": e.grain,
                    "dimensions": dims,
                    "measures": measures,
                }
            )
        return {
            "entities": entities_summary,
            "relationships": [
                {
                    "name": r.name,
                    "from": f"{r.from_entity}.{r.from_column}",
                    "to": f"{r.to_entity}.{r.to_column}",
                    "cardinality": r.cardinality,
                }
                for r in self.relationships
            ],
            "metrics": [
                {"name": m.name, "entity": m.entity, "description": m.description}
                for m in self.metrics
            ],
        }
