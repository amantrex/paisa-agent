from pathlib import Path
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path("data")
    report_dir: Path = Path("reports")
    tickers_file: Path = Path("data/penny_stocks_sample.csv")
    start_date: str = "2022-01-01"
    end_date: str = "2026-05-31"
    starting_capital: float = 10000.0
    daily_budget: float = 100.0
    max_hold_days: int = 180
    min_hold_days: int = 30
    max_daily_positions: int = 3
    price_ceiling: float = 20.0
    min_trading_volume: int = 10000
    buy_score_threshold: float = 50.0
    stop_loss_pct: float = 0.08
    take_profit_pct: float = 0.16
    fundamental_pe_max: float = 100.0
    fundamental_debt_to_equity_max: float = 400.0
    fundamental_marketcap_min: float = 1e8
