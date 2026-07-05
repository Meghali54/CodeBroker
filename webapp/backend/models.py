"""Shared data schemas for the pipeline job state and dashboard payload.

Kept as plain dataclasses (rather than pydantic models) so this module has
zero hard dependency on any particular web framework version being installed;
main.py converts these to JSON directly.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


PIPELINE_STAGES = [
    "repository_agent",
    "security_agent",
    "architecture_agent",
    "quality_agent",
    "improvement_agent",
    "executive_report",
]

STAGE_LABELS = {
    "repository_agent": "Repository Agent",
    "security_agent": "Security Agent",
    "architecture_agent": "Architecture Agent",
    "quality_agent": "Quality Agent",
    "improvement_agent": "Improvement Agent",
    "executive_report": "Executive Report",
}


@dataclass
class StageState:
    name: str
    status: StageStatus = StageStatus.PENDING
    started_at: float | None = None
    finished_at: float | None = None
    tokens_used: int = 0
    output_summary: str | None = None
    error: str | None = None

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at is None:
            return None
        end = self.finished_at if self.finished_at is not None else time.time()
        return round(end - self.started_at, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": STAGE_LABELS.get(self.name, self.name),
            "status": self.status.value,
            "duration_seconds": self.duration_seconds,
            "tokens_used": self.tokens_used,
            "output_summary": self.output_summary,
            "error": self.error,
        }


@dataclass
class Job:
    job_id: str
    repo_url: str
    created_at: float = field(default_factory=time.time)
    stages: dict[str, StageState] = field(
        default_factory=lambda: {name: StageState(name=name) for name in PIPELINE_STAGES}
    )
    status: str = "pending"  # pending | running | complete | error
    dashboard: dict[str, Any] | None = None
    error: str | None = None

    def to_status_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "repo_url": self.repo_url,
            "status": self.status,
            "stages": [self.stages[name].to_dict() for name in PIPELINE_STAGES],
            "error": self.error,
        }
