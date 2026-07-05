"""
GitHub MCP-style toolset.

This module exposes GitHub repository context (README, issues, pull requests,
commits, release history, repository metadata) to the agent pipeline through a
small set of async functions, mirroring the capabilities of an MCP GitHub
server but implemented directly against the GitHub REST API. No external MCP
server process is required.

Set GITHUB_TOKEN in the environment to raise the (otherwise very low)
unauthenticated GitHub API rate limit. The tools work without a token too.
"""
from __future__ import annotations

import asyncio
import base64
import os
import re
from typing import Any

import requests

GITHUB_API_BASE = "https://api.github.com"
_REPO_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$"
)


class GitHubToolError(Exception):
    """Raised when a GitHub API call fails in a way callers should surface."""


def parse_repo_url(repo_url: str) -> tuple[str, str]:
    """Extracts (owner, repo) from a GitHub repository URL.

    Args:
        repo_url: A GitHub repository URL, e.g. https://github.com/owner/repo

    Returns:
        A tuple of (owner, repo).

    Raises:
        GitHubToolError: If the URL is not a recognizable GitHub repo URL.
    """
    match = _REPO_URL_RE.match(repo_url.strip())
    if not match:
        raise GitHubToolError(f"Invalid GitHub repository URL: {repo_url!r}")
    return match.group(1), match.group(2)


def _session() -> requests.Session:
    session = requests.Session()
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    session.headers.update(headers)
    return session


def _get(url: str, params: dict | None = None) -> Any:
    session = _session()
    response = session.get(url, params=params, timeout=20)
    if response.status_code == 404:
        raise GitHubToolError(f"Not found: {url}")
    if response.status_code == 403 and "rate limit" in response.text.lower():
        raise GitHubToolError(
            "GitHub API rate limit exceeded. Set a GITHUB_TOKEN environment "
            "variable to raise the limit."
        )
    if not response.ok:
        raise GitHubToolError(f"GitHub API error {response.status_code} for {url}: {response.text[:300]}")
    return response.json()


async def get_repo_info(repo_url: str) -> dict:
    """Fetches core repository metadata (stars, language, size, description, default branch).

    Args:
        repo_url: The full GitHub repository URL.

    Returns:
        A dictionary of repository metadata, or an error message.
    """
    try:
        owner, repo = parse_repo_url(repo_url)
        data = await asyncio.to_thread(_get, f"{GITHUB_API_BASE}/repos/{owner}/{repo}")
        return {
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "stars": data.get("stargazers_count"),
            "forks": data.get("forks_count"),
            "open_issues": data.get("open_issues_count"),
            "primary_language": data.get("language"),
            "size_kb": data.get("size"),
            "default_branch": data.get("default_branch"),
            "license": (data.get("license") or {}).get("name"),
            "topics": data.get("topics", []),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "archived": data.get("archived", False),
        }
    except GitHubToolError as exc:
        return {"error": str(exc)}


async def get_readme(repo_url: str) -> dict:
    """Fetches and decodes the repository README.

    Args:
        repo_url: The full GitHub repository URL.

    Returns:
        A dictionary with the README text under 'content', or an error message.
    """
    try:
        owner, repo = parse_repo_url(repo_url)
        data = await asyncio.to_thread(_get, f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme")
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
        return {"path": data.get("path"), "content": content}
    except GitHubToolError as exc:
        return {"error": str(exc)}


async def list_issues(repo_url: str, state: str = "open", limit: int = 20) -> dict:
    """Lists repository issues (excluding pull requests).

    Args:
        repo_url: The full GitHub repository URL.
        state: One of 'open', 'closed', 'all'.
        limit: Maximum number of issues to return.

    Returns:
        A dictionary with a list of issues under 'issues', or an error message.
    """
    try:
        owner, repo = parse_repo_url(repo_url)
        data = await asyncio.to_thread(
            _get,
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues",
            {"state": state, "per_page": min(limit, 100)},
        )
        issues = [
            {
                "number": item.get("number"),
                "title": item.get("title"),
                "state": item.get("state"),
                "labels": [label.get("name") for label in item.get("labels", [])],
                "comments": item.get("comments"),
                "created_at": item.get("created_at"),
            }
            for item in data
            if "pull_request" not in item
        ][:limit]
        return {"issues": issues, "count": len(issues)}
    except GitHubToolError as exc:
        return {"error": str(exc)}


async def list_pull_requests(repo_url: str, state: str = "open", limit: int = 20) -> dict:
    """Lists repository pull requests.

    Args:
        repo_url: The full GitHub repository URL.
        state: One of 'open', 'closed', 'all'.
        limit: Maximum number of pull requests to return.

    Returns:
        A dictionary with a list of pull requests under 'pull_requests', or an error message.
    """
    try:
        owner, repo = parse_repo_url(repo_url)
        data = await asyncio.to_thread(
            _get,
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls",
            {"state": state, "per_page": min(limit, 100)},
        )
        pull_requests = [
            {
                "number": item.get("number"),
                "title": item.get("title"),
                "state": item.get("state"),
                "created_at": item.get("created_at"),
                "merged_at": item.get("merged_at"),
                "user": (item.get("user") or {}).get("login"),
            }
            for item in data
        ][:limit]
        return {"pull_requests": pull_requests, "count": len(pull_requests)}
    except GitHubToolError as exc:
        return {"error": str(exc)}


async def list_commits(repo_url: str, limit: int = 20) -> dict:
    """Lists the most recent commits on the default branch.

    Args:
        repo_url: The full GitHub repository URL.
        limit: Maximum number of commits to return.

    Returns:
        A dictionary with a list of commits under 'commits', or an error message.
    """
    try:
        owner, repo = parse_repo_url(repo_url)
        data = await asyncio.to_thread(
            _get,
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
            {"per_page": min(limit, 100)},
        )
        commits = [
            {
                "sha": item.get("sha", "")[:7],
                "message": (item.get("commit") or {}).get("message", "").split("\n")[0],
                "author": ((item.get("commit") or {}).get("author") or {}).get("name"),
                "date": ((item.get("commit") or {}).get("author") or {}).get("date"),
            }
            for item in data
        ][:limit]
        return {"commits": commits, "count": len(commits)}
    except GitHubToolError as exc:
        return {"error": str(exc)}


async def list_releases(repo_url: str, limit: int = 10) -> dict:
    """Lists repository release history.

    Args:
        repo_url: The full GitHub repository URL.
        limit: Maximum number of releases to return.

    Returns:
        A dictionary with a list of releases under 'releases', or an error message.
    """
    try:
        owner, repo = parse_repo_url(repo_url)
        data = await asyncio.to_thread(
            _get,
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases",
            {"per_page": min(limit, 100)},
        )
        releases = [
            {
                "tag_name": item.get("tag_name"),
                "name": item.get("name"),
                "published_at": item.get("published_at"),
                "prerelease": item.get("prerelease"),
            }
            for item in data
        ][:limit]
        return {"releases": releases, "count": len(releases)}
    except GitHubToolError as exc:
        return {"error": str(exc)}


async def fetch_full_repository_context(repo_url: str) -> dict:
    """Fetches repo info, README, issues, pull requests, commits, and releases concurrently.

    Args:
        repo_url: The full GitHub repository URL.

    Returns:
        A dictionary combining all repository context under descriptive keys.
    """
    (
        repo_info,
        readme,
        issues,
        pull_requests,
        commits,
        releases,
    ) = await asyncio.gather(
        get_repo_info(repo_url),
        get_readme(repo_url),
        list_issues(repo_url),
        list_pull_requests(repo_url),
        list_commits(repo_url),
        list_releases(repo_url),
    )
    return {
        "repo_info": repo_info,
        "readme": readme,
        "issues": issues,
        "pull_requests": pull_requests,
        "commits": commits,
        "releases": releases,
    }
