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

st.set_page_config(page_title="SPY Daily", layout="wide")
st.title("SPY — Daily Close, Past 6 Months")

if not API_KEY:
    st.error("No API key found. Set ALPHAVANTAGE_API_KEY in the environment.")
    st.stop()

@st.cache_data(ttl=6 * 3600)
def get_spy():
    params = {"function": "TIME_SERIES_DAILY", "symbol": "SPY", "apikey": API_KEY}
    return requests.get("https://www.alphavantage.co/query", params=params).json()

data = get_spy()
series = data.get("Time Series (Daily)")

if series is None:
    st.error("No data returned.")
    st.write(data)
else:
    df = (pd.DataFrame(series).T
          .rename(columns=lambda c: c.split(". ")[1])
          .astype(float).sort_index())
    df.index = pd.to_datetime(df.index)

    cutoff = df.index.max() - pd.DateOffset(months=6)
    df = df[df.index >= cutoff]

    st.line_chart(df[["close"]])
    st.caption(f"{len(df)} trading days — {df.index.min().date()} to {df.index.max().date()}")