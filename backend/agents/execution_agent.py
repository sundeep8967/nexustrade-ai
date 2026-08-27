"""
Trade Execution & Portfolio Engine: Simulates order fills, maintains balances,
and provides full compatibility with the Alpaca Trading API format.
"""
from typing import Dict, List, Any
import time
import uuid

class ExecutionEngine:
    def __init__(self, initial_cash: float = 100000.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.order_history: List[Dict[str, Any]] = []
        self.portfolio_history: List[Dict[str, Any]] = []
        self._record_portfolio_snapshot(initial_cash)

    def get_portfolio(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        positions_val = 0.0
        positions_summary = []

        for symbol, pos in self.positions.items():
            if pos["qty"] == 0:
                continue
            cur_price = current_prices.get(symbol, pos["avg_entry"])
            market_val = pos["qty"] * cur_price
            unrealized_pl = (cur_price - pos["avg_entry"]) * pos["qty"]
            unrealized_plpc = (cur_price - pos["avg_entry"]) / pos["avg_entry"] if pos["avg_entry"] > 0 else 0.0
            positions_val += market_val

            positions_summary.append({
                "symbol": symbol,
                "qty": pos["qty"],
                "avg_entry_price": round(pos["avg_entry"], 2),
                "current_price": round(cur_price, 2),
                "market_value": round(market_val, 2),
                "unrealized_pl": round(unrealized_pl, 2),
                "unrealized_plpc": round(unrealized_plpc * 100, 2),
            })

        equity = self.cash + positions_val
        total_pl = equity - self.initial_cash
        total_plpc = (total_pl / self.initial_cash) * 100

        return {
            "account_id": "ALPACA-SIM-92847",
            "currency": "USD",
            "cash": round(self.cash, 2),
            "portfolio_value": round(equity, 2),
            "positions_value": round(positions_val, 2),
            "total_pl": round(total_pl, 2),
            "total_plpc": round(total_plpc, 2),
            "positions": positions_summary,
            "buying_power": round(self.cash * 2.0, 2), # 2x margin
        }

    def execute_order(self, symbol: str, side: str, qty: float, price: float, agent_id: str = "SWARM-CONSENSUS") -> Dict[str, Any]:
        order_id = str(uuid.uuid4())[:8].upper()
        now = int(time.time())
        order_val = qty * price

        if side == "BUY":
            if order_val > self.cash:
                return {"status": "REJECTED", "reason": "Insufficient buying power"}
            self.cash -= order_val
            pos = self.positions.get(symbol, {"qty": 0.0, "avg_entry": 0.0})
            new_qty = pos["qty"] + qty
            new_avg = ((pos["qty"] * pos["avg_entry"]) + order_val) / new_qty if new_qty > 0 else price
            self.positions[symbol] = {"qty": new_qty, "avg_entry": new_avg}
        elif side == "SELL":
            pos = self.positions.get(symbol, {"qty": 0.0, "avg_entry": 0.0})
            if pos["qty"] < qty:
                return {"status": "REJECTED", "reason": f"Insufficient position to sell (Holdings: {pos['qty']}, Requested: {qty})"}
            self.cash += order_val
            new_qty = pos["qty"] - qty
            self.positions[symbol] = {"qty": new_qty, "avg_entry": pos["avg_entry"] if new_qty > 0 else 0.0}

        order_record = {
            "id": f"ORD-{order_id}",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "filled_avg_price": round(price, 2),
            "status": "FILLED",
            "agent_attribution": agent_id,
            "timestamp": now,
            "total_cost": round(order_val, 2),
        }
        self.order_history.insert(0, order_record)
        return {"status": "FILLED", "order": order_record}

    def _record_portfolio_snapshot(self, equity: float):
        self.portfolio_history.append({
            "timestamp": int(time.time()),
            "equity": equity,
        })
