"""FastAPI backend for Code Broker's Executive Dashboard.

Run with:
    cd webapp/backend
    uvicorn main:app --reload --port 8000

Then open http://localhost:8000 in a browser.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from agents.pipeline import run_pipeline
from job_manager import job_manager
from tools.github_tool import GitHubToolError, parse_repo_url

load_dotenv()

app = FastAPI(title="Code Broker Executive Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


class AnalyzeRequest(BaseModel):
    repo_url: str

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, value: str) -> str:
        try:
            parse_repo_url(value)
        except GitHubToolError as exc:
            raise ValueError(str(exc)) from exc
        return value.strip()


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    """Starts a new analysis job for the given GitHub repository URL."""
    job = job_manager.create_job(request.repo_url)
    import asyncio

    asyncio.create_task(run_pipeline(job))
    return {"job_id": job.job_id}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Returns the current status of a job (polling fallback for the WebSocket)."""
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    payload = job.to_status_dict()
    if job.dashboard is not None:
        payload["dashboard"] = job.dashboard
    return payload


@app.websocket("/ws/jobs/{job_id}")
async def job_updates(websocket: WebSocket, job_id: str):
    """Streams live stage updates for a job until it completes or errors."""
    job = job_manager.get_job(job_id)
    if job is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    await job_manager.subscribe(job_id, websocket)

    # Send current state immediately so late-connecting clients aren't stuck.
    await websocket.send_json({"type": "snapshot", "job": job.to_status_dict()})
    if job.dashboard is not None:
        await websocket.send_json({"type": "complete", "dashboard": job.dashboard})

    try:
        while True:
            # Keep the connection open; the client doesn't need to send anything.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await job_manager.unsubscribe(job_id, websocket)


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
