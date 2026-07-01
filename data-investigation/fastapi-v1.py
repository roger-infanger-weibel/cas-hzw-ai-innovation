from fastapi import FastAPI
import json
import requests

app = FastAPI()

# 1. JSON-Daten einmalig lokal laden
with open("view_parkhaus_sax_strings.json", "r", encoding="utf-8") as f:
    parking_data = json.load(f)

# 2. Eine Filter-Funktion für das LLM bereitstellen
def filter_parking_data(city: str = None, name: str = None, wochentag: int = None):
    results = parking_data
    if city:
        results = [r for r in results if r["city"].lower() == city.lower()]
    if name:
        results = [r for r in results if name.lower() in r["name"].lower()]
    if wochentag is not None:
        results = [r for r in results if r["wochentag"] == wochentag]
    # Begrenzen, um das Kontextfenster des LLMs zu schonen
    return results[:20] 

# 3. API-Endpunkt für deinen Browser-Chat
@app.post("/chat")
def chat_with_llm(user_message: str):
    # Einfaches Beispiel: Wir filtern basierend auf Keywords in der Frage
    # (Kann später durch echtes Tool-Calling / Function-Calling ersetzt werden)
    detected_city = None
    for city in ["basel", "bern", "luzern", "zurich"]:
        if city in user_message.lower():
            detected_city = city
            
    relevant_context = filter_parking_data(city=detected_city)
    
    # Prompt für Ollama zusammenbauen
    prompt = f"""Du bist ein Datenanalyst. Hier sind die relevanten Parkhaus-Daten als JSON-Auszug:
    {json.dumps(relevant_context, indent=2)}
    
    Frage des Nutzers: {user_message}
    Antworte präzise basierend auf den Daten.
    """
    
    # Anfrage an Ollama senden
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3", "prompt": prompt, "stream": False}
    )
    
    return {"response": response.json()["response"]}