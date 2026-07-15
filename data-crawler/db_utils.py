
import os
import json
import logging
import mysql.connector
from mysql.connector import Error

from dotenv import load_dotenv
load_dotenv()

# --- KONFIGURATION ---
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "ph_fetch_test")


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_connection():
    """Establish a connection to the MariaDB database."""
    try:
        connection =  mysql.connector.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                autocommit=True
            )
        if connection.is_connected():
            return connection
    except Error as e:
        logging.error(f"Error connecting to MariaDB: {e}")
        raise e

def insert_measurement(cursor, data):
    """
    Insert a single measurement record using the provided cursor.
    Does NOT commit the transaction.
    
    Args:
        cursor: Active database cursor.
        data (dict): Dictionary containing the data to insert.
    """
    
    insert_query = """
    INSERT INTO pls_fetch_current 
    (day, fetch_ts, city, id, name, free, total)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        record = (
            data.get('day'),
            data.get('fetch_ts'),
            data.get('city'),
            data.get('id'),
            data.get('name'),
            data.get('free'),
            data.get('total')
        )
        cursor.execute(insert_query, record)
    except Error as e:
        logging.error(f"Error inserting record {data}: {e}")
        raise

def get_cities_config():
    """
    Load city configuration from the `cities` table.

    Returns:
        dict: {"cities": {city_id: {name, url, latitude, longitude, collector, api_url}}}
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, url, latitude, longitude, collector, api_url FROM cities")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return {"cities": {row["id"]: row for row in rows}}


def insert_log(cursor, severity, text):
    """
    Insert a log entry into the log table.
    
    Args:
        cursor: Active database cursor.
        severity (str): Log severity (I=Info, W=Warning, E=Error).
        text (str): Log message text.
    """
    
    insert_query = """
    INSERT INTO log (timestamp, severity, text)
    VALUES (NOW(), %s, %s)
    """
    
    try:
        # Truncate text if it's too long for the database column (assuming 65535 for TEXT or similar)
        safe_text = text[:60000] if text else ""
        cursor.execute(insert_query, (severity, safe_text))
    except Error as e:
        logging.error(f"Error inserting log: {e}")
        raise