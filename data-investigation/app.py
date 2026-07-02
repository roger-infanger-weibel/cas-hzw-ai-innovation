import json
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# CORS aktivieren, damit der Browser problemlos auf die API zugreifen kann
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. JSON-Daten beim Starten des Servers einmalig laden
JSON_FILE_PATH = "view_parkhaus_sax_strings.json"

try:
    with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
        parking_data = json.load(f)
    print(f"[INFO] Erfolgreich {len(parking_data)} Datensätze aus JSON geladen.")
except FileNotFoundError:
    print(f"[ERROR] Datei '{JSON_FILE_PATH}' wurde nicht gefunden! Bitte Pfad prüfen.")
    parking_data = []

# Pydantic-Model für den eingehenden Browser-Request
class ChatRequest(BaseModel):
    user_message: str

# 2. Verbesserte Hilfsfunktion zum Filtern der JSON-Daten
def filter_parking_data(city: str = None, name: str = None):
    if not parking_data:
        return []
        
    results = parking_data
    
    # Filtern nach Stadt (Vergleich in Kleinbuchstaben, um Fehler zu vermeiden)
    if city:
        results = [
            r for r in results 
            if str(r.get("city", "")).lower() == city.lower() or 
               str(r.get("name", "")).lower() == city.lower()
        ]
        
    # Filtern nach spezifischem Parkhausnamen (falls im Text erwähnt)
    if name:
        results = [r for r in results if name.lower() in str(r.get("name", "")).lower()]
        
    # Auf 20 Einträge begrenzen, um das LLM-Kontextfenster nicht zu sprengen
    return results[:20]

# 3. Der API-Endpunkt für deine Browser-Oberfläche
@app.post("/chat")
async def chat_with_llm(request: ChatRequest):
    user_message = request.user_message
    
    # Städtenamen-Mapping für flexible Erkennung (inkl. Umlaut/Mundart)
    city_mapping = {
        "zurich": ["zurich", "zürich", "züri"],
        "basel": ["basel"],
        "bern": ["bern"],
        "luzern": ["luzern"]
    }
    
    detected_city = None
    for city_key, aliases in city_mapping.items():
        if any(alias in user_message.lower() for alias in aliases):
            detected_city = city_key
            break
            
    # Daten basierend auf der erkannten Stadt aus dem JSON filtern
    relevant_context = filter_parking_data(city=detected_city)
    
    # --- DIAGNOSE-PRINTS FÜR DEINE KONSOLE ---
    print("\n--- NEUE ANFRAGE ---")
    print(f"User Nachricht: '{user_message}'")
    print(f"Erkannte Stadt für Filter: {detected_city}")
    print(f"Gefundene Datensätze im JSON: {len(relevant_context)}")
    # -----------------------------------------

    # Prompt für Ollama aufbauen
    if not relevant_context:
        prompt = f"""Der Nutzer fragt: '{user_message}'. 
        Leider wurden für diese Anfrage keine passenden Schweizer Parkhausdaten (Basel, Bern, Luzern, Zürich) in der Datenbank gefunden. 
        Bitte antworte höflich auf Deutsch, weise darauf hin und frage nach, für welche dieser Städte er Daten sehen möchte."""
    else:
        prompt = f"""Du bist ein Datenanalyst für Schweizer Parkhäuser. 
Hier ist ein relevanter JSON-Auszug aus den gesammelten SAX-Zeitreihendaten (Juni 2026).
Die SAX-Strings repräsentieren 24 Stunden (A = sehr leer, D = sehr voll). Wochentag 0 = Montag, 6 = Sonntag.

Relevante Daten:
{json.dumps(relevant_context, indent=2)}

Frage des Nutzers: {user_message}

Antworte präzise, übersichtlich und direkt auf Deutsch basierend auf diesen Daten.
"""

    # 4. Anfrage an Ollama senden
    OLLAMA_URL = "http://localhost:11434/api/generate"
    OLLAMA_MODEL = "llama3" 
    
    try:
        print(f"[OLLAMA] Sende Prompt an Modell '{OLLAMA_MODEL}'...")
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL, 
                "prompt": prompt, 
                "stream": False
            },
            timeout=45
        )
        
        ollama_response = response.json().get("response", "Keine Antwort vom Modell erhalten.")
        print("[OLLAMA] Antwort erfolgreich generiert.")
        return {"response": ollama_response}
        
    except requests.exceptions.Timeout:
        print("[ERROR] Timeout bei der Anfrage an Ollama.")
        return {"response": "Ollama hat zu lange für die Antwort gebraucht (Timeout). Bitte versuche es nochmals."}
    except requests.exceptions.ConnectionError:
        print("[ERROR] Keine Verbindung zu Ollama auf Port 11434 möglich.")
        return {"response": "⚠️ Hinweis: Das Backend funktioniert, aber Ollama läuft im Hintergrund nicht. Bitte starte die Ollama-App auf deinem Rechner."}
    except Exception as e:
        print(f"[ERROR] Allgemeiner Fehler: {str(e)}")
        return {"response": f"Fehler bei der Verarbeitung: {str(e)}"}

# 5. Homepage-Endpunkt liefert die index.html aus
@app.get("/")
async def get_homepage():
    return FileResponse("index.html")