"""Improvement Agent. Synthesizes findings from all prior agents into
actionable, prioritized recommendations using an LLM."""
from __future__ import annotations

import json

from agents.fallback_content import fallback_recommendations, is_llm_placeholder
from agents.llm_utils import run_llm_prompt

INSTRUCTION = """You are an expert software engineer specializing in code and repository \
improvement. You will be given structured findings from a Repository Agent, a Security \
Agent, an Architecture Agent, and a Quality Agent. Produce a concise, prioritized list of \
actionable recommendations grouped under these headings:

1. Security fixes (most critical first)
2. Architecture & design improvements
3. Code quality & maintainability
4. Feature/functionality suggestions

Keep each bullet to one or two sentences. Be specific and reference concrete findings \
(file names, endpoint counts, vulnerability types) where available. Do not invent facts \
not present in the findings."""


async def run_improvement_agent(
    repository_result: dict, security_result: dict, architecture_result: dict, quality_result: dict
) -> tuple[str, int]:
    """Asks the LLM to synthesize recommendations from all prior stage outputs.

    Args:
        repository_result: Output of the Repository Agent.
        security_result: Output of the Security Agent.
        architecture_result: Output of the Architecture Agent.
        quality_result: Output of the Quality Agent.

    Returns:
        A tuple of (recommendations_text, tokens_used).
    """
    findings = {
        "repository": {
            "repo_info": repository_result.get("context", {}).get("repo_info", {}),
            "open_issues": repository_result.get("context", {}).get("issues", {}).get("count"),
        },
        "security": {
            "security_score": security_result.get("security_score"),
            "severity_counts": security_result.get("severity_counts"),
            "top_vulnerabilities": security_result.get("vulnerabilities", [])[:3],
        },
        "architecture": {
            "frameworks": architecture_result.get("frameworks"),
            "design_patterns": architecture_result.get("design_patterns"),
            "endpoint_count": len(architecture_result.get("api_endpoints", [])),
            "dependency_count": len(architecture_result.get("dependency_graph", {}).get("dependencies", [])),
        },
        "quality": {
            "pylint_average": quality_result.get("pylint", {}).get("average_score"),
            "maintainability_index": quality_result.get("complexity", {}).get("maintainability_index"),
            "average_complexity": quality_result.get("complexity", {}).get("average_complexity"),
            "technical_debt_score": quality_result.get("technical_debt_score"),
        },
    }

    prompt = f"Findings:\n{json.dumps(findings, default=str)}\n\nProduce the recommendations now."
    text, tokens_used = await run_llm_prompt("improvement_recommender", INSTRUCTION, prompt)

    if is_llm_placeholder(text):
        return fallback_recommendations(findings), tokens_used
    return text, tokens_used


def summarize(recommendations_text: str) -> str:
    first_line = next((line for line in recommendations_text.splitlines() if line.strip()), "")
    return f"Generated recommendations. {first_line[:140]}"
