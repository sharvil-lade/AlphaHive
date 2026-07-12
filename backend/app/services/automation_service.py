import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Watchlist, Alert
from app.services.stock_service import stock_service
from app.services.indicators_service import indicators_service
from app.services.sentiment_service import sentiment_service

logger = logging.getLogger("automation-service")


class AutomationService:
    """Service class managing user watchlist tracking and executing background alert rule checks."""

    # Watchlist CRUD
    async def get_watchlist(self, db: AsyncSession, session_id: str) -> List[Watchlist]:
        """Fetch all tickers stored in the user's watchlist."""
        stmt = select(Watchlist).where(Watchlist.session_id == session_id).order_by(Watchlist.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def add_to_watchlist(self, db: AsyncSession, session_id: str, symbol: str) -> Watchlist:
        """Add ticker to watchlist. Ensures uniqueness and capitalizes symbol names."""
        symbol = symbol.upper().strip()
        stmt = select(Watchlist).where(Watchlist.session_id == session_id, Watchlist.symbol == symbol)
        result = await db.execute(stmt)
        watchlist_item = result.scalar_one_or_none()
        
        if not watchlist_item:
            watchlist_item = Watchlist(session_id=session_id, symbol=symbol)
            db.add(watchlist_item)
            await db.commit()
            
            # Re-query
            stmt = select(Watchlist).where(Watchlist.session_id == session_id, Watchlist.symbol == symbol)
            result = await db.execute(stmt)
            watchlist_item = result.scalar_one_or_none()
        return watchlist_item

    async def remove_from_watchlist(self, db: AsyncSession, session_id: str, symbol: str) -> bool:
        """Delete ticker from watchlist."""
        symbol = symbol.upper().strip()
        stmt = select(Watchlist).where(Watchlist.session_id == session_id, Watchlist.symbol == symbol)
        result = await db.execute(stmt)
        watchlist_item = result.scalar_one_or_none()
        if watchlist_item:
            await db.delete(watchlist_item)
            await db.commit()
            return True
        return False

    # Alerts CRUD
    async def get_alerts(self, db: AsyncSession, session_id: str, active_only: bool = True) -> List[Alert]:
        """Fetch watchlist alerts configured by the user."""
        stmt = select(Alert).where(Alert.session_id == session_id)
        if active_only:
            stmt = stmt.where(Alert.is_active == True)
        stmt = stmt.order_by(Alert.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_alert(
        self, db: AsyncSession, session_id: str, symbol: str, trigger_type: str, trigger_value: float
    ) -> Alert:
        """Declare a new active alert threshold."""
        symbol = symbol.upper().strip()
        alert = Alert(
            session_id=session_id,
            symbol=symbol,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            is_active=True
        )
        db.add(alert)
        await db.commit()
        
        # Re-query to guarantee access to generated fields
        stmt = select(Alert).where(Alert.id == alert.id)
        result = await db.execute(stmt)
        return result.scalar_one()

    async def delete_alert(self, db: AsyncSession, session_id: str, alert_id: uuid.UUID) -> bool:
        """Cancel an active alert."""
        stmt = select(Alert).where(Alert.session_id == session_id, Alert.id == alert_id)
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()
        if alert:
            await db.delete(alert)
            await db.commit()
            return True
        return False

    # Evaluation Engine
    async def check_alerts(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Check all active alert thresholds, evaluate satisfied triggers, and deactivate them."""
        stmt = select(Alert).where(Alert.is_active == True)
        result = await db.execute(stmt)
        active_alerts = result.scalars().all()
        
        triggered_alerts = []
        
        # Group alerts by symbol to batch third-party network fetches
        symbol_alerts = {}
        for alert in active_alerts:
            symbol_alerts.setdefault(alert.symbol, []).append(alert)
            
        for symbol, alerts in symbol_alerts.items():
            quote = None
            indicators = None
            sentiment = None
            
            for alert in alerts:
                triggered = False
                current_val = 0.0
                
                try:
                    # 1. Price Triggers
                    if alert.trigger_type in ["price_above", "price_below"]:
                        if quote is None:
                            quote = await stock_service.fetch_quote(symbol)
                        
                        if quote and "price" in quote:
                            current_val = quote["price"]
                            if alert.trigger_type == "price_above" and current_val > alert.trigger_value:
                                triggered = True
                            elif alert.trigger_type == "price_below" and current_val < alert.trigger_value:
                                triggered = True
                                
                    # 2. RSI Triggers
                    elif alert.trigger_type in ["rsi_above", "rsi_below"]:
                        if indicators is None:
                            indicators = await indicators_service.calculate_indicators(symbol)
                            
                        if indicators and "rsi" in indicators:
                            current_val = indicators["rsi"]
                            if alert.trigger_type == "rsi_above" and current_val > alert.trigger_value:
                                triggered = True
                            elif alert.trigger_type == "rsi_below" and current_val < alert.trigger_value:
                                triggered = True
                                
                    # 3. Sentiment Triggers
                    elif alert.trigger_type == "sentiment_drop":
                        if sentiment is None:
                            sentiment = await sentiment_service.analyze_sentiment(symbol, session_id=alert.session_id)
                            
                        if sentiment and "score" in sentiment:
                            current_val = sentiment["score"]
                            if current_val < alert.trigger_value:
                                triggered = True
                                
                except Exception as e:
                    logger.error(f"Error checking alert ID {alert.id} for ticker {symbol}: {e}")
                    continue
                    
                if triggered:
                    alert.is_active = False
                    triggered_alerts.append({
                        "alert_id": str(alert.id),
                        "session_id": alert.session_id,
                        "symbol": symbol,
                        "trigger_type": alert.trigger_type,
                        "trigger_value": alert.trigger_value,
                        "current_value": current_val,
                        "triggered_at": datetime.utcnow().isoformat()
                    })
                    logger.info(f"[ALERT TRIGGERED] {symbol} {alert.trigger_type} met: value {current_val} crossed trigger {alert.trigger_value}")
                    
        if triggered_alerts:
            await db.commit()
            
        return triggered_alerts


automation_service = AutomationService()
