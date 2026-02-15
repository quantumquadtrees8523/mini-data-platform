"""
Airflow DAG to ingest all data sources into DuckDB raw layer.

Reads sources/sources.yml to discover which CSVs to load.
To add a new data source, add an entry to sources.yml and drop a CSV
in the appropriate sources/ subdirectory.
"""
from datetime import datetime
from pathlib import Path
import sqlite3
import sys

import yaml
from airflow.sdk import dag, task

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.warehouse import ensure_warehouse_exists, load_csv_to_raw

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = PROJECT_ROOT / "sources" / "sources.yml"


def _load_manifest() -> list[dict]:
    """Read and return the sources manifest."""
    with open(MANIFEST_PATH) as f:
        manifest = yaml.safe_load(f)
    return manifest["sources"]


_sources = _load_manifest()
_all_systems = sorted(set(s["system"] for s in _sources))

# Validate no duplicate table names
_tables = [s["table"] for s in _sources]
if len(_tables) != len(set(_tables)):
    raise ValueError(f"Duplicate table names in {MANIFEST_PATH}: {_tables}")


def _make_load_task(source_entry: dict):
    """Factory to create a load task for a manifest entry."""

    @task(task_id=f"load_{source_entry['table']}")
    def load_source(warehouse_path: str):
        csv_path = str(PROJECT_ROOT / source_entry["path"])
        return load_csv_to_raw(warehouse_path, csv_path, source_entry["table"])

    return load_source


@dag(
    dag_id="ingest_sources",
    start_date=datetime(2020, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["ingestion"] + _all_systems,
)
def ingest_sources():
    """DAG to ingest all data sources from the manifest into DuckDB."""
    warehouse_path = ensure_warehouse_exists()

    for source in _sources:
        load_task = _make_load_task(source)
        load_task(warehouse_path)


dag_instance = ingest_sources()

if __name__ == "__main__":
    # TODO: Optimization - only clear cache when manifest has changed (e.g., track
    # manifest hash and compare). Currently clears on every run for simplicity.
    # Clear stale DAG serialization to ensure test uses current manifest
    db_path = Path(__file__).parent.parent / "airflow.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM serialized_dag WHERE dag_id = 'ingest_sources'")
            conn.execute("DELETE FROM dag_version WHERE dag_id = 'ingest_sources'")
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass  # Tables might not exist yet

    print("Testing ingest_sources DAG...")
    dag_instance.test()
