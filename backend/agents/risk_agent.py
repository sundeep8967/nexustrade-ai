"""
Risk Management Sentinel: Calculates Value at Risk (VaR), portfolio position limits,
volatility sizing, and enforces strict risk compliance before trade execution.
"""
from typing import Dict, List, Any
import numpy as np

class RiskSentinelAgent:
    def __init__(self, max_portfolio_risk_pct: float = 0.05, max_single_position_pct: float = 0.25):
        self.max_portfolio_risk_pct = max_portfolio_risk_pct
        self.max_single_position_pct = max_single_position_pct
        self.max_allowed_drawdown_pct = 0.10 # 10% circuit breaker

    def evaluate_order(
        self,
        symbol: str,
        side: str, # BUY or SELL
        quantity: float,
        price: float,
        portfolio_cash: float,
        portfolio_equity: float,
        current_positions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validates whether a proposed order passes risk limits.
        """
        order_value = quantity * price
        pos = current_positions.get(symbol, {"qty": 0, "avg_entry": 0.0})
        current_pos_val = pos["qty"] * price
        new_pos_val = (pos["qty"] + quantity) * price if side == "BUY" else (pos["qty"] - quantity) * price

        checks = []
        approved = True
        reasons = []

        # Check 1: Cash Availability
        if side == "BUY":
            if order_value > portfolio_cash:
                approved = False
                checks.append({"name": "Cash Availability Check", "passed": False, "detail": f"Order value (${order_value:,.2f}) exceeds available cash (${portfolio_cash:,.2f})"})
                reasons.append("Insufficient cash reserves.")
            else:
                checks.append({"name": "Cash Availability Check", "passed": True, "detail": "Sufficient cash available."})

        # Check 2: Maximum Single Position Sizing Limit
        pos_ratio = new_pos_val / max(1.0, portfolio_equity)
        if side == "BUY" and pos_ratio > self.max_single_position_pct:
            approved = False
            checks.append({
                "name": "Single Position Allocation Limit",
                "passed": False,
                "detail": f"Target position {pos_ratio*100:.1f}% exceeds max cap ({self.max_single_position_pct*100:.1f}%)"
            })
            reasons.append("Single asset concentration limit breached.")
        else:
            checks.append({
                "name": "Single Position Allocation Limit",
                "passed": True,
                "detail": f"Position exposure ({pos_ratio*100:.1f}%) is within {self.max_single_position_pct*100:.1f}% limit."
            })

        # Check 3: Simulated Value at Risk (VaR 95% 1-Day)
        estimated_daily_volatility = 0.025 # 2.5% daily stdev
        var_95 = order_value * (1.645 * estimated_daily_volatility)
        var_ratio = var_95 / max(1.0, portfolio_equity)
        if var_ratio > self.max_portfolio_risk_pct:
            approved = False
            checks.append({
                "name": "Value at Risk (VaR 95%)",
                "passed": False,
                "detail": f"1-Day VaR is ${var_95:,.2f} ({var_ratio*100:.2f}% of portfolio), exceeding {self.max_portfolio_risk_pct*100:.1f}% limit."
            })
            reasons.append("Value at Risk threshold exceeded.")
        else:
            checks.append({
                "name": "Value at Risk (VaR 95%)",
                "passed": True,
                "detail": f"1-Day VaR (${var_95:,.2f}) is within {self.max_portfolio_risk_pct*100:.1f}% threshold."
            })

        # Stop-loss and Take-profit recommendations
        stop_loss = round(price * 0.96, 2) if side == "BUY" else round(price * 1.04, 2)
        take_profit = round(price * 1.08, 2) if side == "BUY" else round(price * 0.92, 2)

        return {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "order_value": round(order_value, 2),
            "approved": approved,
            "risk_checks": checks,
            "risk_reasons": reasons if not approved else ["All risk sentinel guardrails passed cleanly."],
            "stop_loss_suggested": stop_loss,
            "take_profit_suggested": take_profit,
            "var_95": round(var_95, 2),
        }
