# Parkhaus-Prognose

KI-gestützte Belegungsprognose für Parkhäuser, basierend auf den in
`ph_fetch.pls_fetch_current` gesammelten 15-Minuten-Messwerten.

## 1. Voraussetzungen

- Linux-Server mit Python 3.12, Docker + Docker Compose
- Lesezugriff auf die bestehende MySQL/MariaDB `ph_fetch`

**Empfehlung:** eigenen read-only DB-User für die App anlegen, statt den
bestehenden Fetch-User zu verwenden:

```sql
CREATE USER 'parkhaus_reader'@'%' IDENTIFIED BY 'STARKES_PASSWORT';
GRANT SELECT ON ph_fetch.* TO 'parkhaus_reader'@'%';
FLUSH PRIVILEGES;
```

## 2. Setup

```bash
git clone <repo> parkhaus-prognose && cd parkhaus-prognose
cp .env.example .env
# .env ausfüllen: DB_HOST, DB_USER, DB_PASSWORD, WEATHER_LAT/LON (Standort der Parkhäuser)

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Erstes Modell trainieren

```bash
# einzelnes Parkhaus (ID aus der DB, z.B. "baselparkhausaeschen")
python -m data_pipeline.train --parkhaus_id baselparkhausaeschen --since 2026-01-16

# alle Parkhäuser auf einmal
python -m data_pipeline.retrain_all
```

Ergebnis landet in `models/lightgbm_occupancy_<parkhaus_id>.joblib`.
Metriken (MAE/RMSE/MAPE, Vergleich gegen Baseline) werden in der Konsole
ausgegeben und optional in MLflow geloggt (`mlflow ui` zum Ansehen).

**Wichtig zur Interpretation:** Die Konsolenausgabe zeigt u.a.
`Verbesserung ggü. Baseline (7-Tage-Lag)`. Ist die Verbesserung gering oder
negativ, deutet das auf zu wenig Historie oder ein sehr unregelmässiges
Belegungsmuster für dieses Parkhaus hin - dann lohnt sich ein Blick in die
Rohdaten, bevor man dem Modell vertraut.

## 4. Lokal testen (ohne Docker)

```bash
# Terminal 1 - API
uvicorn api.main:app --reload --port 8000

# Terminal 2 - Frontend
streamlit run frontend/app.py
```

Dashboard: http://localhost:8501, API-Doku: http://localhost:8000/docs

## 5. Produktiv-Deployment (Docker Compose)

```bash
docker compose build
docker compose up -d
```

- Frontend: Port 8501
- API: Port 8000 (Swagger-UI unter `/docs`)
- MLflow: Port 5000

Davor `nginx/parkhaus.conf` nach `/etc/nginx/sites-available/`, Domain
anpassen, dann:

```bash
sudo ln -s /etc/nginx/sites-available/parkhaus.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d parkhaus.deine-domain.ch   # TLS
```

## 6. Automatisches Retraining einrichten

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

## 7. Bekannte Einschränkungen (bewusste Design-Entscheidungen)

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

## 8. Projektstruktur

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
