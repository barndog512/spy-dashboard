import os
import requests
import pandas as pd
import streamlit as st

API_KEY = os.environ.get("ALPHAVANTAGE_API_KEY", "")
if not API_KEY:
    try:
        API_KEY = st.secrets["ALPHAVANTAGE_API_KEY"]
    except Exception:
        API_KEY = ""

st.set_page_config(page_title="SPY Data", layout="wide")
st.title("SPY — Daily OHLCV")

if not API_KEY:
    st.error("No API key found. Set ALPHAVANTAGE_API_KEY in the environment or Streamlit secrets.")
    st.stop()

@st.cache_data(ttl=24 * 3600)          # daily data changes once a day
def get_spy():
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": "SPY",
        "outputsize": "full",
        "apikey": API_KEY,
    }
    data = requests.get("https://www.alphavantage.co/query", params=params).json()

    series = data.get("Time Series (Daily)")
    if series is None:
        return None, data

    df = (pd.DataFrame(series).T
          .rename(columns=lambda c: c.split(". ")[1])
          .astype(float)
          .sort_index())
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    df["volume"] = df["volume"].astype("int64")
    return df, None

df, err = get_spy()

if df is None:
    st.error("No data returned.")
    st.write(err)
    st.stop()

# --- date filter ---
data_min, data_max = df.index.min().date(), df.index.max().date()
c1, c2 = st.columns(2)
start = c1.date_input("Start", value=data_min, min_value=data_min, max_value=data_max)
end   = c2.date_input("End",   value=data_max, min_value=data_min, max_value=data_max)

if start > end:
    st.warning("Start is after end.")
    st.stop()

view = df.loc[(df.index.date >= start) & (df.index.date <= end)]

# --- table ---
st.dataframe(
    view.sort_index(ascending=False),
    use_container_width=True,
    height=600,
    column_config={
        "open":   st.column_config.NumberColumn("Open",   format="$%.2f"),
        "high":   st.column_config.NumberColumn("High",   format="$%.2f"),
        "low":    st.column_config.NumberColumn("Low",    format="$%.2f"),
        "close":  st.column_config.NumberColumn("Close",  format="$%.2f"),
        "volume": st.column_config.NumberColumn("Volume", format="%d"),
    },
)

st.caption(f"{len(view):,} rows — {view.index.min().date()} to {view.index.max().date()}")

st.download_button(
    "Download CSV",
    view.to_csv().encode(),
    file_name="spy_daily.csv",
    mime="text/csv",
)