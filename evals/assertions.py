"""Assertion helpers for evaluating agent answers against ground truth."""

import re
from dataclasses import dataclass


@dataclass
class AssertionResult:
    passed: bool
    message: str


def check_assertion(answer: str, assertion: dict) -> AssertionResult:
    """Dispatch an assertion check based on its type."""
    dispatch = {
        "exact_number": _check_exact_number,
        "row_count": _check_exact_number,
        "approx_number": _check_approx_number,
        "contains_all": _check_contains_all,
        "contains_any": _check_contains_any,
        "ordered_list": _check_ordered_list,
    }
    checker = dispatch.get(assertion["type"])
    if checker is None:
        return AssertionResult(False, f"Unknown assertion type: {assertion['type']}")
    return checker(answer, assertion)


def _extract_numbers(text: str) -> list[float]:
    """Extract all numbers from text, handling commas, dollar signs, and suffixes.

    Handles formats like: 35980, 35,980, $1,006.25, 18.6 million, etc.
    """
    cleaned = text.replace("$", "")
    raw_matches = re.findall(r"[\d,]+\.?\d*", cleaned)
    numbers = []
    for match in raw_matches:
        try:
            numbers.append(float(match.replace(",", "")))
        except ValueError:
            continue

    for pattern, multiplier in [
        (r"([\d,.]+)\s*million", 1_000_000),
        (r"([\d,.]+)\s*billion", 1_000_000_000),
    ]:
        for m in re.findall(pattern, text, re.IGNORECASE):
            try:
                numbers.append(float(m.replace(",", "")) * multiplier)
            except ValueError:
                continue

    return numbers


def _check_exact_number(answer: str, assertion: dict) -> AssertionResult:
    expected = float(assertion["value"])
    numbers = _extract_numbers(answer)
    if expected in numbers:
        return AssertionResult(True, f"Found exact number {expected}")
    return AssertionResult(
        False,
        f"Expected exact number {expected}, found: {numbers}",
    )


def _check_approx_number(answer: str, assertion: dict) -> AssertionResult:
    expected = float(assertion["value"])
    tolerance = float(assertion.get("tolerance", 0.01))
    relative = assertion.get("relative", False)
    numbers = _extract_numbers(answer)

    for n in numbers:
        if relative:
            if expected != 0 and abs(n - expected) / abs(expected) <= tolerance:
                return AssertionResult(
                    True, f"Found {n} within {tolerance * 100}% of {expected}"
                )
        else:
            if abs(n - expected) <= tolerance:
                return AssertionResult(
                    True, f"Found {n} within +/-{tolerance} of {expected}"
                )
    return AssertionResult(
        False,
        f"No number within tolerance of {expected} "
        f"(tol={tolerance}, relative={relative}). Found: {numbers}",
    )


def _check_contains_all(answer: str, assertion: dict) -> AssertionResult:
    values = assertion["values"]
    lower_answer = answer.lower()
    missing = [v for v in values if v.lower() not in lower_answer]
    if not missing:
        return AssertionResult(True, f"Answer contains all of {values}")
    return AssertionResult(
        False, f"Answer missing: {missing} (expected all of {values})"
    )


def _check_contains_any(answer: str, assertion: dict) -> AssertionResult:
    values = assertion["values"]
    lower_answer = answer.lower()
    found = [v for v in values if v.lower() in lower_answer]
    if found:
        return AssertionResult(True, f"Answer contains: {found}")
    return AssertionResult(False, f"Answer contains none of {values}")


def _check_ordered_list(answer: str, assertion: dict) -> AssertionResult:
    """Check that items appear in the answer in the specified order."""
    values = assertion["values"]
    lower_answer = answer.lower()
    positions = []
    for v in values:
        pos = lower_answer.find(v.lower())
        if pos == -1:
            return AssertionResult(
                False, f"'{v}' not found in answer (checking order of {values})"
            )
        positions.append(pos)

    if positions == sorted(positions):
        return AssertionResult(True, f"Items appear in correct order: {values}")
    return AssertionResult(
        False,
        f"Items out of order. Expected {values}, "
        f"positions: {list(zip(values, positions))}",
    )
