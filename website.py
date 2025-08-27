# Prototype for a website through streamlit
import os, sys, datetime as dt
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
sys.path.append(os.path.dirname(__file__))

from data_api import get_stock_prices

st.set_page_config(page_title="Financial Agent Prototype", layout="wide")
st.title("AI Stock")
st.caption("Type a ticker, get prices, and draw a 1-year chart.")

ticker = st.text_input("Input a ticker (e.g., AAPL, TSLA):", value="AAPL").strip().upper()
if not ticker:
    st.stop()

with st.spinner("Fetching prices…"):
    prices_json = get_stock_prices(
        ticker=ticker,
        interval="day",
        interval_multiplier=1,
        start_date="2025-01-01",
        end_date=dt.date.today().isoformat()
    )

def to_price_df(prices_json):
    if not prices_json:
        return None
    rows = prices_json.get("data") if isinstance(prices_json, dict) else prices_json
    if not rows:
        return None
    df = pd.DataFrame(rows).copy()
    df.columns = [c.lower() for c in df.columns]
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    elif "timestamp" in df.columns:
        df["date"] = pd.to_datetime(df["timestamp"])
    else:
        return None
    for c in ["close", "adj_close", "c", "closing_price"]:
        if c in df.columns:
            df = df.sort_values("date")
            return df[["date", c]].rename(columns={c: "close"})
    return None

df = to_price_df(prices_json)

if df is None or df.empty:
    st.error("No price data returned by your API. Try another ticker.")
    st.stop()

# Draw the chart
st.subheader(f"{ticker} — 1 Year Price")
fig, ax = plt.subplots()
ax.plot(df["date"], df["close"])
ax.set_xlabel("Date")
ax.set_ylabel("Close")
ax.grid(True, alpha=0.3)
st.pyplot(fig)

