import logging
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_principal, owned_holding
from app.db.session import get_db
from app.models.models import PortfolioHolding
from app.schemas.schemas import (
    GrowwImportRequest,
    PortfolioHoldingCreate,
    PortfolioHoldingSchema,
    PortfolioHoldingUpdate,
    PortfolioImportResult,
    PortfolioSchema,
    PortfolioSummaryResponse,
)
from app.services.groww_service import GrowwImportError, groww_service
from app.services.portfolio_service import portfolio_service

router = APIRouter()
logger = logging.getLogger("portfolio-api")

# Cap upload size so a huge/garbage file can't exhaust memory (holdings files are tiny).
_MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB
_ALLOWED_UPLOAD_SUFFIXES = (".csv", ".xlsx", ".xls")


@router.get("", response_model=PortfolioSchema)
async def get_portfolio(
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve (or lazily create) the portfolio owned by the caller's session."""
    return await portfolio_service.get_or_create_portfolio(db, principal.session_id)


@router.post("/holdings", response_model=PortfolioHoldingSchema, status_code=status.HTTP_201_CREATED)
async def add_portfolio_holding(
    holding_in: PortfolioHoldingCreate,
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
):
    """Add a stock holding to the caller's portfolio."""
    return await portfolio_service.add_holding(
        db,
        session_id=principal.session_id,
        symbol=holding_in.symbol,
        shares=holding_in.shares,
        average_buy_price=holding_in.average_buy_price,
    )


@router.put("/holdings/{holding_id}", response_model=PortfolioHoldingSchema)
async def update_portfolio_holding(
    holding_in: PortfolioHoldingUpdate,
    holding: PortfolioHolding = Depends(owned_holding),
    db: AsyncSession = Depends(get_db),
):
    """Modify shares or cost basis on a holding."""
    holding.shares = holding_in.shares
    holding.average_buy_price = holding_in.average_buy_price
    holding.last_updated = datetime.utcnow()
    await db.commit()
    return holding


@router.delete("/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio_holding(
    holding: PortfolioHolding = Depends(owned_holding),
    db: AsyncSession = Depends(get_db),
):
    """Remove a holding from the caller's portfolio."""
    await db.delete(holding)
    await db.commit()


@router.post("/import/groww", response_model=PortfolioImportResult)
async def import_from_groww(
    payload: GrowwImportRequest,
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
):
    """Import holdings from the user's Groww account via the official Groww Trade API.

    The user pastes a daily access token generated on Groww's Trading APIs page. By
    default this replaces the portfolio (a full sync of the Groww account). The token
    is used for this request only and is never persisted.
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

    result = await portfolio_service.import_holdings(
        db, principal.session_id, holdings, replace=payload.replace
    )
    return {**result, "message": f"Imported {result['imported']} holdings from Groww."}


@router.post("/import/file", response_model=PortfolioImportResult)
async def import_from_file(
    replace: bool = Query(True, description="Replace existing holdings (full sync) vs merge"),
    file: UploadFile = File(..., description="Groww holdings/P&L export (.csv or .xlsx)"),
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
):
    """Import holdings from an uploaded Groww statement export (CSV or Excel).

    Works without a Groww API subscription — the user exports Holdings/P&L from
    Groww's Reports section and uploads the file here.
    """
    filename = file.filename or "upload.csv"
    if not filename.lower().endswith(_ALLOWED_UPLOAD_SUFFIXES):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a .csv, .xlsx or .xls file exported from Groww.",
        )

    # Capped read: an unbounded one buffers the whole body before the size check.
    content = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 2 MB)."
        )

    try:
        holdings = groww_service.parse_holdings_file(filename, content)
    except GrowwImportError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error(f"File import parse failed: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not parse that file.")

    result = await portfolio_service.import_holdings(db, principal.session_id, holdings, replace=replace)
    return {**result, "message": f"Imported {result['imported']} holdings from {filename}."}


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
):
    """Full portfolio metrics, allocations, volatility, and individual holdings."""
    return await portfolio_service.get_portfolio_summary(db, principal.session_id)
