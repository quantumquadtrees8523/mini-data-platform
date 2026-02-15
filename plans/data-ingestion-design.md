# Data Ingestion Pipeline: Manifest-Driven CSV → DuckDB

A YAML-driven ingestion system that automatically loads CSV files into the DuckDB warehouse raw layer.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  sources/                                                               │
│  ├── postgres/products.csv                                              │
│  ├── postgres/users.csv        ──┐                                      │
│  ├── salesforce/campaigns.csv    │   CSV files on disk                  │
│  └── analytics/pageviews.csv   ──┘                                      │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  scripts/sync_sources.py                                                 │
│  • Scans sources/**/*.csv                                                │
│  • Updates sources/sources.yml manifest                                  │
│  • Adds new CSVs, removes deleted entries                                │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  sources/sources.yml                                                     │
│  sources:                                                                │
│    - table: products                                                     │
│      path: sources/postgres/products.csv                                 │
│      system: postgres                                                    │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  airflow/dags/ingest_sources.py                                          │
│  • Reads manifest at DAG parse time                                      │
│  • Dynamically creates one task per source                               │
│  • Calls warehouse.load_csv_to_raw() for each                            │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  warehouse/data.duckdb                                                   │
│  └── raw schema                                                          │
│      ├── products (CREATE OR REPLACE TABLE)                              │
│      ├── users                                                           │
│      ├── transactions                                                    │
│      └── ...                                                             │
└──────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

| Stage | Schema | Tool | Description |
|-------|--------|------|-------------|
| Source | filesystem | CSV files | Raw data in `sources/<system>/` directories |
| Manifest | filesystem | YAML | `sources/sources.yml` declares what to ingest |
| Sync | n/a | `sync_sources.py` | Keeps manifest in sync with files on disk |
| Ingest | `raw` | Airflow DAG | Loads CSVs into DuckDB via `read_csv_auto()` |
| Transform | `staging`, `marts` | dbt | Cleans and models data (separate DAG) |

## Key Components

### 1. Manifest Format (`sources/sources.yml`)

```yaml
sources:
  - table: products           # Target table name in raw schema
    path: sources/postgres/products.csv  # Relative path from project root
    system: postgres          # Source system (used for DAG tags)
```

Each entry maps a CSV file to a raw table. The `system` field groups sources for filtering/tagging.

### 2. Sync Script (`scripts/sync_sources.py`)

| Function | Purpose |
|----------|---------|
| `discover_csvs()` | Walk `sources/**/*.csv`, build entry list |
| `load_manifest()` | Read current `sources.yml` |
| `save_manifest()` | Write updated manifest |
| `sync()` | Diff discovered vs manifest, add/remove entries |

Run via: `just sync` or `uv run python scripts/sync_sources.py`

### 3. Ingestion DAG (`airflow/dags/ingest_sources.py`)

```
DAG: ingest_sources
├── ensure_warehouse_exists   (creates raw/staging/marts schemas)
└── load_<table>              (one task per manifest entry)
    └── calls load_csv_to_raw()
```

Key behaviors:
- Reads manifest at **parse time** (not runtime)
- Creates tasks dynamically via `_make_load_task()` factory
- Validates no duplicate table names
- Tags DAG with all source systems for filtering

### 4. Warehouse Utilities (`airflow/utils/warehouse.py`)

| Function | Purpose |
|----------|---------|
| `ensure_warehouse_exists()` | Create DuckDB file + schemas if missing |
| `load_csv_to_raw()` | `CREATE OR REPLACE TABLE raw.{table} AS SELECT * FROM read_csv_auto()` |

The `load_csv_to_raw()` function is a plain Python function (not a task) so it can be called from DAGs, scripts, or the agent.

## How to Add a New Data Source

1. **Drop CSV file**: Place your CSV in `sources/<system>/` (e.g., `sources/postgres/new_data.csv`)

2. **Sync manifest**:
   ```bash
   just sync
   ```
   This auto-discovers the new CSV and adds it to `sources/sources.yml`

3. **Run pipeline**:
   ```bash
   just pipeline
   ```
   Or run individually: `just ingest` then `just transform`

4. **Verify**:
   ```bash
   just query
   # Then in DuckDB shell:
   SELECT COUNT(*) FROM raw.new_data;
   ```

**One-liner**: `just pipeline` handles sync + ingest + transform automatically.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| YAML manifest | Human-readable, version-controlled source of truth |
| Auto-sync from disk | Reduces manual steps; prevents drift between files and config |
| Dynamic task creation | Single DAG scales with sources; no code changes to add data |
| `CREATE OR REPLACE TABLE` | Idempotent loads; safe to re-run without manual cleanup |
| Parse-time manifest read | Airflow sees tasks in UI; enables proper scheduling and monitoring |
| Plain function for load | Reusable outside Airflow (scripts, agents, tests) |
| System-based directories | Organizes sources by origin; enables system-level filtering |

## File Reference

| File | Purpose |
|------|---------|
| `sources/sources.yml` | Manifest declaring all data sources |
| `scripts/sync_sources.py` | Sync manifest with CSV files on disk |
| `airflow/dags/ingest_sources.py` | Airflow DAG that ingests all manifest sources |
| `airflow/utils/warehouse.py` | DuckDB connection and load utilities |
| `warehouse/data.duckdb` | DuckDB database file |
| `justfile` | Command runner with `sync`, `ingest`, `pipeline` recipes |

## Pipeline Commands

```bash
just sync       # Update manifest from disk
just ingest     # Load CSVs to raw schema
just transform  # Run dbt models
just pipeline   # All three in sequence
just query      # Interactive DuckDB shell
```
