"""Shared pytest fixtures for agent evaluation."""

import os
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def pytest_collection_modifyitems(config, items):
    """Mark all eval tests with the 'eval' marker automatically."""
    for item in items:
        if "evals" in str(item.fspath):
            item.add_marker(pytest.mark.eval)


@pytest.fixture(scope="session")
def db_path() -> Path:
    """Resolve the warehouse database path."""
    path = PROJECT_ROOT / "warehouse" / "data.duckdb"
    if not path.exists():
        pytest.skip(f"Database not found at {path}. Run `just pipeline` first.")
    return path


@pytest.fixture(scope="session")
def data_layer(db_path):
    """Create a DataLayer connected to the warehouse (session-scoped)."""
    from astro.db import DataLayer

    dl = DataLayer(db_path)
    yield dl
    dl.close()


@pytest.fixture(scope="session")
def duckdb_conn(db_path):
    """Raw DuckDB connection for running verification SQL."""
    import duckdb

    conn = duckdb.connect(str(db_path), read_only=True)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def api_key() -> str:
    """Resolve the Gemini API key from the environment."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        pytest.skip(
            "GEMINI_API_KEY or GOOGLE_API_KEY not set. "
            "Export the key to run agent evaluations."
        )
    return key.strip()


@pytest.fixture
def agent(data_layer, api_key):
    """Create a fresh Agent per test for conversation isolation.

    Function-scoped so that conversation history from one test case
    does not leak into the next. Each test gets a clean agent.
    """
    from astro.agent import Agent

    return Agent(data_layer, api_key, model="gemini-2.0-flash")


@pytest.fixture(scope="session")
def eval_cases() -> list[dict]:
    """Load evaluation cases from cases.yml."""
    cases_path = Path(__file__).parent / "cases.yml"
    if not cases_path.exists():
        pytest.fail(f"Evaluation cases file not found: {cases_path}")
    with open(cases_path) as f:
        data = yaml.safe_load(f)
    return data["cases"]
