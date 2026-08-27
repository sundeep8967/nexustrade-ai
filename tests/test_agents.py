import pytest
import numpy as np
from agents.market_data_agent import MarketDataAgent, compute_rsi, compute_ema, compute_macd
from agents.sentiment_agent import SentimentAgent
from agents.risk_agent import RiskSentinelAgent
from agents.execution_agent import ExecutionEngine
from agents.backtester import StrategyBacktester

def test_technical_indicator_calculations():
    prices = np.array([100.0, 102.0, 101.0, 104.0, 106.0, 105.0, 108.0, 110.0, 109.0, 112.0, 115.0, 114.0, 116.0, 118.0, 120.0])
    rsi = compute_rsi(prices, 14)
    assert 0 <= rsi <= 100
    assert rsi > 50 # upward trending prices should yield RSI > 50

    ema20 = compute_ema(prices, 10)
    assert ema20 > 0

    macd = compute_macd(prices)
    assert "macd" in macd
    assert "signal" in macd

def test_risk_sentinel_rejections():
    risk = RiskSentinelAgent(max_portfolio_risk_pct=0.05, max_single_position_pct=0.25)
    
    # Over-budget cash test
    eval_cash = risk.evaluate_order(
        symbol="NVDA",
        side="BUY",
        quantity=1000,
        price=200.0, # $200,000 order
        portfolio_cash=50000.0,
        portfolio_equity=100000.0,
        current_positions={}
    )
    assert not eval_cash["approved"]
    assert "Insufficient cash reserves." in eval_cash["risk_reasons"]

    # Position concentration limit test
    eval_pos = risk.evaluate_order(
        symbol="AAPL",
        side="BUY",
        quantity=200,
        price=200.0, # $40,000 order (40% of $100,000 equity)
        portfolio_cash=80000.0,
        portfolio_equity=100000.0,
        current_positions={}
    )
    assert not eval_pos["approved"]
    assert "Single asset concentration limit breached." in eval_pos["risk_reasons"]

def test_execution_engine_order_fill():
    engine = ExecutionEngine(initial_cash=100000.0)
    res = engine.execute_order(symbol="NVDA", side="BUY", qty=10, price=120.0)
    assert res["status"] == "FILLED"
    assert engine.cash == 100000.0 - 1200.0
    assert engine.positions["NVDA"]["qty"] == 10

    # Sell half
    res_sell = engine.execute_order(symbol="NVDA", side="SELL", qty=5, price=130.0)
    assert res_sell["status"] == "FILLED"
    assert engine.positions["NVDA"]["qty"] == 5
    assert engine.cash == (100000.0 - 1200.0) + 650.0

def test_backtester_metrics():
    bt = StrategyBacktester()
    res = bt.run_backtest(symbol="NVDA", strategy_type="MULTI_AGENT_SWARM", initial_capital=100000.0, days=90)
    assert "cagr_pct" in res
    assert "sharpe_ratio" in res
    assert "max_drawdown_pct" in res
    assert len(res["equity_curve"]) == 91
