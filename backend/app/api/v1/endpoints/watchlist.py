import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.schemas import WatchlistSchema, WatchlistCreate
from backend.app.services.automation_service import automation_service

router = APIRouter()
logger = logging.getLogger("watchlist-api")


@router.get("", response_model=List[WatchlistSchema])
async def get_watchlist(
    session_id: str = Query(..., description="Client Session ID"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all symbols in the user's watchlist."""
    try:
        return await automation_service.get_watchlist(db, session_id)
    except Exception as e:
        logger.error(f"Error fetching watchlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch watchlist: {str(e)}"
        )


@router.post("", response_model=WatchlistSchema, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    watchlist_in: WatchlistCreate,
    session_id: str = Query(..., description="Client Session ID"),
    db: AsyncSession = Depends(get_db)
):
    """Add a new ticker symbol to the watchlist."""
    try:
        return await automation_service.add_to_watchlist(db, session_id, watchlist_in.symbol)
    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add symbol: {str(e)}"
        )


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_from_watchlist(
    symbol: str,
    session_id: str = Query(..., description="Client Session ID"),
    db: AsyncSession = Depends(get_db)
):
    """Remove a symbol from the watchlist."""
    try:
        success = await automation_service.remove_from_watchlist(db, session_id, symbol)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Symbol {symbol} not found in watchlist"
            )
        return
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error deleting symbol {symbol} from watchlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete symbol: {str(e)}"
        )
