"""Orchestrates the 6-stage agent pipeline and reports live progress.

Repository Agent -> Security Agent -> Architecture Agent -> Quality Agent
-> Improvement Agent -> Executive Report
"""
from __future__ import annotations

from agents import architecture_agent, executive_report_agent, improvement_agent, quality_agent, repository_agent, security_agent
from job_manager import job_manager
from models import Job
from tools.repo_clone import cleanup_directory


async def run_pipeline(job: Job) -> None:
    """Runs the full pipeline for a job, broadcasting stage updates as it goes.

    Args:
        job: The Job to execute. Mutates job.status/job.dashboard/job.error.
    """
    local_path = None
    try:
        # 1. Repository Agent
        await job_manager.start_stage(job, "repository_agent")
        repository_result = await repository_agent.run_repository_agent(job.repo_url)
        if repository_result.get("error") and not repository_result.get("local_path"):
            await job_manager.fail_stage(job, "repository_agent", repository_result["error"])
            await job_manager.fail_job(job, f"Repository Agent failed: {repository_result['error']}")
            return
        local_path = repository_result.get("local_path")
        await job_manager.complete_stage(
            job, "repository_agent", repository_agent.summarize(repository_result)
        )

        # 2. Security Agent
        await job_manager.start_stage(job, "security_agent")
        security_result = await security_agent.run_security_agent(local_path)
        await job_manager.complete_stage(job, "security_agent", security_agent.summarize(security_result))

        # 3. Architecture Agent
        await job_manager.start_stage(job, "architecture_agent")
        architecture_result = await architecture_agent.run_architecture_agent(local_path)
        await job_manager.complete_stage(job, "architecture_agent", architecture_agent.summarize(architecture_result))

        # 4. Quality Agent
        await job_manager.start_stage(job, "quality_agent")
        quality_result = await quality_agent.run_quality_agent(local_path)
        await job_manager.complete_stage(job, "quality_agent", quality_agent.summarize(quality_result))

        # 5. Improvement Agent (LLM)
        await job_manager.start_stage(job, "improvement_agent")
        recommendations_text, improvement_tokens = await improvement_agent.run_improvement_agent(
            repository_result, security_result, architecture_result, quality_result
        )
        await job_manager.complete_stage(
            job, "improvement_agent", improvement_agent.summarize(recommendations_text), tokens_used=improvement_tokens
        )

        # 6. Executive Report (LLM + aggregation)
        await job_manager.start_stage(job, "executive_report")
        dashboard = await executive_report_agent.run_executive_report_agent(
            repository_result, security_result, architecture_result, quality_result, recommendations_text
        )
        executive_tokens = dashboard.pop("_tokens_used", 0)
        await job_manager.complete_stage(
            job, "executive_report", executive_report_agent.summarize(dashboard), tokens_used=executive_tokens
        )

        dashboard["agent_timeline"] = [stage.to_dict() for stage in job.stages.values()]
        await job_manager.finish_job(job, dashboard)

    except Exception as exc:  # noqa: BLE001 - any unhandled stage error should fail the job, not crash the server
        await job_manager.fail_job(job, str(exc))
    finally:
        if local_path:
            cleanup_directory(local_path)
