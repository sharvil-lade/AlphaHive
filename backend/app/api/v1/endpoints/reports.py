import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_principal, require_principal
from app.db.session import get_db
from app.models.models import AgentRun, InvestmentReport
from app.schemas.schemas import ReportHistoryItem
from app.services.memo_service import memo_service

router = APIRouter()
logger = logging.getLogger("reports-api")


async def _owned_report(run_id: UUID, session_id: str, db: AsyncSession) -> InvestmentReport:
    """Resolve a report by run id, scoped to the caller's session.

    Reports quote the user's holdings and position sizing, so a bare run id must not
    be enough to download someone else's memo.
    """
    stmt = (
        select(InvestmentReport)
        .join(AgentRun, AgentRun.id == InvestmentReport.run_id)
        .where(InvestmentReport.run_id == run_id, AgentRun.session_id == session_id)
    )
    report = (await db.execute(stmt)).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return report


@router.get("/history", response_model=List[ReportHistoryItem])
async def get_reports_history(
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
):
    """Historical memo reports for the caller's session."""
    return await memo_service.get_reports_history(db, principal.session_id)


@router.get("/{run_id}/markdown")
async def download_markdown_report(
    run_id: UUID,
    principal: Principal = Depends(require_principal),
    db: AsyncSession = Depends(get_db),
):
    """Download the executive investment report as a markdown file (.md)."""
    report = await _owned_report(run_id, principal.session_id, db)
    filename = f"Investment_Memo_{report.ticker.upper()}_{run_id.hex[:8]}.md"
    return Response(
        content=report.content_markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{run_id}/pdf")
async def download_pdf_report(
    run_id: UUID,
    principal: Principal = Depends(require_principal),
    db: AsyncSession = Depends(get_db),
):
    """Download the executive investment report compiled into a styled PDF (.pdf)."""
    report = await _owned_report(run_id, principal.session_id, db)
    pdf_bytes = await memo_service.compile_report_pdf(report)
    filename = f"Investment_Memo_{report.ticker.upper()}_{run_id.hex[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
