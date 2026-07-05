"""Security Agent. Runs static vulnerability scanning over the local checkout."""
from __future__ import annotations

from tools.static_analysis import run_security_scan


async def run_security_agent(local_path: str) -> dict:
    """Runs the security scan and returns its full result.

    Args:
        local_path: Local filesystem path to the repository checkout.

    Returns:
        The dict produced by tools.static_analysis.run_security_scan.
    """
    return await run_security_scan(local_path)


def summarize(result: dict) -> str:
    if result.get("error"):
        return f"Security scan could not complete: {result['error']}"
    counts = result.get("severity_counts", {})
    score = result.get("security_score")
    return (
        f"Security score {score}/100 — "
        f"{counts.get('HIGH', 0)} high, {counts.get('MEDIUM', 0)} medium, "
        f"{counts.get('LOW', 0)} low severity findings."
    )
