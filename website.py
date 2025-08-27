# Prototype for a website through streamlit
import os, sys, datetime as dt
import streamlit as st # the website framework
import matplotlib.pyplot as plt  # makes the chart
import pandas as pd # makes tables (DataFrames)
sys.path.append(os.path.dirname(__file__)) # to get local files

from data_api import get_stock_prices
with st.expander("Debug to see the shape"):
    st.write(type(prices_json))
    st.write(str(prices_json)[:1000])

st.set_page_config(page_title="Financial Agent Prototype", layout="wide")
st.title("AI Stock")
st.caption("Type a ticker, get prices, and draw a 1-year chart.")

# shows a textbox with "AAPL" as default
ticker = st.text_input("Input a ticker (e.g., AAPL, TSLA):", value="AAPL").strip().upper()
if not ticker:
    st.stop()

# calls your data_api.py, asks for daily prices from Jan 1 2025 until today
# returns a Python dict/list (JSON)
with st.spinner("Fetching prices…"):
    prices_json = get_stock_prices(
        ticker=ticker,
        interval="day",
        interval_multiplier=1,
        start_date="2025-01-01",
        end_date=dt.date.today().isoformat()
    )

# converts JSON to a DataFrame
def to_price_df(prices_json):
    if not prices_json:
        return None

    # if JSON is a dict and starts with "data"
    if isinstance(prices_json, dict) and "data" in prices_json:
        rows = prices_json["data"]
    # if JSON is already a list 
    elif isinstance(prices_json, list):
        rows = prices_json
    else:
        return None

    # turn into table
    df = pd.DataFrame(rows)  

    # try to find a date column
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    elif "timestamp" in df.columns:
        df["date"] = pd.to_datetime(df["timestamp"])
    else:
        return None

    # try to find a close column
    for c in ["close", "adj_close", "c", "closing_price", "price"]:
        if c in df.columns:
            df = df.sort_values("date")
            return df[["date", c]].rename(columns={c: "close"})

    # if no usable columns
    return None  
    

# Call to convert JSON
df = to_price_df(prices_json)
if df is None or df.empty:
    
    st.error("No price data returned by your API. Try another ticker.")
    st.stop()

# Draw the chart
st.subheader(f"{ticker} — 1 Year Price")
fig, ax = plt.subplots() # make an empty chart
ax.plot(df["date"], df["close"]) # plot dates vs closes
ax.set_xlabel("Date") #x-axis
ax.set_ylabel("Close") #y-axis
ax.grid(True, alpha=0.3) # add grid lines
st.pyplot(fig) # show the chart 
