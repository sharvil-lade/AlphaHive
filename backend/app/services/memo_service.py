import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AgentRun, InvestmentReport
from app.utils.pdf_generator import generate_report_pdf

logger = logging.getLogger("memo-service")


class MemoService:
    """Service handling database lookup of investment reports and PDF compilation."""

    async def get_report_by_run_id(self, db: AsyncSession, run_id: UUID) -> InvestmentReport | None:
        """Fetch investment report by run_id from Postgres."""
        stmt = select(InvestmentReport).where(InvestmentReport.run_id == run_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_reports_history(self, db: AsyncSession, session_id: str) -> list[dict[str, Any]]:
        """Retrieve historical memos summary for a client session ID."""
        stmt = (
            select(AgentRun, InvestmentReport)
            .join(InvestmentReport, AgentRun.id == InvestmentReport.run_id)
            .where(AgentRun.session_id == session_id)
            .order_by(InvestmentReport.created_at.desc())
        )
        result = await db.execute(stmt)
        history = []

        for agent_run, report in result.all():
            history.append(
                {
                    "run_id": agent_run.id,
                    "ticker": agent_run.ticker,
                    "status": agent_run.status,
                    "recommendation": report.recommendation,
                    "confidence_score": report.confidence_score,
                    "created_at": report.created_at.isoformat(),
                }
            )

        return history

    async def compile_report_pdf(self, report: InvestmentReport) -> bytes:
        """Helper to generate PDF byte data using xhtml2pdf wrapper."""
        title = f"AlphaHive Research Memo: {report.ticker.upper()} ({report.recommendation.upper()})"
        return await generate_report_pdf(report.content_markdown, title)


memo_service = MemoService()
