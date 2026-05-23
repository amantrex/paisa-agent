from pathlib import Path
from datetime import date
import pandas as pd
from paisa_agent.config import Settings
from paisa_agent.data import load_tickers, fetch_bulk
from paisa_agent.strategy import score_stock
from paisa_agent.report import write_transaction_log, write_eod_report


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
    if candidates.empty:
        return candidates
    recommended = candidates.head(settings.max_daily_positions).copy()
    recommended["action"] = "buy"
    recommended["invest_amount"] = recommended["price"].apply(lambda price: min(settings.daily_budget, price * int(settings.daily_budget // price)))
    recommended["shares"] = (recommended["invest_amount"] / recommended["price"]).astype(int)
    recommended = recommended[recommended["shares"] >= 1]
    return recommended


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
    print(recommendations[["ticker", "price", "score", "shares", "reason", "projected_window"]].to_string(index=False))


if __name__ == "__main__":
    run_paper_trader()
