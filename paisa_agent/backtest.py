from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List, Optional
import pandas as pd

from .config import Settings
from .strategy import score_stock
from .indicators import add_technical_indicators


@dataclass
class Position:
    ticker: str
    buy_date: pd.Timestamp
    buy_price: float
    shares: int
    invested: float
    projected_sell_date: pd.Timestamp
    reason: str


class BacktestEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.positions: List[Position] = []
        self.cash = settings.starting_capital
        self.trade_history: List[dict] = []
        self.portfolio_history: List[dict] = []

    def run(self, prices: Dict[str, pd.DataFrame], fundamentals: Optional[Dict[str, dict]] = None) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Run a forward‑simulation over the supplied price data.

        * prices – dict of ticker → DataFrame with OHLCV (must contain a ``Close`` column)
        * fundamentals – optional dict of ticker → dict with fundamental data used by ``score_stock``
        Returns a tuple ``(trades_df, portfolio_df)``.
        """
        fundamentals = fundamentals or {}
        # Pre‑calculate technical indicators once per ticker (performance optimisation)
        prices_with_indicators = {t: add_technical_indicators(df) for t, df in prices.items()}
        # All unique trading dates across all tickers, sorted chronologically
        trading_dates = sorted({d for df in prices.values() for d in df.index})

        for current_date in trading_dates:
            # Build a dict of available daily price slices for tickers that have data on this date
            daily_prices = {
                ticker: prices_with_indicators[ticker].loc[:current_date]
                for ticker, df in prices_with_indicators.items()
                if current_date in df.index
            }
            if not daily_prices:
                continue

            # 1️⃣ Process any existing sells first (protect against holding too long)
            self._process_sells(current_date, daily_prices, fundamentals)

            # 2️⃣ Rank possible buys for the day
            buy_targets = self._rank_buy_candidates(current_date, daily_prices, fundamentals)

            # 3️⃣ Execute buys respecting guard‑rails
            self._process_buys(current_date, buy_targets, daily_prices)

            # 4️⃣ Daily‑loss guard – if cash fell below the permitted loss threshold, skip portfolio recording for the rest of the day
            if self.cash < self.settings.starting_capital * (1 - self.settings.max_daily_loss_pct):
                # No further buying for this day; we still record the portfolio state that existed before the loss
                self._record_portfolio(current_date, daily_prices)
                continue

            # 5️⃣ Record portfolio snapshot for the day
            self._record_portfolio(current_date, daily_prices)

        trades_df = pd.DataFrame(self.trade_history)
        portfolio_df = pd.DataFrame(self.portfolio_history)
        return trades_df, portfolio_df

    # ---------------------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------------------
    def _rank_buy_candidates(self, current_date: pd.Timestamp, daily_prices: Dict[str, pd.DataFrame], fundamentals: Dict[str, dict]) -> List[dict]:
        """Return a list of buy candidates sorted by descending score.
        Each candidate dict contains ``ticker``, ``score``, ``price``, ``reason`` and ``projected_window``.
        """
        candidates = []
        held_tickers = {p.ticker for p in self.positions}
        for ticker, df in daily_prices.items():
            if ticker in held_tickers:
                continue
            score_data = score_stock(df, self.settings, fundamentals.get(ticker))
            if score_data["score"] < self.settings.buy_score_threshold:
                continue
            candidates.append({
                "ticker": ticker,
                "score": score_data["score"],
                "price": float(df["Close"].iloc[-1]),
                "reason": score_data["reason"],
                "projected_window": score_data["projected_window"],
            })
        return sorted(candidates, key=lambda c: c["score"], reverse=True)

    def _process_buys(self, current_date: pd.Timestamp, buy_targets: List[dict], daily_prices: Dict[str, pd.DataFrame]):
        """Open new positions according to the portfolio optimiser.
        * Respect ``max_daily_positions``.
        * Allocate equal cash to the selected top‑N candidates.
        * Enforce per‑ticker exposure cap, slippage and flat commission.
        """
        open_slots = self.settings.max_daily_positions - len(self.positions)
        if open_slots <= 0:
            return
        # Determine how many candidates we can actually act on (cannot exceed open slots)
        top_n = min(self.settings.portfolio_opt_top_n, open_slots, len(buy_targets))
        selected = buy_targets[:top_n]
        allocation_cash = self.cash / top_n if top_n > 0 else 0

        for target in selected:
            ticker = target["ticker"]
            price = target["price"]
            # Effective price includes slippage
            effective_price = price * (1 + self.settings.slippage_pct)
            # Maximum cash allowed for this ticker (exposure cap)
            max_allowed = self.settings.max_position_pct * self.cash
            # Determine max shares respecting allocation cash and exposure cap
            max_shares_by_cash = int(allocation_cash // effective_price)
            max_shares_by_cap = int((max_allowed - self.settings.commission_per_share) // effective_price)
            shares = min(max_shares_by_cash, max_shares_by_cap)
            if shares < 1:
                continue
            commission = shares * self.settings.commission_per_share
            invested = shares * effective_price + commission
            self.cash -= invested
            projected_sell = current_date + timedelta(days=self.settings.max_hold_days)
            self.positions.append(Position(ticker, current_date, price, shares, invested, projected_sell, target["reason"]))
            self.trade_history.append({
                "date": current_date,
                "ticker": ticker,
                "action": "buy",
                "price": price,
                "effective_price": effective_price,
                "shares": shares,
                "commission": commission,
                "invested": invested,
                "cash": self.cash,
                "reason": target["reason"],
                "projected_sell_date": projected_sell,
            })

    def _process_sells(self, current_date: pd.Timestamp, daily_prices: Dict[str, pd.DataFrame], fundamentals: Dict[str, dict]):
        """Sell positions that hit stop‑loss, take‑profit, max‑hold, or deteriorating score.
        Transaction cost and slippage are applied on the sell side.
        """
        remaining: List[Position] = []
        for position in self.positions:
            if position.ticker not in daily_prices:
                remaining.append(position)
                continue
            current_price = float(daily_prices[position.ticker]["Close"].iloc[-1])
            held_days = (current_date - position.buy_date).days
            stop_price = position.buy_price * (1 - self.settings.stop_loss_pct)
            take_price = position.buy_price * (1 + self.settings.take_profit_pct)
            reason = None
            if current_price <= stop_price:
                reason = "stop loss"
            elif current_price >= take_price:
                reason = "take profit"
            elif held_days >= self.settings.max_hold_days:
                reason = "maximum hold period"
            elif held_days >= self.settings.min_hold_days:
                score_data = score_stock(daily_prices[position.ticker], self.settings, fundamentals.get(position.ticker))
                if score_data["score"] < self.settings.buy_score_threshold * 0.6:
                    reason = "score deterioration"
            if reason:
                # Apply slippage and commission on sell side
                effective_price = current_price * (1 - self.settings.slippage_pct)
                commission = position.shares * self.settings.commission_per_share
                proceeds = effective_price * position.shares - commission
                profit = proceeds - position.invested
                self.cash += proceeds
                self.trade_history.append({
                    "date": current_date,
                    "ticker": position.ticker,
                    "action": "sell",
                    "price": current_price,
                    "effective_price": effective_price,
                    "shares": position.shares,
                    "commission": commission,
                    "proceeds": proceeds,
                    "profit": profit,
                    "cash": self.cash,
                    "reason": reason,
                    "hold_days": held_days,
                })
            else:
                remaining.append(position)
        self.positions = remaining

    def _record_portfolio(self, current_date: pd.Timestamp, daily_prices: Dict[str, pd.DataFrame]):
        market_value = 0.0
        tickers: List[str] = []
        for pos in self.positions:
            if pos.ticker in daily_prices:
                price = float(daily_prices[pos.ticker]["Close"].iloc[-1])
                market_value += price * pos.shares
                tickers.append(pos.ticker)
        total = self.cash + market_value
        self.portfolio_history.append({
            "date": current_date,
            "cash": self.cash,
            "market_value": market_value,
            "total_value": total,
            "positions": ",".join(tickers),
        })

    # ---------------------------------------------------------------------
    # Evaluation utilities
    # ---------------------------------------------------------------------
    def evaluate(self, trades: pd.DataFrame, portfolio: pd.DataFrame) -> dict:
        if portfolio.empty:
            return {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "win_rate": 0.0,
                "trade_count": 0,
                "max_drawdown": 0.0,
            }
        start = self.settings.starting_capital
        end = float(portfolio.iloc[-1]["total_value"])
        total_ret = (end / start - 1) * 100
        days = (portfolio.iloc[-1]["date"] - portfolio.iloc[0]["date"]).days or 1
        ann_ret = ((end / start) ** (365.0 / days) - 1) * 100
        sells = trades[trades["action"] == "sell"] if not trades.empty else trades
        wins = sells[sells["profit"] > 0] if not sells.empty else pd.DataFrame()
        win_rate = float(len(wins) / len(sells) * 100) if len(sells) > 0 else 0.0
        max_dd = self._compute_max_drawdown(portfolio["total_value"].tolist())
        avg_hold = float(sells["hold_days"].mean()) if not sells.empty else 0.0
        return {
            "start_value": round(start, 2),
            "end_value": round(end, 2),
            "total_return_pct": round(total_ret, 2),
            "annualized_return_pct": round(ann_ret, 2),
            "trade_count": int(len(sells)),
            "win_rate_pct": round(win_rate, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "average_hold_days": round(avg_hold, 1),
        }

    @staticmethod
    def _compute_max_drawdown(values: List[float]) -> float:
        peak = values[0]
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            draw = (peak - v) / peak if peak > 0 else 0.0
            if draw > max_dd:
                max_dd = draw
        return max_dd
