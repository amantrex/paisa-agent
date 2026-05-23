from pathlib import Path
import pandas as pd
from datetime import date


def write_transaction_log(transactions: pd.DataFrame, report_dir: Path | str) -> Path:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    file_path = report_path / f"transactions_{date.today().isoformat()}.csv"
    transactions.to_csv(file_path, index=False)
    return file_path


def write_trade_log(trades: pd.DataFrame, report_dir: Path | str) -> Path:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    file_path = report_path / f"backtest_trades_{date.today().isoformat()}.csv"
    trades.to_csv(file_path, index=False)
    return file_path


def write_portfolio_log(portfolio: pd.DataFrame, report_dir: Path | str) -> Path:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    file_path = report_path / f"backtest_portfolio_{date.today().isoformat()}.csv"
    portfolio.to_csv(file_path, index=False)
    return file_path


def write_performance_summary(metrics: dict, report_dir: Path | str) -> Path:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    file_path = report_path / f"backtest_summary_{date.today().isoformat()}.csv"
    pd.DataFrame([metrics]).to_csv(file_path, index=False)
    return file_path


def write_eod_report(portfolio: list, summary: pd.DataFrame, report_dir: Path | str) -> Path:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    rows = []
    for pos in portfolio:
        rows.append({
            "ticker": pos.ticker,
            "buy_date": pos.buy_date.date().isoformat(),
            "buy_price": pos.buy_price,
            "shares": pos.shares,
            "invested": pos.invested,
            "projected_sell_date": pos.projected_sell_date.date().isoformat(),
            "reason": pos.reason,
        })
    portfolio_df = pd.DataFrame(rows)
    summary_file = report_path / f"portfolio_{date.today().isoformat()}.csv"
    portfolio_df.to_csv(summary_file, index=False)
    report_file = report_path / f"eod_summary_{date.today().isoformat()}.csv"
    summary.to_csv(report_file, index=False)
    return report_file
