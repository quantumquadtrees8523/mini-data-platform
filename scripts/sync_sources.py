"""
Sync sources/sources.yml with the CSV files on disk.

Scans sources/ for *.csv files, adds new ones to the manifest,
and removes entries whose CSVs no longer exist.

Usage:
    uv run python scripts/sync_sources.py
"""
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
SOURCES_DIR = PROJECT_ROOT / "sources"
MANIFEST_PATH = SOURCES_DIR / "sources.yml"
DAG_FILE = PROJECT_ROOT / "airflow" / "dags" / "ingest_sources.py"


def discover_csvs() -> list[dict]:
    """Walk sources/ and build entries for every CSV found."""
    entries = []
    for csv_path in sorted(SOURCES_DIR.rglob("*.csv")):
        rel_path = csv_path.relative_to(PROJECT_ROOT)
        # Derive system from the first directory under sources/
        # e.g. sources/postgres/products.csv -> system="postgres"
        system = rel_path.parts[1]
        table = csv_path.stem
        entries.append({
            "table": table,
            "path": str(rel_path),
            "system": system,
        })
    return entries


def load_manifest() -> list[dict]:
    """Load the current manifest, or return empty list if it doesn't exist."""
    if not MANIFEST_PATH.exists():
        return []
    with open(MANIFEST_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("sources", []) if data else []


def save_manifest(sources: list[dict]) -> None:
    """Write the manifest file."""
    with open(MANIFEST_PATH, "w") as f:
        f.write(
            "# Source manifest for the ingestion pipeline.\n"
            "# To add a new source: place a CSV in sources/<system>/ and add an entry here,\n"
            "# or run `just sync` to auto-discover CSVs.\n\n"
        )
        yaml.dump({"sources": sources}, f, default_flow_style=False, sort_keys=False)


def sync():
    existing = load_manifest()
    discovered = discover_csvs()

    existing_paths = {e["path"] for e in existing}
    discovered_paths = {d["path"] for d in discovered}

    added = [d for d in discovered if d["path"] not in existing_paths]
    removed = [e for e in existing if e["path"] not in discovered_paths]
    kept = [e for e in existing if e["path"] in discovered_paths]

    updated = kept + added

    if not added and not removed:
        print(f"Manifest is up to date ({len(updated)} sources)")
        return

    if added:
        print(f"Added {len(added)} source(s):")
        for a in added:
            print(f"  + {a['table']} ({a['path']})")

    if removed:
        print(f"Removed {len(removed)} source(s):")
        for r in removed:
            print(f"  - {r['table']} ({r['path']})")

    save_manifest(updated)
    DAG_FILE.touch()  # Update mtime to help Airflow detect changes
    print(f"Manifest updated: {len(updated)} total sources")


if __name__ == "__main__":
    sync()
