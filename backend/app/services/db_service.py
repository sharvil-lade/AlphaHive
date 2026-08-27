import logging
from datetime import date
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import Stock, StockPrice

logger = logging.getLogger("db-service")


class DBService:
    """Service class handling CRUD operations for Stocks and StockPrices in PostgreSQL."""

    async def upsert_stock(
        self,
        db: AsyncSession,
        symbol: str,
        name: str,
        sector: str | None = None,
        industry: str | None = None,
    ) -> Stock:
        """Upsert stock metadata records.

        Returns:
            Stock: Database stock model.
        """
        symbol = symbol.upper()

        stmt = insert(Stock).values(symbol=symbol, name=name, sector=sector, industry=industry)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol"],
            set_={
                "name": stmt.excluded.name,
                "sector": stmt.excluded.sector,
                "industry": stmt.excluded.industry,
            },
        )

        await db.execute(stmt)
        await db.flush()

        result = await db.execute(select(Stock).where(Stock.symbol == symbol))
        return result.scalar_one()

    async def save_historical_prices(
        self, db: AsyncSession, symbol: str, prices_list: list[dict[str, Any]]
    ) -> int:
        """Save a series of OHLCV prices into PostgreSQL using high-performance bulk upserts.

        Returns:
            int: Number of rows successfully inserted/updated.
        """
        if not prices_list:
            return 0

        symbol = symbol.upper()
        upsert_count = 0

        value_rows = []
        for item in prices_list:
            d_val = item["date"]
            if isinstance(d_val, str):
                d_val = date.fromisoformat(d_val)

            value_rows.append(
                {
                    "symbol": symbol,
                    "date": d_val,
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                    "volume": int(item["volume"]),
                }
            )

        # Process in chunks of 100 to avoid query size limits
        chunk_size = 100
        for i in range(0, len(value_rows), chunk_size):
            chunk = value_rows[i : i + chunk_size]

            stmt = insert(StockPrice).values(chunk)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_symbol_date",
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                },
            )

            res = await db.execute(stmt)
            upsert_count += res.rowcount

        await db.flush()
        logger.info(f"Successfully upserted {upsert_count} stock price records for {symbol}")
        return upsert_count

    async def get_stored_prices(self, db: AsyncSession, symbol: str, limit: int = 100) -> list[StockPrice]:
        """Retrieve stored historical stock prices from DB, sorted by date ascending.

        Returns:
            List[StockPrice]: Stored stock prices.
        """
        symbol = symbol.upper()
        stmt = (
            select(StockPrice).where(StockPrice.symbol == symbol).order_by(StockPrice.date.asc()).limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


db_service = DBService()
