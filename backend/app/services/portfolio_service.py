import logging
import uuid
from typing import Dict, Any, List, Optional
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.models import Portfolio, PortfolioHolding
from backend.app.services.stock_service import stock_service

logger = logging.getLogger("portfolio-service")


class PortfolioService:
    """Service class managing portfolio CRUD operations and computing risk/sector analytics."""

    async def get_or_create_portfolio(
        self, db: AsyncSession, session_id: str, name: str = "My AI Portfolio"
    ) -> Portfolio:
        """Find user's portfolio by session_id, or create a default one if not found."""
        stmt = select(Portfolio).options(selectinload(Portfolio.holdings)).where(Portfolio.session_id == session_id)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            portfolio = Portfolio(session_id=session_id, name=name)
            db.add(portfolio)
            await db.commit()
            
            # Re-query to guarantee access to generated fields
            stmt = select(Portfolio).options(selectinload(Portfolio.holdings)).where(Portfolio.session_id == session_id)
            result = await db.execute(stmt)
            portfolio = result.scalar_one_or_none()
        return portfolio

    async def add_holding(
        self, db: AsyncSession, session_id: str, symbol: str, shares: float, average_buy_price: float
    ) -> PortfolioHolding:
        """Add a holding to the user's portfolio. Updates existing shares/cost if symbol matches."""
        portfolio = await self.get_or_create_portfolio(db, session_id)
        symbol = symbol.upper().strip()
        
        stmt = select(PortfolioHolding).where(
            PortfolioHolding.portfolio_id == portfolio.id,
            PortfolioHolding.symbol == symbol
        )
        result = await db.execute(stmt)
        holding = result.scalar_one_or_none()
        
        if holding:
            # Update weighted average cost and accumulated shares
            total_cost = (holding.shares * holding.average_buy_price) + (shares * average_buy_price)
            total_shares = holding.shares + shares
            holding.shares = total_shares
            holding.average_buy_price = total_cost / total_shares if total_shares > 0 else 0.0
        else:
            holding = PortfolioHolding(
                portfolio_id=portfolio.id,
                symbol=symbol,
                shares=shares,
                average_buy_price=average_buy_price
            )
            db.add(holding)
            
        await db.commit()
        return holding

    async def update_holding(
        self, db: AsyncSession, holding_id: uuid.UUID, shares: float, average_buy_price: float
    ) -> Optional[PortfolioHolding]:
        """Modify shares or buy price on an existing holding."""
        stmt = select(PortfolioHolding).where(PortfolioHolding.id == holding_id)
        result = await db.execute(stmt)
        holding = result.scalar_one_or_none()
        if holding:
            holding.shares = shares
            holding.average_buy_price = average_buy_price
            await db.commit()
        return holding

    async def delete_holding(self, db: AsyncSession, holding_id: uuid.UUID) -> bool:
        """Remove a holding from database."""
        stmt = select(PortfolioHolding).where(PortfolioHolding.id == holding_id)
        result = await db.execute(stmt)
        holding = result.scalar_one_or_none()
        if holding:
            await db.delete(holding)
            await db.commit()
            return True
        return False

    async def get_portfolio_summary(self, db: AsyncSession, session_id: str) -> Dict[str, Any]:
        """Fetch portfolio holdings details and calculate volatility, beta, and sector allocation metrics."""
        portfolio = await self.get_or_create_portfolio(db, session_id)
        
        stmt = select(PortfolioHolding).where(PortfolioHolding.portfolio_id == portfolio.id)
        result = await db.execute(stmt)
        holdings = result.scalars().all()
        
        total_value = 0.0
        total_cost = 0.0
        
        holdings_detail = []
        sector_values = {}
        
        weighted_beta_sum = 0.0
        weighted_vol_sum = 0.0
        
        for h in holdings:
            symbol = h.symbol
            shares = h.shares
            avg_price = h.average_buy_price
            
            # 1. Fetch current price with fallback to average buy price
            current_price = avg_price
            try:
                quote = await stock_service.fetch_quote(symbol)
                if quote and "price" in quote:
                    current_price = quote["price"]
            except Exception as e:
                logger.warning(f"Failed to fetch quote for {symbol} in portfolio: {e}")
                
            # 2. Fetch sector with fallback
            sector = "Other"
            try:
                profile = await stock_service.fetch_profile(symbol)
                if profile and profile.get("sector"):
                    sector = profile["sector"]
            except Exception as e:
                logger.warning(f"Failed to fetch profile for {symbol} in portfolio: {e}")
                
            # 3. Calculate volatility and beta
            beta = 1.0
            vol = 0.0
            try:
                stock_history = await stock_service.fetch_history(symbol, range_str="1y")
                spy_history = await stock_service.fetch_history("SPY", range_str="1y")
                
                if len(stock_history) > 10:
                    stock_closes = [sh["close"] for sh in stock_history]
                    stock_returns = np.diff(stock_closes) / stock_closes[:-1]
                    daily_vol = np.std(stock_returns)
                    vol = float(daily_vol * np.sqrt(252))
                    
                    stock_by_date = {sh["date"]: sh["close"] for sh in stock_history}
                    spy_by_date = {sh["date"]: sh["close"] for sh in spy_history}
                    common_dates = sorted(list(set(stock_by_date.keys()) & set(spy_by_date.keys())))
                    
                    if len(common_dates) > 10:
                        aligned_stock = [stock_by_date[d] for d in common_dates]
                        aligned_spy = [spy_by_date[d] for d in common_dates]
                        
                        stock_rets = np.diff(aligned_stock) / aligned_stock[:-1]
                        spy_rets = np.diff(aligned_spy) / aligned_spy[:-1]
                        
                        cov = np.cov(stock_rets, spy_rets)[0][1]
                        spy_var = np.var(spy_rets)
                        beta = float(cov / spy_var if spy_var > 0 else 1.0)
            except Exception as e:
                logger.warning(f"Failed to calculate statistical metrics for {symbol}: {e}")
                
            h_cost = shares * avg_price
            h_value = shares * current_price
            h_gain = h_value - h_cost
            h_gain_pct = (h_gain / h_cost * 100.0) if h_cost > 0 else 0.0
            
            total_cost += h_cost
            total_value += h_value
            
            sector_values[sector] = sector_values.get(sector, 0.0) + h_value
            
            holdings_detail.append({
                "id": str(h.id),
                "portfolio_id": str(h.portfolio_id),
                "symbol": symbol,
                "shares": shares,
                "average_buy_price": avg_price,
                "current_price": current_price,
                "total_value": h_value,
                "total_cost": h_cost,
                "gain_loss": h_gain,
                "gain_loss_percentage": h_gain_pct,
                "sector": sector,
                "beta": beta,
                "volatility": vol,
                "last_updated": h.last_updated.isoformat() if h.last_updated else None
            })
            
        # Sector weights & weighted risk indicators
        sector_weights = {}
        for s, val in sector_values.items():
            sector_weights[s] = (val / total_value * 100.0) if total_value > 0 else 0.0
            
        for hd in holdings_detail:
            weight = (hd["total_value"] / total_value) if total_value > 0 else 0.0
            weighted_beta_sum += hd["beta"] * weight
            weighted_vol_sum += hd["volatility"] * weight
            
        gain_loss = total_value - total_cost
        gain_loss_pct = (gain_loss / total_cost * 100.0) if total_cost > 0 else 0.0
        
        return {
            "portfolio_id": str(portfolio.id),
            "name": portfolio.name,
            "total_value": total_value,
            "total_cost": total_cost,
            "gain_loss": gain_loss,
            "gain_loss_percentage": gain_loss_pct,
            "weighted_beta": weighted_beta_sum,
            "weighted_volatility": weighted_vol_sum,
            "holdings": holdings_detail,
            "sector_weights": sector_weights
        }


portfolio_service = PortfolioService()
