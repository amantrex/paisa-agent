from argparse import ArgumentParser
from pathlib import Path
from datetime import date
import pandas as pd
from paisa_agent.config import Settings
from paisa_agent.data import load_tickers, fetch_bulk, filter_penny_tickers_by_current_price
from paisa_agent.fundamentals import fetch_fundamentals_bulk
from paisa_agent.backtest import BacktestEngine
from paisa_agent.report import write_trade_log, write_portfolio_log, write_performance_summary
from paisa_agent.knowledge import append_knowledge_records


def run_historical_backtest(settings: Settings, refresh: bool = False) -> dict | None:
    tickers = load_tickers(settings.tickers_file)
    tickers = filter_penny_tickers_by_current_price(tickers, settings.price_ceiling)
    if not tickers:
        return None
    prices = fetch_bulk(tickers, settings.start_date, settings.end_date, cache_dir=settings.data_dir / "cache")
    if not prices:
        return None
    fundamentals = fetch_fundamentals_bulk(list(prices.keys()), cache_dir=settings.data_dir / "cache", refresh=refresh)
    engine = BacktestEngine(settings)
    trades, daily_portfolio = engine.run(prices, fundamentals)
    metrics = engine.evaluate(trades, daily_portfolio)
    report_dir = Path(settings.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    trades_file = write_trade_log(trades, report_dir)
    portfolio_file = write_portfolio_log(daily_portfolio, report_dir)
    summary_file = write_performance_summary(metrics, report_dir)
    knowledge_file = append_knowledge_records(trades, report_dir)
    return {
        "metrics": metrics,
        "trades_file": trades_file,
        "portfolio_file": portfolio_file,
        "summary_file": summary_file,
        "knowledge_file": knowledge_file,
    }


def main():
    parser = ArgumentParser(description="Run a full historical penny stock backtest.")
    parser.add_argument("--refresh-fundamentals", action="store_true", help="Refresh cached fundamentals data.")
    args = parser.parse_args()

    settings = Settings()
    result = run_historical_backtest(settings, refresh=args.refresh_fundamentals)
    if result is None:
        print("Historical backtest failed or produced no valid result.")
        return

    print("Backtest complete.")
    print(f"Knowledge base updated: {result['knowledge_file']}")
    print(f"Trades written to: {result['trades_file']}")
    print(f"Daily portfolio values written to: {result['portfolio_file']}")
    print(f"Performance summary written to: {result['summary_file']}")
    print("Metrics:")
    for key, value in result["metrics"].items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
