import logging
from uuid import UUID
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.schemas import AlertSchema, AlertCreate
from backend.app.services.automation_service import automation_service

router = APIRouter()
logger = logging.getLogger("alerts-api")


@router.get("", response_model=List[AlertSchema])
async def get_alerts(
    session_id: str = Query(..., description="Client Session ID"),
    active_only: bool = Query(True, description="Only return active alerts"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve watchlist alerts configured in this session."""
    try:
        return await automation_service.get_alerts(db, session_id, active_only)
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch alerts: {str(e)}"
        )


@router.post("", response_model=AlertSchema, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_in: AlertCreate,
    session_id: str = Query(..., description="Client Session ID"),
    db: AsyncSession = Depends(get_db)
):
    """Create a new rules-based alert threshold."""
    try:
        return await automation_service.create_alert(
            db, 
            session_id=session_id, 
            symbol=alert_in.symbol, 
            trigger_type=alert_in.trigger_type, 
            trigger_value=alert_in.trigger_value
        )
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to declare alert: {str(e)}"
        )


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: UUID,
    session_id: str = Query(..., description="Client Session ID"),
    db: AsyncSession = Depends(get_db)
):
    """Cancel and delete an alert."""
    try:
        success = await automation_service.delete_alert(db, session_id, alert_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found"
            )
        return
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error deleting alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete alert: {str(e)}"
        )


@router.post("/check", response_model=List[Dict[str, Any]])
async def check_watchlist_alerts(
    db: AsyncSession = Depends(get_db)
):
    """Scan all active watchlist alerts and check satisfied triggers immediately."""
    try:
        return await automation_service.check_alerts(db)
    except Exception as e:
        logger.error(f"Error running alert scanner task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alert checker run failed: {str(e)}"
        )
