import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from app.services.stock_service import stock_service

logger = logging.getLogger("indicators-service")


class IndicatorsService:
    """Calculates technical analysis indicators natively using pandas and numpy."""

    async def calculate_indicators(self, symbol: str) -> Dict[str, Any]:
        """Fetch historical daily data for a stock and calculate all key technical indicators.

        Returns:
            Dict[str, Any]: A dictionary containing calculated indicators for the most recent day.
        """
        symbol = symbol.upper()
        # Fetch last 3 months of historical daily price series to have enough data for 50/200 SMA
        history = await stock_service.fetch_history(symbol, interval="1d", range_str="3mo")
        if not history or len(history) < 20:
            logger.warn(f"Insufficient history data for {symbol} to calculate indicators.")
            return {}

        # Convert historical list to pandas DataFrame
        df = pd.DataFrame(history)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # 1. Simple Moving Averages (SMA) & Exponential Moving Averages (EMA)
        df["sma_20"] = df["close"].rolling(window=20).mean()
        df["sma_50"] = df["close"].rolling(window=50).mean()
        # Fallback to SMA 50 if history size is less than 200 bars for SMA 200
        if len(df) >= 200:
            df["sma_200"] = df["close"].rolling(window=200).mean()
        else:
            # Recompute on 1 year if needed, or set to null
            df["sma_200"] = None

        df["ema_9"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema_21"] = df["close"].ewm(span=21, adjust=False).mean()

        # 2. Relative Strength Index (RSI 14)
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        
        # Wilder's Smoothing for RSI
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss
        df["rsi"] = 100.0 - (100.0 / (1.0 + rs))

        # 3. MACD (12, 26, 9)
        ema_12 = df["close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema_12 - ema_26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # 4. Bollinger Bands (20, 2)
        std_20 = df["close"].rolling(window=20).std()
        df["bb_middle"] = df["sma_20"]
        df["bb_upper"] = df["bb_middle"] + (2 * std_20)
        df["bb_lower"] = df["bb_middle"] - (2 * std_20)

        # 5. Volume Indicators
        df["volume_sma_20"] = df["volume"].rolling(window=20).mean()

        # Extract the latest calculated indicators (last row of DataFrame)
        latest_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else latest_row

        # Determine crossovers
        macd_crossover_bullish = bool(prev_row["macd"] <= prev_row["macd_signal"] and latest_row["macd"] > latest_row["macd_signal"])
        macd_crossover_bearish = bool(prev_row["macd"] >= prev_row["macd_signal"] and latest_row["macd"] < latest_row["macd_signal"])

        # Pivot point support / resistance (based on the previous bar's metrics)
        pivot_metrics = prev_row
        high = float(pivot_metrics["high"])
        low = float(pivot_metrics["low"])
        close = float(pivot_metrics["close"])

        p = (high + low + close) / 3.0
        r1 = (2.0 * p) - low
        s1 = (2.0 * p) - high
        r2 = p + (high - low)
        s2 = p - (high - low)

        return {
            "symbol": symbol,
            "date": latest_row["date"].strftime("%Y-%m-%d"),
            "close": float(latest_row["close"]),
            "rsi": float(latest_row["rsi"]) if not pd.isna(latest_row["rsi"]) else 50.0,
            "macd": float(latest_row["macd"]) if not pd.isna(latest_row["macd"]) else 0.0,
            "macd_signal": float(latest_row["macd_signal"]) if not pd.isna(latest_row["macd_signal"]) else 0.0,
            "macd_hist": float(latest_row["macd_hist"]) if not pd.isna(latest_row["macd_hist"]) else 0.0,
            "macd_crossover_bullish": macd_crossover_bullish,
            "macd_crossover_bearish": macd_crossover_bearish,
            "sma_20": float(latest_row["sma_20"]) if not pd.isna(latest_row["sma_20"]) else None,
            "sma_50": float(latest_row["sma_50"]) if not pd.isna(latest_row["sma_50"]) else None,
            "sma_200": float(latest_row["sma_200"]) if (latest_row["sma_200"] is not None and not pd.isna(latest_row["sma_200"])) else None,
            "ema_9": float(latest_row["ema_9"]) if not pd.isna(latest_row["ema_9"]) else None,
            "ema_21": float(latest_row["ema_21"]) if not pd.isna(latest_row["ema_21"]) else None,
            "bb_upper": float(latest_row["bb_upper"]) if not pd.isna(latest_row["bb_upper"]) else None,
            "bb_middle": float(latest_row["bb_middle"]) if not pd.isna(latest_row["bb_middle"]) else None,
            "bb_lower": float(latest_row["bb_lower"]) if not pd.isna(latest_row["bb_lower"]) else None,
            "volume": int(latest_row["volume"]),
            "volume_sma_20": float(latest_row["volume_sma_20"]) if not pd.isna(latest_row["volume_sma_20"]) else None,
            "pivots": {
                "pivot": p,
                "r1": r1,
                "s1": s1,
                "r2": r2,
                "s2": s2
            }
        }


indicators_service = IndicatorsService()
