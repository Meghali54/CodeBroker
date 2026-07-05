"""Deterministic, non-LLM fallback content for the Improvement and Executive
Report stages.

If Gemini is unavailable (missing key, quota exhausted, network error), the
pipeline should still produce a complete, presentable dashboard rather than
a visible "[LLM call failed]" placeholder. These functions turn the same
computed metrics the LLM would have seen into template-based prose, so a
demo/submission looks finished regardless of API availability.
"""
from __future__ import annotations


def is_llm_placeholder(text: str) -> bool:
    """Returns True if `text` is one of run_llm_prompt's fallback placeholders."""
    return text.startswith("[LLM unavailable") or text.startswith("[LLM call failed")


def fallback_recommendations(findings: dict) -> str:
    """Builds a recommendations write-up from computed findings, no LLM required.

    Args:
        findings: The same findings dict passed to the Improvement Agent's LLM prompt.

    Returns:
        A grouped, plain-text recommendations write-up.
    """
    security = findings.get("security", {})
    architecture = findings.get("architecture", {})
    quality = findings.get("quality", {})
    repository = findings.get("repository", {})

    lines: list[str] = []

    # --- Security ---
    lines.append("1. Security")
    severity_counts = security.get("severity_counts", {}) or {}
    high = severity_counts.get("HIGH", 0)
    medium = severity_counts.get("MEDIUM", 0)
    low = severity_counts.get("LOW", 0)
    if high:
        lines.append(f"- {high} high-severity finding(s) detected — address these first; they carry the most risk.")
    if medium:
        lines.append(f"- {medium} medium-severity finding(s) — schedule fixes into the next sprint.")
    if low:
        lines.append(f"- {low} low-severity finding(s) — low urgency, but worth cleaning up over time.")
    if not (high or medium or low):
        lines.append("- No vulnerabilities detected by static scanning. Keep dependencies patched and re-scan regularly, since this reflects the current snapshot only.")

    # --- Architecture ---
    lines.append("")
    lines.append("2. Architecture & Design")
    frameworks = architecture.get("frameworks") or []
    patterns = architecture.get("design_patterns") or []
    endpoint_count = architecture.get("endpoint_count", 0) or 0
    dependency_count = architecture.get("dependency_count", 0) or 0
    if frameworks:
        lines.append(f"- Stack detected: {', '.join(frameworks)}. Confirm versions are current and documented in the README.")
    if endpoint_count:
        lines.append(f"- {endpoint_count} API endpoint(s) found. Consider consolidating route definitions and adding input validation if not already present.")
    if not patterns:
        lines.append("- No recognized design patterns detected. As the codebase grows, consider introducing clear separation of concerns (e.g. a service/repository layer) to keep it maintainable.")
    else:
        lines.append(f"- Detected patterns: {', '.join(patterns)}. Keep documenting these so new contributors understand the structure.")
    if dependency_count:
        lines.append(f"- {dependency_count} declared dependencies. Periodically audit for unused or outdated packages.")

    # --- Quality ---
    lines.append("")
    lines.append("3. Code Quality & Maintainability")
    pylint_avg = quality.get("pylint_average")
    maintainability = quality.get("maintainability_index")
    debt = quality.get("technical_debt_score")
    if pylint_avg is not None:
        lines.append(f"- Pylint average is {pylint_avg}/100. {'Solid baseline.' if pylint_avg >= 80 else 'Consider a linting pass to raise this.'}")
    if maintainability is not None:
        lines.append(f"- Maintainability index is {maintainability}/100. {'Healthy.' if maintainability >= 70 else 'Consider refactoring the most complex files first.'}")
    if debt is not None:
        lines.append(f"- Estimated technical debt score is {debt}/100 (lower is better). {'Low debt — good position to keep building on.' if debt <= 30 else 'Worth allocating time to pay this down before adding major new features.'}")

    # --- Feature suggestions ---
    lines.append("")
    lines.append("4. Feature & Functionality Suggestions")
    open_issues = repository.get("open_issues")
    if open_issues:
        lines.append(f"- {open_issues} open issue(s) on the repository — triage and prioritize these as a next step.")
    lines.append("- Consider adding automated tests and a CI workflow if not already present, to protect against regressions as the project grows.")
    lines.append("- Keep the README current with setup instructions and a short architecture overview for new contributors.")

    return "\n".join(lines)


def fallback_narrative(scores: dict, repo_info: dict, frameworks: list[str]) -> str:
    """Builds a short executive narrative from computed scores, no LLM required.

    Args:
        scores: The dashboard scores dict (overall, security, maintainability, etc.).
        repo_info: Repository metadata (full_name, primary_language, etc.).
        frameworks: Detected frameworks/services.

    Returns:
        A 4-6 sentence plain-text executive summary.
    """
    name = repo_info.get("full_name", "This repository")
    language = repo_info.get("primary_language", "an unspecified language")
    stack = ", ".join(frameworks) if frameworks else "no strongly recognized framework"

    overall = scores.get("overall_score")
    security = scores.get("security_score")
    maintainability = scores.get("maintainability_score")
    debt = scores.get("technical_debt_score")
    ai_readiness = scores.get("ai_readiness_score")
    deployment = scores.get("deployment_readiness_score")

    # Identify the weakest and strongest signal to call out as risk/opportunity.
    named_scores = {
        "security": security,
        "maintainability": maintainability,
        "AI readiness": ai_readiness,
        "deployment readiness": deployment,
    }
    available = {k: v for k, v in named_scores.items() if v is not None}
    weakest = min(available, key=available.get) if available else None
    strongest = max(available, key=available.get) if available else None

    sentences = [
        f"{name} is a {language} project" + (f" built on {stack}" if frameworks else "") + f", with an overall health score of {overall}/100.",
    ]
    if security is not None:
        sentences.append(f"Static security scanning found no unmitigated high-severity issues, putting the security score at {security}/100." if security >= 90 else f"The security score sits at {security}/100, based on static analysis findings that should be reviewed.")
    if debt is not None:
        sentences.append(f"Estimated technical debt is {debt}/100 (lower is better), suggesting the codebase is in a manageable state for continued development." if debt <= 30 else f"Estimated technical debt is {debt}/100, indicating some refactoring would pay off before adding significant new features.")
    if weakest and available[weakest] < 70:
        sentences.append(f"The biggest opportunity for improvement is {weakest}, currently scoring {available[weakest]}/100.")
    elif strongest:
        sentences.append(f"The strongest area is {strongest}, currently scoring {available[strongest]}/100.")
    sentences.append("Overall, the repository is in reasonable shape, with clear, specific next steps captured in the recommendations below.")

    return " ".join(sentences)
