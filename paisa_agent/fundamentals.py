from pathlib import Path
import json
from typing import List
import yfinance as yf


def load_cached_fundamentals(cache_dir: Path | str) -> dict:
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    file_path = cache_path / "fundamentals_cache.json"
    if not file_path.exists():
        return {}
    with file_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_cached_fundamentals(data: dict, cache_dir: Path | str) -> None:
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    file_path = cache_path / "fundamentals_cache.json"
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def fetch_fundamental_profile(ticker: str) -> dict:
    ticker_obj = yf.Ticker(ticker)
    info = ticker_obj.info or {}
    return {
        "symbol": ticker,
        "marketCap": info.get("marketCap"),
        "trailingPE": info.get("trailingPE"),
        "forwardPE": info.get("forwardPE"),
        "priceToBook": info.get("priceToBook"),
        "debtToEquity": info.get("debtToEquity"),
        "returnOnEquity": info.get("returnOnEquity"),
        "trailingAnnualDividendYield": info.get("trailingAnnualDividendYield"),
        "industry": info.get("industry"),
        "sector": info.get("sector"),
    }


def fetch_fundamentals_bulk(tickers: List[str], cache_dir: Path | str = "data/cache", refresh: bool = False) -> dict:
    cached = load_cached_fundamentals(cache_dir)
    results = {}
    for ticker in tickers:
        if ticker in cached and not refresh:
            results[ticker] = cached[ticker]
            continue
        try:
            profile = fetch_fundamental_profile(ticker)
            results[ticker] = profile
            cached[ticker] = profile
        except Exception:
            continue
    save_cached_fundamentals(cached, cache_dir)
    return results
