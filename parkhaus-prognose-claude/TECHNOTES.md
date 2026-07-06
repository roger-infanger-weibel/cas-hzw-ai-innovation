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

#python -m venv .venv && source .venv/bin/activate  
# dies oben hat nicht funktioniert, aber dies:
 .venv\Scripts\Activate.bat

# mit "pip --version" kann geprüft werden, ob geklappt hat
# wenn .venv Ordner erscheint, hat es geklappt

pip install -r requirements.txt
```

## 1. Erstes Modell trainieren

```bash
# einzelnes Parkhaus (ID aus der DB, z.B. "Löwencenter)
python -m data_pipeline.train --parkhaus_id NP12 --since 2026-01-16

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

## 3. Wetterdaten: Wie genau sie geholt werden

Die Wetterdaten kommen nicht aus der Parkhaus-Datenbank, sondern von Open-Meteo.

### 3.1 Quelle und Ablauf
- Die Trainings- und Inferenzpipeline verwendet die Funktion `fetch_weather_features(...)` aus `data_pipeline/features.py`.
- Für jedes Parkhaus werden die Koordinaten aus den Umgebungsvariablen `WEATHER_LAT` und `WEATHER_LON` verwendet.
- Es wird ein HTTP-Request an die Open-Meteo-Archive-API geschickt:
  - Endpoint: `https://archive-api.open-meteo.com/v1/archive`
  - Parameter: `latitude`, `longitude`, `start_date`, `end_date`, `hourly=temperature_2m,precipitation`, `timezone=Europe/Zurich`
- Die Antwort enthält historische stündliche Werte für Temperatur und Niederschlag.

### 3.2 Umwandlung ins Modell-Raster
- Die Wetterwerte werden in ein DataFrame überführt.
- Danach werden sie auf das gleiche 15-Minuten-Raster wie die Parkhausdaten hochgerechnet (`resample("15min").ffill()`).
- Anschließend werden die Wetterwerte mit den Parkhauszeitreihen per `ts` gemerged.
- Fehlen einzelne Werte, werden sie mit `ffill()` nachgezogen.

### 3.3 Warum das so gemacht wird
- Die Belegungsdaten liegen in 15-Minuten-Schritten vor.
- Die Wetterdaten kommen stündlich, deshalb muss ein konsistentes Raster hergestellt werden.
- Für die Trainings- und Inferenzpipeline ist es wichtig, dass beide Quellen dieselbe Zeitbasis haben.

> Falls der Wetter-Request fehlschlägt, wird das Training nicht abgebrochen. In diesem Fall wird ohne Wetterfeatures weitertrainiert.

## 4. LightGBM-Setup und Training im Detail

Die Modellierung wird pro Parkhaus separat durchgeführt. Das heißt: Für jedes Parkhaus gibt es ein eigenes Modell, keine globale Modell-Datei für alle Standorte.

### 4.1 Feature-Erzeugung
Vor dem Training baut die Pipeline ein Feature-Set auf. Dazu gehören:
- Kalenderfeatures: Stunde, Wochentag, Monat, Wochenende, Feiertag
- Zyklische Kodierung für Uhrzeit und Wochentag (`sin`/`cos`)
- Lags: Werte aus der Vergangenheit in 15 Minuten, 1 Stunde, 4 Stunden, 24 Stunden und 7 Tagen
- Rolling-Statistiken über die letzten 4 Stunden und 24 Stunden
- Optional: Wetterfeatures wie Temperatur und Niederschlag
- Die Zielvariable heißt `y` und entspricht der belegten Anzahl an Stellplätzen

Die eigentliche Feature-Matrix wird in `data_pipeline/features.py` erzeugt.

### 4.2 Train/Test-Aufteilung
- Es wird kein zufälliger Split verwendet, sondern ein zeitlicher Split.
- Das Modell wird auf den älteren Daten trainiert und auf den neueren Daten evaluiert.
- Das verhindert Datenleckage, weil zukünftige Daten nicht in die Trainingsphase einbezogen werden.
- Standardwert: `test_size = 0.15`

### 4.3 Modelltyp und wichtigste Parameter
Das Modell ist ein `lightgbm.LGBMRegressor` mit diesen Central-Parametern:

- `n_estimators=500`: maximale Anzahl der Bäume
- `learning_rate=0.03`: Schrittweite pro Baum, eher konservativ
- `num_leaves=31`: Komplexität pro Baum, hilft gegen zu starke Überanpassung
- `max_depth=-1`: keine harte Baumtiefe, LightGBM entscheidet selbst
- `min_child_samples=20`: Mindestanzahl an Samples pro Blatt
- `subsample=0.8`: Teilmenge der Samples pro Baum
- `colsample_bytree=0.8`: Teilmenge der Features pro Baum
- `random_state=42`: reproduzierbare Ergebnisse
- `verbosity=-1`: reduziert die Konsolenausgabe

Zusätzlich wird Early Stopping verwendet:
- `early_stopping(30, verbose=False)`
- Wenn sich die Validierungs-Metrik über 30 Iterationen nicht verbessert, wird das Training abgebrochen.

### 4.4 Warum gerade diese Konfiguration?
- LightGBM ist schnell und robust für tabellarische Zeitreihen.
- Die gewählten Werte sind ein guter Mittelweg zwischen Genauigkeit und Generalisierung.
- Die Regularisierung über `num_leaves`, `min_child_samples`, `subsample` und `colsample_bytree` hilft, die Modelle nicht zu überfitten.

## 5. Warum die Baseline mit 7 Tagen gewählt wurde

Als Vergleichsmodell wird ein einfaches saisonales Naive-Modell verwendet:
- Die Prognose für den nächsten Zeitpunkt ist gleich dem Wert vor genau 7 Tagen.
- Das ist ein sinnvoller Baseline-Check, weil Parkhausbelegung oft eine starke Wochenzyklus-Struktur hat.
- Viele Parkhäuser zeigen ähnliche Muster an denselben Wochentagen und zu denselben Tageszeiten.

### 5.1 Warum gerade 7 Tage?
- Ein 7-Tage-Lag reflektiert typische Wochenmuster.
- Das ist oft robuster als ein 1-Tages-Lag, weil der Wochenrhythmus stärker sichtbar wird.
- Es liefert eine einfache, verständliche und starke Benchmark für die Frage:
  "Ist unser ML-Modell wirklich besser als ein sehr einfacher Wiederholungsansatz?"

### 5.2 Wie die Verbesserung berechnet wird
Die Ausgabe `Verbesserung ggü. Baseline (7-Tage-Lag)` ist eine relative Verbesserung gegenüber dem Naive-7-Tage-Modell.

Beispiel:
- Wenn das ML-Modell eine MAE von 3.0 hat und die Baseline 10.0, dann ist die Verbesserung deutlich.
- Wenn die Baseline selbst schon sehr gut ist oder bei manchen Parkhäusern fast null, kann die Verbesserung nicht sinnvoll berechnet werden.

## 6. Quickstart für neue Entwickler

### 6.1 Lokales Setup
```bash
# im Projektverzeichnis
.venv\Scripts\Activate.bat
pip install -r requirements.txt
```

Falls noch keine `.env` existiert, eine lokale Variante anlegen und die wichtigsten Werte setzen:
```bash
DB_HOST=...
DB_USER=...
DB_PASSWORD=...
WEATHER_LAT=47.3769
WEATHER_LON=8.5417
TRAIN_SINCE=2026-01-16
```

### 6.2 Erstes Training starten
```bash
# ein einzelnes Parkhaus
python -m data_pipeline.train --parkhaus_id NP12 --since 2026-01-16

# alle Parkhäuser
python -m data_pipeline.retrain_all
```

### 6.3 Wichtige Dateien
- `data_pipeline/db.py` – Daten aus der MySQL/MariaDB holen
- `data_pipeline/features.py` – Zeitraster, Lags, Wetterfeatures, Zielvariable
- `data_pipeline/train.py` – Training, Evaluation und Modell-Logging
- `data_pipeline/retrain_all.py` – Batch-Retraining über alle Parkhäuser
- `api/inference.py` – Modell-Laden und Vorhersage für zukünftige Zeitpunkte
- `frontend/app.py` – Streamlit-Frontend

### 6.4 Schnell prüfen, ob alles läuft
```bash
# Training testen
python -m data_pipeline.train --parkhaus_id NP12 --since 2026-01-16

# API lokal starten
uvicorn api.main:app --reload --port 8000

# Frontend lokal starten
streamlit run frontend/app.py
```

## 7. Lokal testen (ohne Docker)

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

