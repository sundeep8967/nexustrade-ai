// State
let currentSymbol = "NVDA";
let currentPrice = 128.50;
let autonomousMode = false;
let chartCandles = [];
let currentConsensus = null;

// DOM Elements
const symbolPills = document.querySelectorAll("#symbolPills .pill");
const tickerItems = document.querySelectorAll(".ticker-item");
const tabBtns = document.querySelectorAll(".tab-btn");
const tabContents = document.querySelectorAll(".tab-content");

const activePriceEl = document.getElementById("activePrice");
const activeSignalEl = document.getElementById("activeSignal");
const orderSymbolEl = document.getElementById("orderSymbol");
const orderQtyEl = document.getElementById("orderQty");
const orderSideEl = document.getElementById("orderSide");
const orderEstCostEl = document.getElementById("orderEstCost");
const submitOrderBtn = document.getElementById("submitOrderBtn");
const orderResultBox = document.getElementById("orderResultBox");

const toggleAutonomousBtn = document.getElementById("toggleAutonomousBtn");
const autonomousLabel = document.getElementById("autonomousLabel");
const triggerSwarmScan = document.getElementById("triggerSwarmScan");
const executeConsensusOrder = document.getElementById("executeConsensusOrder");

const runBacktestBtn = document.getElementById("runBacktestBtn");
const backtestResults = document.getElementById("backtestResults");

// Canvas
const priceCanvas = document.getElementById("priceChart");
const priceCtx = priceCanvas.getContext("2d");
const backtestCanvas = document.getElementById("backtestChart");
const backtestCtx = backtestCanvas ? backtestCanvas.getContext("2d") : null;

// Initialize
window.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initSymbolSelectors();
    initOrderCalculations();
    fetchMarketData(currentSymbol);
    fetchPortfolio();
    fetchOrders();

    // Periodic live candle & consensus refresh
    setInterval(() => {
        fetchMarketData(currentSymbol, true);
    }, 4000);

    setInterval(fetchPortfolio, 5000);
});

// Tabs
function initTabs() {
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));
            btn.classList.add("active");
            const target = btn.getAttribute("data-tab");
            document.getElementById(target).classList.add("active");
        });
    });
}

// Symbol selection
function initSymbolSelectors() {
    symbolPills.forEach(pill => {
        pill.addEventListener("click", () => {
            symbolPills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            currentSymbol = pill.getAttribute("data-symbol");
            orderSymbolEl.value = currentSymbol;
            fetchMarketData(currentSymbol);
        });
    });

    tickerItems.forEach(item => {
        item.addEventListener("click", () => {
            const sym = item.getAttribute("data-symbol");
            const matchingPill = document.querySelector(`#symbolPills .pill[data-symbol="${sym}"]`);
            if (matchingPill) matchingPill.click();
        });
    });
}

function initOrderCalculations() {
    const updateEstCost = () => {
        const qty = parseFloat(orderQtyEl.value) || 0;
        const total = qty * currentPrice;
        orderEstCostEl.textContent = `$${total.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    };
    orderQtyEl.addEventListener("input", updateEstCost);
}

// Fetch Market & Swarm Analysis
async function fetchMarketData(symbol, silent = false) {
    try {
        const res = await fetch(`/api/market/${symbol}`);
        const data = await res.json();

        currentPrice = data.technical.current_price;
        chartCandles = data.technical.candles;
        currentConsensus = data.consensus;

        // UI Updates
        activePriceEl.textContent = `$${currentPrice.toFixed(2)}`;
        document.getElementById("orderSymbol").value = symbol;
        const qty = parseFloat(orderQtyEl.value) || 1;
        orderEstCostEl.textContent = `$${(qty * currentPrice).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

        // Signal Badge
        const signal = data.consensus.action;
        activeSignalEl.textContent = `${signal} (${data.consensus.confidence_pct}%)`;
        activeSignalEl.className = `badge badge-${signal === 'BUY' ? 'bullish' : (signal === 'SELL' ? 'bearish' : 'neutral')}`;

        // Indicators
        document.getElementById("indRsi").textContent = data.technical.indicators.rsi;
        document.getElementById("indEma20").textContent = `$${data.technical.indicators.ema20.toFixed(2)}`;
        document.getElementById("indEma50").textContent = `$${data.technical.indicators.ema50.toFixed(2)}`;
        document.getElementById("indMacd").textContent = (data.technical.indicators.macd.histogram >= 0 ? '+' : '') + data.technical.indicators.macd.histogram;
        document.getElementById("indBBU").textContent = `$${data.technical.indicators.bollinger.upper.toFixed(2)}`;
        document.getElementById("indBBL").textContent = `$${data.technical.indicators.bollinger.lower.toFixed(2)}`;

        // Swarm Deliberations
        document.getElementById("agentTechScore").textContent = (data.technical.technical_score >= 0 ? '+' : '') + data.technical.technical_score;
        const techList = document.getElementById("techReasoningList");
        techList.innerHTML = data.technical.technical_reasoning.map(r => `<li>${r}</li>`).join("");

        document.getElementById("agentSentScore").textContent = (data.sentiment.overall_sentiment_score >= 0 ? '+' : '') + data.sentiment.overall_sentiment_score;
        document.getElementById("sentReasoning").textContent = data.sentiment.reasoning;

        const newsContainer = document.getElementById("newsHeadlines");
        newsContainer.innerHTML = data.sentiment.news_catalysts.slice(0, 2).map(n => `
            <div class="headline-item">
                <strong>${n.source}:</strong> ${n.headline} (${n.score >= 0 ? '+' : ''}${n.score})
            </div>
        `).join("");

        // Risk previews
        document.getElementById("stopLossDisplay").textContent = `$${(currentPrice * 0.96).toFixed(2)}`;
        document.getElementById("takeProfitDisplay").textContent = `$${(currentPrice * 1.08).toFixed(2)}`;
        document.getElementById("varDisplay").textContent = `$${((qty * currentPrice) * 0.041).toFixed(2)}`;

        // Consensus Banner
        document.getElementById("consensusHeadline").textContent = `Swarm Consensus: ${data.consensus.action} (${data.consensus.confidence_pct}% Conviction)`;
        document.getElementById("consensusSub").textContent = data.consensus.synthesis;

        // Render Canvas Chart
        renderCandleChart(chartCandles);

    } catch (e) {
        console.error("Error fetching market analysis:", e);
    }
}

// Custom High-Res Canvas Candlestick Renderer
function renderCandleChart(candles) {
    if (!candles || candles.length === 0) return;
    const width = priceCanvas.width = priceCanvas.parentElement.clientWidth;
    const height = priceCanvas.height = priceCanvas.parentElement.clientHeight;

    priceCtx.clearRect(0, 0, width, height);

    const padding = 30;
    const chartHeight = height - padding * 2;
    const chartWidth = width - padding * 2;

    let minPrice = Infinity;
    let maxPrice = -Infinity;

    candles.forEach(c => {
        if (c.low < minPrice) minPrice = c.low;
        if (c.high > maxPrice) maxPrice = c.high;
    });

    const priceRange = (maxPrice - minPrice) || 1.0;
    const candleWidth = Math.max(3, (chartWidth / candles.length) - 3);

    // Draw grid lines
    priceCtx.strokeStyle = "rgba(255, 255, 255, 0.04)";
    priceCtx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding + (chartHeight / 4) * i;
        priceCtx.beginPath();
        priceCtx.moveTo(padding, y);
        priceCtx.lineTo(width - padding, y);
        priceCtx.stroke();

        const pVal = maxPrice - (priceRange / 4) * i;
        priceCtx.fillStyle = "#64748b";
        priceCtx.font = "10px JetBrains Mono";
        priceCtx.fillText(`$${pVal.toFixed(2)}`, width - padding + 4, y + 3);
    }

    // Draw candles
    candles.forEach((c, idx) => {
        const x = padding + (idx * (chartWidth / candles.length)) + (candleWidth / 2);
        const yOpen = padding + chartHeight * (1 - (c.open - minPrice) / priceRange);
        const yClose = padding + chartHeight * (1 - (c.close - minPrice) / priceRange);
        const yHigh = padding + chartHeight * (1 - (c.high - minPrice) / priceRange);
        const yLow = padding + chartHeight * (1 - (c.low - minPrice) / priceRange);

        const isUp = c.close >= c.open;
        priceCtx.strokeStyle = isUp ? "#10b981" : "#f43f5e";
        priceCtx.fillStyle = isUp ? "#10b981" : "#f43f5e";

        // Wick
        priceCtx.beginPath();
        priceCtx.moveTo(x, yHigh);
        priceCtx.lineTo(x, yLow);
        priceCtx.stroke();

        // Body
        const bodyY = Math.min(yOpen, yClose);
        const bodyHeight = Math.max(2, Math.abs(yClose - yOpen));
        priceCtx.fillRect(x - candleWidth / 2, bodyY, candleWidth, bodyHeight);
    });
}

// Portfolio & Orders
async function fetchPortfolio() {
    try {
        const res = await fetch("/api/portfolio");
        const port = await res.json();

        document.getElementById("headerEquity").textContent = `$${port.portfolio_value.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
        document.getElementById("portTotalEquity").textContent = `$${port.portfolio_value.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
        document.getElementById("portCash").textContent = `$${port.cash.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
        document.getElementById("portBuyingPower").textContent = `$${port.buying_power.toLocaleString('en-US', {minimumFractionDigits: 2})}`;

        const plEl = document.getElementById("portTotalPL");
        const plSign = port.total_pl >= 0 ? '+' : '';
        plEl.textContent = `${plSign}$${port.total_pl.toFixed(2)} (${plSign}${port.total_plpc.toFixed(2)}%)`;
        plEl.className = `stat-value ${port.total_pl >= 0 ? 'text-success' : 'text-danger'}`;

        const posBody = document.querySelector("#positionsTable tbody");
        if (port.positions.length === 0) {
            posBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: #64748b;">No active positions</td></tr>`;
        } else {
            posBody.innerHTML = port.positions.map(p => `
                <tr>
                    <td><strong>${p.symbol}</strong></td>
                    <td>${p.qty}</td>
                    <td>$${p.avg_entry_price.toFixed(2)}</td>
                    <td>$${p.market_value.toFixed(2)}</td>
                    <td class="${p.unrealized_pl >= 0 ? 'text-success' : 'text-danger'}">${p.unrealized_pl >= 0 ? '+' : ''}$${p.unrealized_pl.toFixed(2)} (${p.unrealized_plpc >= 0 ? '+' : ''}${p.unrealized_plpc.toFixed(2)}%)</td>
                </tr>
            `).join("");
        }
    } catch (e) {
        console.error("Error fetching portfolio:", e);
    }
}

async function fetchOrders() {
    try {
        const res = await fetch("/api/orders");
        const data = await res.json();
        const tbody = document.querySelector("#ordersTable tbody");

        if (!data.orders || data.orders.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: #64748b;">No order executions yet</td></tr>`;
            return;
        }

        tbody.innerHTML = data.orders.slice(0, 10).map(o => `
            <tr>
                <td><small>${o.id}</small></td>
                <td><strong>${o.symbol}</strong></td>
                <td><span class="badge ${o.side === 'BUY' ? 'badge-bullish' : 'badge-bearish'}">${o.side}</span></td>
                <td>${o.qty}</td>
                <td>$${o.filled_avg_price.toFixed(2)}</td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("Error fetching orders:", e);
    }
}

// Order Submission
submitOrderBtn.addEventListener("click", async () => {
    const symbol = document.getElementById("orderSymbol").value;
    const side = document.getElementById("orderSide").value;
    const quantity = parseFloat(orderQtyEl.value) || 1;

    try {
        submitOrderBtn.disabled = true;
        submitOrderBtn.textContent = "Validating Sentinel & Sizing...";

        const res = await fetch("/api/order", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol, side, quantity, agent_override: "MANUAL_DISPATCH" })
        });
        const result = await res.json();

        orderResultBox.style.display = "block";
        if (result.status === "APPROVED_AND_FILLED") {
            orderResultBox.className = "risk-audit-log text-success";
            orderResultBox.innerHTML = `
                <strong>✅ Order Approved & Filled</strong><br>
                Executed ${result.execution.order.side} ${result.execution.order.qty} ${symbol} @ $${result.execution.order.filled_avg_price.toFixed(2)}.<br>
                <small>Risk Check: 1-Day VaR $${result.risk_evaluation.var_95} (Within limits).</small>
            `;
            fetchPortfolio();
            fetchOrders();
        } else {
            orderResultBox.className = "risk-audit-log text-danger";
            orderResultBox.innerHTML = `
                <strong>❌ Blocked by Risk Sentinel</strong><br>
                ${result.risk_evaluation.risk_reasons.join("<br>")}
            `;
        }
    } catch (e) {
        console.error("Order dispatch error:", e);
    } finally {
        submitOrderBtn.disabled = false;
        submitOrderBtn.textContent = "Submit to Execution Engine";
    }
});

// Consensus Order Placement
executeConsensusOrder.addEventListener("click", () => {
    if (!currentConsensus) return;
    const action = currentConsensus.action;
    if (action === "HOLD") {
        alert("Swarm recommendation is currently HOLD. No directional order queued.");
        return;
    }
    orderSideEl.value = action;
    orderQtyEl.value = 15;
    document.querySelector('.tab-btn[data-tab="tradeTab"]').click();
    submitOrderBtn.click();
});

// Autonomous toggle
toggleAutonomousBtn.addEventListener("click", async () => {
    try {
        const res = await fetch("/api/autonomous/toggle", { method: "POST" });
        const data = await res.json();
        autonomousMode = data.autonomous_mode;
        
        if (autonomousMode) {
            toggleAutonomousBtn.classList.add("active");
            autonomousLabel.textContent = "Autonomous Swarm: ACTIVE";
        } else {
            toggleAutonomousBtn.classList.remove("active");
            autonomousLabel.textContent = "Autonomous Swarm: OFF";
        }
    } catch (e) {
        console.error("Error toggling autonomous mode:", e);
    }
});

// Swarm Manual Trigger
triggerSwarmScan.addEventListener("click", () => {
    triggerSwarmScan.textContent = "Scanning...";
    fetchMarketData(currentSymbol).then(() => {
        triggerSwarmScan.textContent = "⚡ Run Swarm Scan";
    });
});

// Backtest Execution
runBacktestBtn.addEventListener("click", async () => {
    const strategy_type = document.getElementById("backtestStrategy").value;
    const days = parseInt(document.getElementById("backtestDays").value);

    runBacktestBtn.disabled = true;
    runBacktestBtn.textContent = "Running Monte Carlo & Backtest...";

    try {
        const res = await fetch("/api/backtest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol: currentSymbol, strategy_type, days, capital: 100000.0 })
        });
        const bt = await res.json();

        backtestResults.style.display = "block";
        document.getElementById("btCagr").textContent = (bt.cagr_pct >= 0 ? '+' : '') + bt.cagr_pct + "%";
        document.getElementById("btSharpe").textContent = bt.sharpe_ratio;
        document.getElementById("btMaxDD").textContent = "-" + bt.max_drawdown_pct + "%";
        document.getElementById("btWinRate").textContent = bt.win_rate_pct + "%";

        // Render backtest chart
        renderBacktestChart(bt.equity_curve, bt.benchmark_curve);
    } catch (e) {
        console.error("Backtest error:", e);
    } finally {
        runBacktestBtn.disabled = false;
        runBacktestBtn.textContent = "⚡ Execute Backtest";
    }
});

function renderBacktestChart(equityCurve, benchmarkCurve) {
    if (!backtestCtx) return;
    const width = backtestCanvas.width = backtestCanvas.parentElement.clientWidth;
    const height = backtestCanvas.height = 180;

    backtestCtx.clearRect(0, 0, width, height);

    const minVal = Math.min(...equityCurve, ...benchmarkCurve);
    const maxVal = Math.max(...equityCurve, ...benchmarkCurve);
    const range = (maxVal - minVal) || 1.0;

    const plot = (curve, color) => {
        backtestCtx.strokeStyle = color;
        backtestCtx.lineWidth = 2;
        backtestCtx.beginPath();
        curve.forEach((val, idx) => {
            const x = (idx / (curve.length - 1)) * (width - 40) + 20;
            const y = height - 20 - ((val - minVal) / range) * (height - 40);
            if (idx === 0) backtestCtx.moveTo(x, y);
            else backtestCtx.lineTo(x, y);
        });
        backtestCtx.stroke();
    };

    plot(benchmarkCurve, "#64748b"); // benchmark in grey
    plot(equityCurve, "#3b82f6"); // strategy in blue
}
