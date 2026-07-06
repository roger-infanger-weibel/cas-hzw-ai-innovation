"""
Lädt trainierte Modelle (ein Modell pro Parkhaus) und erzeugt Prognosen.

Multi-Step-Vorgehen: Da wir Lag-Features nutzen (z.B. lag_15min), muss die
Prognose für t+2 den vorhergesagten Wert von t+1 als neuen Lag verwenden
("rekursive Prognose"). Das ist Standard bei Lag-Feature-Modellen und
funktioniert für Horizonte von einigen Stunden sehr gut; der Prognosefehler
akkumuliert sich aber mit der Anzahl Schritte - deshalb wird der Horizont
bewusst begrenzt (siehe MAX_HORIZON_STEPS).
"""
import os
from datetime import timedelta

import joblib
import pandas as pd

from data_pipeline.features import (
    add_calendar_features,
    fetch_weather_features,
    fetch_weather_forecast,
    regularize_timeseries,
)
from data_pipeline.db import fetch_raw_occupancy

MODEL_DIR = os.getenv("MODEL_DIR", "./models")
MODEL_NAME = os.getenv("MODEL_NAME", "lightgbm_occupancy")
MAX_HORIZON_STEPS = 32  # 32 * 15min = 8 Stunden Prognosehorizont, Obergrenze für Genauigkeit
WEATHER_LAT = float(os.getenv("WEATHER_LAT", "47.3769"))
WEATHER_LON = float(os.getenv("WEATHER_LON", "8.5417"))
WEATHER_FEATURES = ["temperature", "precipitation"]

_model_cache: dict[str, dict] = {}


def load_model(parkhaus_id: str) -> dict:
    if parkhaus_id not in _model_cache:
        path = os.path.join(MODEL_DIR, f"{MODEL_NAME}_{parkhaus_id}.joblib")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Kein trainiertes Modell für '{parkhaus_id}' gefunden ({path})")
        _model_cache[parkhaus_id] = joblib.load(path)
    return _model_cache[parkhaus_id]


def _build_inference_row(
    history: pd.DataFrame,
    target_ts: pd.Timestamp,
    total_spots: int,
    weather_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Baut die Feature-Zeile für genau einen zukünftigen Zeitpunkt aus der (ggf. bereits
    um vorherige Prognosen erweiterten) Historie."""
    row = pd.DataFrame({"parkhaus_id": [history["parkhaus_id"].iloc[0]], "ts": [target_ts]})
    row = add_calendar_features(row)

    def get_lag(steps_back_minutes: int):
        t = target_ts - timedelta(minutes=steps_back_minutes)
        match = history.loc[history["ts"] == t, "occupied_spots"]
        return match.iloc[0] if not match.empty else None

    row["lag_15min"] = get_lag(15)
    row["lag_1h"] = get_lag(60)
    row["lag_4h"] = get_lag(240)
    row["lag_24h"] = get_lag(24 * 60)
    row["lag_7d"] = get_lag(7 * 24 * 60)

    recent = history[history["ts"] < target_ts].tail(96)
    row["roll_mean_4h"] = recent.tail(16)["occupied_spots"].mean()
    row["roll_std_4h"] = recent.tail(16)["occupied_spots"].std()
    row["roll_mean_24h"] = recent["occupied_spots"].mean()

    row["total_spots"] = total_spots

    if weather_df is not None:
        def get_weather(feature_name: str):
            match = weather_df.loc[weather_df["ts"] == target_ts, feature_name]
            if not match.empty:
                return match.iloc[0]
            fallback = weather_df[weather_df["ts"] < target_ts].tail(1)[feature_name]
            return fallback.iloc[0] if not fallback.empty else None

        row["temperature"] = get_weather("temperature")
        row["precipitation"] = get_weather("precipitation")

    return row


def _fetch_weather_for_forecast(start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DataFrame:
    start_date = start_ts.strftime("%Y-%m-%d")
    end_date = end_ts.strftime("%Y-%m-%d")
    weather_df = fetch_weather_forecast(WEATHER_LAT, WEATHER_LON, start_date, end_date)
    weather_df["ts"] = pd.to_datetime(weather_df["ts"])
    return weather_df


def forecast(parkhaus_id: str, horizon_minutes: int = 240) -> list[dict]:
    """Erzeugt eine rekursive Multi-Step-Prognose für die nächsten `horizon_minutes`."""
    bundle = load_model(parkhaus_id)
    model, feature_cols = bundle["model"], bundle["feature_cols"]

    # genug Historie laden, um alle Lags (bis 7 Tage) berechnen zu können.
    # since= grenzt die Query auf ~9 Tage ein (Performance bei 1.3 Mio+ Zeilen in pls_fetch_current)
    since = (pd.Timestamp.utcnow() - timedelta(days=9)).strftime("%Y-%m-%d")
    raw_history = fetch_raw_occupancy(parkhaus_id=parkhaus_id, since=since)
    if raw_history.empty:
        raise ValueError(f"Keine historischen Daten für '{parkhaus_id}' verfügbar.")

    # unregelmaessige fetch_ts auf 15-Min-Raster bringen, wie beim Training
    history = regularize_timeseries(raw_history)
    history = history.dropna(subset=["occupied_spots", "total_spots"])

    total_spots = int(history["total_spots"].iloc[-1])
    last_ts = history["ts"].iloc[-1]

    n_steps = min(horizon_minutes // 15, MAX_HORIZON_STEPS)
    results = []

    working_history = history[["parkhaus_id", "ts", "occupied_spots", "total_spots"]].copy()
    weather_df = None
    if any(c in WEATHER_FEATURES for c in feature_cols):
        try:
            weather_df = _fetch_weather_for_forecast(last_ts + timedelta(minutes=15), last_ts + timedelta(minutes=15 * n_steps))
        except Exception as e:
            # Forecast should still work without weather if API request fails.
            print(f"Warnung: Wetterprognose fehlgeschlagen ({e}), berechne Prognose ohne Wetter.")
            weather_df = None

    for step in range(1, n_steps + 1):
        target_ts = last_ts + timedelta(minutes=15 * step)
        row = _build_inference_row(working_history, target_ts, total_spots, weather_df=weather_df)

        missing = [c for c in feature_cols if c not in row.columns or row[c].isna().any()]
        if missing:
            # zu wenig Historie oder fehlende Wetterdaten -> Prognose an dieser Stelle abbrechen
            break

        pred = float(model.predict(row[feature_cols])[0])
        pred = max(0.0, min(pred, total_spots))

        results.append({
            "ts": target_ts,
            "predicted_occupied_spots": round(pred, 1),
            "predicted_free_spots": round(total_spots - pred, 1),
            "total_spots": total_spots,
        })

        # vorhergesagten Wert als "Ist-Wert" anhängen, damit der nächste Schritt
        # ihn als Lag nutzen kann (rekursive Prognose)
        working_history = pd.concat([
            working_history,
            pd.DataFrame([{
                "parkhaus_id": parkhaus_id, "ts": target_ts,
                "occupied_spots": pred, "total_spots": total_spots,
            }])
        ], ignore_index=True)

    return results
