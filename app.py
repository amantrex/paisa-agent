import streamlit as st
from pathlib import Path
from datetime import date
import pandas as pd
from paisa_agent.config import Settings
from paisa_agent.data import load_tickers, fetch_bulk
from paisa_agent.strategy import score_stock
from paisa_agent.report import write_transaction_log, write_eod_report

@st.cache_data(ttl=3600)
def discover_candidates(settings: Settings) -> pd.DataFrame:
    tickers = load_tickers(settings.tickers_file)
    prices = fetch_bulk(tickers, settings.start_date, settings.end_date, cache_dir=settings.data_dir / "cache")
    rows = []
    for ticker, df in prices.items():
        score = score_stock(df, settings)
        if score["score"] <= 0:
            continue
        rows.append({
            "ticker": ticker,
            "score": score["score"],
            "reason": score["reason"],
            "projected_window": score["projected_window"],
            "price": float(df["Close"].iloc[-1]),
            "date": df.index[-1].date().isoformat(),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(by="score", ascending=False)


def build_daily_recommendations(candidates: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Allocate cash to top candidates using the portfolio optimizer.
    Returns a DataFrame with ticker, price, shares, invested, action ('buy' or 'skip'),
    and the scoring metadata (score, reason, projected_window)."""
    if candidates.empty:
        return pd.DataFrame(columns=["ticker", "price", "shares", "invested", "action", "score", "reason", "projected_window"])
    # Use the optimizer to get allocation respecting guard‑rails
    from paisa_agent.optimizer import allocate_capital
    allocation_df = allocate_capital(candidates, settings)
    # Prepare full decision DataFrame
    full_df = candidates.copy()
    full_df["action"] = "skip"
    full_df["shares"] = 0
    full_df["invested"] = 0.0
    if not allocation_df.empty:
        # Merge allocation info (shares, invested) back into full_df
        merged = pd.merge(full_df, allocation_df[["ticker", "shares", "invested"]], on="ticker", how="left", suffixes=("", "_alloc"))
        # Update rows where allocation exists
        allocated_mask = merged["shares_alloc"].notna()
        merged.loc[allocated_mask, "action"] = "buy"
        merged.loc[allocated_mask, "shares"] = merged.loc[allocated_mask, "shares_alloc"].astype(int)
        merged.loc[allocated_mask, "invested"] = merged.loc[allocated_mask, "invested_alloc"]
        # Drop temporary allocation columns
        full_df = merged.drop(columns=["shares_alloc", "invested_alloc"])
    else:
        full_df = full_df
    # Ensure column order
    return full_df[["ticker", "price", "shares", "invested", "action", "score", "reason", "projected_window"]]


def run_paper_trader():
    settings = Settings()
    print("Loading ticker universe from:", settings.tickers_file)
    candidates = discover_candidates(settings)
    print(f"Found {len(candidates)} candidate stocks today.")
    recommendations = build_daily_recommendations(candidates, settings)
    if recommendations.empty:
        print("No buy candidates found today based on the current rules.")
        return
    report_dir = Path(settings.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    recommendations_file = report_dir / f"recommendations_{date.today().isoformat()}.csv"
    recommendations.to_csv(recommendations_file, index=False)
    print("Daily recommendation report written to:", recommendations_file)
    print(recommendations[["ticker", "price", "shares", "invested", "action"]].to_string(index=False))


if __name__ == "__main__":
    run_paper_trader()
