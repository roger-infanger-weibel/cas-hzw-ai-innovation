"""
Feature Engineering für die Belegungsprognose.

Nimmt rohe 15-Minuten-Zeitreihendaten und baut daraus die Feature-Matrix,
die LightGBM (und die API zur Inferenzzeit) benötigt.

Wichtig: Diese Funktion muss zur TRAININGSZEIT und zur INFERENZZEIT
identisch verwendet werden (siehe api/inference.py), sonst gibt es
Train/Serve-Skew.
"""
import os
from datetime import datetime

import numpy as np
import pandas as pd
import holidays
import requests

CH_HOLIDAYS = holidays.Switzerland()  # ggf. Kanton spezifizieren: holidays.Switzerland(subdiv="ZH")


def add_calendar_features(df: pd.DataFrame, ts_col: str = "ts") -> pd.DataFrame:
    df = df.copy()
    ts = df[ts_col]

    df["hour"] = ts.dt.hour
    df["weekday"] = ts.dt.weekday
    df["month"] = ts.dt.month
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)
    df["is_holiday"] = ts.dt.date.map(lambda d: d in CH_HOLIDAYS).astype(int)

    # zyklische Kodierung, damit z.B. 23 Uhr und 0 Uhr für das Modell "nah" sind
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["weekday_sin"] = np.sin(2 * np.pi * df["weekday"] / 7)
    df["weekday_cos"] = np.cos(2 * np.pi * df["weekday"] / 7)

    return df


def regularize_timeseries(
    df: pd.DataFrame,
    freq: str = "15min",
    ffill_limit: int = 2,
) -> pd.DataFrame:
    """
    Die realen fetch_ts-Zeitstempel liegen NICHT exakt im 15-Min-Raster
    (z.B. 13:10, 13:25, 13:40, 13:54, 14:15, ... teils mit Luecken wie
    16:45 -> 17:15). Lag-Features per shift() setzen aber ein konstantes
    Raster voraus - deshalb wird hier PRO Parkhaus auf ein exaktes
    15-Min-Raster reindexiert.

    Kleine Luecken (bis ffill_limit Schritte, hier: 2 x 15min = 30 Min)
    werden vorwaerts gefuellt (der Sensor hat sich einfach etwas verspaetet).
    Groessere Luecken bleiben NaN und werden spaeter beim Feature-Building
    automatisch verworfen (kein Erfinden von Daten ueber laengere Ausfaelle).
    """
    frames = []
    for pid, g in df.groupby("parkhaus_id"):
        g = g.set_index("ts").sort_index()
        g = g[~g.index.duplicated(keep="last")]  # doppelte Timestamps (Retries) bereinigen

        # WICHTIG: resample() bucketet jeden Zeitstempel in das naechstgelegene
        # Intervall (floor auf 15-Min-Raster) - anders als reindex(), das nur
        # exakte Treffer uebernimmt und bei leicht verschobenen fetch_ts sonst
        # fast alles auf NaN setzen wuerde.
        g = g[["occupied_spots", "total_spots"]].resample(freq).last()
        g = g.ffill(limit=ffill_limit)
        g["parkhaus_id"] = pid

        g.index.name = "ts"
        frames.append(g.reset_index())

    return pd.concat(frames, ignore_index=True)


def add_lag_and_rolling_features(df: pd.DataFrame, target_col: str = "occupied_spots") -> pd.DataFrame:
    """
    Erwartet df sortiert nach (parkhaus_id, ts) mit konstantem 15-Min-Raster
    (siehe regularize_timeseries - wird in build_feature_matrix automatisch
    davor aufgerufen). Lags/Rolling werden PRO Parkhaus berechnet.
    """
    df = df.copy()
    g = df.groupby("parkhaus_id")[target_col]

    # Lags: 15min, 1h, 4h, 24h, 7 Tage (in 15-Min-Schritten: 1, 4, 16, 96, 672)
    for steps, name in [(1, "15min"), (4, "1h"), (16, "4h"), (96, "24h"), (672, "7d")]:
        df[f"lag_{name}"] = g.shift(steps)

    # Rolling-Statistiken über die letzten 4h / 24h (auf Basis der Lags, um Leakage zu vermeiden)
    df["roll_mean_4h"] = g.shift(1).rolling(16).mean().reset_index(0, drop=True)
    df["roll_std_4h"] = g.shift(1).rolling(16).std().reset_index(0, drop=True)
    df["roll_mean_24h"] = g.shift(1).rolling(96).mean().reset_index(0, drop=True)

    return df


def fetch_weather_features(lat: float, lon: float, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Holt historische stündliche Wetterdaten von Open-Meteo (kostenlos, kein Key).
    Wird auf 15-Min-Raster hochgesampelt (forward-fill).
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,precipitation",
        "timezone": "Europe/Zurich",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()["hourly"]

    weather = pd.DataFrame(
        {
            "ts": pd.to_datetime(data["time"]),
            "temperature": data["temperature_2m"],
            "precipitation": data["precipitation"],
        }
    ).set_index("ts").resample("15min").ffill().reset_index()

    return weather


def fetch_weather_forecast(lat: float, lon: float, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Holt stündliche Wetterprognosen von Open-Meteo für zukünftige Zeitpunkte.
    Wird auf 15-Minuten-Raster hochgesampelt (forward-fill).
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation",
        "timezone": "Europe/Zurich",
        "start_date": start_date,
        "end_date": end_date,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()["hourly"]

    weather = pd.DataFrame(
        {
            "ts": pd.to_datetime(data["time"]),
            "temperature": data["temperature_2m"],
            "precipitation": data["precipitation"],
        }
    ).set_index("ts").resample("15min").ffill().reset_index()

    return weather


def build_feature_matrix(
    raw_df: pd.DataFrame,
    weather_df: pd.DataFrame | None = None,
    target_col: str = "occupied_spots",
) -> pd.DataFrame:
    """
    Vollständige Feature-Pipeline: Kalender + Lags + Wetter (optional).
    Gibt DataFrame zurück inkl. Ziel-Spalte `y` (= occupied_spots),
    NaN-Zeilen (durch Lags am Anfang der Zeitreihe) werden entfernt.
    """
    df = raw_df.sort_values(["parkhaus_id", "ts"]).reset_index(drop=True)
    df = regularize_timeseries(df)  # unregelmaessige fetch_ts -> exaktes 15-Min-Raster

    df["occupancy_rate"] = df[target_col] / df["total_spots"]

    df = add_calendar_features(df)
    df = add_lag_and_rolling_features(df, target_col=target_col)

    if weather_df is not None:
        df = df.merge(weather_df, on="ts", how="left")
        df[["temperature", "precipitation"]] = df[["temperature", "precipitation"]].ffill()

    df["y"] = df[target_col]

    feature_cols = [
        "hour_sin", "hour_cos", "weekday_sin", "weekday_cos",
        "is_weekend", "is_holiday", "month",
        "lag_15min", "lag_1h", "lag_4h", "lag_24h", "lag_7d",
        "roll_mean_4h", "roll_std_4h", "roll_mean_24h",
        "total_spots",
    ]
    if weather_df is not None:
        feature_cols += ["temperature", "precipitation"]

    df = df.dropna(subset=feature_cols + ["y"]).reset_index(drop=True)

    return df, feature_cols


if __name__ == "__main__":
    # Selbsttest mit LEICHT UNREGELMAESSIGEN Zeitstempeln (wie in der echten DB:
    # z.B. 13:10, 13:25, 13:40, 13:54, 14:15 statt exakt alle 15 Min)
    rng = pd.date_range("2026-01-01", periods=2000, freq="15min")
    jitter = pd.to_timedelta(np.random.randint(-3, 4, size=2000), unit="min")
    rng_jittered = rng + jitter

    demo = pd.DataFrame({
        "parkhaus_id": "baselparkhausaeschen",
        "ts": rng_jittered,
        "occupied_spots": (np.sin(np.arange(2000) / 96 * 2 * np.pi) * 50 + 150).astype(int),
        "total_spots": 300,
    })
    features, cols = build_feature_matrix(demo)
    print(f"{len(demo)} rohe Zeilen (unregelmaessig) -> {len(features)} nutzbare Feature-Zeilen")
    print(features[cols + ["y"]].head())
