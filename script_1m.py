# -*- coding: utf-8 -*-
import os
import io
import time
import json
import datetime as dt
from typing import Optional

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Intradía 1m • Polygon.io (sin ajustar)", layout="wide")

# --------------------------
# CONFIGURACIÓN
# --------------------------
POLYGON_API_KEY = "jpenHG984Gtqgvphgw_XS6e_kysajwAt"  # <<<< tu API key

# --------------------------
# Helpers
# --------------------------
@st.cache_data(show_spinner=False)
def load_csv(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(file_bytes))
    ticker_col, date_col = None, None
    for c in df.columns:
        lc = str(c).lower().strip()
        if lc in ("ticker", "symbol"):
            ticker_col = c
        if lc in ("date", "fecha"):
            date_col = c
    if ticker_col is None or date_col is None:
        raise ValueError("El CSV debe tener columnas 'ticker' y 'date' (o 'fecha').")
    df = df.rename(columns={ticker_col: "ticker", date_col: "date"})
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.dropna(subset=["ticker", "date"]).reset_index(drop=True)
    return df[["ticker", "date"]]

def polygon_agg_url(ticker: str, start_iso: str, end_iso: str) -> str:
    return (
        f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/"
        f"{start_iso}/{end_iso}?adjusted=false&limit=50000&sort=asc&apiKey={POLYGON_API_KEY}"
    )

def fetch_polygon_minutes(ticker: str, target_date: dt.date) -> pd.DataFrame:
    from_zone = "America/New_York"
    from_day = target_date.strftime("%Y-%m-%d")
    url = polygon_agg_url(ticker, from_day, from_day)
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Polygon error {r.status_code}: {r.text}")
    data = r.json()
    if data.get("status") != "OK" and "results" not in data:
        return pd.DataFrame(columns=["datetime_utc","open","high","low","close","volume","vwap","transactions","ticker","date"])

    results = data.get("results", []) or []
    if not results:
        return pd.DataFrame(columns=["datetime_utc","open","high","low","close","volume","vwap","transactions","ticker","date"])

    df = pd.DataFrame(results).rename(
        columns={"t":"ts_ms","o":"open","h":"high","l":"low","c":"close","v":"volume","vw":"vwap","n":"transactions"}
    )
    df["datetime_utc"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    df["ticker"] = ticker
    df["date"] = pd.to_datetime(target_date).date()
    df["_ny_time"] = df["datetime_utc"].dt.tz_convert(from_zone)
    mask = df["_ny_time"].dt.date == target_date
    df = df.loc[mask].drop(columns=["ts_ms","_ny_time"])
    return df[["datetime_utc","open","high","low","close","volume","vwap","transactions","ticker","date"]]

def add_local_times(df_m1: pd.DataFrame, tz_out: str) -> pd.DataFrame:
    if df_m1.empty:
        return df_m1
    df = df_m1.copy().sort_values("datetime_utc")
    df["bar_time_local"] = df["datetime_utc"].dt.tz_convert(tz_out)
    df["madrid_time"] = df["datetime_utc"].dt.tz_convert("Europe/Madrid")
    cols = [
        "ticker","date",
        "datetime_utc","madrid_time","bar_time_local",
        "open","high","low","close","volume","vwap","transactions"
    ]
    return df[cols]

def filter_session_m1(df_m1: pd.DataFrame, session_only: bool) -> pd.DataFrame:
    if df_m1.empty or not session_only:
        return df_m1
    local = df_m1.copy()
    hhmm = local["bar_time_local"].dt.strftime("%H:%M")
    mask = (hhmm >= "09:30") & (hhmm < "16:00")
    return local.loc[mask]

# --------------------------
# UI
# --------------------------
st.title("Descarga intradía 1 minuto (sin ajustar) • Polygon.io")
st.caption("CSV con 'ticker' y 'date'. Devuelve velas de 1m sin ajustar por splits.")

with st.sidebar:
    tz_out = st.selectbox("Zona horaria", ["America/New_York","UTC","Europe/Madrid"], index=0)
    session_only = st.checkbox("Solo sesión regular (09:30-16:00)", value=True)
    throttle_s = st.number_input("Pausa entre requests (seg)", min_value=0.0, value=0.25, step=0.05)

uploaded = st.file_uploader("CSV de entrada", type=["csv"])

with st.expander("Formato esperado"):
    st.code("ticker,date\nAAPL,2025-09-08\nMSFT,2025-09-08")

if uploaded is not None:
    df_in = load_csv(uploaded.getvalue())
    df_in = df_in.drop_duplicates(subset=["ticker","date"]).reset_index(drop=True)
    st.success(f"{len(df_in)} filas cargadas.")

    progress = st.progress(0.0, text="Descargando 1m…")
    status = st.empty()

    all_m1 = []
    total = len(df_in)
    for i, row in enumerate(df_in.itertuples(index=False)):
        ticker = row.ticker
        date_py = row.date
        status.write(f"{i+1}/{total} • {ticker} • {date_py}")
        try:
            m1 = fetch_polygon_minutes(ticker, date_py)
            if not m1.empty:
                m1 = add_local_times(m1, tz_out=tz_out)
                m1 = filter_session_m1(m1, session_only=session_only)
                all_m1.append(m1)
            else:
                st.warning(f"Sin datos: {ticker} {date_py}")
        except Exception as e:
            st.error(f"{ticker} {date_py}: {e}")
        time.sleep(float(throttle_s))
        progress.progress((i+1)/total)

    if all_m1:
        out = pd.concat(all_m1, ignore_index=True)
        out_fmt = out.copy()
        out_fmt["datetime_utc"] = out_fmt["datetime_utc"].dt.strftime("%H:%M:%S")
        out_fmt["madrid_time"] = out_fmt["madrid_time"].dt.strftime("%H:%M:%S")
        out_fmt["bar_time_local"] = out_fmt["bar_time_local"].dt.strftime("%H:%M:%S")
        out_fmt = out_fmt.rename(columns={"madrid_time": "Madrid Time"})
        st.subheader("Velas 1m (sin ajustar)")
        st.dataframe(out_fmt.head(200), use_container_width=True)
        csv_bytes = out_fmt.to_csv(index=False).encode("utf-8")
        st.download_button("Descargar CSV", data=csv_bytes, file_name="intraday_1m_unadjusted.csv", mime="text/csv")
    else:
        st.warning("No se generaron velas de 1m.")
else:
    st.info("Cargá un CSV para empezar.")