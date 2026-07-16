import os
import requests
import pandas as pd
import numpy as np
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

# ============================================================
# STRIKE SELECTOR
# ============================================================
st.header("Strike Selector")

last_spy = float(spy["close"].iloc[-1])
last_vix = float(vix["close"].iloc[-1])
last_date = spy.index[-1].date()

st.caption(f"Latest close: {last_date}")

c1, c2, c3, c4 = st.columns(4)
spot = c1.number_input("SPY spot", value=round(last_spy, 2), step=0.01, format="%.2f")
v    = c2.number_input("VIX", value=round(last_vix, 2), step=0.01, format="%.2f")
k_put  = c3.number_input("k — put side",  value=1.50, step=0.25, min_value=0.5, max_value=4.0)
k_call = c4.number_input("k — call side", value=1.25, step=0.25, min_value=0.5, max_value=4.0)

implied_1sd = v / 100 / np.sqrt(52)          # weekly 1sd from annualized VIX

put_dist  = k_put  * implied_1sd
call_dist = k_call * implied_1sd
put_strike  = spot * (1 - put_dist)
call_strike = spot * (1 + call_dist)

m1, m2, m3 = st.columns(3)
m1.metric("Implied 1σ (weekly)", f"{implied_1sd:.2%}")
m2.metric(f"Short PUT  (k={k_put})",  f"${put_strike:,.2f}", f"-{put_dist:.2%}")
m3.metric(f"Short CALL (k={k_call})", f"${call_strike:,.2f}", f"+{call_dist:.2%}")

st.caption(
    "Nearest $1 strikes: "
    f"**put {round(put_strike)}** / **call {round(call_strike)}**  ·  "
    f"Historical close-breach at these k: put ≈2.6%, call ≈2.6% (1,211 weeks, 1999–2026)"
)

with st.expander("Historical breach rates by k (Friday close outside strike)"):
    st.markdown("""
| k | Either side | Put side | Call side |
|---|---|---|---|
| 1.00 | 14.5% | 7.8% | 6.8% |
| 1.25 | 7.3% | 4.6% | 2.6% |
| 1.50 | 3.5% | 2.6% | 0.9% |
| 1.75 | 1.5% | 1.3% | 0.2% |
| 2.00 | 1.0% | 1.0% | 0.0% |
| 2.50 | 0.4% | 0.4% | 0.0% |

Monday close → Friday close, 1,211 weeks. Breach rates hold roughly flat across VIX
buckets and across five-year eras, so a single *k* travels. Puts breach ~2–3× as often
as calls at the same distance — hence the wider default on the put side.
    """)

st.divider()

# ============================================================
# DATA TABLES
# ============================================================
data_min = max(spy.index.min(), vix.index.min()).date()
data_max = min(spy.index.max(), vix.index.max()).date()

c1, c2 = st.columns(2)
start = c1.date_input("Start", value=data_min, min_value=data_min, max_value=data_max)
end   = c2.date_input("End",   value=data_max, min_value=data_min, max_value=data_max)

if start > end:
    st.warning("Start is after end."); st.stop()

spy_v = spy.loc[(spy.index.date >= start) & (spy.index.date <= end)].sort_index(ascending=False)
vix_v = vix.loc[(vix.index.date >= start) & (vix.index.date <= end)].sort_index(ascending=False)

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