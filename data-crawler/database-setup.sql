-- 1. Städte-Tabelle (Metadata)
CREATE TABLE IF NOT EXISTS cities (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    url VARCHAR(255) NULL,
    latitude DECIMAL(9, 6) NOT NULL,
    longitude DECIMAL(9, 6) NOT NULL
);

INSERT INTO cities (id, name, url, latitude, longitude) VALUES
('basel', 'Basel', 'https://www.parkleitsystem-basel.ch/', 47.559600, 7.588600),
('bern', 'Bern', 'https://www.parking-bern.ch/', 46.948000, 7.447400),
('luzern', 'Luzern', 'https://www.pls-luzern.ch/', 47.050200, 8.309300),
('stgallen', 'St. Gallen', 'https://www.pls-sg.ch/', 47.423900, 9.374800),
('zurich', 'Zürich', 'https://www.pls-zh.ch/', 47.376900, 8.541700)
ON DUPLICATE KEY UPDATE name=VALUES(name), url=VALUES(url), latitude=VALUES(latitude), longitude=VALUES(longitude);

-- 2. Parkhäuser-Tabelle
CREATE TABLE IF NOT EXISTS parkhaeuser (
    id VARCHAR(100) PRIMARY KEY,
    city_id VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    parking_group VARCHAR(100) NULL,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_parkhaeuser_cities FOREIGN KEY (city_id) REFERENCES cities (id) ON DELETE CASCADE
);

INSERT INTO parkhaeuser (id, city_id, name, parking_group, is_active) VALUES
-- Basel Parkhäuser
('baselparkhausaeschen', 'basel', 'Basel Parkhaus Aeschen', 'Parkhäuser Zentrum Süd', TRUE),
('baselparkhausanfos', 'basel', 'Basel Parkhaus Anfos', 'Parkhäuser Zentrum Süd', TRUE),
('baselparkhausbadbahnhof', 'basel', 'Basel Parkhaus Bad Bahnhof', 'Parkhäuser Zentrum Nord', TRUE),
('baselparkhausbahnhofsued', 'basel', 'Basel Parkhaus Bahnhof Süd', 'Parkhäuser Zentrum Süd', TRUE),
('baselparkhauscentralbahn', 'basel', 'Basel Parkhaus Centralbahn', 'Parkhäuser Zentrum Süd', TRUE),
('baselparkhauscity', 'basel', 'Basel Parkhaus City', 'Parkhäuser Zentrum West', TRUE),
('baselparkhausclarahuus', 'basel', 'Basel Parkhaus Clarahuus', 'Parkhäuser Zentrum Nord', TRUE),
('baselparkhausclaramatte', 'basel', 'Basel Parkhaus Claramatte', 'Parkhäuser Zentrum Nord', TRUE),
('baselparkhauselisabethen', 'basel', 'Basel Parkhaus Elisabethen', 'Parkhäuser Zentrum West', TRUE),
('baselparkhauseurope', 'basel', 'Basel Parkhaus Europe', 'Parkhäuser Zentrum Nord', TRUE),
('baselparkhauskunstmuseum', 'basel', 'Basel Parkhaus Kunstmuseum', 'Parkhäuser Zentrum Süd', TRUE),
('baselparkhausmesse', 'basel', 'Basel Parkhaus Messe', 'Parkhäuser Zentrum Nord', TRUE),
('baselparkhausrebgasse', 'basel', 'Basel Parkhaus Rebgasse', 'Parkhäuser Zentrum Nord', TRUE),
('baselparkhaussteinen', 'basel', 'Basel Parkhaus Steinen', 'Parkhäuser Zentrum West', TRUE),
('baselparkhausstorchen', 'basel', 'Basel Parkhaus Storchen', 'Parkhäuser Zentrum West', TRUE),
('baselparkhauspostbasel', 'basel', 'Basel Parkhaus Post Basel', 'Parkhäuser Zentrum Süd', TRUE),

-- Bern Parkhäuser
('bernparkhausbahnhof', 'bern', 'Bern Parkhaus Bahnhof', 'Parkhäuser Zentrum', TRUE),
('bernparkhauscasino', 'bern', 'Bern Parkhaus Casino', 'Parkhäuser Zentrum', TRUE),
('bernparkhausmetro', 'bern', 'Bern Parkhaus Metro', 'Parkhäuser Zentrum', TRUE),
('bernparkhausrathaus', 'bern', 'Bern Parkhaus Rathaus', 'Parkhäuser Zentrum', TRUE),

-- Luzern Parkhäuser
('luzernparkhausbahnhof', 'luzern', 'Luzern Parkhaus Bahnhof', NULL, TRUE),
('luzernparkhausschweizerhof', 'luzern', 'Luzern Parkhaus Schweizerhof', 'Parkhäuser Nord', TRUE),
('luzernparkhauskesselturm', 'luzern', 'Luzern Parkhaus Kesselturm', 'Parkhäuser Süd', TRUE),
('luzernparkhausloewencenter', 'luzern', 'Luzern Parkhaus Löwen-Center', 'Parkhäuser Nord', TRUE),
('luzernparkhauscasinopalace', 'luzern', 'Luzern Parkhaus Casino-Palace', 'Parkhäuser Nord', TRUE),
('luzernparkhauscityparking', 'luzern', 'Luzern Parkhaus City Parking', 'Parkhäuser Nord', TRUE),
('luzernparkhausnationalhof', 'luzern', 'Luzern Parkhaus Nationalhof', 'Parkhäuser Nord', TRUE),
('luzernparkhausaltstadt', 'luzern', 'Luzern Parkhaus Altstadt', 'Parkhäuser Süd', TRUE),
('luzernparkhausamguetsch', 'luzern', 'Luzern Parkhaus am Gütsch', 'Parkhäuser Süd', TRUE),
('luzernparkhausflora', 'luzern', 'Luzern Parkhaus Flora', 'Parkhäuser Süd', TRUE),
('luzernparkhaushirzenmatt', 'luzern', 'Luzern Parkhaus Hirzenmatt', 'Parkhäuser Süd', TRUE),
('luzernparkhauskantonalbank', 'luzern', 'Luzern Parkhaus Kantonalbank', 'Parkhäuser Süd', TRUE),
('luzernparkingstadttheater', 'luzern', 'Luzern Parking Stadt Theater', 'Parkhäuser Süd', TRUE),
('luzernparkhausbahnhofp1p2', 'luzern', 'Luzern Parkhaus Bahnhofparking P1+P2', 'Parkhäuser Süd', TRUE),
('luzernparkhausbahnhofp3', 'luzern', 'Luzern Parkhaus Bahnhofparking P3', 'Parkhäuser Süd', TRUE),
('luzernparkhaussportgebaeude', 'luzern', 'Luzern Parkhaus Sportgebäude', 'Allmend / Messe', TRUE),

-- Zürich Parkhäuser
('zuerichparkhaushauptbahnhof', 'zurich', 'Zürich Parkhaus Hauptbahnhof', NULL, TRUE),
('zuerichparkhausurania', 'zurich', 'Zürich Parkhaus Urania', NULL, TRUE),
('zuerichparkhaushohepromenade', 'zurich', 'Zürich Parkhaus Hohe Promenade', NULL, TRUE),
('zuerichparkhausglobus', 'zurich', 'Zürich Parkhaus Globus', NULL, TRUE),
('zuerichparkhausjelmoli', 'zurich', 'Zürich Parkhaus Jelmoli', NULL, TRUE),
('zuerichparkhausopéra', 'zurich', 'Zürich Parkhaus Opéra', NULL, TRUE),
('zuerichparkhauspfingstweid', 'zurich', 'Zürich Parkhaus Pfingstweid', NULL, TRUE),
('zuerichparkhaushelvetiaplatz', 'zurich', 'Zürich Parkhaus Helvetiaplatz', NULL, TRUE),
('zuerichparkhausaccu', 'zurich', 'Zürich Parkhaus Accu', NULL, TRUE),
('zuerichparkhausalbisriederplatz', 'zurich', 'Zürich Parkhaus Albisriederplatz', NULL, TRUE),
('zuerichparkhausbleicherweg', 'zurich', 'Zürich Parkhaus Bleicherweg', NULL, TRUE),
('zuerichparkhauscentereleven', 'zurich', 'Zürich Parkhaus Center Eleven', NULL, TRUE),
('zuerichparkhauscityparking', 'zurich', 'Zürich Parkhaus City Parking', NULL, TRUE),
('zuerichparkhauscityport', 'zurich', 'Zürich Parkhaus Cityport', NULL, TRUE),
('zuerichparkhauscrowneplaza', 'zurich', 'Zürich Parkhaus Crowne Plaza', NULL, TRUE),
('zuerichparkhausdorflinde', 'zurich', 'Zürich Parkhaus Dorflinde', NULL, TRUE),
('zuerichparkhausfeldegg', 'zurich', 'Zürich Parkhaus Feldegg', NULL, TRUE),
('zuerichparkhaushardauii', 'zurich', 'Zürich Parkhaus Hardau II', NULL, TRUE),
('zuerichparkhausjungholz', 'zurich', 'Zürich Parkhaus Jungholz', NULL, TRUE),
('zuerichparkhausmessezuerichag', 'zurich', 'Zürich Parkhaus Messe Zürich', 'Oerlikon / Messe', TRUE),
('zuerichparkhausnordhaus', 'zurich', 'Zürich Parkhaus Nordhaus', NULL, TRUE),
('zuerichparkhausoctavo', 'zurich', 'Zürich Parkhaus Octavo', NULL, TRUE),
('zuerichparkhausparkside', 'zurich', 'Zürich Parkhaus Parkside', NULL, TRUE),
('zuerichparkhauspwest', 'zurich', 'Zürich Parkhaus P-West', NULL, TRUE),
('zuerichparkhausstampfenbach', 'zurich', 'Zürich Parkhaus Stampfenbach', NULL, TRUE),
('zuerichparkhaustalgarten', 'zurich', 'Zürich Parkhaus Talgarten', NULL, TRUE),
('zuerichparkhausuniirchel', 'zurich', 'Zürich Parkhaus Uni Irchel', NULL, TRUE),
('zuerichparkhaususznord', 'zurich', 'Zürich Parkhaus USZ Nord', NULL, TRUE),
('zuerichparkhausutoquai', 'zurich', 'Zürich Parkhaus Utoquai', NULL, TRUE),
('zuerichparkhauszueri11shopping', 'zurich', 'Zürich Parkhaus Züri 11 Shopping', NULL, TRUE),
('zuerichparkhauszuerichhorn', 'zurich', 'Zürich Parkhaus Zürichhorn', NULL, TRUE),
('zuerichparkplatztheater11', 'zurich', 'Zürich Parkplatz Theater 11', 'Oerlikon / Messe', TRUE),
('zuerichparkplatzuszsued', 'zurich', 'Zürich Parkplatz USZ Süd', NULL, TRUE),

-- St. Gallen Parkhäuser
('stgallenparkhausrathaus', 'stgallen', 'St. Gallen Parkhaus Rathaus', 'Zentrum West', TRUE),
('stgallenparkhausstadtpark', 'stgallen', 'St. Gallen Parkhaus Stadtpark', 'Zentrum Ost', TRUE),
('stgallenparkhausneumarkt', 'stgallen', 'St. Gallen Parkhaus Neumarkt', 'Zentrum West', TRUE),
('stgallenparkhausmanor', 'stgallen', 'St. Gallen Parkhaus Manor', 'Zentrum West', TRUE),
('stgallenparkhausbahnhof', 'stgallen', 'St. Gallen Parkhaus Bahnhof', 'Zentrum West', TRUE),
('stgallenparkhauskreuzbleiche', 'stgallen', 'St. Gallen Parkhaus Kreuzbleiche', 'Zentrum West', TRUE),
('stgallenparkhausoberergraben', 'stgallen', 'St. Gallen Parkhaus Oberer Graben', 'Klosterviertel', TRUE),
('stgallenparkhausraiffeisen', 'stgallen', 'St. Gallen Parkhaus Raiffeisen', 'Klosterviertel', TRUE),
('stgallenparkhauseinstein', 'stgallen', 'St. Gallen Parkhaus Einstein', 'Klosterviertel', TRUE),
('stgallenparkhausburggraben', 'stgallen', 'St. Gallen Parkhaus Burggraben', 'Marktplatz', TRUE),
('stgallenparkhausspisertor', 'stgallen', 'St. Gallen Parkhaus Spisertor', 'Marktplatz', TRUE),
('stgallenparkhausbruehltor', 'stgallen', 'St. Gallen Parkhaus Brühltor', 'Marktplatz', TRUE),
('stgallenparkhausstadtparkazsg', 'stgallen', 'St. Gallen Parkhaus Stadtpark AZSG', 'Zentrum Ost', TRUE),
('stgallenparkhausspelterini', 'stgallen', 'St. Gallen Parkhaus Spelterini', 'Zentrum Ost', TRUE),
('stgallenparkhausolmaparkplatz', 'stgallen', 'St. Gallen Parkhaus OLMA Parkplatz', 'Zentrum Ost', TRUE),
('stgallenparkhausolmamessen', 'stgallen', 'St. Gallen Parkhaus OLMA Messen', 'Zentrum Ost', TRUE)

ON DUPLICATE KEY UPDATE name=VALUES(name), parking_group=VALUES(parking_group), is_active=VALUES(is_active);


-- 3. Wetter-Messwerte & Vorhersagen (Historisch + Zukunft)
-- Ein Unique Constraint auf (city_id, timestamp) erlaubt das einfache Überschreiben (UPSERT)
CREATE TABLE weather_forecasts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    city_id VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    temperature DECIMAL(4, 1),      
    precipitation DECIMAL(5, 2),    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT unique_city_timestamp UNIQUE (city_id, `timestamp`),
    CONSTRAINT fk_weather_cities FOREIGN KEY (city_id) REFERENCES cities(id)
);

-- 4. Kulturevents
CREATE TABLE local_events (
    id VARCHAR(100) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    venue VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    description TEXT,
    category VARCHAR(50),           -- 'Theater', 'Konzert', 'Messe'
    peak_occupancy_bonus DECIMAL(3, 2) DEFAULT 0.30, -- z.B. 0.35 für +35% Peak
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 5. Zuordnung: Welche Parkhäuser sind von welchem Event betroffen?
-- (N:M Beziehung)
CREATE TABLE event_parkhaus (
    event_id VARCHAR(100),
    parkhaus_id VARCHAR(100),
    PRIMARY KEY (event_id, parkhaus_id),
    CONSTRAINT fk_event_parkhaus_event FOREIGN KEY (event_id) REFERENCES local_events(id) ON DELETE CASCADE,
    CONSTRAINT fk_event_parkhaus_parkhaus FOREIGN KEY (parkhaus_id) REFERENCES parkhaeuser(id) ON DELETE CASCADE
);

-- Indizes für schnelle Abfragen der Echtzeit-Modulation
CREATE INDEX idx_weather_timestamp ON weather_forecasts(`timestamp`);
CREATE INDEX idx_events_time ON local_events(start_time, end_time);

-- Index zur schnellen Abfrage von Parkhäusern einer bestimmten Gruppe
CREATE INDEX idx_group_parkings_group ON group_parkings(group_id);