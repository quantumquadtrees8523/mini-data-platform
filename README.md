# Mini Data Platform

```bash
export GEMINI_API_KEY=your-api-key
uv run astro
```

The CLI looks for `warehouse/data.duckdb` in the current directory or up to 6 parent directories.

---

If you have an applied AI interview at Astronomer, we'll ask you to build a small project around this repo. You can also proactively do this as part of your application to speed up the process.

This repo is a synthetic data platform containing mock data csv files, Airflow DAGs, dbt models, Evidence dashboards, and a DuckDB data warehouse. Your objective is to create an agent exposed via a CLI to interact with the data platform. This CLI agent should be geared specifically towards ad-hoc questions and analysis. Things like:

- How much in sales did we do last quarter?
- Which two products are most frequently bought together?
- Are there any anomalies with how we sell products?
- What's our average customer lifetime value?
- ... and other, more complex things!

To complete this, fork the repo and build a CLI agent where you can send questions like the ones above. We have no particular requirements around languages, model providers, methods, etc - instead, we want you to demonstrate how you think about these problems! While this repo is representative of an e-commerce company's data platform, you should aim to keep your implementation generic enough that you could plug in other "mini data platforms". See how much you can infer based on the code and warehouse metadata instead of providing explicit documentation about this data platform to the agent upfront.

To submit, send us a fork of your repo. You should modify / create a new README that outlines your approach and where you'd continue building things if you had more time. This should take no more than a few hours.

## Quick Setup

Run the setup script to initialize everything:

```bash
./setup.sh
```

This will:
1. Generate synthetic data
2. Initialize Airflow and load data into DuckDB
3. Run dbt transformations

Then view the dashboards:

```bash
cd evidence
npm install       # First time only
npm run sources   # Build data sources
npm run dev       # Start dev server
# Open http://localhost:3000
```

## Common Commands

Run `just` to see all available commands.

| Command | Description |
|---------|-------------|
| `just setup` | Full initialization (generate data, init Airflow, run pipeline) |
| `just pipeline` | Run full pipeline: sync → ingest → transform |
| `just sync` | Sync sources.yml manifest with CSV files on disk |
| `just ingest` | Load all manifest sources into DuckDB raw layer |
| `just transform` | Run dbt staging + marts transformations |
| `just query` | Open interactive DuckDB shell |
| `just agent` | Launch the Astro agent CLI |

**Adding new data sources**: Drop a CSV in `sources/<system>/` and run `just pipeline`.

---

## Manual Setup (Advanced)

<details>
<summary>Click to expand manual setup steps</summary>

### 1. Install dependencies

```bash
uv sync
```

### 2. Generate synthetic data

```bash
uv run python scripts/generate_all.py
```

### 3. Initialize Airflow

First, update `airflow/airflow.cfg` to use an absolute path for the database:

```bash
cd airflow
# Update sql_alchemy_conn in airflow.cfg to:
# sql_alchemy_conn = sqlite:////absolute/path/to/your/mini-data-platform/airflow/airflow.db

export AIRFLOW_HOME=$(pwd)
uv run airflow db migrate
```

### 4. Run ingestion DAG

```bash
# From airflow/ directory
export AIRFLOW_HOME=$(pwd)
uv run python dags/ingest_sources.py
```

### 5. Run dbt transformations

```bash
# From airflow/ directory
export AIRFLOW_HOME=$(pwd)
uv run python dags/run_dbt.py

# Or run dbt directly
cd ../dbt_project
uv run dbt build --profiles-dir .
```

</details>

## Project Structure

```sh
mini-data-platform/
├── sources/              # Raw source data (CSV files)
│   ├── sources.yml       # Source manifest (auto-synced by scripts/sync_sources.py)
│   ├── postgres/         # Sales, products, users
│   ├── salesforce/       # Marketing campaigns
│   └── analytics/        # Page view events
├── airflow/
│   ├── dags/            # Airflow DAGs for ingestion and transformation
│   │   ├── ingest_sources.py  # Load all manifest sources → raw schema
│   │   ├── run_dbt.py   # Run dbt staging → marts pipeline
│   │   └── build_evidence.py  # Build Evidence dashboards
│   └── utils/           # Shared utilities
├── justfile              # Command runner — run `just` to see all recipes
├── warehouse/           # DuckDB database (data.duckdb)
├── dbt_project/         # dbt transformations
│   └── models/
│       ├── staging/     # Clean raw data (5 models)
│       └── marts/       # Analytics-ready tables (3 models)
├── evidence/            # Evidence BI dashboards
│   ├── pages/           # Dashboard pages (index, sales, products, customers)
│   └── sources/         # SQL queries and connection
└── scripts/             # Data generation scripts
```

## Data Pipeline

### Raw Layer (`raw` schema)

- Loaded by `ingest_sources` DAG from `sources/sources.yml` manifest
- 5 tables: products, users, transactions, campaigns, pageviews

### Staging Layer (`staging` schema)

- Created by dbt
- 5 views: stg_products, stg_users, stg_transactions, stg_campaigns, stg_pageviews

### Marts Layer (`marts` schema)

- Created by dbt
- Denormalized tables for analysis
- 3 tables:
  - `dim_products`: Current product catalog (62 products)
  - `dim_customers`: Current customer info (5,000 customers)
  - `fct_orders`: Order line items with dimensions (35,980 rows)

## Data Volumes

- **Raw**: ~93K total rows across 5 tables
- **Staging**: Same as raw (views)
- **Marts**: 5,062 dimension rows + 35,980 fact rows
- **Database Size**: ~5-10 MB (DuckDB)

## Evidence Dashboards

The project includes interactive dashboards built with Evidence:

### Available Dashboards

1. **Overview** (`/`) - Key metrics, revenue trends, category performance
2. **Sales** (`/sales`) - Daily/monthly sales, country analysis, recent orders
3. **Products** (`/products`) - Product performance, category trends, price analysis
4. **Customers** (`/customers`) - Customer segments, lifetime value, acquisition trends

### Running Evidence

```bash
cd evidence
npm install       # First time only
npm run sources   # Build data sources
npm run dev       # Start dev server
```

Then open http://localhost:3000 to view dashboards.

**Note**: Evidence connects to the DuckDB warehouse at `../warehouse/data.duckdb` and queries the `marts` schema through pass-through SQL files (`fct_orders.sql`, `dim_customers.sql`, `dim_products.sql`).

### Building Evidence (Static Site)

```bash
# Using Airflow DAG
cd airflow
uv run python dags/build_evidence.py

# Or build directly
cd evidence
npm run build
```
