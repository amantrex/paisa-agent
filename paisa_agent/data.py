from pathlib import Path
from typing import List
import pandas as pd
import yfinance as yf
from .config import Settings


def load_tickers(path: Path | str) -> List[str]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Tickers file not found: {path}")
    df = pd.read_csv(path, header=None, names=["ticker"])
    tickers = []
    seen = set()
    for raw in df["ticker"].tolist():
        ticker = str(raw).strip().upper()
        if not ticker:
            continue
        symbol = f"{ticker}.NS" if not ticker.endswith(".NS") else ticker
        if symbol not in seen:
            seen.add(symbol)
            tickers.append(symbol)
    return tickers


def filter_penny_tickers_by_current_price(tickers: List[str], max_price: float = 20.0, batch_size: int = 50) -> List[str]:
    valid_tickers: List[str] = []
    skipped: List[str] = []
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        try:
            raw = yf.download(batch, period="2d", progress=False)
        except Exception as exc:
            print(f"Warning: batch price fetch failed for {batch}: {exc}")
            for ticker in batch:
                try:
                    df = yf.download(ticker, period="2d", progress=False)
                except Exception:
                    skipped.append(ticker)
                    continue
                if df.empty:
                    skipped.append(ticker)
                    continue
                close = df["Close"].iloc[-1]
                if close < max_price:
                    valid_tickers.append(ticker)
                else:
                    skipped.append(ticker)
            continue
        if raw.empty:
            skipped.extend(batch)
            continue
        if isinstance(raw.columns, pd.MultiIndex):
            for ticker in batch:
                if ticker not in raw.columns.get_level_values(1):
                    skipped.append(ticker)
                    continue
                try:
                    close = raw[("Close", ticker)].iloc[-1]
                except Exception:
                    skipped.append(ticker)
                    continue
                if close < max_price:
                    valid_tickers.append(ticker)
                else:
                    skipped.append(ticker)
        else:
            for ticker in batch:
                if "Close" not in raw.columns:
                    skipped.append(ticker)
                    continue
                try:
                    close = raw["Close"].iloc[-1]
                except Exception:
                    skipped.append(ticker)
                    continue
                if close < max_price:
                    valid_tickers.append(ticker)
                else:
                    skipped.append(ticker)
    if skipped:
        print(f"Filtered out {len(skipped)} ticker(s) above ₹{max_price} or with invalid current data.")
    return valid_tickers


def fetch_historical(ticker: str, start: str, end: str) -> pd.DataFrame:
    try:
        df = yf.download(ticker, start=start, end=end, progress=False)
    except Exception as exc:
        print(f"Warning: failed to download {ticker}: {exc}")
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    if "Adj Close" not in df.columns and "Close" in df.columns:
        df["Adj Close"] = df["Close"]

    required = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    available = [col for col in required if col in df.columns]
    if len(available) < len(required):
        print(f"Warning: {ticker} data missing required columns: {set(required) - set(available)}")
        return pd.DataFrame()

    df = df[available].dropna()
    if df.empty:
        return pd.DataFrame()

    df.index = pd.to_datetime(df.index)
    
    # Validate data integrity
    if len(df) == 0:
        print(f"Warning: {ticker} has no valid data after filtering")
        return pd.DataFrame()
    if (df < 0).any().any():
        print(f"Warning: {ticker} has negative values, removing invalid rows")
        df = df[(df > 0).all(axis=1)]
    if df.empty:
        return pd.DataFrame()
    
    return df


def fetch_bulk(tickers: List[str], start: str, end: str, cache_dir: Path | str = "data/cache") -> dict:
    from datetime import datetime
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    results = {}
    skipped = []
    for ticker in tickers:
        file_path = cache_path / f"{ticker.replace('.', '_')}.csv"
        df = pd.DataFrame()
        
        # Check cache validity: use cached data only if less than 1 day old
        if file_path.exists():
            cache_age_seconds = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).total_seconds()
            if cache_age_seconds < 86400:  # 24 hours
                try:
                    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                    if not df.empty and len(df) > 0:
                        results[ticker] = df
                        continue
                except Exception as e:
                    print(f"Warning: Failed to read cache for {ticker}: {e}")
        
        # Fetch fresh data if cache miss or cache too old
        df = fetch_historical(ticker, start, end)
        if not df.empty:
            try:
                df.to_csv(file_path)
                results[ticker] = df
            except Exception as e:
                print(f"Warning: Failed to cache {ticker}: {e}")
                # Still add to results even if cache write fails
                results[ticker] = df
        else:
            skipped.append(ticker)
    
    if skipped:
        print(f"Skipped {len(skipped)} ticker(s) due to missing or invalid historical data: {','.join(skipped)}")
    return results
