
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sys
import os
from datetime import datetime

import db_utils

# Initialize Flask app
app = Flask(__name__, static_folder='.')
CORS(app)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/logs')
def logs():
    return send_from_directory('.', 'logs.html')

@app.route('/cities.json')
def serve_cities_json():
    return send_from_directory('.', 'cities.json')

@app.route('/config/<path:filename>')
def serve_config(filename):
    return send_from_directory('config', filename)

@app.route('/api/cities')
def get_cities():
    try:
        conn = db_utils.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT city FROM pls_fetch_current ORDER BY city")
        cities = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify(cities)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dates/<city>')
def get_dates(city):
    try:
        conn = db_utils.get_connection()
        cursor = conn.cursor()
        query = "SELECT DISTINCT day FROM pls_fetch_current WHERE city = %s ORDER BY day DESC"
        cursor.execute(query, (city,))
        rows = cursor.fetchall()
        # rows are tuples ('2026-01-14',)
        dates = [str(row[0]) for row in rows]
        conn.close()
        return jsonify(dates)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/data/<city>/<date>')
def get_data(city, date):
    try:
        conn = db_utils.get_connection()
        cursor = conn.cursor(dictionary=True)
        # Fetch data for the specific city and day
        query = """
            SELECT fetch_ts, id, name, free, total 
            FROM pls_fetch_current 
            WHERE city = %s AND day = %s 
            ORDER BY fetch_ts ASC
        """
        cursor.execute(query, (city, date))
        rows = cursor.fetchall()
        conn.close()
        
        # Convert datetime objects to string
        for row in rows:
            if isinstance(row['fetch_ts'], datetime):
                row['fetch_ts'] = row['fetch_ts'].isoformat()
                
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs')
def get_logs():
    try:
        conn = db_utils.get_connection()
        cursor = conn.cursor(dictionary=True)
        # Fetch status logs
        query = "SELECT timestamp, severity, text FROM log ORDER BY timestamp DESC"
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert datetime objects to string
        for row in rows:
            if isinstance(row['timestamp'], datetime):
                row['timestamp'] = row['timestamp'].isoformat()
                
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs/daily_counts')
def get_daily_log_counts():
    try:
        conn = db_utils.get_connection()
        cursor = conn.cursor(dictionary=True)
        # Fetch log counts per day
        query = """
            SELECT DATE(timestamp) as day, COUNT(*) as count 
            FROM log 
            GROUP BY DATE(timestamp) 
            ORDER BY day DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert date objects to string
        for row in rows:
            if row['day']:
                row['day'] = row['day'].isoformat()
                
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"Serving files from: {os.getcwd()}")
    app.run(debug=True, host='0.0.0.0', port=80)
