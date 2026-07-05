"""Executive Report Agent. The final pipeline stage.

Computes the scores and chart-ready data behind the Executive Dashboard, then
asks an LLM to write a short narrative executive summary. Scores are computed
deterministically in Python (not by the LLM) so the dashboard numbers stay
stable and explainable.
"""
from __future__ import annotations

import os

from agents.fallback_content import fallback_narrative, is_llm_placeholder
from agents.llm_utils import run_llm_prompt

INSTRUCTION = """You are a technical lead writing a short executive summary for \
non-technical stakeholders. You will receive computed scores and key findings for a \
GitHub repository. Write 4-6 sentences: overall health, the single biggest risk, and the \
single biggest opportunity. Plain language, no bullet points, no repeating raw numbers \
verbatim in a list — weave them into prose."""


def _ai_readiness_score(repository_result: dict, architecture_result: dict) -> float:
    context = repository_result.get("context", {})
    readme = context.get("readme", {}).get("content", "") or ""
    structure = architecture_result.get("folder_structure", {})
    languages = structure.get("language_distribution", {})

    points = 0
    total = 5

    if len(readme) > 200:
        points += 1
    if any(key in languages for key in ("py", "ts", "js")):
        points += 1  # common, well-tooled languages for AI-assisted dev
    if architecture_result.get("dependency_graph", {}).get("dependencies"):
        points += 1  # explicit, machine-readable dependency manifest
    if architecture_result.get("api_endpoints"):
        points += 1  # structured interfaces are easier for agents to reason about
    if "test" in languages or structure.get("folder_sizes_bytes", {}).get("tests"):
        points += 1

    return round((points / total) * 100, 1)


def _deployment_readiness_score(local_path: str | None, architecture_result: dict, security_result: dict) -> float:
    points = 0
    total = 5
    layers = architecture_result.get("layers", {})

    if "Docker" in architecture_result.get("frameworks", []):
        points += 1
    if local_path and os.path.exists(os.path.join(local_path, ".github", "workflows")):
        points += 1
    if local_path and any(
        os.path.exists(os.path.join(local_path, name)) for name in ("requirements.txt", "package.json", "pyproject.toml")
    ):
        points += 1
    if local_path and any(
        os.path.exists(os.path.join(local_path, name)) for name in ("LICENSE", "LICENSE.md", "LICENSE.txt")
    ):
        points += 1
    severity_counts = security_result.get("severity_counts", {})
    if severity_counts.get("HIGH", 0) == 0:
        points += 1

    return round((points / total) * 100, 1)


def _overall_score(security_score, maintainability, technical_debt_score, ai_readiness, deployment_readiness) -> float:
    components = []
    weights = []
    if security_score is not None:
        components.append(security_score)
        weights.append(0.3)
    if maintainability is not None:
        components.append(maintainability)
        weights.append(0.25)
    if technical_debt_score is not None:
        components.append(100 - technical_debt_score)
        weights.append(0.2)
    components.append(ai_readiness)
    weights.append(0.125)
    components.append(deployment_readiness)
    weights.append(0.125)

    if not components:
        return 0.0
    weight_sum = sum(weights)
    weighted = sum(c * w for c, w in zip(components, weights)) / weight_sum
    return round(weighted, 1)


async def run_executive_report_agent(
    repository_result: dict,
    security_result: dict,
    architecture_result: dict,
    quality_result: dict,
    recommendations_text: str,
) -> dict:
    """Computes final scores/chart data and generates the narrative summary.

    Args:
        repository_result: Output of the Repository Agent.
        security_result: Output of the Security Agent.
        architecture_result: Output of the Architecture Agent.
        quality_result: Output of the Quality Agent.
        recommendations_text: Output of the Improvement Agent.

    Returns:
        A dict shaped for direct consumption by the frontend dashboard.
    """
    local_path = repository_result.get("local_path")
    security_score = security_result.get("security_score")
    maintainability = quality_result.get("complexity", {}).get("maintainability_index")
    technical_debt_score = quality_result.get("technical_debt_score")

    ai_readiness = _ai_readiness_score(repository_result, architecture_result)
    deployment_readiness = _deployment_readiness_score(local_path, architecture_result, security_result)
    overall_score = _overall_score(security_score, maintainability, technical_debt_score, ai_readiness, deployment_readiness)

    scores = {
        "overall_score": overall_score,
        "security_score": security_score,
        "maintainability_score": maintainability,
        "technical_debt_score": technical_debt_score,
        "ai_readiness_score": ai_readiness,
        "deployment_readiness_score": deployment_readiness,
    }

    prompt = (
        f"Scores: {scores}\n"
        f"Repo: {repository_result.get('context', {}).get('repo_info', {})}\n"
        f"Top vulnerabilities: {security_result.get('vulnerabilities', [])[:3]}\n"
        f"Detected stack: {architecture_result.get('frameworks', [])}\n"
        f"Recommendations already generated:\n{recommendations_text[:1200]}\n\n"
        "Write the executive summary now."
    )
    narrative, tokens_used = await run_llm_prompt("executive_report_generator", INSTRUCTION, prompt)
    if is_llm_placeholder(narrative):
        narrative = fallback_narrative(scores, repository_result.get("context", {}).get("repo_info", {}), architecture_result.get("frameworks", []))

    charts = {
        "vulnerabilities_by_severity": security_result.get("severity_counts", {}),
        "top_complex_files": quality_result.get("complexity", {}).get("files", [])[:10],
        "language_distribution": architecture_result.get("folder_structure", {}).get("language_distribution", {}),
        "folder_sizes_bytes": architecture_result.get("folder_structure", {}).get("folder_sizes_bytes", {}),
    }

    return {
        "scores": scores,
        "narrative_summary": narrative,
        "recommendations": recommendations_text,
        "charts": charts,
        "architecture": {
            "layers": architecture_result.get("layers", {}),
            "frameworks": architecture_result.get("frameworks", []),
            "design_patterns": architecture_result.get("design_patterns", []),
            "api_endpoints": architecture_result.get("api_endpoints", []),
            "dependency_graph": architecture_result.get("dependency_graph", {}),
        },
        "repository": repository_result.get("context", {}),
        "_tokens_used": tokens_used,
    }


def summarize(result: dict) -> str:
    return f"Overall score {result['scores']['overall_score']}/100. Executive summary and dashboard ready."
