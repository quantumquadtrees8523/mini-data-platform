# Mini Data Platform — run `just` to see all commands

# Sync sources.yml manifest with CSVs on disk
sync:
    uv run python scripts/sync_sources.py

# Load all manifest sources into DuckDB raw layer
ingest:
    cd airflow && AIRFLOW_HOME=$(pwd) uv run python dags/ingest_sources.py

# Run dbt staging + marts transformations
transform:
    cd airflow && AIRFLOW_HOME=$(pwd) uv run python dags/run_dbt.py

# Full pipeline: sync manifest, ingest, transform
pipeline: sync ingest transform

# Open a DuckDB shell on the warehouse
query:
    duckdb warehouse/data.duckdb

# Launch the Astro agent
agent:
    uv run astro

# Run full setup from scratch (generate data, init Airflow, run pipeline)
setup:
    ./setup.sh
