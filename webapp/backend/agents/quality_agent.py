"""Quality Agent. Aggregates linting, complexity, and maintainability into
a technical-debt estimate."""
from __future__ import annotations

from tools.static_analysis import run_complexity_analysis, run_pylint_aggregate


async def run_quality_agent(local_path: str) -> dict:
    """Runs pylint + radon and derives a technical debt estimate.

    Args:
        local_path: Local filesystem path to the repository checkout.

    Returns:
        A dict with 'pylint', 'complexity', and 'technical_debt_score'
        (0-100, higher means MORE debt / worse).
    """
    pylint_result = await run_pylint_aggregate(local_path)
    complexity_result = await run_complexity_analysis(local_path)

    pylint_score = pylint_result.get("average_score")
    maintainability = complexity_result.get("maintainability_index")
    avg_complexity = complexity_result.get("average_complexity", 0.0)

    # Technical debt heuristic: weighted inverse of quality signals we have.
    # Missing signals are simply excluded rather than assumed.
    debt_components = []
    if pylint_score is not None:
        debt_components.append(100 - pylint_score)
    if maintainability is not None:
        debt_components.append(100 - maintainability)
    debt_components.append(min(100, avg_complexity * 8))  # complexity penalty, capped

    technical_debt_score = round(sum(debt_components) / len(debt_components), 1) if debt_components else None

    return {
        "pylint": pylint_result,
        "complexity": complexity_result,
        "technical_debt_score": technical_debt_score,
    }


def summarize(result: dict) -> str:
    pylint_score = result.get("pylint", {}).get("average_score")
    maintainability = result.get("complexity", {}).get("maintainability_index")
    debt = result.get("technical_debt_score")
    return (
        f"Pylint avg {pylint_score if pylint_score is not None else 'n/a'}/100, "
        f"maintainability index {maintainability if maintainability is not None else 'n/a'}, "
        f"estimated technical debt score {debt if debt is not None else 'n/a'}/100."
    )
