from typing import Optional
import pandas as pd
from .indicators import add_technical_indicators
from .config import Settings


def score_stock(df: pd.DataFrame, settings: Settings, fundamentals: Optional[dict] = None) -> dict:
    if df.empty or len(df) < 50:
        return {"score": 0.0, "reason": "insufficient price history", "projected_window": None}
    df = add_technical_indicators(df)
    latest = df.iloc[-1]
    price = latest["Close"]
    if price > settings.price_ceiling:
        return {"score": 0.0, "reason": f"price above ceiling ({price:.2f})", "projected_window": None}
    if latest["Volume"] < settings.min_trading_volume:
        return {"score": 0.0, "reason": "low trading volume", "projected_window": None}

    score = 0.0
    reasons = []

    if latest["EMA20"] > latest["EMA50"]:
        score += 25
        reasons.append("short-term trend positive")
    else:
        reasons.append("weak short-term trend")

    if 30 <= latest["RSI"] <= 55:
        score += 20
        reasons.append("momentum is healthy")
    elif latest["RSI"] < 30:
        score += 10
        reasons.append("oversold, watch for reversal")
    else:
        reasons.append("RSI elevated")

    if latest["Close"] > latest["SMA20"]:
        score += 15
        reasons.append("price above 20-day average")
    else:
        reasons.append("below 20-day average")

    if latest["Close"] > latest["SMA50"]:
        score += 15
        reasons.append("above 50-day average")
    else:
        reasons.append("below 50-day average")

    if latest["MACD"] > latest["MACD_signal"]:
        score += 15
        reasons.append("MACD bullish")
    else:
        reasons.append("MACD weak")

    if latest["VolumeChange"] > 0.2:
        score += 10
        reasons.append("volume has picked up")

    if fundamentals:
        pe = fundamentals.get("trailingPE")
        if isinstance(pe, (int, float)) and 0 < pe <= settings.fundamental_pe_max:
            score += 10
            reasons.append("reasonable PE")
        elif isinstance(pe, (int, float)):
            reasons.append("high PE")

        dte = fundamentals.get("debtToEquity")
        if isinstance(dte, (int, float)) and dte <= settings.fundamental_debt_to_equity_max:
            score += 5
            reasons.append("manageable debt")
        elif isinstance(dte, (int, float)):
            reasons.append("high leverage")

        mc = fundamentals.get("marketCap")
        if isinstance(mc, (int, float)) and mc >= settings.fundamental_marketcap_min:
            score += 5
            reasons.append("minimum market cap met")
        elif mc is not None:
            reasons.append("market cap below ideal minimum")

    reason = "; ".join(reasons)
    projected_window = f"{settings.min_hold_days}-{settings.max_hold_days} days"
    return {"score": float(score), "reason": reason, "projected_window": projected_window}
