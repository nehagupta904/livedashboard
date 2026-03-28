# 📈 Stock Dashboard

A Streamlit dashboard for tracking stocks with live data and manual entry support.

## Features

- **Live API Mode** — Real-time stock data via Yahoo Finance (yfinance)
- **Manual Entry Mode** — Upload CSV or enter OHLCV data by hand
- **Candlestick & Line Charts** — Toggle between chart types
- **Key Metrics** — Price, volume, % change, 52-week high/low, market cap
- **Multi-Stock Comparison** — Normalized performance chart for comparing tickers
- **Portfolio Tracker** — Add holdings, see P&L and allocation breakdown
- **Auto-Refresh** — Optional periodic refresh for near-live updates

## Quick Start (Local)

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set **Main file path** to `app.py`
5. Click **Deploy** — that's it!

## CSV Format (for Manual Mode)

Your CSV should have a date index and these columns:

```
Date,Open,High,Low,Close,Volume
2024-01-02,185.0,186.5,184.0,185.5,50000000
2024-01-03,186.0,187.0,184.5,186.2,48000000
```

## Tech Stack

- **Streamlit** — UI framework
- **yfinance** — Yahoo Finance data
- **Plotly** — Interactive charts
- **streamlit-autorefresh** — Periodic data refresh

## Screenshot

> Deploy the app and add a screenshot here!

---

*Data provided by Yahoo Finance. Not financial advice.*
