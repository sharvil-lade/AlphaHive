import logging
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.schemas import ReportHistoryItem
from backend.app.services.memo_service import memo_service

router = APIRouter()
logger = logging.getLogger("reports-api")


@router.get("/history", response_model=List[ReportHistoryItem])
async def get_reports_history(
    session_id: str = Query(..., description="Client Session ID"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve historical memo reports list for a client session ID."""
    try:
        return await memo_service.get_reports_history(db, session_id)
    except Exception as e:
        logger.error(f"Error fetching historical reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query report history: {e}"
        )


@router.get("/{run_id}/markdown")
async def download_markdown_report(
    run_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    """Download the executive investment report as a formatted markdown file (.md)."""
    report = await memo_service.get_report_by_run_id(db, run_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investment report not found for run ID: {run_id}"
        )
        
    filename = f"Investment_Memo_{report.ticker.upper()}_{run_id.hex[:8]}.md"
    return Response(
        content=report.content_markdown,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/{run_id}/pdf")
async def download_pdf_report(
    run_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    """Download the executive investment report compiled into a styled PDF file (.pdf)."""
    report = await memo_service.get_report_by_run_id(db, run_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investment report not found for run ID: {run_id}"
        )
        
    try:
        pdf_bytes = await memo_service.compile_report_pdf(report)
        filename = f"Investment_Memo_{report.ticker.upper()}_{run_id.hex[:8]}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        logger.error(f"Failed to compile and stream PDF report for {run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile PDF memo: {e}"
        )
