"""Repository Agent.

The first stage of the pipeline. Combines:
  - GitHub MCP-style metadata (README, issues, PRs, commits, releases, repo info)
  - a local shallow clone (needed by later stages for real static analysis)
"""
from __future__ import annotations

from tools import github_tool
from tools.repo_clone import RepoCloneError, clone_repository


async def run_repository_agent(repo_url: str) -> dict:
    """Gathers full repository context and produces a local checkout.

    Args:
        repo_url: The full GitHub repository URL.

    Returns:
        A dict with 'context' (GitHub metadata) and 'local_path' (clone path),
        or 'error' if the repository could not be cloned.
    """
    context = await github_tool.fetch_full_repository_context(repo_url)

    try:
        local_path = await clone_repository(repo_url)
    except RepoCloneError as exc:
        return {"context": context, "local_path": None, "error": str(exc)}

    return {"context": context, "local_path": local_path, "error": None}


def summarize(result: dict) -> str:
    context = result.get("context", {})
    repo_info = context.get("repo_info", {})
    if result.get("error"):
        return f"Fetched GitHub metadata, but clone failed: {result['error']}"
    issues_count = context.get("issues", {}).get("count", 0)
    prs_count = context.get("pull_requests", {}).get("count", 0)
    commits_count = context.get("commits", {}).get("count", 0)
    releases_count = context.get("releases", {}).get("count", 0)
    return (
        f"Loaded {repo_info.get('full_name', 'repository')} "
        f"({repo_info.get('primary_language', 'unknown language')}, "
        f"{repo_info.get('stars', 0)}★) — README, {issues_count} issues, "
        f"{prs_count} PRs, {commits_count} recent commits, {releases_count} releases."
    )
