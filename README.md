# TID Portfolio Web & Mobile Dashboard (Streamlit)

A quantitative decision-support terminal in Python & Streamlit matching **TID - IA13 Portfolio Master Scanner**, **TID - DCA Efficiency Dashboard v2.0**, and **TID - Optimised Trend v1.1**.

---

## 🚀 Key Features

1. **17-Stock Portfolio Scanner**:
   - Covers: `ALAB`, `AMD`, `ARM`, `ASML`, `AVGO`, `GOOG`, `MRVL`, `MU`, `NVDA`, `PLTR`, `SKHY`, `SMSN` (`SMSN.IL`), `SPCX`, `TSLA`, `TSM`, `SMGB` (`SMGB.L`), and `XNAQ` (`XNAQ.L`).
   - Dynamic auto-sorting descending by **Continuous DCA Score (1.0 to 10.0)**.
   - **Today's 1D Change %** and **Yesterday's 1D Change %**.
   - **CVD Order Flow (Cumulative Volume Delta)**: `BULLISH`, `WEAKENING`, `RECOVERING`, `BEARISH`.
   - **Institutional Volume & Falling Knife Guard**: `SCALE IN (SELLING)` protection when institutional liquidation strikes on high volume.
   - Status Badges: `CONFIRMED BUY`, `GHOST CAP`, `VALUE ZONE`, `FAIR VALUE`, `WAIT`.
   - Portfolio Breadth statistics summary and tactical action guide.

2. **DCA Efficiency Dashboard v2.0 (Asset Deep-Dive)**:
   - Detailed single-asset view matching the TradingView HUD.
   - **Macro Valuation (1D • 3-Pillar)**: Trend direction (50/200 SMA), market momentum (MACD), 14 RSI, Z-Score, 50 SMA distance, 200 SMA distance, ATH peak drawdown %.
   - **Execution Engine**: Order Flow CVD state, institutional volume spikes, and Falling Knife guard.
   - **Capital Tranche Sizing Calculator**: Input your regular deposit amount to see suggested multiplier (0.0x to 2.0x) and exact capital to deploy.
   - **Interactive Technical Chart**: Plotly interactive candlestick chart with 50 SMA, 200 SMA, ±2.2σ Volatility Envelope bands, Confirmed / Ghost buy markers, and Cumulative Volume Delta.

3. **TradingView Webhook Integration (TID - Optimised Trend)**:
   - Built-in background webhook server running on `http://localhost:8000/webhook`.
   - Captures alerts for `Confirmed Reversal BUY`, `Ghost Capitulation BUY`, `Optimised Trend: Flipped BLUE/ORANGE`, `Confirmed SELL`, and `Pre-Earnings Caution`.
   - Persists signals in local SQLite database (`tid_portfolio.db`).
   - Includes live alert simulator for instant testing and copy-paste TradingView alert setup templates.

4. **📱 Responsive Mobile Touch View**:
   - Touch-friendly cards auto-sorted by conviction, formatted for mobile smartphone browsers.

---

## 🏃 Quick Start

Run the dashboard with Streamlit:

```bash
streamlit run app.py
```

Or on Windows, simply double-click `run_dashboard.bat`.
