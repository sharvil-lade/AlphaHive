import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.schemas import BacktestRequest, BacktestResponse
from app.services.backtest_service import backtest_service

router = APIRouter()
logger = logging.getLogger("backtest-api")


@router.post("", response_model=BacktestResponse, status_code=status.HTTP_200_OK)
async def run_backtest(
    backtest_in: BacktestRequest
):
    """Run historical backtesting simulation for a symbol, strategy, and range."""
    try:
        result = await backtest_service.run_backtest(
            symbol=backtest_in.symbol,
            strategy=backtest_in.strategy,
            initial_capital=backtest_in.initial_capital,
            range_str=backtest_in.range_str
        )
        return result
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backtest execution failed: {str(e)}"
        )
