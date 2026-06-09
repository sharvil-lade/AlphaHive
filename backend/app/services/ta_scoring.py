import logging
from typing import Dict, Any

logger = logging.getLogger("ta-scoring")


class TAScoring:
    """Quantitative scoring engine evaluating technical analysis indicators and generating postures."""

    def evaluate_posture(self, indicators: Dict[str, Any], price_quote: Dict[str, Any]) -> Dict[str, Any]:
        """Assess technical indicators and assign a normalized technical score between -100 and +100.

        Returns:
            Dict[str, Any]: Consolidated technical score, rating, and component signals.
        """
        if not indicators:
            return {
                "score": 0,
                "rating": "HOLD",
                "signals": {},
                "summary": "Insufficient technical indicator metrics to compute rating."
            }

        symbol = indicators["symbol"]
        close = indicators["close"]
        rsi = indicators["rsi"]
        
        # Components breakdown dictionary
        signals = {
            "rsi": {"score": 0, "signal": "neutral"},
            "macd": {"score": 0, "signal": "neutral"},
            "trends": {"score": 0, "signal": "neutral"},
            "bollinger": {"score": 0, "signal": "neutral"},
            "volume": {"score": 0, "signal": "neutral"}
        }

        # 1. RSI Scoring
        if rsi < 30:
            signals["rsi"] = {"score": 15, "signal": "oversold_bullish"}
        elif rsi > 70:
            signals["rsi"] = {"score": -15, "signal": "overbought_bearish"}
        elif 30 <= rsi <= 40:
            signals["rsi"] = {"score": 5, "signal": "accumulating_bullish"}
        elif 60 <= rsi <= 70:
            signals["rsi"] = {"score": -5, "signal": "distributing_bearish"}
        
        # 2. MACD Momentum Scoring
        if indicators["macd_crossover_bullish"]:
            signals["macd"] = {"score": 20, "signal": "bullish_crossover"}
        elif indicators["macd_crossover_bearish"]:
            signals["macd"] = {"score": -20, "signal": "bearish_crossover"}
        else:
            # Check momentum states
            macd_hist = indicators["macd_hist"]
            if macd_hist > 0:
                signals["macd"] = {"score": 10, "signal": "bullish_momentum"}
            else:
                signals["macd"] = {"score": -10, "signal": "bearish_momentum"}

        # 3. Moving Averages Trend Scoring
        trend_score = 0
        sma_50 = indicators.get("sma_50")
        sma_200 = indicators.get("sma_200")
        ema_9 = indicators.get("ema_9")
        ema_21 = indicators.get("ema_21")

        if sma_50:
            trend_score += 10 if close > sma_50 else -10
        if sma_200:
            trend_score += 15 if close > sma_200 else -15
        if ema_9 and ema_21:
            trend_score += 10 if ema_9 > ema_21 else -10

        # Classify overall trend signal
        trend_sig = "neutral"
        if trend_score > 15:
            trend_sig = "strong_bullish_trend"
        elif trend_score > 0:
            trend_sig = "weak_bullish_trend"
        elif trend_score < -15:
            trend_sig = "strong_bearish_trend"
        elif trend_score < 0:
            trend_sig = "weak_bearish_trend"
            
        signals["trends"] = {"score": trend_score, "signal": trend_sig}

        # 4. Bollinger Bands Scoring
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        if bb_upper and close >= bb_upper:
            signals["bollinger"] = {"score": -15, "signal": "overextended_bearish"}
        elif bb_lower and close <= bb_lower:
            signals["bollinger"] = {"score": 15, "signal": "overextended_bullish"}

        # 5. Volume Scoring
        volume = indicators["volume"]
        volume_sma_20 = indicators.get("volume_sma_20")
        if volume_sma_20 and volume > volume_sma_20:
            # Check price direction change
            pct_change = price_quote.get("percent_change", 0.0)
            if pct_change > 0:
                signals["volume"] = {"score": 10, "signal": "high_volume_accumulation"}
            elif pct_change < 0:
                signals["volume"] = {"score": -10, "signal": "high_volume_distribution"}

        # Calculate final aggregated score
        total_raw_score = (
            signals["rsi"]["score"] +
            signals["macd"]["score"] +
            signals["trends"]["score"] +
            signals["bollinger"]["score"] +
            signals["volume"]["score"]
        )

        # Normalize score to sit strictly between -100 and +100
        normalized_score = max(-100, min(100, total_raw_score))

        # Assign ratings based on normalized score threshold bounds
        if normalized_score >= 30:
            rating = "BUY"
            summary = f"Technical indicators suggest robust bullish momentum for {symbol}. Moving averages trend is supportive."
        elif normalized_score <= -30:
            rating = "SELL"
            summary = f"Technical indicators indicate severe bearish momentum or overextension for {symbol}. Exercise caution."
        else:
            rating = "HOLD"
            summary = f"Technical postures for {symbol} are conflicting or neutral. Market indicates consolidation."

        return {
            "symbol": symbol,
            "close": close,
            "score": normalized_score,
            "rating": rating,
            "signals": signals,
            "summary": summary,
            "pivots": indicators.get("pivots")
        }


ta_scoring = TAScoring()
