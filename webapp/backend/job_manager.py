"""In-memory job registry + pub/sub broadcast used to drive the live
agent-workflow visualization over WebSockets.

An in-memory store is sufficient for a demo/single-process deployment; swap
for Redis or a database if this needs to run across multiple workers.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from fastapi import WebSocket

from models import Job, StageState, StageStatus


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._subscribers: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    def create_job(self, repo_url: str) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job = Job(job_id=job_id, repo_url=repo_url)
        self._jobs[job_id] = job
        self._subscribers[job_id] = set()
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def subscribe(self, job_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._subscribers.setdefault(job_id, set()).add(websocket)

    async def unsubscribe(self, job_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._subscribers.get(job_id, set()).discard(websocket)

    async def _broadcast(self, job_id: str, message: dict[str, Any]) -> None:
        dead = []
        for websocket in list(self._subscribers.get(job_id, set())):
            try:
                await websocket.send_json(message)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            await self.unsubscribe(job_id, websocket)

    async def start_stage(self, job: Job, stage_name: str) -> None:
        stage = job.stages[stage_name]
        stage.status = StageStatus.RUNNING
        stage.started_at = time.time()
        job.status = "running"
        await self._broadcast(job.job_id, {"type": "stage_update", "stage": stage.to_dict()})

    async def complete_stage(
        self, job: Job, stage_name: str, output_summary: str, tokens_used: int = 0
    ) -> None:
        stage = job.stages[stage_name]
        stage.status = StageStatus.COMPLETE
        stage.finished_at = time.time()
        stage.output_summary = output_summary
        stage.tokens_used = tokens_used
        await self._broadcast(job.job_id, {"type": "stage_update", "stage": stage.to_dict()})

    async def fail_stage(self, job: Job, stage_name: str, error: str) -> None:
        stage = job.stages[stage_name]
        stage.status = StageStatus.ERROR
        stage.finished_at = time.time()
        stage.error = error
        await self._broadcast(job.job_id, {"type": "stage_update", "stage": stage.to_dict()})

    async def finish_job(self, job: Job, dashboard: dict[str, Any]) -> None:
        job.status = "complete"
        job.dashboard = dashboard
        await self._broadcast(job.job_id, {"type": "complete", "dashboard": dashboard})

    async def fail_job(self, job: Job, error: str) -> None:
        job.status = "error"
        job.error = error
        await self._broadcast(job.job_id, {"type": "error", "message": error})


job_manager = JobManager()
