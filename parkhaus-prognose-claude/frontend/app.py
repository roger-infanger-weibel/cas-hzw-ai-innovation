"""
Streamlit-Dashboard fuer die Parkhaus-Prognose (MVP-Frontend).

Start: streamlit run frontend/app.py
Erwartet die FastAPI unter API_BASE_URL (siehe .env / Umgebungsvariable).
"""
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import time
import plotly.graph_objects as go
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Parkhaus-Prognose", page_icon="🅿️", layout="wide")
st.title("🅿️ Parkhaus-Belegungsprognose")


def _format_temperature(value: float | None) -> str:
    return f"{value:.1f} °C" if value is not None else "n/a"


def _format_precipitation(value: float | None) -> str:
    return f"{value:.1f} mm" if value is not None else "n/a"



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
    url = f"{API_BASE_URL}/parkhaus/{parkhaus_id}/prognose"
    params = {"horizon_minutes": horizon_minutes}
    # simple retry with exponential backoff and graceful fallback
    attempts = 3
    timeout = 20
    for attempt in range(attempts):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException:
            if attempt < attempts - 1:
                time.sleep(1 * (2 ** attempt))
                continue
            # final fallback: return empty forecast structure
            return {"points": []}


@st.cache_data(ttl=300)
def get_history(parkhaus_id: str, von: str, bis: str):
    r = requests.get(
        f"{API_BASE_URL}/parkhaus/{parkhaus_id}/verlauf",
        params={"von": von, "bis": bis},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=60)
def get_sax_overview(parkhaus_id: str):
    r = requests.get(f"{API_BASE_URL}/parkhaus/{parkhaus_id}/sax", timeout=15)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=60)
def get_weather_overview(parkhaus_id: str):
    r = requests.get(f"{API_BASE_URL}/parkhaus/{parkhaus_id}/wetter", timeout=15)
    r.raise_for_status()
    return r.json()


try:
    parkhaeuser = get_parkhaeuser()
except Exception as e:
    st.error(f"API nicht erreichbar unter {API_BASE_URL} ({e}). Läuft der API-Service?")
    st.stop()

def _read_query_params_safe() -> dict:
    try:
        return st.experimental_get_query_params()
    except Exception:
        # Streamlit may not expose experimental_get_query_params in some installs
        try:
            # newer internal API (best-effort)
            from streamlit import runtime

            return runtime.get_query_params()
        except Exception:
            return {}


def _set_query_params_safe(**kwargs) -> None:
    try:
        st.experimental_set_query_params(**kwargs)
    except Exception:
        # best-effort fallback: persist into session_state when query API unavailable
        for k, v in kwargs.items():
            # don't overwrite existing widget-backed keys (Streamlit forbids this)
            if k in st.session_state:
                continue
            st.session_state[k] = v

params = _read_query_params_safe()
selected_city = params.get('city', ['Alle'])[0] or 'Alle'
selected_city = selected_city.title() if isinstance(selected_city, str) else 'Alle'
selected_parkhaus_id = params.get('parkhaus_id', [None])[0]

try:
    horizon_value = params.get('horizon_hours', [None])[0]
    horizon = int(horizon_value) * 60 if isinstance(horizon_value, str) and horizon_value.isdigit() else st.session_state.get('horizon_hours', 4) * 60
except (ValueError, TypeError):
    horizon = 4 * 60

try:
    history_value = params.get('history_days', [None])[0]
    history_days = int(history_value) if isinstance(history_value, str) and history_value.isdigit() else st.session_state.get('history_days', 3)
except (ValueError, TypeError):
    history_days = 3

with st.sidebar:
    # parkhaeuser is now a list of {id,name,city}
    cities = sorted({p.get("city", "").strip().title() for p in parkhaeuser if p.get("city")})
    cities.insert(0, "Alle")
    selected_city = st.selectbox(
        "Stadt",
        cities,
        index=cities.index(selected_city) if selected_city in cities else 0,
        key="selected_city",
    )

    # filter parkhaeuser by city
    if selected_city and selected_city != "Alle":
        filtered = [p for p in parkhaeuser if p.get("city", "").strip().lower() == selected_city.lower()]
    else:
        filtered = parkhaeuser

    # display human-friendly names in the dropdown, fall back to id
    options = [f"{p.get('name') or p.get('id')} ({p.get('id')})" for p in filtered]
    default_index = 0
    if selected_parkhaus_id:
        for idx, p in enumerate(filtered):
            if p.get("id") == selected_parkhaus_id:
                default_index = idx
                break
    choice = st.selectbox("Parkhaus", options, index=default_index, key="selected_parkhaus")
    # extract id from chosen option
    parkhaus_id = choice.split("(")[-1].rstrip(")")

    horizon_hours = st.slider(
        "Prognosehorizont (Stunden)",
        1,
        8,
        value=horizon // 60,
        key="horizon_hours",
    )
    history_days = st.slider(
        "Historie anzeigen (Tage)",
        1,
        14,
        value=history_days,
        key="history_days",
    )

    _set_query_params_safe(
        city=st.session_state.selected_city,
        parkhaus_id=parkhaus_id,
        horizon_hours=str(horizon_hours),
        history_days=str(history_days),
    )

st.session_state["selected_parkhaus_id"] = parkhaus_id
horizon = horizon_hours * 60

col1, col2, col3 = st.columns(3)

current = get_current(parkhaus_id)
free_now = None
if current.get("total_spots") is not None and current.get("occupied_spots") is not None:
    free_now = current["total_spots"] - current["occupied_spots"]

occupancy_rate = current.get("occupancy_rate")
if occupancy_rate is None or pd.isna(occupancy_rate):
    occupancy_text = "n/a"
else:
    occupancy_text = f"{occupancy_rate * 100:.0f}%"

last_update = None
if current.get("ts"):
    last_update = pd.to_datetime(current["ts"]).strftime("%H:%M")

col1.metric("Freie Plätze jetzt", free_now if free_now is not None else "n/a")
col2.metric("Auslastung", occupancy_text)
col3.metric("Letztes Update", last_update or "unbekannt")

von = (datetime.now(timezone.utc) - timedelta(days=history_days)).strftime("%Y-%m-%d")
bis = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

hist = pd.DataFrame(get_history(parkhaus_id, von, bis))
hist["ts"] = pd.to_datetime(hist["ts"])
hist["free_spots"] = hist["total_spots"] - hist["occupied_spots"]
hist["occupancy_rate"] = hist["occupied_spots"] / hist["total_spots"]


def _symbol_from_rate(rate: float) -> str:
    if rate <= 0.20:
        return "A"
    if rate <= 0.50:
        return "B"
    if rate <= 0.80:
        return "C"
    return "D"


def _badge_html(symbol: str) -> str:
    colors = {
        "A": "#2ECC71",
        "B": "#F1C40F",
        "C": "#E67E22",
        "D": "#E74C3C",
    }
    color = colors.get(symbol, "#95A5A6")
    return (
        f"<span style='display:inline-block;padding:6px 10px;border-radius:12px;"
        f"background:{color};color:#ffffff;font-weight:700;'>{symbol}</span>"
    )


def _num_html(percent: float, is_forecast: bool = False) -> str:
    """Return compact numeric HTML for occupancy percent (integer)."""
    try:
        val = int(round(float(percent)))
    except Exception:
        return ""
    # continuous gradient: 0-50 green->yellow, 50-100 yellow->red
    def hex_to_rgb(h: str) -> tuple:
        h = h.lstrip('#')
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    def rgb_to_hex(rgb: tuple) -> str:
        return '#%02X%02X%02X' % rgb

    green = hex_to_rgb('2ECC71')
    yellow = hex_to_rgb('F1C40F')
    red = hex_to_rgb('E74C3C')

    p = max(0, min(val, 100))
    if p <= 50:
        t = p / 50.0
        start, end = green, yellow
    else:
        t = (p - 50.0) / 50.0
        start, end = yellow, red

    interp = tuple(int(start[i] + (end[i] - start[i]) * t) for i in range(3))
    bg = rgb_to_hex(interp)

    inner = f"<span style='font-size:12px;font-weight:700;color:#ffffff'>{val}</span>"
    if is_forecast:
        return f"<div style='display:inline-block;padding:4px;border-radius:8px;border:2px solid #E74C3C;background:{bg};'>{inner}</div>"
    return f"<div style='display:inline-block;padding:4px;border-radius:8px;background:{bg};'>{inner}</div>"

weekday_abbr = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
hist["weekday"] = hist["ts"].dt.weekday.apply(lambda x: weekday_abbr[x])
hist["day"] = hist["ts"].dt.strftime("%Y-%m-%d")
hist["hour"] = hist["ts"].dt.strftime("%H")
hist["symbol"] = hist["occupancy_rate"].apply(_symbol_from_rate)

weekday_hourly = (
    hist.groupby(["weekday", "hour"], as_index=False)
    .agg(occupancy_rate=("occupancy_rate", "mean"))
)
weekday_hourly["display_html"] = weekday_hourly["occupancy_rate"].apply(lambda r: _num_html(r * 100))
weekday_hourly["weekday"] = pd.Categorical(weekday_hourly["weekday"], categories=weekday_abbr, ordered=True)

# Stündliche Werte: ein Wert pro Stunde, ohne Minuten
hist_hourly = hist.copy()
hist_hourly["ts"] = hist_hourly["ts"].dt.floor("h")
hist_hourly = hist_hourly.sort_values("ts").groupby("ts", as_index=False).last()
hist_hourly["weekday"] = hist_hourly["ts"].dt.weekday.apply(lambda x: weekday_abbr[x])
hist_hourly["day"] = hist_hourly["ts"].dt.strftime("%Y-%m-%d")
hist_hourly["hour"] = hist_hourly["ts"].dt.strftime("%H")
hist_hourly["symbol"] = hist_hourly["occupancy_rate"].apply(_symbol_from_rate)
hist_hourly["is_forecast"] = False

forecast_data = get_forecast(parkhaus_id, horizon)
fc = pd.DataFrame(forecast_data["points"])
if not fc.empty:
    fc["ts"] = pd.to_datetime(fc["ts"])
    fc["ts"] = fc["ts"].dt.floor("h")
    fc["occupancy_rate"] = (fc["total_spots"] - fc["predicted_free_spots"]) / fc["total_spots"]
    fc = fc.sort_values("ts").groupby("ts", as_index=False).first()
    fc["weekday"] = fc["ts"].dt.weekday.apply(lambda x: weekday_abbr[x])
    fc["day"] = fc["ts"].dt.strftime("%Y-%m-%d")
    fc["hour"] = fc["ts"].dt.strftime("%H")
    fc["symbol"] = fc["occupancy_rate"].apply(_symbol_from_rate)
    fc["is_forecast"] = True

merged_hourly = pd.concat([
    hist_hourly[["day", "weekday", "hour", "ts", "occupancy_rate", "is_forecast"]],
    fc[["day", "weekday", "hour", "ts", "occupancy_rate", "is_forecast"]] if not fc.empty else pd.DataFrame(columns=["day", "weekday", "hour", "ts", "occupancy_rate", "is_forecast"]),
], ignore_index=True)
merged_hourly = merged_hourly.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
merged_hourly["display_html"] = merged_hourly.apply(
    lambda row: _num_html(row.get("occupancy_rate", 0) * 100, bool(row.get("is_forecast", False))),
    axis=1,
)

st.markdown("---")
st.subheader("Belegungsniveau")

# legend removed: we now show numeric occupancy percentages directly

st.write("**Tägliche Durchschnittswerte**")
weekday_matrix = weekday_hourly.pivot(index="weekday", columns="hour", values="display_html").sort_index()
hours = sorted(weekday_matrix.columns)
header_cells = "".join(
    f"<th style='padding:6px;border-bottom:1px solid #444;text-align:center;color:#ffffff;background:#222;'>{hour}:00</th>"
    for hour in hours
)
body_rows = []
for weekday, row in weekday_matrix.iterrows():
    badge_cells = "".join(
        f"<td style='padding:6px;text-align:center;border-bottom:1px solid #eee;'>{row[hour] if pd.notna(row[hour]) else ''}</td>"
        for hour in hours
    )
    body_rows.append(
        f"<tr><td style='padding:6px;border-bottom:1px solid #444;white-space:nowrap;color:#ffffff;background:#111;'>{weekday}</td>{badge_cells}</tr>"
    )
summary_html = (
    "<table style='width:100%;border-collapse:collapse;background:#111;color:#ffffff;'>"
    "<thead><tr><th style='text-align:left;padding:6px;border-bottom:1px solid #444;color:#ffffff;background:#222;'>Wochentag</th>"
    f"{header_cells}</tr></thead>"
    f"<tbody>{''.join(body_rows)}</tbody></table>"
)
st.markdown(summary_html, unsafe_allow_html=True)

st.write("**Stündliche Werte (letzte Daten + Prognose)**")
if not merged_hourly.empty:
    matrix = merged_hourly.pivot(index=["weekday", "day"], columns="hour", values="display_html")
    # order the rows by the most recent timestamp (latest first)
    order_df = merged_hourly.groupby(["weekday", "day"], as_index=False).agg(latest_ts=("ts", "max"))
    order_df = order_df.sort_values("latest_ts", ascending=False)
    ordered_index = [(r["weekday"], r["day"]) for _, r in order_df.iterrows()]
    # reindex to place newest days on top; missing combinations remain NaN
    matrix = matrix.reindex(ordered_index)
    hours = sorted([c for c in matrix.columns if c is not None])
    header_cells = "".join(
        f"<th style='padding:6px;border-bottom:1px solid #444;text-align:center;color:#ffffff;background:#222;'>{hour}:00</th>"
        for hour in hours
    )
    body_rows = []
    for (weekday, day), row in matrix.iterrows():
        badge_cells = "".join(
            f"<td style='padding:6px;text-align:center;border-bottom:1px solid #eee;'>{row[hour] if pd.notna(row[hour]) else ''}</td>"
            for hour in hours
        )
        body_rows.append(
            f"<tr><td style='padding:6px;border-bottom:1px solid #444;white-space:nowrap;color:#ffffff;background:#111;'>{weekday} {day}</td>{badge_cells}</tr>"
        )
    hourly_html = (
        "<table style='width:100%;border-collapse:collapse;background:#111;color:#ffffff;'>"
        "<thead><tr><th style='text-align:left;padding:6px;border-bottom:1px solid #444;color:#ffffff;background:#222;'>Tag</th>"
        f"{header_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
    )
    st.markdown(hourly_html, unsafe_allow_html=True)
else:
    st.write("Keine stündlichen Belegungswerte verfügbar.")

st.markdown("---")

st.subheader("Verlauf & Prognose")

von = (datetime.now(timezone.utc) - timedelta(days=history_days)).strftime("%Y-%m-%d")
bis = datetime.now(timezone.utc).strftime("%Y-%m-%d")

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
        last_hist_ts = pd.to_datetime(hist["ts"].iloc[-1])
        first_fc_ts = pd.to_datetime(fc["ts"].iloc[0])
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
st.plotly_chart(fig, width="stretch")

with st.expander("Rohdaten Prognose"):
    st.dataframe(fc)
