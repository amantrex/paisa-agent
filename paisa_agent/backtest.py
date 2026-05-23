from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List, Optional
import pandas as pd
from .config import Settings
from .strategy import score_stock


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
        fundamentals = fundamentals or {}
        trading_dates = sorted({date for df in prices.values() for date in df.index})
        for current_date in trading_dates:
            daily_prices = {ticker: df.loc[:current_date] for ticker, df in prices.items() if current_date in df.index}
            if not daily_prices:
                continue
            self._process_sells(current_date, daily_prices, fundamentals)
            buy_targets = self._rank_buy_candidates(current_date, daily_prices, fundamentals)
            self._process_buys(current_date, buy_targets, daily_prices)
            self._record_portfolio(current_date, daily_prices)
        history_df = pd.DataFrame(self.trade_history)
        portfolio_df = pd.DataFrame(self.portfolio_history)
        return history_df, portfolio_df

    def _rank_buy_candidates(self, current_date: pd.Timestamp, daily_prices: Dict[str, pd.DataFrame], fundamentals: Dict[str, dict]) -> List[dict]:
        candidates = []
        held_tickers = {position.ticker for position in self.positions}
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
        return sorted(candidates, key=lambda item: item["score"], reverse=True)

    def _process_buys(self, current_date: pd.Timestamp, buy_targets: List[dict], daily_prices: Dict[str, pd.DataFrame]):
        open_slots = self.settings.max_daily_positions - len(self.positions)
        if open_slots <= 0:
            return
        for target in buy_targets[:open_slots]:
            ticker = target["ticker"]
            price = target["price"]
            if self.cash < self.settings.daily_budget or price <= 0:
                continue
            shares = int(self.settings.daily_budget // price)
            if shares < 1:
                continue
            invested = shares * price
            self.cash -= invested
            projected_sell_date = current_date + timedelta(days=self.settings.max_hold_days)
            self.positions.append(Position(ticker, current_date, price, shares, invested, projected_sell_date, target["reason"]))
            self.trade_history.append({
                "date": current_date,
                "ticker": ticker,
                "action": "buy",
                "price": price,
                "shares": shares,
                "invested": invested,
                "cash": self.cash,
                "reason": target["reason"],
                "projected_sell_date": projected_sell_date,
            })

    def _process_sells(self, current_date: pd.Timestamp, daily_prices: Dict[str, pd.DataFrame], fundamentals: Dict[str, dict]):
        remaining_positions = []
        for position in self.positions:
            if position.ticker not in daily_prices:
                remaining_positions.append(position)
                continue
            current_price = float(daily_prices[position.ticker]["Close"].iloc[-1])
            held_days = (current_date - position.buy_date).days
            stop_loss_price = position.buy_price * (1 - self.settings.stop_loss_pct)
            take_profit_price = position.buy_price * (1 + self.settings.take_profit_pct)
            sell_reason = None
            if current_price <= stop_loss_price:
                sell_reason = "stop loss"
            elif current_price >= take_profit_price:
                sell_reason = "take profit"
            elif held_days >= self.settings.max_hold_days:
                sell_reason = "maximum hold period"
            elif held_days >= self.settings.min_hold_days:
                score_data = score_stock(daily_prices[position.ticker], self.settings, fundamentals.get(position.ticker))
                if score_data["score"] < self.settings.buy_score_threshold * 0.6:
                    sell_reason = "score deterioration"
            if sell_reason:
                proceeds = current_price * position.shares
                profit = proceeds - position.invested
                self.cash += proceeds
                self.trade_history.append({
                    "date": current_date,
                    "ticker": position.ticker,
                    "action": "sell",
                    "price": current_price,
                    "shares": position.shares,
                    "proceeds": proceeds,
                    "profit": profit,
                    "cash": self.cash,
                    "reason": sell_reason,
                    "hold_days": held_days,
                })
            else:
                remaining_positions.append(position)
        self.positions = remaining_positions

    def _record_portfolio(self, current_date: pd.Timestamp, daily_prices: Dict[str, pd.DataFrame]):
        market_value = 0.0
        positions = []
        for position in self.positions:
            if position.ticker in daily_prices:
                price = float(daily_prices[position.ticker]["Close"].iloc[-1])
                market_value += price * position.shares
                positions.append(position.ticker)
        total_value = self.cash + market_value
        self.portfolio_history.append({
            "date": current_date,
            "cash": self.cash,
            "market_value": market_value,
            "total_value": total_value,
            "positions": ",".join(positions),
        })

    def evaluate(self, trades: pd.DataFrame, portfolio: pd.DataFrame) -> dict:
        if portfolio.empty:
            return {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "win_rate": 0.0,
                "trade_count": 0,
                "max_drawdown": 0.0,
            }
        start_value = self.settings.starting_capital
        end_value = float(portfolio.iloc[-1]["total_value"])
        total_return = (end_value / start_value - 1) * 100
        days = (portfolio.iloc[-1]["date"] - portfolio.iloc[0]["date"]).days or 1
        annualized_return = ((end_value / start_value) ** (365.0 / days) - 1) * 100
        sells = trades[trades["action"] == "sell"] if not trades.empty else trades
        wins = sells[sells["profit"] > 0] if not sells.empty else pd.DataFrame()
        win_rate = float(len(wins) / len(sells) * 100) if len(sells) > 0 else 0.0
        max_drawdown = self._compute_max_drawdown(portfolio["total_value"].tolist())
        avg_hold_days = float(sells["hold_days"].mean()) if not sells.empty else 0.0
        return {
            "start_value": round(start_value, 2),
            "end_value": round(end_value, 2),
            "total_return_pct": round(total_return, 2),
            "annualized_return_pct": round(annualized_return, 2),
            "trade_count": int(len(sells)),
            "win_rate_pct": round(win_rate, 2),
            "max_drawdown_pct": round(max_drawdown * 100, 2),
            "average_hold_days": round(avg_hold_days, 1),
        }

    @staticmethod
    def _compute_max_drawdown(values: List[float]) -> float:
        peak = values[0]
        drawdowns = [0.0]
        for value in values:
            peak = max(peak, value)
            drawdown = (peak - value) / peak if peak > 0 else 0.0
            drawdowns.append(drawdown)
        return max(drawdowns)
