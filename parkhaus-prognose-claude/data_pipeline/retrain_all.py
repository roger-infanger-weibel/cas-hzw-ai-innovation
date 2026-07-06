"""
Trainiert das Modell fuer ALLE Parkhaeuser neu. Wird taeglich vom
systemd-Timer (deploy/retrain.timer) aufgerufen.

Einzelnes Parkhaus manuell trainieren: python -m data_pipeline.train --parkhaus_id ...
"""
import os
import traceback

from dotenv import load_dotenv

from data_pipeline.db import list_parkhaeuser
from data_pipeline.train import run
from datetime import datetime

load_dotenv()

SINCE = os.getenv("TRAIN_SINCE", "2026-01-16")
WEATHER_LAT = float(os.getenv("WEATHER_LAT", 47.3769))
WEATHER_LON = float(os.getenv("WEATHER_LON", 8.5417))


def main():
    parkhaeuser = list_parkhaeuser()
    print(f"Retraining für {len(parkhaeuser)} Parkhäuser: {parkhaeuser}")

    failures = []
    skipped = []
    total = len(parkhaeuser)
    for index, pid in enumerate(parkhaeuser, start=1):
        progress_pct = int((index / total) * 100) if total else 100
        print(f"\n=== {pid} ({progress_pct}%) ===")
        try:
            run(pid, SINCE, WEATHER_LAT, WEATHER_LON)
        except ValueError as e:
            if "Nicht genug Daten" in str(e) or "Leere Feature" in str(e) or "2-dimensional" in str(e):
                print(f"  Übersprungen bei {pid}: {e}")
                skipped.append(pid)
            else:
                print(f"  FEHLER bei {pid}: {e}")
                traceback.print_exc()
                failures.append(pid)
        except Exception as e:
            print(f"  FEHLER bei {pid}: {e}")
            traceback.print_exc()
            failures.append(pid)

    if failures:
        print(f"\nRetraining abgeschlossen mit Fehlern bei: {failures}")
    else:
        print("\nRetraining für alle Parkhäuser erfolgreich abgeschlossen.")

    if skipped:
        print(f"Übersprungen ({len(skipped)}): {skipped}")


if __name__ == "__main__":
    print(">Start:",datetime.now())   
    main()
    print(">Ended:",datetime.now())   
