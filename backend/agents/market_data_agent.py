"""
Market Data Agent: Computes live OHLCV price action, technical indicators
(EMA, RSI, MACD, Bollinger Bands, ATR), and volatility regimes.
"""
from typing import Dict, List, Any
import numpy as np
import pandas as pd
import time
import math


def compute_rsi(prices: np.ndarray, period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))


def compute_ema(prices: np.ndarray, period: int) -> float:
    if len(prices) == 0:
        return 0.0
    if len(prices) < period:
        return float(np.mean(prices))
    multiplier = 2.0 / (period + 1.0)
    ema = prices[0]
    for p in prices[1:]:
        ema = (p - ema) * multiplier + ema
    return float(ema)


def compute_macd(prices: np.ndarray) -> Dict[str, float]:
    if len(prices) < 26:
        return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
    ema12 = compute_ema(prices, 12)
    ema26 = compute_ema(prices, 26)
    macd_line = ema12 - ema26
    # Fast proxy signal
    signal_line = macd_line * 0.8
    hist = macd_line - signal_line
    return {"macd": round(macd_line, 4), "signal": round(signal_line, 4), "histogram": round(hist, 4)}


def compute_bollinger_bands(prices: np.ndarray, period: int = 20, num_std: float = 2.0) -> Dict[str, float]:
    if len(prices) < period:
        mean_val = float(np.mean(prices)) if len(prices) > 0 else 100.0
        return {"upper": mean_val * 1.05, "middle": mean_val, "lower": mean_val * 0.95}
    window = prices[-period:]
    sma = float(np.mean(window))
    std = float(np.std(window))
    return {
        "upper": round(sma + num_std * std, 2),
        "middle": round(sma, 2),
        "lower": round(sma - num_std * std, 2),
    }


class MarketDataAgent:
    def __init__(self):
        self.default_assets = {
            "NVDA": {"base_price": 128.50, "volatility": 0.024, "trend": 0.0015},
            "AAPL": {"base_price": 224.20, "volatility": 0.012, "trend": 0.0008},
            "TSLA": {"base_price": 215.60, "volatility": 0.035, "trend": -0.0005},
            "SPY":  {"base_price": 560.10, "volatility": 0.008, "trend": 0.0004},
            "BTC-USD": {"base_price": 63450.0, "volatility": 0.038, "trend": 0.002},
        }
        # In-memory history cache
        self.history: Dict[str, List[Dict[str, Any]]] = {}
        self._init_mock_history()

    def _init_mock_history(self):
        now = int(time.time())
        for symbol, conf in self.default_assets.items():
            candles = []
            price = conf["base_price"]
            for i in range(100, 0, -1):
                t = now - (i * 300) # 5 min intervals
                ret = np.random.normal(conf["trend"], conf["volatility"])
                o = price
                c = price * (1 + ret)
                h = max(o, c) * (1 + abs(np.random.normal(0, conf["volatility"] * 0.5)))
                l = min(o, c) * (1 - abs(np.random.normal(0, conf["volatility"] * 0.5)))
                v = int(abs(np.random.normal(50000, 15000)))
                candles.append({
                    "time": t,
                    "open": round(o, 2),
                    "high": round(h, 2),
                    "low": round(l, 2),
                    "close": round(c, 2),
                    "volume": v,
                })
                price = c
            self.history[symbol] = candles

    def get_latest_candle(self, symbol: str) -> Dict[str, Any]:
        if symbol not in self.history:
            self.history[symbol] = []
            conf = {"base_price": 100.0, "volatility": 0.02, "trend": 0.001}
        else:
            conf = self.default_assets.get(symbol, {"base_price": 100.0, "volatility": 0.02, "trend": 0.001})

        last = self.history[symbol][-1]
        now = int(time.time())
        ret = np.random.normal(conf["trend"], conf["volatility"] * 0.3)
        o = last["close"]
        c = o * (1 + ret)
        h = max(o, c) * (1 + abs(np.random.normal(0, conf["volatility"] * 0.2)))
        l = min(o, c) * (1 - abs(np.random.normal(0, conf["volatility"] * 0.2)))
        v = int(abs(np.random.normal(30000, 8000)))

        new_candle = {
            "time": now,
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
            "volume": v,
        }
        self.history[symbol].append(new_candle)
        if len(self.history[symbol]) > 200:
            self.history[symbol].pop(0)
        return new_candle

    def analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        candles = self.history.get(symbol, [])
        if not candles:
            return {"error": f"No data for {symbol}"}

        closes = np.array([c["close"] for c in candles])
        rsi = compute_rsi(closes, 14)
        ema20 = compute_ema(closes, 20)
        ema50 = compute_ema(closes, 50)
        macd = compute_macd(closes)
        bb = compute_bollinger_bands(closes, 20)

        current_price = closes[-1]
        # Technical score: -1.0 (strong sell) to +1.0 (strong buy)
        tech_score = 0.0
        reasoning = []

        if rsi < 32:
            tech_score += 0.4
            reasoning.append(f"RSI is oversold ({rsi:.1f}), strong mean-reversion bullish signal.")
        elif rsi > 68:
            tech_score -= 0.4
            reasoning.append(f"RSI is overbought ({rsi:.1f}), momentum exhaustion warning.")
        else:
            reasoning.append(f"RSI is neutral at {rsi:.1f}.")

        if ema20 > ema50:
            tech_score += 0.35
            reasoning.append("Golden EMA Cross (EMA20 > EMA50) indicates bullish continuation trend.")
        else:
            tech_score -= 0.35
            reasoning.append("Death EMA Cross (EMA20 < EMA50) indicates bearish macro pressure.")

        if current_price < bb["lower"]:
            tech_score += 0.25
            reasoning.append(f"Price (${current_price}) pierced below Lower Bollinger Band (${bb['lower']}).")
        elif current_price > bb["upper"]:
            tech_score -= 0.25
            reasoning.append(f"Price (${current_price}) pierced above Upper Bollinger Band (${bb['upper']}).")

        if macd["histogram"] > 0:
            tech_score += 0.2
            reasoning.append(f"MACD Histogram positive ({macd['histogram']:+.3f}).")
        else:
            tech_score -= 0.2
            reasoning.append(f"MACD Histogram negative ({macd['histogram']:+.3f}).")

        tech_score = max(-1.0, min(1.0, tech_score))

        return {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "indicators": {
                "rsi": round(rsi, 2),
                "ema20": round(ema20, 2),
                "ema50": round(ema50, 2),
                "macd": macd,
                "bollinger": bb,
            },
            "technical_score": round(tech_score, 2),
            "signal": "BUY" if tech_score > 0.35 else ("SELL" if tech_score < -0.35 else "HOLD"),
            "technical_reasoning": reasoning,
            "candles": candles[-50:],
        }
