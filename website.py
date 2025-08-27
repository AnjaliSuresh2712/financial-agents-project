# Prototype for a website through streamlit
import os, sys, datetime as dt
sys.path.append(os.path.dirname(__file__))  # to get local files
import streamlit as st # the website framework
import matplotlib.pyplot as plt  # makes the chart
import pandas as pd # makes tables (DataFrames)

from data_api import get_stock_prices

st.set_page_config(page_title="AI Stock Prototype", layout="wide")
st.title("AI Stock")
st.caption("Type a ticker, get prices, chart, and moving prices.")

# shows a textbox with AAPL and TSLA as default
# multiple inputs
tickers_input = st.text_input("Input tickers (comma-separated):", value="AAPL, TSLA")
tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
if not tickers:
    st.stop()


# helper funciton
# converts JSON to a DataFrame
def to_price_df(payload) -> pd.DataFrame | None:

    if not isinstance(payload, dict):
        return None
    prices = payload.get("prices")
    if prices is None:
        return None
    
    rows = None
    if isinstance(prices, list):
        rows = prices
    elif isinstance(prices, dict):
        rows = []
        def _key_order(k):
            try:
                return int(str(k).split("-")[0].strip())
            except Exception:
                return 0
        for k in sorted(prices.keys(), key=_key_order):
            chunk = prices[k]
            if isinstance(chunk, list):
                rows.extend(chunk)

    if not rows:
        return None

    df = pd.DataFrame(rows)
    if df.empty:
        return None

    # normalize column names
    df.columns = [str(c).lower() for c in df.columns]

    if "time" in df.columns:
        df["date"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    elif "time_milliseconds" in df.columns:
        df["date"] = pd.to_datetime(df["time_milliseconds"], unit="ms", utc=True, errors="coerce")
    elif "timestamp" in df.columns:
        df["date"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    else:
        return None
    
    close_col = next((c for c in ("close", "closing_price", "c", "adj_close", "price") if c in df.columns), None)
    if not close_col:
        return None
    
    cols = ["date", close_col] + (["volume"] if "volume" in df.columns else [])
    output = (
        df.loc[:, cols]
          .rename(columns={close_col: "close"})
          .dropna(subset=["date", "close"])
          .sort_values("date")
          .drop_duplicates(subset=["date"])
          .reset_index(drop=True)
    )



    #new moving averages
    output["MA_7"] = output["close"].rolling(7).mean()
    output["MA_30"] = output["close"].rolling(30).mean()

    if not output.empty:
        return output
    else:
        None

# calls data_api.py and gets daily prices from Jan 1 2025 until today
# Returns raw JSON/dict data (list of daily stock prices)
# loading animation while waiting for the data
all_dfs: dict[str, pd.DataFrame] = {}
failed: list[str] = []

with st.spinner("Fetching prices…"):
    for t in tickers:
        payload = get_stock_prices(
            ticker=t,
            interval="day",
            interval_multiplier=1,
            start_date="2025-01-01",
            end_date=dt.date.today().isoformat(),
        )

        df = to_price_df(payload)
        if df is not None:
            all_dfs[t] = df
        else:
            failed.append(t)

if not all_dfs:
    st.error("No valid price data returned for any ticker. Try again.")
    st.stop()
if failed:
    st.warning(f"No parsed data for: {', '.join(failed)}")

# Draw the chart
st.subheader("Closing Prices with Moving Averages")
fig, ax = plt.subplots(figsize=(10, 5))
for t, df in all_dfs.items():
    ax.plot(df["date"], df["close"], label=f"{t} Close")
    ax.plot(df["date"], df["MA_7"], linestyle="--", alpha=0.7, label=f"{t} 7d MA")
    ax.plot(df["date"], df["MA_30"], linestyle=":", alpha=0.7, label=f"{t} 30d MA")
ax.set_xlabel("Date"); ax.set_ylabel("Close"); ax.grid(True, alpha=0.3); ax.legend()
st.pyplot(fig)

st.subheader("Latest Summary")
rows = []
for t, df in all_dfs.items():
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    change_pct = ((latest["close"] - prev["close"]) / prev["close"] * 100.0) if prev["close"] else 0.0
    rows.append({
        "Ticker": t,
        "Latest Close": round(float(latest["close"]), 2),
        "Change % (1d)": round(float(change_pct), 2),
        "Volume": int(latest["volume"]) if "volume" in df.columns and pd.notna(latest.get("volume")) else None
    })
st.dataframe(pd.DataFrame(rows))
