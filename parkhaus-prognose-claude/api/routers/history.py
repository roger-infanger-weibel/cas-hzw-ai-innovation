import os
from datetime import datetime, timedelta

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from data_pipeline.db import (
    fetch_raw_occupancy,
    fetch_sax_strings,
    list_parkhaeuser,
    list_parkhaeuser_info,
)
from data_pipeline.features import fetch_weather_forecast
from api.schemas import (
    OccupancyPoint,
    ParkhausInfo,
    SaxOverview,
    WeatherPoint,
    WeatherOverview,
)

WEATHER_LAT = float(os.getenv("WEATHER_LAT", 47.3769))
WEATHER_LON = float(os.getenv("WEATHER_LON", 8.5417))
WEEKDAY_NAMES = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

router = APIRouter(tags=["history"])


def _majority_sax(strings: pd.Series) -> str:
    if strings.empty:
        return ""

    matrix = pd.DataFrame(strings.apply(list).tolist())
    result = []
    for column in matrix.columns:
        counts = matrix[column].value_counts()
        if counts.empty:
            result.append("A")
            continue
        result.append(counts.sort_values(ascending=False).idxmax())
    return "".join(result)


@router.get("/parkhaeuser", response_model=list[ParkhausInfo])
def get_parkhaeuser():
    return list_parkhaeuser_info()


@router.get("/parkhaus/{parkhaus_id}/sax", response_model=SaxOverview)
def get_sax_overview(parkhaus_id: str):
    sax_df = fetch_sax_strings(
        parkhaus_id=parkhaus_id,
        since=(datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%d"),
    )
    if sax_df.empty:
        raise HTTPException(404, f"Keine SAX-Daten für '{parkhaus_id}' gefunden.")

    sax_df["datum"] = pd.to_datetime(sax_df["datum"])
    sax_df["weekday"] = sax_df["datum"].dt.weekday

    today = pd.Timestamp.utcnow().normalize()
    today_rows = sax_df[sax_df["datum"].dt.normalize() == today]
    if not today_rows.empty:
        current_row = today_rows.iloc[-1]
    else:
        current_row = sax_df.sort_values("datum").iloc[-1]

    weekday = int(current_row["weekday"])
    same_weekday = sax_df[sax_df["weekday"] == weekday]
    weekday_average_sax = _majority_sax(same_weekday["sax_string"])

    return SaxOverview(
        parkhaus_id=parkhaus_id,
        date=current_row["datum"].strftime("%Y-%m-%d"),
        weekday=weekday,
        weekday_name=WEEKDAY_NAMES[weekday],
        sax_string=current_row["sax_string"],
        weekday_average_sax=weekday_average_sax,
    )


@router.get("/parkhaus/{parkhaus_id}/wetter", response_model=WeatherOverview)
def get_weather(parkhaus_id: str):
    df = fetch_raw_occupancy(parkhaus_id=parkhaus_id)
    if df.empty:
        raise HTTPException(404, f"Keine Daten für '{parkhaus_id}' gefunden.")

    now = pd.Timestamp.utcnow()
    start_date = now.strftime("%Y-%m-%d")
    end_date = (now + timedelta(hours=12)).strftime("%Y-%m-%d")

    try:
        weather_df = fetch_weather_forecast(WEATHER_LAT, WEATHER_LON, start_date, end_date)
    except Exception as e:
        raise HTTPException(503, f"Wetterdienst nicht verfügbar: {e}")

    weather_df["ts"] = pd.to_datetime(weather_df["ts"])
    if weather_df["ts"].dt.tz is not None:
        weather_df["ts"] = weather_df["ts"].dt.tz_convert("UTC").dt.tz_localize(None)

    forecast_rows = weather_df[weather_df["ts"] >= now].reset_index(drop=True)

    current = None
    if not forecast_rows.empty:
        row = forecast_rows.iloc[0]
        current = WeatherPoint(
            ts=row["ts"],
            temperature=float(row["temperature"]),
            precipitation=float(row["precipitation"]),
        )

    forecast = [
        WeatherPoint(
            ts=row["ts"],
            temperature=float(row["temperature"]),
            precipitation=float(row["precipitation"]),
        )
        for _, row in forecast_rows.head(8).iterrows()
    ]

    return WeatherOverview(current=current, forecast=forecast)


@router.get("/parkhaus/{parkhaus_id}/aktuell", response_model=OccupancyPoint)
def get_current(parkhaus_id: str):
    df = fetch_raw_occupancy(parkhaus_id=parkhaus_id)
    if df.empty:
        raise HTTPException(404, f"Keine Daten für '{parkhaus_id}'")
    last = df.iloc[-1]
    return OccupancyPoint(
        ts=last["ts"],
        occupied_spots=int(last["occupied_spots"]),
        total_spots=int(last["total_spots"]),
        occupancy_rate=round(last["occupied_spots"] / last["total_spots"], 3),
    )


@router.get("/parkhaus/{parkhaus_id}/verlauf", response_model=list[OccupancyPoint])
def get_history(
    parkhaus_id: str,
    von: str = Query(..., description="ISO-Datum, z.B. 2026-06-01"),
    bis: str = Query(..., description="ISO-Datum, z.B. 2026-06-30"),
):
    df = fetch_raw_occupancy(parkhaus_id=parkhaus_id, since=von, until=bis)
    if df.empty:
        raise HTTPException(404, "Keine Daten im angegebenen Zeitraum")

    return [
        OccupancyPoint(
            ts=row["ts"],
            occupied_spots=int(row["occupied_spots"]),
            total_spots=int(row["total_spots"]),
            occupancy_rate=round(row["occupied_spots"] / row["total_spots"], 3),
        )
        for _, row in df.iterrows()
    ]
