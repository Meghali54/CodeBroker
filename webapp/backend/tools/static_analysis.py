"""Static analysis toolset used by the Security and Quality agents.

Wraps three well-known tools rather than reinventing analysis:
  - bandit: security vulnerability scanning for Python code
  - radon:  cyclomatic complexity + maintainability index
  - pylint: general code quality / style scoring

Each function degrades gracefully (returns an 'error' or 'unavailable' key)
if the underlying tool isn't installed, rather than crashing the pipeline.
"""
from __future__ import annotations

import asyncio
import json
import os


def _iter_python_files(root: str) -> list[str]:
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "venv", ".venv", "__pycache__")]
        for filename in filenames:
            if filename.endswith(".py"):
                py_files.append(os.path.join(dirpath, filename))
    return py_files


import subprocess


def _run_sync(command: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    result = subprocess.run(command, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout, result.stderr


async def _run(command: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    # Runs the blocking subprocess call in a worker thread rather than via
    # asyncio.create_subprocess_exec, since that requires the Proactor event
    # loop on Windows and uvicorn resets the loop back to Selector at startup.
    return await asyncio.to_thread(_run_sync, command, cwd)


async def run_security_scan(repo_path: str) -> dict:
    """Runs bandit across the repository and summarizes vulnerabilities.

    Args:
        repo_path: Local filesystem path to the repository checkout.

    Returns:
        A dict with 'vulnerabilities' (list), 'severity_counts' (dict),
        and 'security_score' (0-100, higher is safer).
    """
    py_files = _iter_python_files(repo_path)
    if not py_files:
        return {
            "vulnerabilities": [],
            "severity_counts": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "security_score": 100.0,
            "note": "No Python files found to scan.",
        }

    returncode, stdout, stderr = await _run(
        ["bandit", "-r", repo_path, "-f", "json", "-q"]
    )
    if not stdout.strip():
        return {
            "vulnerabilities": [],
            "severity_counts": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "security_score": None,
            "error": f"bandit produced no output (returncode={returncode}): {stderr[:300]}",
        }

    try:
        report = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "vulnerabilities": [],
            "severity_counts": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "security_score": None,
            "error": "Could not parse bandit output.",
        }

    severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    vulnerabilities = []
    for issue in report.get("results", []):
        severity = issue.get("issue_severity", "LOW").upper()
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        vulnerabilities.append(
            {
                "file": os.path.relpath(issue.get("filename", ""), repo_path),
                "line": issue.get("line_number"),
                "severity": severity,
                "confidence": issue.get("issue_confidence"),
                "test_id": issue.get("test_id"),
                "description": issue.get("issue_text"),
            }
        )

    # Weighted deduction: HIGH costs more than MEDIUM costs more than LOW.
    penalty = severity_counts["HIGH"] * 12 + severity_counts["MEDIUM"] * 5 + severity_counts["LOW"] * 1.5
    security_score = max(0.0, round(100 - penalty, 1))

    return {
        "vulnerabilities": vulnerabilities[:100],
        "severity_counts": severity_counts,
        "security_score": security_score,
        "files_scanned": len(py_files),
    }


async def run_complexity_analysis(repo_path: str) -> dict:
    """Runs radon cyclomatic complexity + maintainability index across the repo.

    Args:
        repo_path: Local filesystem path to the repository checkout.

    Returns:
        A dict with per-file complexity, an average complexity score, and
        a maintainability index (0-100, higher is better).
    """
    py_files = _iter_python_files(repo_path)
    if not py_files:
        return {"files": [], "average_complexity": 0.0, "maintainability_index": 100.0}

    returncode, stdout, stderr = await _run(["radon", "cc", repo_path, "-j"])
    file_complexities = []
    total_complexity = 0
    block_count = 0
    if stdout.strip():
        try:
            cc_report = json.loads(stdout)
            for filepath, blocks in cc_report.items():
                file_total = sum(block.get("complexity", 0) for block in blocks)
                if blocks:
                    file_complexities.append(
                        {
                            "file": os.path.relpath(filepath, repo_path),
                            "complexity": file_total,
                            "blocks": len(blocks),
                        }
                    )
                    total_complexity += file_total
                    block_count += len(blocks)
        except json.JSONDecodeError:
            pass

    average_complexity = round(total_complexity / block_count, 2) if block_count else 0.0
    file_complexities.sort(key=lambda item: item["complexity"], reverse=True)

    mi_returncode, mi_stdout, _ = await _run(["radon", "mi", repo_path, "-j"])
    maintainability_scores = []
    if mi_stdout.strip():
        try:
            mi_report = json.loads(mi_stdout)
            maintainability_scores = [v.get("mi", 0) for v in mi_report.values() if isinstance(v, dict)]
        except json.JSONDecodeError:
            pass
    maintainability_index = round(sum(maintainability_scores) / len(maintainability_scores), 1) if maintainability_scores else None

    return {
        "files": file_complexities[:25],
        "average_complexity": average_complexity,
        "maintainability_index": maintainability_index,
    }


async def run_pylint_aggregate(repo_path: str, max_files: int = 40) -> dict:
    """Runs pylint across (a sample of) the repository's Python files.

    Args:
        repo_path: Local filesystem path to the repository checkout.
        max_files: Caps how many files are linted to keep runtime bounded.

    Returns:
        A dict with the average pylint score (0-100 scale) and per-file scores.
    """
    py_files = _iter_python_files(repo_path)[:max_files]
    if not py_files:
        return {"average_score": None, "files": [], "note": "No Python files found."}

    scores = []
    per_file = []
    for filepath in py_files:
        returncode, stdout, _ = await _run(["pylint", filepath, "--score=y"])
        match = None
        for line in stdout.splitlines():
            if "Your code has been rated at" in line:
                match = line
                break
        if match:
            try:
                score_out_of_10 = float(match.split("rated at")[1].split("/")[0].strip())
                score_pct = round(score_out_of_10 * 10, 1)
                scores.append(score_pct)
                per_file.append({"file": os.path.relpath(filepath, repo_path), "score": score_pct})
            except (ValueError, IndexError):
                continue

    average_score = round(sum(scores) / len(scores), 1) if scores else None
    return {"average_score": average_score, "files": per_file}
