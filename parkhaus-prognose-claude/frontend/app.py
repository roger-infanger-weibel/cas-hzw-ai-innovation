"""
Streamlit-Dashboard fuer die Parkhaus-Prognose (MVP-Frontend).

Start: streamlit run frontend/app.py
Erwartet die FastAPI unter API_BASE_URL (siehe .env / Umgebungsvariable).
"""
import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Parkhaus-Prognose", page_icon="🅿️", layout="wide")
st.title("🅿️ Parkhaus-Belegungsprognose")


@st.cache_data(ttl=60)
def get_parkhaeuser():
    r = requests.get(f"{API_BASE_URL}/parkhaeuser", timeout=10)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=60)
def get_current(parkhaus_id: str):
    r = requests.get(f"{API_BASE_URL}/parkhaus/{parkhaus_id}/aktuell", timeout=10)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=60)
def get_forecast(parkhaus_id: str, horizon_minutes: int):
    r = requests.get(
        f"{API_BASE_URL}/parkhaus/{parkhaus_id}/prognose",
        params={"horizon_minutes": horizon_minutes},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=300)
def get_history(parkhaus_id: str, von: str, bis: str):
    r = requests.get(
        f"{API_BASE_URL}/parkhaus/{parkhaus_id}/verlauf",
        params={"von": von, "bis": bis},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


try:
    parkhaeuser = get_parkhaeuser()
except Exception as e:
    st.error(f"API nicht erreichbar unter {API_BASE_URL} ({e}). Läuft der API-Service?")
    st.stop()

with st.sidebar:
    # parkhaeuser is now a list of {id,name,city}
    cities = sorted({p.get("city") for p in parkhaeuser if p.get("city")})
    cities.insert(0, "Alle")
    selected_city = st.selectbox("Stadt", cities, index=0)

    # filter parkhaeuser by city
    if selected_city and selected_city != "Alle":
        filtered = [p for p in parkhaeuser if p.get("city") == selected_city]
    else:
        filtered = parkhaeuser

    # display human-friendly names in the dropdown, fall back to id
    options = [f"{p.get('name') or p.get('id')} ({p.get('id')})" for p in filtered]
    choice = st.selectbox("Parkhaus", options)
    # extract id from chosen option
    parkhaus_id = choice.split("(")[-1].rstrip(")")

    horizon = st.slider("Prognosehorizont (Stunden)", 1, 8, 4) * 60
    history_days = st.slider("Historie anzeigen (Tage)", 1, 14, 3)

col1, col2, col3 = st.columns(3)

current = get_current(parkhaus_id)
free_now = current["total_spots"] - current["occupied_spots"]

col1.metric("Freie Plätze jetzt", free_now)
col2.metric("Auslastung", f"{current['occupancy_rate'] * 100:.0f}%")
col3.metric("Letztes Update", pd.to_datetime(current["ts"]).strftime("%H:%M"))

st.subheader("Verlauf & Prognose")

von = (datetime.utcnow() - timedelta(days=history_days)).strftime("%Y-%m-%d")
bis = datetime.utcnow().strftime("%Y-%m-%d")

hist = pd.DataFrame(get_history(parkhaus_id, von, bis))
hist["ts"] = pd.to_datetime(hist["ts"])
hist["free_spots"] = hist["total_spots"] - hist["occupied_spots"]

forecast_data = get_forecast(parkhaus_id, horizon)
fc = pd.DataFrame(forecast_data["points"])
if not fc.empty:
    fc["ts"] = pd.to_datetime(fc["ts"])
    # If the forecast starts after the last history timestamp, prepend a connector
    # using the last observed free_spots so the plot looks continuous.
    # This is a visual aid only and does not alter the actual forecast points.
    if not hist.empty:
        last_hist_ts = hist["ts"].iloc[-1]
        first_fc_ts = fc["ts"].iloc[0]
        if first_fc_ts > last_hist_ts:
            connector = pd.DataFrame([
                {"ts": last_hist_ts, "predicted_free_spots": hist["free_spots"].iloc[-1]}
            ])
            fc = pd.concat([connector, fc], ignore_index=True)
    fc = fc.sort_values("ts").reset_index(drop=True)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=hist["ts"], y=hist["free_spots"],
    mode="lines", name="Historie (freie Plätze)",
    line=dict(color="#2E86AB"),
))
if not fc.empty:
    fig.add_trace(go.Scatter(
        x=fc["ts"], y=fc["predicted_free_spots"],
        mode="lines", name="Prognose (freie Plätze)",
        line=dict(color="#E63946", dash="dash"),
    ))
fig.update_layout(
    xaxis_title="Zeit", yaxis_title="Freie Plätze",
    hovermode="x unified", height=450,
)
st.plotly_chart(fig, use_container_width=True)

with st.expander("Rohdaten Prognose"):
    st.dataframe(fc)
