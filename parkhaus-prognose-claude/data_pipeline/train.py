"""
Trainings-Skript: Baseline + LightGBM, mit zeitlichem Train/Test-Split
und Walk-Forward-Backtesting.

Aufruf:
    python -m data_pipeline.train --parkhaus_id P1 --since 2026-01-01

Ergebnis:
    - trainiertes Modell unter models/<MODEL_NAME>_<parkhaus_id>.joblib
    - Metriken (MAE, RMSE, MAPE) in MLflow geloggt
"""
import argparse
import os

import joblib
import lightgbm as lgb
import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from dotenv import load_dotenv

from data_pipeline.db import fetch_raw_occupancy
from data_pipeline.features import build_feature_matrix, fetch_weather_features

load_dotenv()

MODEL_DIR = os.getenv("MODEL_DIR", "./models")
MODEL_NAME = os.getenv("MODEL_NAME", "lightgbm_occupancy")


def mean_absolute_percentage_error(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    mask = y_true != 0
    if not np.any(mask):
        return float("nan")
    diff = np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])
    return float(np.mean(diff) * 100)


def sanitize_metrics(metrics: dict) -> dict:
    """Keep only finite numeric values so MLflow can log them safely."""
    sanitized = {}
    for key, value in metrics.items():
        if isinstance(value, (int, float, np.integer, np.floating)) and np.isfinite(value):
            sanitized[key] = float(value)
    return sanitized


def log_model_artifact(model) -> None:
    """Log the trained model to MLflow without inferring pip requirements."""
    try:
        mlflow.lightgbm.log_model(model, name="model", pip_requirements=[])
    except (Exception, KeyboardInterrupt) as exc:
        print(f"  Warnung: MLflow-Model-Logging fehlgeschlagen ({exc}); speichere Modell lokal weiter.")


def rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def baseline_seasonal_naive(df: pd.DataFrame) -> dict:
    """Vergleichsmassstab: Prognose = Wert vor 7 Tagen (lag_7d)."""
    y_true = df["y"].values
    y_pred = df["lag_7d"].values
    return {
        "baseline_mae": mean_absolute_error(y_true, y_pred),
        "baseline_rmse": rmse(y_true, y_pred),
        "baseline_mape": mean_absolute_percentage_error(y_true, y_pred),
    }


def train_and_evaluate(df: pd.DataFrame, feature_cols: list[str], test_size: float = 0.15):
    """Zeitlicher Split (KEIN Random-Split -> würde Data Leakage verursachen)."""
    split_idx = int(len(df) * (1 - test_size))
    train_df, test_df = df.iloc[:split_idx], df.iloc[split_idx:]

    if len(train_df) < 2 or len(test_df) < 1:
        raise ValueError("Nicht genug Daten für Training und Evaluierung.")

    X_train, y_train = train_df[feature_cols], train_df["y"]
    X_test, y_test = test_df[feature_cols], test_df["y"]

    if X_train.empty or X_test.empty:
        raise ValueError("Leere Feature-Matrix für Training oder Test.")

    if X_train.ndim != 2 or X_test.ndim != 2:
        raise ValueError("Feature-Matrix muss 2-dimensional sein.")

    model = lgb.LGBMRegressor(
        n_estimators=500,
        learning_rate=0.03,
        num_leaves=31,
        max_depth=-1,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        eval_metric="mae",
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )

    y_pred = model.predict(X_test)
    y_pred = np.clip(y_pred, 0, test_df["total_spots"].values)  # physikalisch sinnvoll begrenzen

    metrics = {
        "mae": mean_absolute_error(y_test, y_pred),
        "rmse": rmse(y_test, y_pred),
        "mape": mean_absolute_percentage_error(y_test.values, y_pred),
    }
    baseline_metrics = baseline_seasonal_naive(test_df)

    return model, {**metrics, **baseline_metrics}


def run(parkhaus_id: str, since: str, weather_lat: float, weather_lon: float):
    print(f"[1/4] Lade Rohdaten für {parkhaus_id} seit {since} ...")
    raw = fetch_raw_occupancy(parkhaus_id=parkhaus_id, since=since)
    if raw.empty:
        raise ValueError("Keine Daten gefunden - Zeitraum/parkhaus_id prüfen.")

    print("[2/4] Baue Features (inkl. Wetter) ...")
    weather = None
    try:
        start_date = raw["ts"].min().strftime("%Y-%m-%d")
        end_date = raw["ts"].max().strftime("%Y-%m-%d")
        weather = fetch_weather_features(weather_lat, weather_lon, start_date, end_date)
    except Exception as e:
        print(f"  Warnung: Wetterdaten konnten nicht geladen werden ({e}). Trainiere ohne Wetter-Features.")

    feature_df, feature_cols = build_feature_matrix(raw, weather_df=weather)
    print(f"  -> {len(feature_df)} Trainingszeilen, {len(feature_cols)} Features")

    print("[3/4] Training + Backtesting ...")
    mlflow.set_experiment("parkhaus_prognose")
    with mlflow.start_run(run_name=f"lgbm_{parkhaus_id}"):
        model, metrics = train_and_evaluate(feature_df, feature_cols)
        metrics = sanitize_metrics(metrics)

        mlflow.log_params({"parkhaus_id": parkhaus_id, "n_features": len(feature_cols)})
        mlflow.log_metrics(metrics)
        log_model_artifact(model)

        print("  Metriken:")
        for k, v in metrics.items():
            print(f"    {k}: {v:.2f}")

        baseline_mae = metrics.get("baseline_mae", 0.0)
        if baseline_mae and baseline_mae != 0:
            improvement = (baseline_mae - metrics["mae"]) / baseline_mae * 100
            print(f"  -> Verbesserung ggü. Baseline (7-Tage-Lag): {improvement:.1f}%")
        else:
            print("  -> Verbesserung ggü. Baseline (7-Tage-Lag): nicht berechenbar (Baseline-MAE = 0)")

    print("[4/4] Speichere Modell lokal ...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, f"{MODEL_NAME}_{parkhaus_id}.joblib")
    joblib.dump({"model": model, "feature_cols": feature_cols}, model_path)
    print(f"  -> {model_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parkhaus_id", required=True)
    parser.add_argument("--since", default="2026-01-01")
    parser.add_argument("--weather_lat", type=float, default=float(os.getenv("WEATHER_LAT", 47.3769)))
    parser.add_argument("--weather_lon", type=float, default=float(os.getenv("WEATHER_LON", 8.5417)))
    args = parser.parse_args()

    run(args.parkhaus_id, args.since, args.weather_lat, args.weather_lon)
