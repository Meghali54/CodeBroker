"""Clones a GitHub repository to a local temp directory for static analysis.

Deep static analysis (security scanning, complexity, linting, architecture
detection) needs real files on disk rather than per-file API calls, which
would be slow and rate-limited. This module handles that local checkout.

Uses a blocking subprocess call wrapped in asyncio.to_thread rather than
asyncio.create_subprocess_exec, because asyncio subprocess support requires
the Proactor event loop on Windows, and uvicorn resets the loop policy back
to the Selector loop at startup regardless of what's configured beforehand.
Running the blocking call in a worker thread sidesteps that entirely.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile


class RepoCloneError(Exception):
    pass


def _clone_sync(repo_url: str, temp_dir: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, temp_dir],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stderr


async def clone_repository(repo_url: str) -> str:
    """Shallow-clones a public GitHub repository into a new temp directory.

    Args:
        repo_url: The full URL of the GitHub repository to clone.

    Returns:
        The path to the local clone.

    Raises:
        RepoCloneError: If the clone fails.
    """
    temp_dir = tempfile.mkdtemp(prefix="code_broker_")
    returncode, stderr = await asyncio.to_thread(_clone_sync, repo_url, temp_dir)
    if returncode != 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RepoCloneError(f"Failed to clone repository: {stderr}")
    return temp_dir


def cleanup_directory(path: str) -> None:
    """Best-effort removal of a local clone directory."""
    if path and os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
