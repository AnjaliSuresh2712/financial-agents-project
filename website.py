# Prototype for a website through streamlit
import os, sys, datetime as dt
sys.path.append(os.path.dirname(__file__))  # to get local files
import streamlit as st # the website framework
import matplotlib.pyplot as plt  # makes the chart
import pandas as pd # makes tables (DataFrames)

from data_api import get_stock_prices

st.set_page_config(page_title="Financial Agent Prototype", layout="wide")
st.title("AI Stock")
st.caption("Type a ticker, get prices, and draw a 1-year chart.")
st.info(f"Running file: {__file__}\nCWD: {os.getcwd()}")

# shows a textbox with "AAPL" as default
ticker = st.text_input("Input a ticker (e.g., AAPL, TSLA):", value="AAPL").strip().upper()
if not ticker:
    st.stop()

# calls data_api.py and gets daily prices from Jan 1 2025 until today
# Returns raw JSON/dict data (list of daily stock prices)
# loading animation while waiting for the data
with st.spinner("Fetching prices…"):
    prices_json = get_stock_prices(
        ticker=ticker,
        interval="day",
        interval_multiplier=1,
        start_date="2025-01-01",
        end_date=dt.date.today().isoformat()
    )

# collapsible section which will print the type fo prices_json, the keys,
# and number of rows if it has prices. It shows the first 1000 character of the 
# JSON. Can be used for debuggin when parsing fails
with st.expander("Debug to see the shape"):
    st.write("type:", type(prices_json))
    if isinstance(prices_json, dict):
        st.write("keys:", list(prices_json.keys()))
        if "prices" in prices_json and isinstance(prices_json["prices"], list):
            st.write("len(prices):", len(prices_json["prices"]))
    st.code(str(prices_json)[:1000])

# helper funciton
# converts JSON to a DataFrame
def to_price_df(prices_json):
    if not prices_json:
        return None

    # makes sure the data is a dict with a prices list
    if not (isinstance(prices_json, dict) and isinstance(prices_json.get("prices"), list)):
        return None
    rows = prices_json["prices"]
    if not rows:
        return None
    # turns the list of dicts into a df
    df = pd.DataFrame(rows).copy()
    if df.empty:
        return None
    
    #normalize
    df.columns = [str(c).lower() for c in df.columns]


    # adds a date column from ISO timestamps or epoch ms
    if "time" in df.columns:
        df["date"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    elif "time_milliseconds" in df.columns:
        df["date"] = pd.to_datetime(df["time_milliseconds"], unit="ms", utc=True, errors="coerce")
    else:
        return None


    # looks for the column that show closing proces of adjacent names
    close_col = None
    for c in ("close", "closing_price", "c", "adj_close", "price"):
        if c in df.columns:
            close_col = c
            break
    if close_col is None:
        return None

    # Cleans up final output
    output = (
        df.loc[:, ["date", close_col]]
          .rename(columns={close_col: "close"})
          .dropna(subset=["date", "close"])
          .sort_values("date")
          .drop_duplicates(subset=["date"])
    )
    if not output.empty:
        return output
    else:
        None

# call to helper function
df = to_price_df(prices_json)
    

# If not parsed shows error box and stops running
if df is None:
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
