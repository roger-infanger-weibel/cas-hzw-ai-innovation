## 6. So funktioniert die Forecast-Prognose

Die aktuelle Prognose läuft in zwei Schritten:

1. Ein eigenes LightGBM-Modell wird pro Parkhaus trainiert.
2. Für jeden zukünftigen 15-Minuten-Schritt wird aus der bisherigen Historie ein Feature-Set gebaut, das Modell aufgerufen und der vorhergesagte Wert anschließend als Basis für den nächsten Schritt verwendet.

Das ist eine rekursive Multi-Step-Prognose. Sie funktioniert gut für kurze bis mittlere Horizonte, ist aber nicht unbegrenzt genau: Je weiter man in die Zukunft schaut, desto mehr akkumulieren sich Fehler.

Wichtige Einschränkungen:

- Der Prognosehorizont ist bewusst auf etwa 8 Stunden begrenzt.
- Ungenaues oder unregelmäßiges Zeitraster wird auf 15-Minuten-Schritte regularisiert, aber große Lücken werden nicht künstlich aufgefüllt.
- Für jedes Parkhaus wird ein eigenes Modell verwendet; es gibt aktuell kein gemeinsames Modell über mehrere Standorte hinweg.
- Die Prognose ist eine Punktvorhersage, nicht eine Wahrscheinlichkeitsverteilung mit Unsicherheitsintervallen.

## 7. Automatisches Retraining einrichten

```bash
sudo cp deploy/retrain.service deploy/retrain.timer /etc/systemd/system/
# Pfade in retrain.service anpassen (WorkingDirectory, .venv-Pfad, User)
sudo systemctl daemon-reload
sudo systemctl enable --now retrain.timer
sudo systemctl list-timers | grep retrain   # zur Kontrolle
```

Standardmässig läuft das Retraining täglich um 03:00 Uhr für alle
Parkhäuser. Modelle werden dabei überschrieben - `models/` daher regelmässig
sichern, falls ein Rollback auf eine ältere Version wichtig sein könnte.

## 8. Bekannte Einschränkungen (bewusste Design-Entscheidungen)

- **Zeitstempel unregelmässig:** `fetch_ts` liegt nicht exakt im 15-Min-Raster
  (Netzwerk-Jitter, gelegentliche Ausfälle). `data_pipeline/features.py::regularize_timeseries`
  bucketet auf ein exaktes Raster; Lücken >30 Min werden NICHT künstlich
  aufgefüllt, sondern führen zu fehlenden Trainingszeilen an der Stelle.
- **Prognosehorizont auf 8h begrenzt** (`MAX_HORIZON_STEPS` in `api/inference.py`):
  Die Prognose ist rekursiv (nutzt eigene Vorhersagen als Lags für die
  nächsten Schritte), der Fehler akkumuliert sich mit der Schrittzahl -
  darüber hinaus wird die Prognose unzuverlässig.
- **Pro Parkhaus ein eigenes Modell.** Bei sehr vielen Standorten mit wenig
  individueller Historie wäre ein gemeinsames Modell über alle Standorte
  (mit `parkhaus_id` als Feature) eine sinnvolle spätere Optimierung
  (Cross-Learning zwischen ähnlichen Parkhäusern).
- **LLM-Chat-Layer (`api/routers/chat.py`) ist standardmässig deaktiviert**
  (`ENABLE_LLM_CHAT=false`) und rein optional - die Kernprognose funktioniert
  unabhängig davon vollständig ohne LLM.

## 9. Projektstruktur

```
data_pipeline/
  db.py              MySQL-Anbindung an ph_fetch
  features.py         Feature Engineering + Zeitraster-Regularisierung
  train.py             Training + Backtesting für ein Parkhaus
  retrain_all.py       Training für alle Parkhäuser (vom Timer aufgerufen)
api/
  main.py              FastAPI App
  inference.py          Modell laden + rekursive Multi-Step-Prognose
  schemas.py            Pydantic-Modelle
  routers/
    forecast.py          GET /parkhaus/{id}/prognose
    history.py            GET /parkhaus/{id}/aktuell, /verlauf
    chat.py                optionale LLM-Chat-Schicht
frontend/
  app.py               Streamlit-Dashboard (MVP)
deploy/
  retrain.service|.timer  systemd-Einheiten fürs Retraining
nginx/
  parkhaus.conf         Reverse-Proxy-Konfiguration
docker-compose.yml
```
