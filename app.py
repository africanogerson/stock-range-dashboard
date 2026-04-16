from datetime import datetime, timedelta

import streamlit as st
import yfinance as yf
import plotly.express as px
import pandas as pd
import numpy as np
from curl_cffi import requests as curl_requests

from db import (
    init_db, upsert_ohlcv, load_ohlcv, has_data,
    log_request, get_request_counts, get_last_date,
)


@st.cache_resource
def get_yf_session():
    # Chrome TLS/HTTP fingerprint — Yahoo's free endpoints throttle the
    # default python-requests fingerprint aggressively.
    return curl_requests.Session(impersonate="chrome")

st.set_page_config(page_title="Stock Daily Range", layout="wide")

DEFAULT_TICKERS = [
    "TSLA", "GOOGL", "META", "AAPL", "AMZN",
    "AVGO", "ORCL", "NVDA", "MSFT", "QQQ",
    "SPY", "SLV", "GLD", "IBIT",
]


@st.cache_resource
def get_connection():
    return init_db()


def _fallback_with_warning(conn, ticker: str, reason: str) -> pd.DataFrame:
    """Return cached data (if any) and surface a warning instead of an error."""
    cached = load_ohlcv(conn, ticker)
    ok, total = get_request_counts(conn)
    if not cached.empty:
        last = str(cached.index[-1].date())
        st.warning(
            f"Could not refresh **{ticker}** ({reason}). "
            f"Showing cached data through **{last}**.\n\n"
            f"YF requests: {ok} OK / {total} total"
        )
    else:
        st.error(
            f"Could not fetch data for '{ticker}' ({reason}) and no cached data is available.\n\n"
            f"YF requests: {ok} OK / {total} total"
        )
    return cached


def fetch_and_store(conn, ticker: str) -> pd.DataFrame:
    # Incremental pull: start one day before last stored date (re-fetches that
    # bar in case it was partial, appends anything newer). Full 1y on first use.
    last_date = get_last_date(conn, ticker)
    if last_date:
        start = (datetime.fromisoformat(last_date) - timedelta(days=1)).date()
        kwargs: dict = {"start": start.isoformat()}
    else:
        kwargs = {"period": "1y"}

    try:
        raw = yf.Ticker(ticker, session=get_yf_session()).history(**kwargs)
    except Exception as e:
        log_request(conn, ticker, success=False)
        return _fallback_with_warning(conn, ticker, f"fetch error: {e}")

    if raw.empty:
        log_request(conn, ticker, success=False)
        # Empty incremental pull is normal on weekends/holidays/pre-open —
        # just return cached data silently if it exists.
        if last_date:
            cached = load_ohlcv(conn, ticker)
            if not cached.empty:
                return cached
        return _fallback_with_warning(
            conn, ticker,
            "no data returned — possibly rate-limited, wait a minute",
        )

    log_request(conn, ticker, success=True)
    raw = raw[["Open", "High", "Low", "Close", "Volume"]]
    upsert_ohlcv(conn, ticker, raw)
    return load_ohlcv(conn, ticker)


def make_histogram(series: pd.Series, title: str, unit: str, last_date: str, bin_width: float = 0.0):
    if series.empty:
        return None
    label = "Range ($)" if unit == "$" else "Range (%)"
    if bin_width > 0:
        fig = px.histogram(series, title=title, labels={"value": label})
        fig.update_traces(xbins_size=bin_width)
    else:
        nbins = max(5, len(series) // 2)
        fig = px.histogram(series, nbins=nbins, title=title, labels={"value": label})
    # Compute actual bin width for display
    bin_min = series.min()
    bin_max = series.max()
    if bin_width > 0:
        display_bw = bin_width
    else:
        nbins = max(5, len(series) // 2)
        display_bw = (bin_max - bin_min) / nbins if nbins > 0 else 0
    median_val = series.median()
    fmt = f"{median_val:.2f}"
    fig.add_vline(
        x=median_val,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Median: {fmt}{unit}",
        annotation_position="top right",
        annotation_font_color="red",
    )
    # Show each data point as a rug plot on the x-axis
    fig.add_scatter(
        x=series.values,
        y=[0] * len(series),
        mode="markers",
        marker=dict(symbol="line-ns-open", size=8, color="black"),
        hovertext=[f"{v:.2f}{unit}" for v in series.values],
        hoverinfo="text",
        showlegend=False,
    )
    fig.add_annotation(
        text=f"Last: {last_date} | Bin width: {display_bw:.2f}{unit}",
        xref="paper", yref="paper",
        x=0.5, y=-0.28,
        showarrow=False,
        font=dict(size=11, color="gray"),
    )
    fig.update_layout(
        showlegend=False,
        height=460,
        xaxis_title=label,
        yaxis_title="Count",
        margin=dict(b=100, t=60),
    )
    if display_bw > 0 and bin_max > bin_min:
        bins = np.arange(bin_min, bin_max + display_bw, display_bw)
    else:
        bins = max(5, len(series) // 2)
    hist_counts, _ = np.histogram(series.dropna(), bins=bins)
    fig.update_yaxes(range=[0, int(hist_counts.max() * 1.25) + 1])
    return fig


# ── Init DB connection (once) ────────────────────────────────────────────────
conn = get_connection()

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("Settings")

selected = st.sidebar.selectbox("Default ticker", DEFAULT_TICKERS)
custom = st.sidebar.text_input("Or enter a custom ticker").strip().upper()
ticker = custom if custom else selected

pct_mode = st.sidebar.toggle("Show as percentage (%)", value=False)
custom_n = st.sidebar.number_input("Custom window (days)", min_value=2, max_value=365, value=7)
default_bw = 1.0 if pct_mode else 2.0
custom_bin_width = st.sidebar.number_input("Bin width (0 = auto)", min_value=0.0, value=default_bw, step=0.1, format="%.2f")
refresh = st.sidebar.button("Refresh Data")

st.sidebar.markdown("---")
_ok, _total = get_request_counts(conn)
st.sidebar.caption(f"YF requests: {_ok} OK / {_total} total")

# ── Data loading ─────────────────────────────────────────────────────────────

if refresh or not has_data(conn, ticker):
    with st.spinner(f"Fetching {ticker} from Yahoo Finance..."):
        df = fetch_and_store(conn, ticker)
    # fetch_and_store already surfaces warnings/errors and falls back to
    # cached data when possible. Only stop if we truly have nothing to plot.
    if df.empty:
        st.stop()
else:
    df = load_ohlcv(conn, ticker)

# ── Compute ranges ───────────────────────────────────────────────────────────
if pct_mode:
    df["range"] = (df["High"] - df["Low"]) / df["Close"].shift(1) * 100
    df = df.dropna(subset=["range"])
    unit = "%"
else:
    df["range"] = df["High"] - df["Low"]
    unit = "$"

# ── Histograms ───────────────────────────────────────────────────────────────
st.title(f"Daily Range Distribution — {ticker}")

windows = [14, 28, int(custom_n)]
labels = ["14-Day", "28-Day", f"{int(custom_n)}-Day"]
cols = st.columns(3)

for col, window, label in zip(cols, windows, labels):
    sliced = df.tail(window)
    data = sliced["range"]
    last_date = str(sliced.index[-1].date()) if not sliced.empty else "N/A"
    actual = len(data)
    with col:
        if actual < window:
            st.warning(f"Only {actual} trading days available (requested {window}).")
        fig = make_histogram(data, f"{label} Range", unit, last_date, custom_bin_width)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data to display.")

# ── Time series: Date vs Day Range (custom window) ──────────────────────────
st.markdown("---")
custom_sliced = df.tail(int(custom_n))
if not custom_sliced.empty:
    range_label = f"Range ({unit})"
    ts_fig = px.line(
        custom_sliced,
        x=custom_sliced.index,
        y="range",
        title=f"Daily Range Over Last {int(custom_n)} Days — {ticker}",
        labels={"x": "Date", "range": range_label},
        markers=True,
    )
    ts_fig.update_traces(line_dash="dash")
    median_val = custom_sliced["range"].median()
    ts_fig.add_hline(
        y=median_val,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Median: {median_val:.2f}{unit}",
        annotation_position="top left",
    )
    ts_fig.update_layout(
        height=400,
        xaxis_title="Date",
        yaxis_title=range_label,
        showlegend=False,
    )
    st.plotly_chart(ts_fig, use_container_width=True)
