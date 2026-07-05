"""Architecture analysis toolset used by the Architecture Agent.

Everything here is heuristic/static (regex + file presence checks) rather
than a full language-aware parse, which keeps it dependency-light and fast
across arbitrary repositories of mixed languages.
"""
from __future__ import annotations

import json
import os
import re

IGNORED_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".next"}

FRAMEWORK_SIGNATURES = {
    "React": [r"\breact\b", r"\breact-dom\b"],
    "Next.js": [r"\bnext\b"],
    "Vue": [r"\bvue\b"],
    "Angular": [r"@angular/core"],
    "FastAPI": [r"\bfastapi\b"],
    "Django": [r"\bdjango\b"],
    "Flask": [r"\bflask\b"],
    "Express": [r"\bexpress\b"],
    "Spring Boot": [r"spring-boot"],
    "PostgreSQL": [r"\bpsycopg2?\b", r"\bpostgres\b", r"\bpg\b"],
    "MySQL": [r"\bmysql\b", r"\bpymysql\b"],
    "MongoDB": [r"\bmongo\b", r"\bpymongo\b", r"\bmongoose\b"],
    "Redis": [r"\bredis\b"],
    "Docker": [r"^FROM\s"],
    "GraphQL": [r"\bgraphql\b"],
}

ENDPOINT_PATTERNS = [
    # FastAPI / Flask style: @app.get("/path"), @router.post('/path')
    re.compile(r'@(?:app|router)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']', re.IGNORECASE),
    # Express style: app.get('/path', ...), router.post("/path", ...)
    re.compile(r'(?:app|router)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']', re.IGNORECASE),
]

DESIGN_PATTERN_HINTS = {
    "Singleton": [r"_instance\s*=\s*None", r"getInstance\s*\("],
    "Factory": [r"class\s+\w*Factory\b", r"def\s+create_\w+\("],
    "Observer": [r"class\s+\w*Observer\b", r"\.subscribe\(", r"\.notify\("],
    "Decorator": [r"^\s*@\w+\s*$"],
    "Repository": [r"class\s+\w*Repository\b"],
    "MVC": [],  # detected via folder names instead
    "Dependency Injection": [r"Depends\(", r"@inject\b", r"\bInject\("],
}


def _list_files(root: str) -> list[str]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for filename in filenames:
            files.append(os.path.join(dirpath, filename))
    return files


def analyze_folder_structure(repo_path: str) -> dict:
    """Summarizes folder structure: file counts, sizes, and language distribution.

    Args:
        repo_path: Local filesystem path to the repository checkout.

    Returns:
        A dict with 'language_distribution', 'folder_sizes', and 'total_files'.
    """
    files = _list_files(repo_path)
    language_counts: dict[str, int] = {}
    folder_sizes: dict[str, int] = {}

    for filepath in files:
        ext = os.path.splitext(filepath)[1].lstrip(".").lower() or "no_ext"
        language_counts[ext] = language_counts.get(ext, 0) + 1

        try:
            size = os.path.getsize(filepath)
        except OSError:
            size = 0
        top_folder = os.path.relpath(filepath, repo_path).split(os.sep)[0]
        folder_sizes[top_folder] = folder_sizes.get(top_folder, 0) + size

    return {
        "total_files": len(files),
        "language_distribution": dict(sorted(language_counts.items(), key=lambda kv: kv[1], reverse=True)),
        "folder_sizes_bytes": dict(sorted(folder_sizes.items(), key=lambda kv: kv[1], reverse=True)),
    }


def detect_services_and_frameworks(repo_path: str) -> dict:
    """Detects frameworks/services referenced in dependency manifests and Dockerfiles.

    Args:
        repo_path: Local filesystem path to the repository checkout.

    Returns:
        A dict with 'detected' (list of framework/service names) grouped loosely
        into layers (frontend/backend/database/infra) for a simple architecture view.
    """
    manifest_text = ""
    for manifest in ("requirements.txt", "package.json", "pyproject.toml", "Pipfile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml"):
        path = os.path.join(repo_path, manifest)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    manifest_text += "\n" + fh.read()
            except OSError:
                continue

    detected = []
    for name, patterns in FRAMEWORK_SIGNATURES.items():
        if any(re.search(pattern, manifest_text, re.IGNORECASE | re.MULTILINE) for pattern in patterns):
            detected.append(name)

    layers = {
        "frontend": [f for f in detected if f in ("React", "Next.js", "Vue", "Angular")],
        "backend": [f for f in detected if f in ("FastAPI", "Django", "Flask", "Express", "Spring Boot", "GraphQL")],
        "database": [f for f in detected if f in ("PostgreSQL", "MySQL", "MongoDB", "Redis")],
        "infrastructure": [f for f in detected if f in ("Docker",)],
    }
    return {"detected": detected, "layers": layers}


def extract_api_endpoints(repo_path: str, max_endpoints: int = 200) -> list[dict]:
    """Scans source files for common web-framework route decorator patterns.

    Args:
        repo_path: Local filesystem path to the repository checkout.
        max_endpoints: Caps the number of endpoints returned.

    Returns:
        A list of {method, path, file} dicts.
    """
    endpoints = []
    for filepath in _list_files(repo_path):
        if not filepath.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except OSError:
            continue
        for pattern in ENDPOINT_PATTERNS:
            for match in pattern.finditer(content):
                endpoints.append(
                    {
                        "method": match.group(1).upper(),
                        "path": match.group(2),
                        "file": os.path.relpath(filepath, repo_path),
                    }
                )
                if len(endpoints) >= max_endpoints:
                    return endpoints
    return endpoints


def build_dependency_graph(repo_path: str) -> dict:
    """Builds a shallow dependency graph from Python/Node manifest files.

    Args:
        repo_path: Local filesystem path to the repository checkout.

    Returns:
        A dict with 'nodes' and 'edges' suitable for a simple graph visualization,
        plus 'dependencies' as a flat list with ecosystem + version.
    """
    dependencies = []

    req_path = os.path.join(repo_path, "requirements.txt")
    if os.path.exists(req_path):
        try:
            with open(req_path, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    name = re.split(r"[=<>!~;]", line)[0].strip()
                    if name:
                        dependencies.append({"name": name, "ecosystem": "pypi", "raw": line})
        except OSError:
            pass

    pkg_path = os.path.join(repo_path, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8", errors="ignore") as fh:
                data = json.load(fh)
            for section in ("dependencies", "devDependencies"):
                for name, version in data.get(section, {}).items():
                    dependencies.append({"name": name, "ecosystem": "npm", "raw": f"{name}{version}"})
        except (OSError, json.JSONDecodeError):
            pass

    nodes = [{"id": "project", "type": "root"}] + [
        {"id": dep["name"], "type": dep["ecosystem"]} for dep in dependencies
    ]
    edges = [{"source": "project", "target": dep["name"]} for dep in dependencies]

    return {"dependencies": dependencies, "nodes": nodes, "edges": edges}


def detect_design_patterns(repo_path: str) -> list[str]:
    """Heuristically detects common design patterns by scanning source text.

    Args:
        repo_path: Local filesystem path to the repository checkout.

    Returns:
        A sorted list of detected pattern names.
    """
    found = set()
    top_level_dirs = {
        entry.lower()
        for entry in os.listdir(repo_path)
        if os.path.isdir(os.path.join(repo_path, entry)) and entry not in IGNORED_DIRS
    }
    if {"controllers", "models", "views"} & top_level_dirs or {"controllers", "models"} <= top_level_dirs:
        found.add("MVC")

    for filepath in _list_files(repo_path):
        if not filepath.endswith((".py", ".js", ".ts", ".java")):
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except OSError:
            continue
        for pattern_name, regexes in DESIGN_PATTERN_HINTS.items():
            if pattern_name == "MVC":
                continue
            if any(re.search(regex, content, re.MULTILINE) for regex in regexes):
                found.add(pattern_name)

    return sorted(found)


async def run_architecture_analysis(repo_path: str) -> dict:
    """Runs the full architecture analysis suite and returns a combined report.

    Args:
        repo_path: Local filesystem path to the repository checkout.

    Returns:
        A dict combining folder structure, detected frameworks/layers, API
        endpoints, dependency graph, and detected design patterns.
    """
    structure = analyze_folder_structure(repo_path)
    services = detect_services_and_frameworks(repo_path)
    endpoints = extract_api_endpoints(repo_path)
    dependency_graph = build_dependency_graph(repo_path)
    patterns = detect_design_patterns(repo_path)

    return {
        "folder_structure": structure,
        "frameworks": services["detected"],
        "layers": services["layers"],
        "api_endpoints": endpoints,
        "dependency_graph": dependency_graph,
        "design_patterns": patterns,
    }
