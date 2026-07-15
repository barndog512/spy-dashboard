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

st.set_page_config(page_title="SPY & VIX", layout="wide")
st.title("SPY & VIX — Daily")

if not API_KEY:
    st.error("No API key found. Set ALPHAVANTAGE_API_KEY in the environment or Streamlit secrets.")
    st.stop()

BASE = "https://www.alphavantage.co/query"

@st.cache_data(ttl=24 * 3600)
def get_spy():
    params = {"function": "TIME_SERIES_DAILY", "symbol": "SPY",
              "outputsize": "full", "apikey": API_KEY}
    data = requests.get(BASE, params=params).json()
    series = data.get("Time Series (Daily)")
    if series is None:
        return None, data
    df = (pd.DataFrame(series).T
          .rename(columns=lambda c: c.split(". ")[1])
          .astype(float).sort_index())
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    df["volume"] = df["volume"].astype("int64")
    return df, None

@st.cache_data(ttl=24 * 3600)
def get_vix():
    params = {"function": "INDEX_DATA", "symbol": "VIX",
              "interval": "daily", "apikey": API_KEY}
    data = requests.get(BASE, params=params).json()
    rows = data.get("data")
    if not rows:
        return None, data
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.set_index("date").sort_index()
    return df, None

spy, spy_err = get_spy()
vix, vix_err = get_vix()

if spy is None:
    st.error("SPY: no data returned."); st.write(spy_err); st.stop()
if vix is None:
    st.error("VIX: no data returned."); st.write(vix_err); st.stop()

# --- shared date filter, bounded by the overlap ---
data_min = max(spy.index.min(), vix.index.min()).date()
data_max = min(spy.index.max(), vix.index.max()).date()

c1, c2 = st.columns(2)
start = c1.date_input("Start", value=data_min, min_value=data_min, max_value=data_max)
end   = c2.date_input("End",   value=data_max, min_value=data_min, max_value=data_max)

if start > end:
    st.warning("Start is after end."); st.stop()

spy_v = spy.loc[(spy.index.date >= start) & (spy.index.date <= end)].sort_index(ascending=False)
vix_v = vix.loc[(vix.index.date >= start) & (vix.index.date <= end)].sort_index(ascending=False)

# --- side-by-side tables ---
left, right = st.columns(2)

with left:
    st.subheader("SPY")
    st.dataframe(
        spy_v, width="stretch", height=600,
        column_config={
            "open":   st.column_config.NumberColumn("Open",  format="$%.2f"),
            "high":   st.column_config.NumberColumn("High",  format="$%.2f"),
            "low":    st.column_config.NumberColumn("Low",   format="$%.2f"),
            "close":  st.column_config.NumberColumn("Close", format="$%.2f"),
            "volume": st.column_config.NumberColumn("Volume", format="localized"),
        },
    )
    st.caption(f"{len(spy_v):,} rows")
    st.download_button("Download SPY CSV", spy_v.to_csv().encode(),
                       file_name="spy_daily.csv", mime="text/csv")

with right:
    st.subheader("VIX")
    st.dataframe(
        vix_v, width="stretch", height=600,
        column_config={
            "open":  st.column_config.NumberColumn("Open",  format="%.2f"),
            "high":  st.column_config.NumberColumn("High",  format="%.2f"),
            "low":   st.column_config.NumberColumn("Low",   format="%.2f"),
            "close": st.column_config.NumberColumn("Close", format="%.2f"),
        },
    )
    st.caption(f"{len(vix_v):,} rows")
    st.download_button("Download VIX CSV", vix_v.to_csv().encode(),
                       file_name="vix_daily.csv", mime="text/csv")