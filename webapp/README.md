# Code Broker — Executive Dashboard (Web App)

A FastAPI + HTML/JS front end for Code Broker that replaces manual `git clone`
+ notebook cells with:

1. **GitHub context tools** (MCP-style) — README, issues, pull requests,
   commits, and release history, fetched directly via the GitHub REST API
   (no external MCP server process required).
2. **Live agent workflow visualization** — a 6-stage pipeline
   (`Repository → Security → Architecture → Quality → Improvement →
   Executive Report`) streamed to the browser over a WebSocket, showing the
   currently running agent, time taken, tokens used, and output produced.
3. **Repository Architecture Agent** — folder structure, detected
   frameworks/services, API endpoints, a dependency graph, and design-pattern
   detection.
4. **Executive Dashboard** — Overall / Security / Maintainability / Technical
   Debt / AI Readiness / Deployment Readiness scores, plus charts for
   vulnerabilities, complexity, language distribution, folder size, and the
   agent timeline.

## Project layout

```
webapp/
├── backend/
│   ├── main.py                    # FastAPI app: /api/analyze, /ws/jobs/{id}
│   ├── job_manager.py             # in-memory job store + WebSocket broadcast
│   ├── models.py                  # Job / StageState dataclasses
│   ├── agents/
│   │   ├── pipeline.py            # orchestrates the 6 stages
│   │   ├── repository_agent.py
│   │   ├── security_agent.py
│   │   ├── architecture_agent.py
│   │   ├── quality_agent.py
│   │   ├── improvement_agent.py   # LLM-powered (Google ADK / Gemini)
│   │   ├── executive_report_agent.py  # scores + LLM narrative
│   │   └── llm_utils.py           # shared Gemini call w/ graceful fallback
│   └── tools/
│       ├── github_tool.py         # GitHub REST API (MCP-style) toolset
│       ├── repo_clone.py          # shallow git clone for local analysis
│       ├── static_analysis.py     # bandit / radon / pylint wrappers
│       └── architecture_analysis.py
└── frontend/
    ├── index.html
    ├── styles.css                 # "trading desk for repositories" theme
    └── app.js
```

## Setup

```bash
cd webapp
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# then edit .env:
#   GOOGLE_API_KEY=...   (required for AI-generated recommendations/summary)
#   GITHUB_TOKEN=...     (optional, raises GitHub API rate limit to 5000/hr)
```

You'll also need `git` on PATH (used for the shallow clone that powers
security/quality/architecture analysis).

## Run

```bash
cd webapp/backend
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000**, paste a public GitHub repository URL, and
click **Open Position**.

## Notes / design decisions

- **No external MCP server dependency.** `tools/github_tool.py` implements
  the same repository-context capabilities (files, issues, PRs, commits,
  README, releases) directly against `api.github.com`, so there's nothing
  extra to install or run alongside the app.
- **Deep local clone for code analysis.** GitHub's API isn't practical for
  per-file security/complexity scanning at scale (rate limits, N+1 calls), so
  the Repository Agent also does a shallow `git clone --depth 1` into a temp
  directory. That directory is cleaned up after each job.
- **Only two stages ever call Gemini.** Repository, Security, Architecture,
  and Quality agents are pure static analysis (GitHub REST API, `git clone`,
  bandit, radon, pylint) — zero LLM calls. Only Improvement and Executive
  Report call Gemini, and they run sequentially, never in parallel.
- **Gemini calls are cached, throttled, and retried.** `agents/llm_utils.py`
  caches responses per (agent name, instruction, prompt) so re-analyzing the
  same repo state doesn't re-spend quota; enforces a minimum gap between
  calls via `GEMINI_MIN_SECONDS_BETWEEN_CALLS` (default 4s) to stay under
  free-tier requests-per-minute limits; retries on 429 with exponential
  backoff; and reuses one `LlmAgent`/`InMemoryRunner` per agent name instead
  of rebuilding it on every call. Prompts sent to Gemini are also trimmed
  (top 3 vulnerabilities, compact JSON, truncated recommendation text) to
  keep payload size down.
- **Graceful LLM fallback.** If `GOOGLE_API_KEY` isn't set, or the Gemini
  call fails after retries (including a genuine `0` quota allocation, which
  is an account/billing issue, not something retries can fix), the
  Improvement Agent and Executive Report still run — they return the
  computed metrics and a clearly-labeled "LLM unavailable"/"LLM call failed"
  placeholder instead of crashing the pipeline.
- **Scores are computed in Python, not by the LLM**, so dashboard numbers are
  stable and reproducible run-to-run; only the executive narrative and the
  recommendations list are LLM-generated.
- **Single-process, in-memory job store.** Fine for a demo/single instance.
  If you need multiple workers or restarts mid-analysis, swap `JobManager`'s
  in-memory dict for Redis (the interface is small — `create_job`,
  `get_job`, and the `*_stage`/`finish_job` broadcast methods).

## Not yet tested live

This code was written and syntax-checked in a sandboxed environment without
internet access, so the actual end-to-end run (GitHub API calls, `git
clone`, `pip install`, and the Gemini calls) has not been executed. Please
run through the Setup/Run steps above and let me know if anything breaks —
most likely culprits would be minor API differences in `bandit`/`radon`
JSON output shape or the exact `google-adk` response object fields used for
token accounting in `llm_utils.py`.
