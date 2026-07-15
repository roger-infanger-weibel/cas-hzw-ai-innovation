#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Try to import a MySQL library
try:
    import pymysql
    mysql_lib = "pymysql"
except ImportError:
    try:
        import mysql.connector as pymysql_conn
        mysql_lib = "mysql.connector"
    except ImportError:
        print("Error: Please install pymysql or mysql-connector-python.")
        print("Run: pip install pymysql")
        sys.exit(1)

# Database Connection Settings
# These can be set via environment variables or edited below
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "ph_fetch_test")


print("=" * 60)
print(f"Starting Database Migration with {mysql_lib.upper()}...")
print(f"Target Database: {DB_NAME} at {DB_HOST}:{DB_PORT}")
print("=" * 60)

# Connect to MySQL
try:
    if mysql_lib == "pymysql":
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            autocommit=True
        )
    else:
        conn = pymysql_conn.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            autocommit=True
        )
except Exception as e:
    print(f"Error connecting to database: {e}")
    print("Please make sure your database is running, the schema exists, and credentials are correct.")
    sys.exit(1)

cursor = conn.cursor()

# -------------------------------------------------------------
# CRITICAL FIX: Set Connection Time Zone to UTC (+00:00)
# This prevents Error 1292 "Incorrect datetime value" during 
# Daylight Saving Time transitions (such as March 29, 2026, 02:00:00).
# -------------------------------------------------------------
print("Setting connection timezone to UTC (+00:00) to prevent DST transition errors...")
cursor.execute("SET time_zone = '+00:00';")

# Ensure tables exist
# (User provided schema definition)
print("Verifying / Creating table structure...")
cursor.execute("""
CREATE TABLE IF NOT EXISTS cities (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    url VARCHAR(255) NULL,
    latitude DECIMAL(9, 6) NOT NULL,
    longitude DECIMAL(9, 6) NOT NULL
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS parkhaeuser (
    id VARCHAR(100) PRIMARY KEY,
    city_id VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    parking_group VARCHAR(100) NULL,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_parkhaeuser_cities FOREIGN KEY (city_id) REFERENCES cities (id) ON DELETE CASCADE
);
""")

# 1. Cities Dataset
# Note: city_id are all in lowercase as requested.
cities_data = [
    ("basel", "Basel", "https://www.parkleitsystem-basel.ch/", 47.5596, 7.5886),
    ("bern", "Bern", "https://www.parking-bern.ch/", 46.9480, 7.4474),
    ("luzern", "Luzern", "https://www.pls-luzern.ch/", 47.0502, 8.3093),
    ("stgallen", "St. Gallen", "https://www.pls-sg.ch/", 47.4239, 9.3748),
    ("zurich", "Zürich", "https://www.pls-zh.ch/", 47.3769, 8.5417),
    ("genf", "Genf", None, 46.2044, 6.1432),
    ("lausanne", "Lausanne", None, 46.5197, 6.6323),
    ("winterthur", "Winterthur", None, 47.5009, 8.7259),
    ("lugano", "Lugano", None, 46.0037, 8.9511)
]

# 2. Parkhäuser Dataset with Groupings mapping
# This matches parkhausData.ts and groups.json exactly.
# Note: city_id is lowercase. Total spots is removed from schema.
parkhaeuser_data = [
    # Basel
    ("baselparkhausaeschen", "basel", "Basel Parkhaus Aeschen", "Parkhäuser Zentrum Süd", True),
    ("baselparkhausanfos", "basel", "Basel Parkhaus Anfos", "Parkhäuser Zentrum Süd", True),
    ("baselparkhausbadbahnhof", "basel", "Basel Parkhaus Bad Bahnhof", "Parkhäuser Zentrum Nord", True),
    ("baselparkhausbahnhofsued", "basel", "Basel Parkhaus Bahnhof Süd", "Parkhäuser Zentrum Süd", True),
    ("baselparkhauscentralbahn", "basel", "Basel Parkhaus Centralbahn", "Parkhäuser Zentrum Süd", True),
    ("baselparkhauscity", "basel", "Basel Parkhaus City", "Parkhäuser Zentrum West", True),
    ("baselparkhausclarahuus", "basel", "Basel Parkhaus Clarahuus", "Parkhäuser Zentrum Nord", True),
    ("baselparkhausclaramatte", "basel", "Basel Parkhaus Claramatte", "Parkhäuser Zentrum Nord", True),
    ("baselparkhauselisabethen", "basel", "Basel Parkhaus Elisabethen", "Parkhäuser Zentrum West", True),
    ("baselparkhauseurope", "basel", "Basel Parkhaus Europe", "Parkhäuser Zentrum Nord", True),
    ("baselparkhauskunstmuseum", "basel", "Basel Parkhaus Kunstmuseum", "Parkhäuser Zentrum Süd", True),
    ("baselparkhausmesse", "basel", "Basel Parkhaus Messe", "Parkhäuser Zentrum Nord", True),
    ("baselparkhausrebgasse", "basel", "Basel Parkhaus Rebgasse", "Parkhäuser Zentrum Nord", True),
    ("baselparkhaussteinen", "basel", "Basel Parkhaus Steinen", "Parkhäuser Zentrum West", True),
    ("baselparkhausstorchen", "basel", "Basel Parkhaus Storchen", "Parkhäuser Zentrum West", True),
    ("baselparkhauspostbasel", "basel", "Basel Parkhaus Post Basel", "Parkhäuser Zentrum Süd", True),

    # Zürich
    ("zuerichparkhaushauptbahnhof", "zurich", "Zürich Parkhaus Hauptbahnhof", None, True),
    ("zuerichparkhausurania", "zurich", "Zürich Parkhaus Urania", None, True),
    ("zuerichparkhaushohepromenade", "zurich", "Zürich Parkhaus Hohe Promenade", None, True),
    ("zuerichparkhausglobus", "zurich", "Zürich Parkhaus Globus", None, True),
    ("zuerichparkhausjelmoli", "zurich", "Zürich Parkhaus Jelmoli", None, True),
    ("zuerichparkhausopéra", "zurich", "Zürich Parkhaus Opéra", None, True),
    ("zuerichparkhauspfingstweid", "zurich", "Zürich Parkhaus Pfingstweid", None, True),
    ("zuerichparkhaushelvetiaplatz", "zurich", "Zürich Parkhaus Helvetiaplatz", None, True),
    ("zuerichparkhausaccu", "zurich", "Zürich Parkhaus Accu", None, True),
    ("zuerichparkhausalbisriederplatz", "zurich", "Zürich Parkhaus Albisriederplatz", None, True),
    ("zuerichparkhausbleicherweg", "zurich", "Zürich Parkhaus Bleicherweg", None, True),
    ("zuerichparkhauscentereleven", "zurich", "Zürich Parkhaus Center Eleven", None, True),
    ("zuerichparkhauscityparking", "zurich", "Zürich Parkhaus City Parking", None, True),
    ("zuerichparkhauscityport", "zurich", "Zürich Parkhaus Cityport", None, True),
    ("zuerichparkhauscrowneplaza", "zurich", "Zürich Parkhaus Crowne Plaza", None, True),
    ("zuerichparkhausdorflinde", "zurich", "Zürich Parkhaus Dorflinde", None, True),
    ("zuerichparkhausfeldegg", "zurich", "Zürich Parkhaus Feldegg", None, True),
    ("zuerichparkhaushardauii", "zurich", "Zürich Parkhaus Hardau II", None, True),
    ("zuerichparkhausjungholz", "zurich", "Zürich Parkhaus Jungholz", None, True),
    ("zuerichparkhausmessezuerichag", "zurich", "Zürich Parkhaus Messe Zürich", "Oerlikon / Messe", True),
    ("zuerichparkhausnordhaus", "zurich", "Zürich Parkhaus Nordhaus", None, True),
    ("zuerichparkhausoctavo", "zurich", "Zürich Parkhaus Octavo", None, True),
    ("zuerichparkhausparkside", "zurich", "Zürich Parkhaus Parkside", None, True),
    ("zuerichparkhauspwest", "zurich", "Zürich Parkhaus P-West", None, True),
    ("zuerichparkhausstampfenbach", "zurich", "Zürich Parkhaus Stampfenbach", None, True),
    ("zuerichparkhaustalgarten", "zurich", "Zürich Parkhaus Talgarten", None, True),
    ("zuerichparkhausuniirchel", "zurich", "Zürich Parkhaus Uni Irchel", None, True),
    ("zuerichparkhaususznord", "zurich", "Zürich Parkhaus USZ Nord", None, True),
    ("zuerichparkhausutoquai", "zurich", "Zürich Parkhaus Utoquai", None, True),
    ("zuerichparkhauszueri11shopping", "zurich", "Zürich Parkhaus Züri 11 Shopping", None, True),
    ("zuerichparkhauszuerichhorn", "zurich", "Zürich Parkhaus Zürichhorn", None, True),
    ("zuerichparkplatztheater11", "zurich", "Zürich Parkplatz Theater 11", "Oerlikon / Messe", True),
    ("zuerichparkplatzuszsued", "zurich", "Zürich Parkplatz USZ Süd", None, True),

    # Bern
    ("bernparkhausbahnhof", "bern", "Bern Parkhaus Bahnhof", "Parkhäuser Zentrum", True),
    ("bernparkhauscasino", "bern", "Bern Parkhaus Casino", "Parkhäuser Zentrum", True),
    ("bernparkhausmetro", "bern", "Bern Parkhaus Metro", "Parkhäuser Zentrum", True),
    ("bernparkhausrathaus", "bern", "Bern Parkhaus Rathaus", "Parkhäuser Zentrum", True),

    # Luzern
    ("luzernparkhausbahnhof", "luzern", "Luzern Parkhaus Bahnhof", "Parkhäuser Süd", True),
    ("luzernparkhausschweizerhof", "luzern", "Luzern Parkhaus Schweizerhof", "Parkhäuser Nord", True),
    ("luzernparkhauskesselturm", "luzern", "Luzern Parkhaus Kesselturm", "Parkhäuser Süd", True),
    ("luzernparkhausloewencenter", "luzern", "Luzern Parkhaus Löwen-Center", "Parkhäuser Nord", True),
    ("luzernparkhauscasinopalace", "luzern", "Luzern Parkhaus Casino-Palace", "Parkhäuser Nord", True),
    ("luzernparkhauscityparking", "luzern", "Luzern Parkhaus City Parking", "Parkhäuser Nord", True),
    ("luzernparkhausnationalhof", "luzern", "Luzern Parkhaus Nationalhof", "Parkhäuser Nord", True),
    ("luzernparkhausaltstadt", "luzern", "Luzern Parkhaus Altstadt", "Parkhäuser Süd", True),
    ("luzernparkhausamguetsch", "luzern", "Luzern Parkhaus am Gütsch", "Parkhäuser Süd", True),
    ("luzernparkhausflora", "luzern", "Luzern Parkhaus Flora", "Parkhäuser Süd", True),
    ("luzernparkhaushirzenmatt", "luzern", "Luzern Parkhaus Hirzenmatt", "Parkhäuser Süd", True),
    ("luzernparkhauskantonalbank", "luzern", "Luzern Parkhaus Kantonalbank", "Parkhäuser Süd", True),
    ("luzernparkingstadttheater", "luzern", "Luzern Parking Stadt Theater", "Parkhäuser Süd", True),
    ("luzernparkhausbahnhofp1p2", "luzern", "Luzern Parkhaus Bahnhofparking P1+P2", "Parkhäuser Süd", True),
    ("luzernparkhausbahnhofp3", "luzern", "Luzern Parkhaus Bahnhofparking P3", "Parkhäuser Süd", True),
    ("luzernparkhaussportgebaeude", "luzern", "Luzern Parkhaus Sportgebäude", "Allmend / Messe", True),

    # Genf
    ("genfparkingdumontblanc", "genf", "Genf Parking du Mont-Blanc", None, True),
    ("genfparkingdecornavin", "genf", "Genf Parking de Cornavin", None, True),
    ("genfparkingdesalpes", "genf", "Genf Parking des Alpes", None, True),

    # Lausanne
    ("lausanneparkingducentre", "lausanne", "Lausanne Parking du Centre", None, True),
    ("lausanneparkingdelariponne", "lausanne", "Lausanne Parking de la Riponne", None, True),
    ("lausanneparkingdurotillon", "lausanne", "Lausanne Parking du Rôtillon", None, True),

    # St. Gallen
    ("stgallenparkhausrathaus", "stgallen", "St. Gallen Parkhaus Rathaus", "Zentrum West", True),
    ("stgallenparkhausstadtpark", "stgallen", "St. Gallen Parkhaus Stadtpark", "Zentrum Ost", True),
    ("stgallenparkhausneumarkt", "stgallen", "St. Gallen Parkhaus Neumarkt", "Zentrum West", True),
    ("stgallenparkhausmanor", "stgallen", "St. Gallen Parkhaus Manor", "Zentrum West", True),
    ("stgallenparkhausbahnhof", "stgallen", "St. Gallen Parkhaus Bahnhof", "Zentrum West", True),
    ("stgallenparkhauskreuzbleiche", "stgallen", "St. Gallen Parkhaus Kreuzbleiche", "Zentrum West", True),
    ("stgallenparkhausoberergraben", "stgallen", "St. Gallen Parkhaus Oberer Graben", "Klosterviertel", True),
    ("stgallenparkhausraiffeisen", "stgallen", "St. Gallen Parkhaus Raiffeisen", "Klosterviertel", True),
    ("stgallenparkhauseinstein", "stgallen", "St. Gallen Parkhaus Einstein", "Klosterviertel", True),
    ("stgallenparkhausburggraben", "stgallen", "St. Gallen Parkhaus Burggraben", "Marktplatz", True),
    ("stgallenparkhausspisertor", "stgallen", "St. Gallen Parkhaus Spisertor", "Marktplatz", True),
    ("stgallenparkhausbruehltor", "stgallen", "St. Gallen Parkhaus Brühltor", "Marktplatz", True),
    ("stgallenparkhausstadtparkazsg", "stgallen", "St. Gallen Parkhaus Stadtpark AZSG", "Zentrum Ost", True),
    ("stgallenparkhausspelterini", "stgallen", "St. Gallen Parkhaus Spelterini", "Zentrum Ost", True),
    ("stgallenparkhausolmaparkplatz", "stgallen", "St. Gallen Parkhaus OLMA Parkplatz", "Zentrum Ost", True),
    ("stgallenparkhausolmamessen", "stgallen", "St. Gallen Parkhaus OLMA Messen", "Zentrum Ost", True),

    # Winterthur
    ("winterthurparkhausbahnhof", "winterthur", "Winterthur Parkhaus Bahnhof", None, True),
    ("winterthurparkhausteuchelweiher", "winterthur", "Winterthur Parkhaus Teuchelweiher", None, True),

    # Lugano
    ("luganoparkhausmotta", "lugano", "Lugano Parkhaus Motta", None, True),
    ("luganoparkhausbalestra", "lugano", "Lugano Parkhaus Balestra", None, True)
]

# -------------------------------------------------------------
# IDEMPOTENT INSERTS USING "ON DUPLICATE KEY UPDATE"
# -------------------------------------------------------------
print("Inserting/Updating cities...")
cities_inserted = 0
for city in cities_data:
    try:
        cursor.execute("""
            INSERT INTO cities (id, name, url, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                url = VALUES(url),
                latitude = VALUES(latitude),
                longitude = VALUES(longitude)
        """, city)
        cities_inserted += 1
    except Exception as e:
        print(f"Error inserting city '{city[0]}': {e}")

print(f"Successfully processed {cities_inserted}/{len(cities_data)} cities.")

print("Inserting/Updating parkhaeuser...")
park_inserted = 0
for ph in parkhaeuser_data:
    try:
        cursor.execute("""
            INSERT INTO parkhaeuser (id, city_id, name, parking_group, is_active)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                city_id = VALUES(city_id),
                name = VALUES(name),
                parking_group = VALUES(parking_group),
                is_active = VALUES(is_active)
        """, ph)
        park_inserted += 1
    except Exception as e:
        print(f"Error inserting parkhaus '{ph[0]}': {e}")

print(f"Successfully processed {park_inserted}/{len(parkhaeuser_data)} parkhouses.")

# Close connection
cursor.close()
conn.close()

print("=" * 60)
print("Database migration completed successfully!")
print("=" * 60)
