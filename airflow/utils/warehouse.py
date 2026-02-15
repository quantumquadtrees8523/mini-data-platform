"""
Shared utilities for DuckDB warehouse operations.
"""
from pathlib import Path
import duckdb
from airflow.sdk import task

PROJECT_ROOT = Path(__file__).parent.parent.parent
WAREHOUSE_PATH = PROJECT_ROOT / "warehouse" / "data.duckdb"


@task()
def ensure_warehouse_exists():
    """Ensure the DuckDB warehouse database exists and has required schemas."""
    print(f"Ensuring warehouse exists at {WAREHOUSE_PATH}")
    
    # Create warehouse directory if it doesn't exist
    WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to DuckDB (creates file if it doesn't exist)
    conn = duckdb.connect(str(WAREHOUSE_PATH))
    
    # Create schemas
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.execute("CREATE SCHEMA IF NOT EXISTS staging")
    conn.execute("CREATE SCHEMA IF NOT EXISTS marts")
    
    # Verify
    schemas = conn.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('raw', 'staging', 'marts')").fetchall()
    print(f"✓ Warehouse initialized with schemas: {[s[0] for s in schemas]}")
    
    conn.close()
    return str(WAREHOUSE_PATH)


def load_csv_to_raw(warehouse_path: str, csv_path: str, table_name: str) -> int:
    """Load a CSV file into a raw.* table in the DuckDB warehouse.

    This is a plain function (not an Airflow task) so it can be called
    from DAGs, scripts, or agents.

    Returns:
        Number of rows loaded.
    """
    conn = duckdb.connect(warehouse_path)
    try:
        conn.execute(f"""
            CREATE OR REPLACE TABLE raw.{table_name} AS
            SELECT * FROM read_csv_auto('{csv_path}')
        """)
        count = conn.execute(f"SELECT COUNT(*) FROM raw.{table_name}").fetchone()[0]
        print(f"Loaded {count} records into raw.{table_name}")
        return count
    finally:
        conn.close()
