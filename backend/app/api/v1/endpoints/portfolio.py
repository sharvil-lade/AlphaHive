import logging
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.schemas import (
    PortfolioSchema,
    PortfolioHoldingSchema,
    PortfolioHoldingCreate,
    PortfolioHoldingUpdate,
    PortfolioSummaryResponse,
    GrowwImportRequest,
    PortfolioImportResult,
)
from app.services.groww_service import GrowwImportError, groww_service
from app.services.portfolio_service import portfolio_service

router = APIRouter()
logger = logging.getLogger("portfolio-api")

# Cap upload size so a huge/garbage file can't exhaust memory (holdings files are tiny).
_MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB


@router.get("", response_model=PortfolioSchema)
async def get_portfolio(
    session_id: str = Query(..., description="Client Session ID"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve or create default portfolio for the current session."""
    try:
        return await portfolio_service.get_or_create_portfolio(db, session_id)
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch portfolio: {str(e)}"
        )


@router.post("/holdings", response_model=PortfolioHoldingSchema, status_code=status.HTTP_201_CREATED)
async def add_portfolio_holding(
    holding_in: PortfolioHoldingCreate,
    session_id: str = Query(..., description="Client Session ID"),
    db: AsyncSession = Depends(get_db)
):
    """Add a new stock holding to the portfolio."""
    try:
        return await portfolio_service.add_holding(
            db, 
            session_id=session_id, 
            symbol=holding_in.symbol, 
            shares=holding_in.shares, 
            average_buy_price=holding_in.average_buy_price
        )
    except Exception as e:
        logger.error(f"Error adding holding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add holding: {str(e)}"
        )


@router.put("/holdings/{holding_id}", response_model=PortfolioHoldingSchema)
async def update_portfolio_holding(
    holding_id: UUID,
    holding_in: PortfolioHoldingUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Modify shares or cost basis on a stock holding."""
    try:
        holding = await portfolio_service.update_holding(
            db, 
            holding_id=holding_id, 
            shares=holding_in.shares, 
            average_buy_price=holding_in.average_buy_price
        )
        if not holding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Holding not found with ID: {holding_id}"
            )
        return holding
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating holding {holding_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update holding: {str(e)}"
        )


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio_holding(
    holding_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Remove a stock holding from the portfolio."""
    try:
        success = await portfolio_service.delete_holding(db, holding_id=holding_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Holding not found with ID: {holding_id}"
            )
        return
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error deleting holding {holding_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete holding: {str(e)}"
        )


@router.post("/import/groww", response_model=PortfolioImportResult)
async def import_from_groww(
    payload: GrowwImportRequest,
    session_id: str = Query(..., description="Client Session ID"),
    db: AsyncSession = Depends(get_db),
):
    """Import holdings from the user's Groww account via the official Groww Trade API.

    The user pastes a daily access token generated on Groww's Trading APIs page. By
    default this replaces the portfolio (a full sync of the Groww account).
    """
    try:
        holdings = await groww_service.fetch_holdings_via_api(payload.access_token)
    except GrowwImportError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error(f"Groww API import failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Groww import failed unexpectedly."
        )

    result = await portfolio_service.import_holdings(db, session_id, holdings, replace=payload.replace)
    return {**result, "message": f"Imported {result['imported']} holdings from Groww."}


@router.post("/import/file", response_model=PortfolioImportResult)
async def import_from_file(
    session_id: str = Query(..., description="Client Session ID"),
    replace: bool = Query(True, description="Replace existing holdings (full sync) vs merge"),
    file: UploadFile = File(..., description="Groww holdings/P&L export (.csv or .xlsx)"),
    db: AsyncSession = Depends(get_db),
):
    """Import holdings from an uploaded Groww statement export (CSV or Excel).

    Works without a Groww API subscription — the user exports Holdings/P&L from
    Groww's Reports section and uploads the file here.
    """
    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 2 MB).")

    try:
        holdings = groww_service.parse_holdings_file(file.filename or "upload.csv", content)
    except GrowwImportError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error(f"File import parse failed: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not parse that file.")

    result = await portfolio_service.import_holdings(db, session_id, holdings, replace=replace)
    return {**result, "message": f"Imported {result['imported']} holdings from {file.filename}."}


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(
    session_id: str = Query(..., description="Client Session ID"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve full portfolio metrics, allocations, volatility, and individual holdings."""
    try:
        return await portfolio_service.get_portfolio_summary(db, session_id)
    except Exception as e:
        logger.error(f"Error generating portfolio summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate portfolio summary: {str(e)}"
        )
