import json

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import config
import db

st.set_page_config(page_title="Kronos — Signals", layout="wide")
db.init_db()

BUCKET_NAMES = {
    "daytrade": "Daytrade (1d)",
    "swing": f"Swing ({config.SWING_HORIZON_DAYS}d)",
    "trend_200d": "200-day trend",
    "vol_breakout": "Volatility breakout",
    "mean_reversion": "Mean reversion",
}

st.title("Kronos Watchlist — Daily Signals")

run_dates = db.all_run_dates()
if not run_dates:
    st.warning("No runs yet. Run `python run_daily.py` first.")
    st.stop()

selected_date = st.selectbox("Run date", options=list(reversed(run_dates)), index=0)
signals = db.signals_for_date(selected_date)

if not signals:
    st.info("No signals for this date.")
else:
    df = pd.DataFrame(signals)
    df["bucket"] = df["bucket"].map(BUCKET_NAMES).fillna(df["bucket"])

    def color_label(label):
        l = label.lower()
        if "unreliable" in l:
            color = "#57606a"
        elif "bullish" in l or "confirmed" in l or "up" in l:
            color = "#1a7f37"
        elif "bearish" in l or "diverging" in l or "down" in l:
            color = "#cf222e"
        else:
            color = "#9a6700"
        return f"background-color: {color}22; color: {color}; font-weight: 600"

    st.subheader(f"Signals for {selected_date}")
    display_df = df[["ticker", "bucket", "label", "confidence", "expected_return_pct", "detail"]]
    display_df.columns = ["Ticker", "Bucket", "Signal", "Confidence %", "Expected Return %", "Detail"]
    styled = display_df.style.map(color_label, subset=["Signal"])
    st.dataframe(styled, width="stretch", hide_index=True)

st.divider()
st.subheader("Ticker detail")

ticker = st.selectbox("Ticker", options=config.WATCHLIST)
fc = db.forecast_for(selected_date, ticker)

if fc is None:
    st.info(f"No forecast stored for {ticker} on {selected_date}.")
else:
    history_dates = json.loads(fc["history_dates"])
    history_close = json.loads(fc["history_close"])
    forecast_dates = json.loads(fc["forecast_dates"])
    mean_close = json.loads(fc["mean_close"])
    low_close = json.loads(fc["low_close"])
    high_close = json.loads(fc["high_close"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=history_dates, y=history_close, mode="lines", name="Actual",
                              line=dict(color="#1f77b4")))
    fig.add_trace(go.Scatter(x=forecast_dates, y=mean_close, mode="lines", name="Forecast (mean)",
                              line=dict(color="#ff7f0e")))
    fig.add_trace(go.Scatter(x=forecast_dates + forecast_dates[::-1], y=high_close + low_close[::-1],
                              fill="toself", fillcolor="rgba(255,127,14,0.2)", line=dict(color="rgba(0,0,0,0)"),
                              name="10th-90th percentile"))
    fig.update_layout(height=450, margin=dict(l=20, r=20, t=30, b=20),
                       title=f"{ticker} — last close ${fc['last_close']:.2f}")
    st.plotly_chart(fig, width="stretch")

    ticker_signals = [s for s in signals if s["ticker"] == ticker]
    if ticker_signals:
        for s in ticker_signals:
            st.markdown(f"**{BUCKET_NAMES.get(s['bucket'], s['bucket'])}**: {s['label']} "
                        f"({s['confidence']}%) — {s['detail']}")
    else:
        st.markdown("_No signals triggered for this ticker today._")

st.divider()
st.subheader(f"History for {ticker}")
hist = db.history_for_ticker(ticker)
if hist:
    hist_df = pd.DataFrame(hist)
    hist_df["bucket"] = hist_df["bucket"].map(BUCKET_NAMES).fillna(hist_df["bucket"])
    st.dataframe(hist_df, width="stretch", hide_index=True)
else:
    st.markdown("_No history yet._")
