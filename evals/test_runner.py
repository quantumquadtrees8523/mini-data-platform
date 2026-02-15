"""Pytest-compatible evaluation runner for the Astro agent.

Usage:
    pytest evals/ -v                    # run all eval cases
    pytest evals/ -v -k "revenue"       # run cases with 'revenue' in the id
    pytest evals/ -v -k "ground_truth"  # SQL-only validation (no API key)
    pytest evals/ -v --tb=short         # concise tracebacks
"""

import pytest
import yaml
from pathlib import Path

from evals.assertions import check_assertion

_CASES_PATH = Path(__file__).parent / "cases.yml"
_CASES = []
if _CASES_PATH.exists():
    with open(_CASES_PATH) as _f:
        _data = yaml.safe_load(_f)
        _CASES = _data.get("cases", [])


def _case_id(case: dict) -> str:
    return case.get("id", case["question"][:50])


@pytest.mark.parametrize("case", _CASES, ids=[_case_id(c) for c in _CASES])
def test_ground_truth_sql(case, duckdb_conn):
    """Validate that each verification SQL query runs without error.

    No Gemini API key needed -- this is an offline sanity check that
    ensures the test case definitions in cases.yml are valid.
    """
    verification_sql = case.get("verification_sql")
    if not verification_sql:
        pytest.skip("No verification SQL defined")

    result = duckdb_conn.execute(verification_sql.strip()).fetchall()
    assert len(result) > 0, f"Verification SQL returned no rows for case '{case.get('id')}'"


@pytest.mark.parametrize("case", _CASES, ids=[_case_id(c) for c in _CASES])
def test_agent_eval(case, agent, duckdb_conn):
    """Run a single evaluation case end-to-end.

    1. Run verification SQL to confirm ground truth.
    2. Ask the agent the question.
    3. Check all assertions against the agent's answer.
    """
    question = case["question"]
    verification_sql = case.get("verification_sql")
    assertions = case.get("assertions", [])

    # Step 1: Verify ground truth SQL
    ground_truth = None
    if verification_sql:
        try:
            ground_truth = duckdb_conn.execute(verification_sql.strip()).fetchall()
        except Exception as e:
            pytest.fail(
                f"Verification SQL failed for '{case.get('id', '?')}': {e}\n"
                f"SQL: {verification_sql}"
            )

    # Step 2: Ask the agent
    answer = agent.ask(question)
    sources = agent.get_sources()

    # Step 3: Validate assertions
    failures = []
    for i, assertion in enumerate(assertions):
        result = check_assertion(answer, assertion)
        if not result.passed:
            failures.append(
                f"  Assertion #{i + 1} ({assertion['type']}): {result.message}"
            )

    if failures:
        detail = "\n".join(failures)
        pytest.fail(
            f"\nQuestion: {question}\n"
            f"Agent answer: {answer[:500]}\n"
            f"Ground truth SQL result: {ground_truth}\n"
            f"Sources used: {sources}\n"
            f"Failed assertions:\n{detail}"
        )
