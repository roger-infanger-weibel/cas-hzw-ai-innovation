"""
Zentrale DB-Verbindung fuer MySQL/MariaDB (ph_fetch).

Reales Schema (bestaetigt):
    pls_fetch_current(
        day       DATE,
        fetch_ts  DATETIME,   -- ca. alle 15 Min, aber NICHT exakt im Raster
        city      VARCHAR,
        id        VARCHAR,    -- Parkhaus-ID, z.B. 'baselparkhausaeschen'
        name      VARCHAR,
        free      INT/VARCHAR,
        total     INT/VARCHAR
    )

Hinweis: pls_fetch_current scheint kumulativ zu wachsen (1.3 Mio Zeilen seit
Mitte Januar), ist also die tatsaechliche Historie - kein reiner Snapshot.
Belegte Plaetze werden hier als total - free berechnet.
"""
import os
from functools import lru_cache

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

RAW_TABLE = os.getenv("RAW_TABLE", "pls_fetch_current")
SAX_TABLE = os.getenv("SAX_TABLE", "view_parkhaus_sax_strings")


def get_connection_string() -> str:
    user = os.getenv("DB_USER")
    pwd = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "ph_fetch")
    return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{name}"


@lru_cache(maxsize=1)
def get_engine():
    return create_engine(get_connection_string(), pool_pre_ping=True)


def fetch_raw_occupancy(
    parkhaus_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> pd.DataFrame:
    """
    Laedt Rohdaten aus pls_fetch_current und normalisiert Spaltennamen auf
    das interne Schema (parkhaus_id, ts, occupied_spots, total_spots), das
    von features.py / inference.py verwendet wird.
    """
    query = f"""
        SELECT
            id AS parkhaus_id,
            city,
            name,
            fetch_ts AS ts,
            CAST(total AS UNSIGNED) AS total_spots,
            CAST(total AS UNSIGNED) - CAST(free AS UNSIGNED) AS occupied_spots
        FROM {RAW_TABLE}
        WHERE 1=1
    """
    params = {}
    if parkhaus_id:
        query += " AND id = :parkhaus_id"
        params["parkhaus_id"] = parkhaus_id
    if since:
        query += " AND fetch_ts >= :since"
        params["since"] = since
    if until:
        query += " AND fetch_ts <= :until"
        params["until"] = until

    query += " ORDER BY id, fetch_ts"

    with get_engine().connect() as conn:
        df = pd.read_sql(text(query), conn, params=params, parse_dates=["ts"])
    return df


def list_parkhaeuser() -> list[str]:
    query = f"SELECT DISTINCT id FROM {RAW_TABLE} ORDER BY id"
    with get_engine().connect() as conn:
        return [row[0] for row in conn.execute(text(query))]


def fetch_sax_strings(parkhaus_id: str | None = None, since: str | None = None) -> pd.DataFrame:
    """Laedt die taegliche SAX-Repraesentation - nuetzlich fuer Tages-Aehnlichkeitsanalyse
    und als optionales Zusatzfeature/Plausibilitaetscheck, siehe sax_features.py."""
    query = f"SELECT id AS parkhaus_id, city, name, datum, sax_string FROM {SAX_TABLE} WHERE 1=1"
    params = {}
    if parkhaus_id:
        query += " AND id = :parkhaus_id"
        params["parkhaus_id"] = parkhaus_id
    if since:
        query += " AND datum >= :since"
        params["since"] = since
    query += " ORDER BY id, datum"

    with get_engine().connect() as conn:
        return pd.read_sql(text(query), conn, params=params, parse_dates=["datum"])
