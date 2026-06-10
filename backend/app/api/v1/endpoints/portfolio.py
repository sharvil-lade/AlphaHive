import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.schemas import (
    PortfolioSchema,
    PortfolioHoldingSchema,
    PortfolioHoldingCreate,
    PortfolioHoldingUpdate,
    PortfolioSummaryResponse,
)
from backend.app.services.portfolio_service import portfolio_service

router = APIRouter()
logger = logging.getLogger("portfolio-api")


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
