"""Architecture Agent. Produces architectural intelligence beyond code review."""
from __future__ import annotations

from tools.architecture_analysis import run_architecture_analysis


async def run_architecture_agent(local_path: str) -> dict:
    """Runs the architecture analysis suite.

    Args:
        local_path: Local filesystem path to the repository checkout.

    Returns:
        The dict produced by tools.architecture_analysis.run_architecture_analysis.
    """
    return await run_architecture_analysis(local_path)


def summarize(result: dict) -> str:
    frameworks = result.get("frameworks", [])
    endpoints = result.get("api_endpoints", [])
    patterns = result.get("design_patterns", [])
    deps = result.get("dependency_graph", {}).get("dependencies", [])
    framework_text = ", ".join(frameworks) if frameworks else "no recognized frameworks"
    return (
        f"Detected stack: {framework_text}. Found {len(endpoints)} API endpoints, "
        f"{len(deps)} dependencies, and {len(patterns)} design patterns "
        f"({', '.join(patterns) if patterns else 'none detected'})."
    )
