# paisa-agent

A lean paper-trading engine for Indian penny stocks, built for research, daily recommendation generation, and simulated micro-investing.

## What this initial version includes

- Phase 1 scaffold for market research and historical data ingestion using free data sources
- Technical indicator calculation: SMA, EMA, RSI, MACD, ATR, volume change
- Daily candidate discovery for stocks priced below ₹20
- Recommendation report export to `reports/recommendations_<date>.csv`
- Minimal Streamlit dashboard for candidate review
- Simple portfolio simulation and logging support

## Getting started

1. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

2. Run the paper-trading recommendation builder:

```bash
python app.py
```

3. Run the dashboard locally:

```bash
streamlit run streamlit_app.py
```

## Data

- The sample universe lives in `data/penny_stocks_sample.csv`.
- The loader appends `.NS` and fetches from Yahoo Finance.
- Expand the universe file to 200-250 tickers once you have a broader list.

## Project structure

- `paisa_agent/data.py`: ticker loading and historical data ingestion
- `paisa_agent/indicators.py`: technical indicator computations
- `paisa_agent/strategy.py`: simple scoring engine and buy reasoning
- `paisa_agent/backtest.py`: simulation helpers and position logic
- `paisa_agent/report.py`: CSV report generation
- `app.py`: command-line recommendation generation
- `streamlit_app.py`: lightweight UI for inspection

## Phase roadmap

1. Market research: fetch 1-2 years of history, analyze 200+ penny stocks, refine scoring rules
2. Recommendation engine: daily candidate generator, micro-investment simulation, transaction logging
3. Real execution: broker integration after consistent paper profitability

## Historical backtesting

The current repository now includes a full historical backtest engine that:

- uses real historical daily close prices for each ticker
- integrates a fundamentals scoring layer for market cap, PE and debt ratios
- buys and sells based on technical and fundamental conditions
- applies stop loss, take profit, and time-based exit rules
- logs every trade with reason, cash balance and projection window
- exports daily portfolio values plus performance summary reports
- appends backtest outcome records to a growing knowledge base at `reports/knowledge_base.csv`

Run the backtest with:

```bash
python historical_backtest.py
```

If you want to refresh fundamentals cache:

```bash
python historical_backtest.py --refresh-fundamentals
```

## Notes on cost and API usage

- This repository does not require an LLM API to run. The core engine is pure Python and uses free market data from Yahoo Finance.
- If you choose to add an LLM for journal generation or trading rationale, keep usage small:
  - Market research summaries: 5-10 prompts, ~1000 tokens total
  - Daily recommendation notes: 1 prompt per day, ~200-400 tokens
  - Total expected usage: under 5k tokens per week for initial phases.
- At typical OpenAI pricing, that works out to a few cents per week for summarization alone.
- Recurring cost is therefore dominated by compute and brokerage fees, not LLM credits.

## Next step

- Expand `data/penny_stocks_sample.csv` with the full penny stock universe
- Run `python app.py` and examine generated recommendations and `reports/`
- Run `python historical_backtest.py` to validate the INR penny-stock universe and performance
- Iterate on the `score_stock` rules in `paisa_agent/strategy.py`
