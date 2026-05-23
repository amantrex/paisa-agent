from pathlib import Path
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path("data")
    report_dir: Path = Path("reports")
    tickers_file: Path = Path("data/penny_stocks_sample.csv")
    start_date: str = "2022-01-01"
    end_date: str = "2026-05-31"
    # ----- NEW GUARD‑RAILS -----
    max_daily_loss_pct: float = 0.05        # abort day if loss >5 %
    max_position_pct: float = 0.10          # per‑ticker exposure cap (10 % of cash)
    commission_per_share: float = 0.25      # ₹ per share
    slippage_pct: float = 0.001             # 0.1 % price slippage
    portfolio_opt_top_n: int = 10           # consider top‑N candidates for allocation
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
