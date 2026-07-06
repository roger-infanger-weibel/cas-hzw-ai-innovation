# Forecast-Modul: Wie die Prognose entsteht und welche Grenzen es gibt

Dieses Dokument beschreibt die aktuelle Forecast-Logik des Projekts technisch und nachvollziehbar. Es konzentriert sich auf den tatsächlichen Ablauf im Code und nicht auf eine idealisierte Vorstellung.

## 1. Kurz gesagt

Die Prognose funktioniert aktuell als ein pro Parkhaus trainiertes LightGBM-Modell. Für jeden zukünftigen 15-Minuten-Schritt wird ein Feature-Set gebaut, das Modell aufgerufen und der vorhergesagte Belegungswert als Eingabe für den nächsten Schritt verwendet. Dadurch entsteht eine rekursive Multi-Step-Prognose.

## 2. Datenquelle

Die Rohdaten kommen aus der Datenbanktabelle `pls_fetch_current` über das Modul `data_pipeline/db.py`.

Dort werden folgende Spalten verwendet:

- `id` als Parkhaus-ID
- `fetch_ts` als Zeitstempel
- `total` als Gesamtstellplätze
- `free` als freie Stellplätze

Aus diesen Werten wird intern berechnet:

- `occupied_spots = total - free`
- `total_spots = total`

Die Abfrage ist pro Parkhaus und pro Zeitraum möglich. Für die Inferenz wird in der Praxis nur ein begrenzter Historie-Zeitraum geladen.

## 3. Wie die Features aufgebaut werden

Die eigentliche Feature-Logik sitzt in `data_pipeline/features.py`.

### 3.1 Zeitreihen regularisieren

Die Rohdaten liegen nicht exakt im 15-Minuten-Raster vor. Das ist ein realistischer Datenfehler aus der Quelle (z. B. leichte Abweichungen, Ausfälle oder verspätete Updates).

Deshalb wird die Zeitreihe pro Parkhaus auf ein exaktes 15-Minuten-Raster gebracht:

- Die Zeitstempel werden auf das nächste 15-Minuten-Intervall gebucketet.
- Kleine Lücken werden vorwärts gefüllt.
- Größere Lücken bleiben leer und werden später nicht künstlich aufgeblasen.

Wichtige Konsequenz:

- Lücken von mehr als 30 Minuten führen nicht zu künstlich erzeugten Werten.
- Stattdessen entstehen fehlende Feature-Zeilen, die für das Training bzw. die Inferenz nicht verwendet werden.

### 3.2 Kalender-Features

Für jeden Timestamp werden zusätzliche Merkmale erzeugt:

- Stunde des Tages
- Wochentag
- Monat
- Wochenende oder nicht
- Feiertag oder nicht
- zyklische Kodierung für Uhrzeit und Wochentag

Diese Features helfen dem Modell, typische Muster wie Tageszeiten, Wochenrhythmen und Feiertage zu erkennen.

### 3.3 Lag-Features und Rolling-Features

Das Modell nutzt historische Zustände als Features:

- `lag_15min`
- `lag_1h`
- `lag_4h`
- `lag_24h`
- `lag_7d`

Zusätzlich werden Rolling-Statistiken verwendet:

- Mittelwert der letzten 4 Stunden
- Standardabweichung der letzten 4 Stunden
- Mittelwert der letzten 24 Stunden

Diese Features sind wichtig, weil die Belegung stark von vergangenen Zuständen abhängt.

## 4. Wie das Modell trainiert wird

Das Training läuft über `data_pipeline/train.py`.

### 4.1 Trainingsstrategie

Für jedes Parkhaus wird ein eigenes Modell trainiert.

Das Training verwendet:

- keine zufällige Aufteilung der Daten
- sondern einen zeitlichen Split

Das ist wichtig, weil ein Random-Split Datenleckage erzeugen würde. Die Prognose soll in der Zukunft funktionieren, nicht mit Wissen aus der Zukunft.

### 4.2 Modelltyp

Aktuell wird ein LightGBM-Regressor verwendet.

Die Trainingsdaten enthalten:

- die oben beschriebenen Features
- das Ziel `y = occupied_spots`

### 4.3 Physikalische Begrenzung

Während des Trainings werden Vorhersagen auf den realistischen Bereich begrenzt:

- Minimum: 0
- Maximum: `total_spots`

Damit kann das Modell keine negativen Werte oder mehr belegte Plätze vorhersagen, als das Parkhaus insgesamt hat.

## 5. Wie die Forecast-Inferenz funktioniert

Die eigentliche Prognose wird in `api/inference.py` erzeugt.

### 5.1 Modell laden

Für das angefragte Parkhaus wird das zugehörige Modell aus `models/` geladen.

Beispiel:

- `lightgbm_occupancy_<parkhaus_id>.joblib`

Wenn kein Modell vorhanden ist, wird die Prognose abgebrochen.

### 5.2 Historie laden

Für die Prognose wird eine ausreichende Historie geladen, damit alle Lag-Features berechnet werden können.

Aktuell wird ungefähr ein Zeitraum von 9 Tagen verwendet.

### 5.3 Zeitreihen regularisieren

Wie beim Training wird die Historie ebenfalls auf das 15-Minuten-Raster gebracht.

### 5.4 Rekursive Multi-Step-Prognose

Die Prognose läuft schrittweise:

1. Der nächste Zeitpunkt wird berechnet (z. B. +15 Minuten).
2. Aus der bisherigen Historie wird eine Feature-Zeile für diesen Zeitpunkt gebaut.
3. Das Modell sagt die belegten Plätze voraus.
4. Der Wert wird auf den realistischen Bereich begrenzt.
5. Der vorhergesagte Wert wird in die Historie übernommen.
6. Der nächste Schritt verwendet diesen neuen Wert als Grundlage für seine Lags.

Das ist der entscheidende Punkt: Die Prognose ist rekursiv.

Das bedeutet:

- Schritt 2 nutzt die Vorhersage aus Schritt 1
- Schritt 3 nutzt die Vorhersage aus Schritt 2
- usw.

Dadurch werden Fehler mit jeder weiteren Stufe akkumuliert.

### 5.5 Ausgabe der Prognose

Für jeden prognostizierten Zeitpunkt werden folgende Werte ausgegeben:

- `ts` = Zeitpunkt
- `predicted_occupied_spots`
- `predicted_free_spots`
- `total_spots`

Die freien Plätze werden dabei als:

- `total_spots - predicted_occupied_spots`

berechnet.

## 6. Konkrete Einschränkungen der aktuellen Lösung

Die aktuelle Forecast-Logik ist sinnvoll, aber bewusst begrenzt. Diese Einschränkungen sind im Code und im Verhalten direkt sichtbar.

### 6.1 Prognosehorizont ist begrenzt

Die maximale Anzahl an Schritten ist aktuell auf 32 begrenzt.

Das entspricht:

- $32 \times 15\text{ Minuten} = 8\text{ Stunden}$

Grund: Die rekursive Prognose wird mit zunehmender Schrittzahl unzuverlässiger, weil der Fehler akkumuliert wird.

### 6.2 Die Prognose ist nur so gut wie die Historie

Wenn zu wenig Daten vorhanden sind, kann die Prognose nicht zuverlässig gebildet werden.

Das betrifft vor allem:

- neue Parkhäuser
- kurze Historie
- lange Datenlücken
- fehlende oder unvollständige Sensorwerte

### 6.3 Lücken über 30 Minuten werden nicht künstlich aufgefüllt

Das Modell arbeitet mit einem sauberen 15-Minuten-Raster.

Wenn es große Lücken gibt, werden diese nicht „erfunden“. Stattdessen entstehen fehlende Zeilen, die die Qualität des Trainings und der Inferenz verschlechtern.

### 6.4 Ein eigenes Modell pro Parkhaus

Jedes Parkhaus hat sein eigenes Modell.

Das hat Vorteile:

- individuelle Muster können gut gelernt werden

Aber es hat auch Nachteile:

- für Parkhäuser mit wenig Historie ist das Modell schwächer
- es gibt kein gemeinsames Lernen über ähnliche Parkhäuser hinweg

### 6.5 Wetter ist optional

Wetterdaten können in das Training einbezogen werden, wenn sie verfügbar sind. Falls sie nicht geladen werden können, wird ohne sie trainiert.

Das bedeutet:

- die Prognose funktioniert auch ohne Wetter
- aber Wetter kann die Qualität verbessern

### 6.6 Die Lösung ist nicht probabilistisch

Die Ausgabe ist ein Einzelwert pro Zeitpunkt.

Es gibt aktuell keine Unsicherheitsintervalle oder Wahrscheinlichkeitsverteilungen, also keine Angabe darüber, wie sicher die Prognose ist.

### 6.7 Die Logik ist stark an die gemessene Kapazität gebunden

Die Prognose setzt voraus, dass `total_spots` sinnvoll und stabil verfügbar ist.

Wenn sich die Kapazität eines Parkhauses verändert oder die Messung inkonsistent ist, kann die Prognose falsch sein.

## 7. Praktische Zusammenfassung

Die Forecast-Logik ist aktuell ein rekursives, pro Parkhaus trainiertes LightGBM-Modell mit folgenden Schritten:

1. Rohdaten aus der Datenbank laden
2. Zeitreihe auf 15-Minuten-Raster regularisieren
3. Kalender-, Lag- und Rolling-Features erzeugen
4. Modell für das Parkhaus laden
5. Für jeden zukünftigen Schritt eine neue Feature-Zeile erzeugen
6. Die Vorhersage für den nächsten Schritt als Basis für den folgenden Schritt verwenden
7. Ergebnis als belegte und freie Plätze zurückgeben

## 8. Fazit

Die aktuelle Lösung ist eine robuste und nachvollziehbare Baseline für eine Parkhausprognose. Sie ist gut geeignet für kurze bis mittlere Horizonte, aber bewusst begrenzt auf etwa 8 Stunden, weil die rekursive Prognose mit zunehmender Tiefe unzuverlässiger wird.
