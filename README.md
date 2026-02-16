## What Was Added
_This document is heavily claude generated and human verified_

Everything below this line, and the sections it modifies, reflects work done on top of the original repo. The original repo shipped with synthetic data generation scripts, Airflow DAGs (one per source table), dbt models, Evidence dashboards, and a DuckDB warehouse. The following changes were introduced across three pull requests.

It is important to note that proving performance of the agent over many types of data was prioritized over portability of the agent to multiple mini-data-platforms. See `future_work.md` for a reference to modularizing the agent and putting up on PyPi.

[High Level Thought Process](https://docs.google.com/document/d/1jtkSHYeztzElSry4m3hesk9kLJhFrS2geD90AqAQa_A/edit?tab=t.0)

### PR 1 — Astro CLI Agent (`astro/`)

Added by the user with Claude assistance. This is the core deliverable: an interactive CLI agent that answers natural language analytical questions against the DuckDB warehouse.

- **`astro/` package** — A Gemini-powered REPL agent with five tools (`list_schemas`, `list_tables`, `describe_table`, `sample_data`, `execute_query`) that introspects the warehouse schema and runs SQL on demand.
- **`plans/agent-high-level-design.md`** — Architecture documentation covering module responsibilities, tool descriptions, execution flow, and output strategy.
- **Updated `pyproject.toml`** — Added `google-genai`, `prompt-toolkit`, and `python-dotenv` dependencies.
- **Added `.env.example`** — Template for the `GEMINI_API_KEY` environment variable.

### PR 2 — Manifest-Driven Data Ingestion

Added by the user with Claude assistance. Replaced the original five per-source ingestion DAGs with a single manifest-driven pipeline and made it trivial to add or remove data sources.

- **`sources/sources.yml`** — A YAML manifest that declares every CSV and its target table.
- **`scripts/sync_sources.py`** — Auto-discovers CSVs on disk and keeps `sources.yml` in sync.
- **`airflow/dags/ingest_sources.py`** — Single DAG that reads the manifest and loads all sources into the `raw` schema (replaced the five individual `ingest_*.py` DAGs).
- **`airflow/utils/warehouse.py`** — Shared DuckDB utility functions.
- **`plans/data-ingestion-design.md`** — Design document for the manifest-driven ingestion approach.
- **Three new real-world CSV datasets** added to demonstrate the drop-in workflow:
  - `sources/postgres/chocolate_sales.csv` (3,283 rows)
  - `sources/postgres/tmdb_movies.csv` (100 rows)
  - `sources/salesforce/StudentPerformanceFactors.csv` (6,607 rows)
- **Updated `justfile`** — Added `just sync`, `just ingest`, `just pipeline`, and other recipes.
- **Updated `setup.sh`** — Streamlined initialization to use the new pipeline.

### PR 3 — Agent Evaluation Framework (`evals/`)

Added by the user with Claude assistance. A pytest-based evaluation suite that validates agent answers against ground-truth SQL queries run directly on the warehouse.

- **`evals/cases.yml`** — 25 YAML-defined test cases (7 basic + 18 edge cases). Each case specifies a natural-language question, a verification SQL query, and one or more assertions. Coverage spans simple counts, filtered aggregations, top-N rankings, NULL handling, time boundaries, payment methods, and geographic queries.
- **`evals/test_runner.py`** — Pytest runner with two parametrized test functions:
  - `test_ground_truth_sql` — Offline sanity check that each verification SQL query executes without error (no API key required).
  - `test_agent_eval` — End-to-end evaluation: runs the verification SQL, asks the agent the question, then checks all assertions against the agent's answer.
- **`evals/assertions.py`** — Assertion helpers supporting six types: `exact_number`, `row_count`, `approx_number` (absolute or relative tolerance), `contains_all`, `contains_any`, and `ordered_list`. Includes a number-extraction utility that handles commas, dollar signs, and suffixes like "million"/"billion".
- **`evals/conftest.py`** — Shared session-scoped fixtures for the DuckDB connection, `DataLayer`, API key resolution (`GEMINI_API_KEY` / `GOOGLE_API_KEY`), and a function-scoped `Agent` fixture for conversation isolation.
- **Updated `justfile`** — Added `just eval` (full suite, requires API key) and `just eval-sql` (SQL-only validation, no API key).
- **Updated `pyproject.toml`** — Added pytest configuration and the `eval` marker.

---

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
| `just eval` | Run full agent evaluation suite (requires `GEMINI_API_KEY`) |
| `just eval-sql` | Run ground-truth SQL validation only (no API key needed) |

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
├── astro/                # [ADDED] Gemini-powered CLI agent
│   ├── agent.py          #   Orchestration, tool dispatch, conversation state
│   ├── cli.py            #   Entry point and REPL loop
│   ├── db.py             #   DuckDB DataLayer and schema introspection
│   ├── display.py        #   Result display formatting
│   └── fmt.py            #   ANSI terminal formatting utilities
├── evals/                # [ADDED] Agent evaluation framework
│   ├── cases.yml         #   25 test cases with ground-truth SQL and assertions
│   ├── test_runner.py    #   Pytest runner (ground-truth + end-to-end tests)
│   ├── assertions.py     #   Assertion helpers (6 types)
│   └── conftest.py       #   Shared fixtures (DB, agent, API key)
├── sources/              # Raw source data (CSV files)
│   ├── sources.yml       # [ADDED] Source manifest (auto-synced by scripts/sync_sources.py)
│   ├── postgres/         # products, users, transactions, chocolate_sales, tmdb_movies
│   ├── salesforce/       # campaigns, StudentPerformanceFactors
│   └── analytics/        # pageviews
├── airflow/
│   ├── dags/             # Airflow DAGs for ingestion and transformation
│   │   ├── ingest_sources.py  # [ADDED] Manifest-driven ingestion (replaced 5 per-source DAGs)
│   │   ├── run_dbt.py    # Run dbt staging → marts pipeline
│   │   └── build_evidence.py  # Build Evidence dashboards
│   └── utils/            # [ADDED] Shared utilities (warehouse.py)
├── plans/                # [ADDED] Architecture documentation
│   ├── agent-high-level-design.md
│   └── data-ingestion-design.md
├── scripts/              # Data generation and sync scripts
│   ├── sync_sources.py   # [ADDED] Auto-sync sources.yml with CSV files on disk
│   ├── generate_all.py
│   └── ...               # Per-table generators
├── justfile              # Command runner — run `just` to see all recipes
├── warehouse/            # DuckDB database (data.duckdb)
├── dbt_project/          # dbt transformations
│   └── models/
│       ├── staging/      # Clean raw data (5 models)
│       └── marts/        # Analytics-ready tables (3 models)
├── evidence/             # Evidence BI dashboards
│   ├── pages/            # Dashboard pages (index, sales, products, customers)
│   └── sources/          # SQL queries and connection
└── .env.example          # [ADDED] Template for GEMINI_API_KEY
```

> Items marked **[ADDED]** were introduced in the three PRs described above and are not part of the original repo.

## Data Pipeline

### Raw Layer (`raw` schema)

- Loaded by `ingest_sources` DAG from `sources/sources.yml` manifest
- 8 tables: products, users, transactions, campaigns, pageviews, chocolate_sales, tmdb_movies, StudentPerformanceFactors
- The last 3 tables were added in PR 2 to demonstrate the drop-in CSV workflow

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

- **Raw**: ~103K total rows across 8 tables (original 5 tables ~93K rows + 3 new CSV sources ~10K rows)
- **Staging**: Same as raw (views — covers original 5 tables only; new sources do not yet have staging models)
- **Marts**: 5,062 dimension rows + 35,980 fact rows
- **Database Size**: ~13 MB (DuckDB)

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
