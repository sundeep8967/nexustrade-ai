"""
FastAPI Server & Multi-Agent Swarm Orchestrator for NexusTrade AI.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import asyncio
import json
import os

from agents.market_data_agent import MarketDataAgent
from agents.sentiment_agent import SentimentAgent
from agents.risk_agent import RiskSentinelAgent
from agents.execution_agent import ExecutionEngine
from agents.backtester import StrategyBacktester

app = FastAPI(title="NexusTrade AI - Autonomous Trading Swarm API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core singletons
market_agent = MarketDataAgent()
sentiment_agent = SentimentAgent()
risk_agent = RiskSentinelAgent()
execution_engine = ExecutionEngine(initial_cash=100000.0)
backtester = StrategyBacktester()

# Autonomous agent state
autonomous_trading_enabled = False

class OrderRequest(BaseModel):
    symbol: str
    side: str # BUY or SELL
    quantity: float
    agent_override: Optional[str] = None

class BacktestRequest(BaseModel):
    symbol: str = "NVDA"
    strategy_type: str = "MULTI_AGENT_SWARM"
    days: int = 180
    capital: float = 100000.0

@app.get("/api/market/{symbol}")
async def get_market_analysis(symbol: str):
    symbol = symbol.upper()
    tech_data = market_agent.analyze_symbol(symbol)
    sent_data = sentiment_agent.analyze_sentiment(symbol)
    
    # Calculate Swarm Consensus Score
    tech_score = tech_data.get("technical_score", 0.0)
    sent_score = sent_data.get("overall_sentiment_score", 0.0)
    
    # Weighted ensemble: 55% Technical, 45% Sentiment
    consensus_score = round((tech_score * 0.55) + (sent_score * 0.45), 2)
    
    if consensus_score > 0.30:
        action = "BUY"
        confidence = min(95.0, round(50 + (consensus_score * 45), 1))
    elif consensus_score < -0.30:
        action = "SELL"
        confidence = min(95.0, round(50 + (abs(consensus_score) * 45), 1))
    else:
        action = "HOLD"
        confidence = round(100.0 - (abs(consensus_score) * 80), 1)

    consensus_summary = {
        "action": action,
        "confidence_pct": confidence,
        "composite_score": consensus_score,
        "technical_weight": 0.55,
        "sentiment_weight": 0.45,
        "synthesis": f"Swarm recommends {action} with {confidence}% conviction based on technical score ({tech_score:+.2f}) and sentiment velocity ({sent_score:+.2f})."
    }

    return {
        "symbol": symbol,
        "technical": tech_data,
        "sentiment": sent_data,
        "consensus": consensus_summary,
    }

@app.get("/api/portfolio")
async def get_portfolio_status():
    prices = {s: market_agent.analyze_symbol(s)["current_price"] for s in ["NVDA", "AAPL", "TSLA", "SPY", "BTC-USD"]}
    return execution_engine.get_portfolio(prices)

@app.get("/api/orders")
async def get_orders():
    return {"orders": execution_engine.order_history}

@app.post("/api/order")
async def place_order(req: OrderRequest):
    symbol = req.symbol.upper()
    analysis = market_agent.analyze_symbol(symbol)
    price = analysis.get("current_price", 100.0)
    
    prices = {s: market_agent.analyze_symbol(s)["current_price"] for s in ["NVDA", "AAPL", "TSLA", "SPY", "BTC-USD"]}
    portfolio = execution_engine.get_portfolio(prices)
    
    # 1. Run through Risk Sentinel
    risk_evaluation = risk_agent.evaluate_order(
        symbol=symbol,
        side=req.side.upper(),
        quantity=req.quantity,
        price=price,
        portfolio_cash=portfolio["cash"],
        portfolio_equity=portfolio["portfolio_value"],
        current_positions={p["symbol"]: {"qty": p["qty"], "avg_entry": p["avg_entry_price"]} for p in portfolio["positions"]}
    )

    if not risk_evaluation["approved"]:
        return {
            "status": "REJECTED_BY_RISK_SENTINEL",
            "risk_evaluation": risk_evaluation,
        }

    # 2. Execute via Execution Engine
    exec_result = execution_engine.execute_order(
        symbol=symbol,
        side=req.side.upper(),
        qty=req.quantity,
        price=price,
        agent_id=req.agent_override or "MANUAL_DISPATCH"
    )

    return {
        "status": "APPROVED_AND_FILLED",
        "risk_evaluation": risk_evaluation,
        "execution": exec_result,
    }

@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    return backtester.run_backtest(
        symbol=req.symbol.upper(),
        strategy_type=req.strategy_type,
        initial_capital=req.capital,
        days=req.days
    )

@app.post("/api/autonomous/toggle")
async def toggle_autonomous_mode():
    global autonomous_trading_enabled
    autonomous_trading_enabled = not autonomous_trading_enabled
    return {"autonomous_mode": autonomous_trading_enabled}

@app.get("/api/autonomous/status")
async def get_autonomous_status():
    return {"autonomous_mode": autonomous_trading_enabled}

# Mount static frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
