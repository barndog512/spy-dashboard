import os
import requests
import pandas as pd
import altair as alt
import streamlit as st

API_KEY = os.environ.get("ALPHAVANTAGE_API_KEY", "")
if not API_KEY:
    try:
        API_KEY = st.secrets["ALPHAVANTAGE_API_KEY"]
    except Exception:
        API_KEY = ""

st.set_page_config(page_title="SPY Daily", layout="wide")
st.title("SPY — Daily Close")

if not API_KEY:
    st.error("No API key found. Set ALPHAVANTAGE_API_KEY in the environment or Streamlit secrets.")
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
    st.stop()

df = (pd.DataFrame(series).T
      .rename(columns=lambda c: c.split(". ")[1])
      .astype(float).sort_index())
df.index = pd.to_datetime(df.index)
df.index.name = "date"

data_min = df.index.min().date()
data_max = df.index.max().date()

# --- date pickers ---
c1, c2 = st.columns(2)
start = c1.date_input("Start date", value=data_min, min_value=data_min, max_value=data_max)
end = c2.date_input("End date", value=data_max, min_value=data_min, max_value=data_max)

if start > end:
    st.warning("Start date is after end date.")
    st.stop()

mask = (df.index.date >= start) & (df.index.date <= end)
view = df.loc[mask]

if view.empty:
    st.warning("No trading days in that range.")
    st.stop()

# --- chart with auto-scaled y-axis ---
plot_df = view.reset_index()[["date", "close"]]

chart = (
    alt.Chart(plot_df)
    .mark_line()
    .encode(
        x=alt.X("date:T", title=None),
        y=alt.Y("close:Q", title="Close ($)",
                scale=alt.Scale(zero=False, nice=True)),   # <-- this is the fix
        tooltip=[alt.Tooltip("date:T"), alt.Tooltip("close:Q", format="$.2f")],
    )
    .properties(height=420)
    .interactive()
)

st.altair_chart(chart, use_container_width=True)

lo, hi = view["close"].min(), view["close"].max()
chg = (view["close"].iloc[-1] / view["close"].iloc[0] - 1)
m1, m2, m3 = st.columns(3)
m1.metric("Range", f"${lo:.2f} – ${hi:.2f}")
m2.metric("Change over window", f"{chg:.2%}")
m3.metric("Trading days", len(view))

st.caption(f"Data available: {data_min} to {data_max} (free tier ≈100 days)")