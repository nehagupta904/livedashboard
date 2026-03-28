import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Dashboard",
    page_icon="📈",
    layout="wide",
)

# ── Auto-refresh (optional) ─────────────────────────────────
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

# ── Helper Functions ─────────────────────────────────────────

@st.cache_data(ttl=60)
def fetch_stock_data(ticker: str, period: str = "1mo", interval: str = "1d"):
    """Fetch stock data via yfinance with 60s cache."""
    try:
        t = yf.Ticker(ticker)
        data = t.history(period=period, interval=interval)
        if data.empty:
            return None
        # Ensure we have the expected columns
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        # Remove timezone info from index
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)
        # Ensure standard column names exist
        col_map = {}
        for col in data.columns:
            col_lower = str(col).lower().strip()
            if "open" in col_lower:
                col_map[col] = "Open"
            elif "high" in col_lower:
                col_map[col] = "High"
            elif "low" in col_lower:
                col_map[col] = "Low"
            elif "close" in col_lower and "adj" not in col_lower:
                col_map[col] = "Close"
            elif "volume" in col_lower:
                col_map[col] = "Volume"
        if col_map:
            data = data.rename(columns=col_map)
        required = {"Open", "High", "Low", "Close", "Volume"}
        if not required.issubset(set(data.columns)):
            return None
        return data[list(required)]
    except Exception as e:
        st.error(f"Error fetching {ticker}: {e}")
        return None


@st.cache_data(ttl=60)
def fetch_stock_info(ticker: str):
    """Fetch basic stock info."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info or len(info) < 5:
            return {}
        return info
    except Exception:
        return {}


def make_candlestick(df, title=""):
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
    )])
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        template="plotly_white",
        height=450,
        xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def make_line_chart(df, title=""):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"],
        mode="lines",
        name="Close",
        line=dict(color="#1976d2", width=2),
        fill="tozeroy",
        fillcolor="rgba(25,118,210,0.08)",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        template="plotly_white",
        height=450,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def make_volume_chart(df):
    colors = ["#26a69a" if c >= o else "#ef5350"
              for c, o in zip(df["Close"], df["Open"])]
    fig = go.Figure(data=[go.Bar(
        x=df.index, y=df["Volume"],
        marker_color=colors,
    )])
    fig.update_layout(
        title="Volume",
        template="plotly_white",
        height=250,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def make_comparison_chart(data_dict):
    """Normalized comparison chart for multiple stocks."""
    fig = go.Figure()
    for ticker, df in data_dict.items():
        if df is not None and not df.empty:
            normalized = (df["Close"] / df["Close"].iloc[0] - 1) * 100
            fig.add_trace(go.Scatter(
                x=df.index, y=normalized,
                mode="lines", name=ticker,
                line=dict(width=2),
            ))
    fig.update_layout(
        title="Normalized Performance Comparison (%)",
        xaxis_title="Date",
        yaxis_title="% Change from Start",
        template="plotly_white",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def display_metrics(df, info=None):
    """Display key metric cards."""
    if df is None or df.empty:
        st.warning("No data to display metrics.")
        return

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]

    price = float(latest["Close"])
    change = float(latest["Close"] - prev["Close"])
    pct_change = (change / float(prev["Close"])) * 100 if float(prev["Close"]) != 0 else 0
    volume = int(latest["Volume"])
    high = float(latest["High"])
    low = float(latest["Low"])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Close Price", f"${price:,.2f}", f"{change:+,.2f}")
    c2.metric("% Change", f"{pct_change:+.2f}%")
    c3.metric("Volume", f"{volume:,.0f}")
    c4.metric("Day High", f"${high:,.2f}")
    c5.metric("Day Low", f"${low:,.2f}")

    if info:
        extra1, extra2, extra3 = st.columns(3)
        if "marketCap" in info and info["marketCap"]:
            extra1.metric("Market Cap", f"${info['marketCap']/1e9:,.2f}B")
        if "fiftyTwoWeekHigh" in info:
            extra2.metric("52W High", f"${info['fiftyTwoWeekHigh']:,.2f}")
        if "fiftyTwoWeekLow" in info:
            extra3.metric("52W Low", f"${info['fiftyTwoWeekLow']:,.2f}")


def parse_manual_csv(uploaded_file):
    """Parse an uploaded CSV into OHLCV dataframe."""
    try:
        df = pd.read_csv(uploaded_file, parse_dates=True, index_col=0)
        required = {"Open", "High", "Low", "Close", "Volume"}
        if not required.issubset(set(df.columns)):
            st.error(f"CSV must contain columns: {required}. Found: {set(df.columns)}")
            return None
        df.index = pd.to_datetime(df.index)
        return df.sort_index()
    except Exception as e:
        st.error(f"Could not parse CSV: {e}")
        return None


# ── Sidebar ──────────────────────────────────────────────────
st.sidebar.title("📈 Stock Dashboard")

mode = st.sidebar.radio("Data Mode", ["🌐 Live API", "✏️ Manual Entry"], index=0)

PERIOD_OPTIONS = {
    "1 Day (5m intervals)": ("1d", "5m"),
    "5 Days": ("5d", "15m"),
    "1 Month": ("1mo", "1d"),
    "3 Months": ("3mo", "1d"),
    "6 Months": ("6mo", "1d"),
    "1 Year": ("1y", "1wk"),
    "5 Years": ("5y", "1mo"),
}

if mode == "🌐 Live API":
    st.sidebar.markdown("---")
    ticker_input = st.sidebar.text_input("Primary Ticker", value="AAPL").upper().strip()

    period_label = st.sidebar.selectbox("Time Range", list(PERIOD_OPTIONS.keys()), index=2)
    period, interval = PERIOD_OPTIONS[period_label]

    chart_type = st.sidebar.radio("Chart Type", ["Candlestick", "Line"], index=0)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Compare Stocks")
    compare_input = st.sidebar.text_input(
        "Add tickers (comma-separated)",
        value="MSFT, GOOGL",
        help="Enter tickers to compare against the primary stock",
    )
    compare_tickers = [t.strip().upper() for t in compare_input.split(",") if t.strip()]

    st.sidebar.markdown("---")
    st.sidebar.subheader("Auto Refresh")
    if HAS_AUTOREFRESH:
        auto_refresh = st.sidebar.checkbox("Enable auto-refresh", value=False)
        refresh_secs = st.sidebar.slider("Refresh interval (sec)", 15, 300, 60, step=15)
        if auto_refresh:
            st_autorefresh(interval=refresh_secs * 1000, key="data_refresh")
    else:
        st.sidebar.info("Install `streamlit-autorefresh` for auto-refresh support.")

else:  # Manual Entry
    st.sidebar.markdown("---")
    chart_type = st.sidebar.radio("Chart Type", ["Candlestick", "Line"], index=0)
    st.sidebar.markdown("---")
    st.sidebar.subheader("Upload CSV")
    st.sidebar.caption("CSV must have columns: Date (index), Open, High, Low, Close, Volume")

# ── Portfolio Section (shared) ───────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("💼 Portfolio Tracker")
st.sidebar.caption("Track your holdings (uses live prices in API mode)")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

with st.sidebar.expander("Add Holding", expanded=False):
    p_ticker = st.text_input("Ticker", key="p_ticker", value="AAPL")
    p_shares = st.number_input("Shares", key="p_shares", min_value=0.0, value=10.0, step=1.0)
    p_cost = st.number_input("Avg Cost / Share ($)", key="p_cost", min_value=0.0, value=150.0, step=1.0)
    if st.button("Add to Portfolio"):
        st.session_state.portfolio.append({
            "ticker": p_ticker.upper().strip(),
            "shares": p_shares,
            "avg_cost": p_cost,
        })
        st.rerun()

if st.session_state.portfolio:
    if st.sidebar.button("Clear Portfolio"):
        st.session_state.portfolio = []
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# MAIN AREA
# ═══════════════════════════════════════════════════════════════

if mode == "🌐 Live API":
    # ── Live API Mode ────────────────────────────────────────
    st.header(f"📊 {ticker_input}")

    with st.spinner("Fetching data..."):
        df = fetch_stock_data(ticker_input, period=period, interval=interval)
        info = fetch_stock_info(ticker_input)

    if df is not None and not df.empty:
        # Key Metrics
        display_metrics(df, info)

        st.markdown("---")

        # Price Chart
        if chart_type == "Candlestick":
            st.plotly_chart(make_candlestick(df, f"{ticker_input} Price"), use_container_width=True)
        else:
            st.plotly_chart(make_line_chart(df, f"{ticker_input} Price"), use_container_width=True)

        # Volume Chart
        st.plotly_chart(make_volume_chart(df), use_container_width=True)

        # ── Multi-stock Comparison ───────────────────────────
        if compare_tickers:
            st.markdown("---")
            st.subheader("🔀 Stock Comparison")

            all_tickers = [ticker_input] + [t for t in compare_tickers if t != ticker_input]
            comparison_data = {}
            for t in all_tickers:
                comparison_data[t] = fetch_stock_data(t, period=period, interval=interval)

            st.plotly_chart(make_comparison_chart(comparison_data), use_container_width=True)

            # Side-by-side metrics table
            rows = []
            for t in all_tickers:
                d = comparison_data.get(t)
                if d is not None and not d.empty:
                    latest = d.iloc[-1]
                    first = d.iloc[0]
                    pct = ((float(latest["Close"]) - float(first["Close"])) / float(first["Close"])) * 100
                    rows.append({
                        "Ticker": t,
                        "Current Price": f"${float(latest['Close']):,.2f}",
                        "Period Change": f"{pct:+.2f}%",
                        "Volume (latest)": f"{int(latest['Volume']):,}",
                        "High": f"${float(latest['High']):,.2f}",
                        "Low": f"${float(latest['Low']):,.2f}",
                    })
            if rows:
                st.dataframe(pd.DataFrame(rows).set_index("Ticker"), use_container_width=True)

    else:
        st.error(f"Could not fetch data for **{ticker_input}**. Check the ticker symbol.")

else:
    # ── Manual Entry Mode ────────────────────────────────────
    st.header("✏️ Manual Data Entry")

    tab_csv, tab_form = st.tabs(["📁 Upload CSV", "⌨️ Enter Manually"])

    with tab_csv:
        uploaded = st.file_uploader("Upload OHLCV CSV", type=["csv"])
        if uploaded:
            df = parse_manual_csv(uploaded)
            if df is not None:
                display_metrics(df)
                st.markdown("---")
                if chart_type == "Candlestick":
                    st.plotly_chart(make_candlestick(df, "Uploaded Data"), use_container_width=True)
                else:
                    st.plotly_chart(make_line_chart(df, "Uploaded Data"), use_container_width=True)
                st.plotly_chart(make_volume_chart(df), use_container_width=True)

                st.subheader("Raw Data")
                st.dataframe(df, use_container_width=True)

    with tab_form:
        st.caption("Add rows of OHLCV data below.")

        if "manual_rows" not in st.session_state:
            st.session_state.manual_rows = []

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        m_date = col1.date_input("Date", value=datetime.today())
        m_open = col2.number_input("Open", value=100.0, step=0.5, key="m_open")
        m_high = col3.number_input("High", value=105.0, step=0.5, key="m_high")
        m_low = col4.number_input("Low", value=95.0, step=0.5, key="m_low")
        m_close = col5.number_input("Close", value=102.0, step=0.5, key="m_close")
        m_vol = col6.number_input("Volume", value=1000000, step=10000, key="m_vol")

        bc1, bc2 = st.columns(2)
        if bc1.button("Add Row"):
            st.session_state.manual_rows.append({
                "Date": pd.Timestamp(m_date),
                "Open": m_open,
                "High": m_high,
                "Low": m_low,
                "Close": m_close,
                "Volume": int(m_vol),
            })
            st.rerun()
        if bc2.button("Clear All Rows"):
            st.session_state.manual_rows = []
            st.rerun()

        if st.session_state.manual_rows:
            df = pd.DataFrame(st.session_state.manual_rows).set_index("Date").sort_index()
            st.dataframe(df, use_container_width=True)

            if len(df) >= 2:
                display_metrics(df)
                st.markdown("---")
                if chart_type == "Candlestick":
                    st.plotly_chart(make_candlestick(df, "Manual Data"), use_container_width=True)
                else:
                    st.plotly_chart(make_line_chart(df, "Manual Data"), use_container_width=True)
                st.plotly_chart(make_volume_chart(df), use_container_width=True)
            else:
                st.info("Add at least 2 rows to see charts and metrics.")
        else:
            st.info("No data yet. Use the form above to add rows.")


# ── Portfolio Tracker Section ────────────────────────────────
if st.session_state.portfolio:
    st.markdown("---")
    st.header("💼 Portfolio Tracker")

    portfolio_rows = []
    total_value = 0.0
    total_cost = 0.0

    for holding in st.session_state.portfolio:
        t = holding["ticker"]
        shares = holding["shares"]
        avg_cost = holding["avg_cost"]
        cost_basis = shares * avg_cost
        total_cost += cost_basis

        if mode == "🌐 Live API":
            hdata = fetch_stock_data(t, period="5d", interval="1d")
            if hdata is not None and not hdata.empty:
                current_price = float(hdata.iloc[-1]["Close"])
            else:
                current_price = avg_cost  # fallback
        else:
            current_price = avg_cost  # no live data in manual mode

        market_value = shares * current_price
        total_value += market_value
        pnl = market_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis != 0 else 0

        portfolio_rows.append({
            "Ticker": t,
            "Shares": shares,
            "Avg Cost": f"${avg_cost:,.2f}",
            "Current Price": f"${current_price:,.2f}",
            "Market Value": f"${market_value:,.2f}",
            "P&L": f"${pnl:+,.2f}",
            "P&L %": f"{pnl_pct:+.2f}%",
        })

    if portfolio_rows:
        st.dataframe(pd.DataFrame(portfolio_rows).set_index("Ticker"), use_container_width=True)

        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("Total Cost Basis", f"${total_cost:,.2f}")
        pc2.metric("Total Market Value", f"${total_value:,.2f}")
        pc3.metric("Total P&L", f"${total_value - total_cost:+,.2f}",
                    delta=f"{((total_value - total_cost) / total_cost * 100):+.2f}%" if total_cost else None)

        # Allocation pie chart
        alloc_df = pd.DataFrame(portfolio_rows)
        # Parse market value for pie chart
        alloc_df["value"] = alloc_df["Market Value"].str.replace(r"[$,]", "", regex=True).astype(float)
        fig_pie = px.pie(alloc_df, values="value", names="Ticker", title="Portfolio Allocation")
        fig_pie.update_layout(template="plotly_white", height=350,
                              margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_pie, use_container_width=True)

# ── Footer ───────────────────────────────────────────────────
st.markdown("---")
st.caption("Data provided by Yahoo Finance via yfinance. Dashboard refreshes on interaction or via auto-refresh. "
           "Not financial advice.")
