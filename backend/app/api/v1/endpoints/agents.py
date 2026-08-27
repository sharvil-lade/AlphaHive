import asyncio
import json
import logging
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.utils import get_redis, log_agent_activity
from app.core.deps import Principal, get_principal, require_principal
from app.db.session import AsyncSessionLocal, get_db
from app.models.models import AgentRun, InvestmentReport
from app.schemas.schemas import AgentRunDetailResponse, AgentRunSchema

router = APIRouter()
logger = logging.getLogger("agents-api")


async def execute_agent_workflow(run_id: UUID, session_id: str, ticker: str):
    """Asynchronous background execution of the LangGraph state machine."""
    try:
        from app.agents.graph import agent_graph

        initial_state = {
            "session_id": session_id,
            "ticker": ticker,
            "run_id": str(run_id),
            "status": "running",
            "quotes": {},
            "indicators": {},
            "sentiment": {},
            "sec_context": [],
            "risk_metrics": {},
            "decision": {},
            "logs": [],
        }
        await agent_graph.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"Error executing LangGraph workflow for run {run_id}: {e}")
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    stmt = select(AgentRun).where(AgentRun.id == run_id)
                    result = await session.execute(stmt)
                    agent_run = result.scalar_one_or_none()
                    if agent_run:
                        agent_run.status = "failed"
                        agent_run.ended_at = datetime.utcnow()

            await log_agent_activity(str(run_id), "orchestrator", f"Critical agent workflow failure: {e}")
        except Exception as db_err:
            logger.error(f"Failed to record agent run failure in DB for {run_id}: {db_err}")


async def _owned_run(run_id: UUID, session_id: str, db: AsyncSession) -> AgentRun:
    """Resolve a run id, but only within the caller's own session."""
    stmt = select(AgentRun).where(AgentRun.id == run_id, AgentRun.session_id == session_id)
    agent_run = (await db.execute(stmt)).scalar_one_or_none()
    if not agent_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return agent_run


@router.post("/run", response_model=AgentRunSchema, status_code=status.HTTP_201_CREATED)
async def run_agent_analysis(
    symbol: str = Query(..., min_length=1, max_length=20, description="Stock Ticker Symbol"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
):
    """Initialize an AgentRun session and launch the LangGraph workflow in the background."""
    symbol = symbol.upper()
    session_id = principal.session_id

    from app.services.token_budget_service import token_budget_service

    is_budget_ok = await token_budget_service.check_budget(session_id)
    if not is_budget_ok:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="You've hit this session's usage limit. Try again later.",
        )

    run_id = uuid4()
    agent_run = AgentRun(
        id=run_id, session_id=session_id, ticker=symbol, status="running", started_at=datetime.utcnow()
    )
    db.add(agent_run)
    await db.commit()  # Commit explicitly to make it visible to concurrent/background tasks!

    background_tasks.add_task(execute_agent_workflow, run_id, session_id, symbol)

    return {
        "id": agent_run.id,
        "session_id": agent_run.session_id,
        "ticker": agent_run.ticker,
        "status": agent_run.status,
        "started_at": agent_run.started_at,
        "ended_at": agent_run.ended_at,
        "report": None,
    }


async def log_generator(run_id: UUID):
    """Server-Sent Events generator streaming logs from Redis."""
    redis = get_redis()
    cache_key = f"agent_run_logs:{run_id}"
    read_idx = 0

    while True:
        try:
            logs = await redis.lrange(cache_key, read_idx, -1)
            if logs:
                for log_str in logs:
                    yield f"data: {log_str}\n\n"
                read_idx += len(logs)
        except Exception as e:
            logger.error(f"Error reading logs from Redis in stream generator: {e}")

        try:
            async with AsyncSessionLocal() as session:
                stmt = select(AgentRun).where(AgentRun.id == run_id)
                result = await session.execute(stmt)
                agent_run = result.scalar_one_or_none()

                if agent_run and agent_run.status in ["completed", "failed"]:
                    final_logs = await redis.lrange(cache_key, read_idx, -1)
                    for log_str in final_logs:
                        yield f"data: {log_str}\n\n"

                    completion_data = {
                        "node": "orchestrator",
                        "message": f"Execution finished with status: {agent_run.status}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "done": True,
                    }
                    yield f"data: {json.dumps(completion_data)}\n\n"
                    break
        except Exception as e:
            logger.error(f"Error querying AgentRun in log generator: {e}")

        await asyncio.sleep(0.5)


@router.get("/run/{run_id}/stream")
async def stream_agent_run_logs(
    run_id: UUID,
    principal: Principal = Depends(require_principal),
    db: AsyncSession = Depends(get_db),
):
    """Stream real-time agent execution log entries via SSE."""
    await _owned_run(run_id, principal.session_id, db)
    return StreamingResponse(
        log_generator(run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/run/{run_id}", response_model=AgentRunDetailResponse)
async def get_agent_run_detail(
    run_id: UUID,
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
):
    """Fetch completed agent run info, memo report, and consolidated logs history."""
    agent_run = await _owned_run(run_id, principal.session_id, db)

    logs = []
    try:
        redis = get_redis()
        cache_key = f"agent_run_logs:{run_id}"
        redis_logs = await redis.lrange(cache_key, 0, -1)
        for log_str in redis_logs:
            logs.append(json.loads(log_str))
    except Exception as e:
        logger.error(f"Failed to fetch logs from Redis for {run_id}: {e}")

    # Eagerly load InvestmentReport (to prevent lazy-loading in async db session)
    report_stmt = select(InvestmentReport).where(InvestmentReport.run_id == run_id)
    report_result = await db.execute(report_stmt)
    report = report_result.scalar_one_or_none()

    return {
        "run_id": agent_run.id,
        "ticker": agent_run.ticker,
        "status": agent_run.status,
        "logs": logs,
        "report": report,
        "telemetry": {
            "started_at": agent_run.started_at.isoformat(),
            "ended_at": agent_run.ended_at.isoformat() if agent_run.ended_at else None,
        },
    }
