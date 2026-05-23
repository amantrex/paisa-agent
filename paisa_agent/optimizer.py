import numpy as np
import pandas as pd
from .config import Settings


def allocate_capital(candidates: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Allocate cash to top candidates respecting guard‑rails.

    Returns a DataFrame with columns: ticker, price, shares, invested.
    """
    if candidates.empty:
        return pd.DataFrame(columns=["ticker", "price", "shares", "invested"])
    # Select top N candidates
    top_n = min(settings.portfolio_opt_top_n, len(candidates))
    top = candidates.nlargest(top_n, "score").copy()
    # Softmax weights based on scores
    scores = top["score"].values.astype(float)
    exp_scores = np.exp(scores - np.max(scores))  # for numeric stability
    weights = exp_scores / exp_scores.sum()
    # Compute allocation per ticker
    allocations = []
    max_position_cash = settings.starting_capital * settings.max_position_pct
    for i, (idx, row) in enumerate(top.iterrows()):
        price = row["price"]
        effective_price = price * (1 + settings.slippage_pct) + settings.commission_per_share
        raw_cash = settings.starting_capital * weights[i]
        cash = min(raw_cash, max_position_cash)
        shares = int(cash // effective_price)
        if shares < 1:
            continue
        invested = shares * effective_price
        allocations.append({
            "ticker": row["ticker"],
            "price": price,
            "shares": shares,
            "invested": invested,
        })
    return pd.DataFrame(allocations)
