"""
Optionale LLM-Chat-Schicht.

WICHTIG: Das LLM berechnet KEINE Prognosezahlen selbst. Es bekommt über
Tool-Use Zugriff auf die echten Endpunkte (get_forecast, get_current) und
formuliert nur die Antwort in natürlicher Sprache. Damit "halluziniert"
das Modell keine Belegungszahlen.

Aktiviert über ENABLE_LLM_CHAT=true in der .env. Nutzt hier die Anthropic
API; alternativ kann `anthropic.Anthropic(...)` durch einen lokalen
Ollama-Client ersetzt werden, wenn du komplett offline bleiben willst.
"""
import json
import os

from fastapi import APIRouter, HTTPException

from api import inference
from data_pipeline.db import fetch_raw_occupancy
from api.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])

ENABLE_LLM_CHAT = os.getenv("ENABLE_LLM_CHAT", "false").lower() == "true"

TOOLS = [
    {
        "name": "get_forecast",
        "description": "Liefert die Belegungsprognose für ein Parkhaus für die nächsten X Minuten.",
        "input_schema": {
            "type": "object",
            "properties": {
                "parkhaus_id": {"type": "string"},
                "horizon_minutes": {"type": "integer", "description": "z.B. 240 für 4 Stunden"},
            },
            "required": ["parkhaus_id"],
        },
    },
    {
        "name": "get_current_occupancy",
        "description": "Liefert die aktuelle Belegung eines Parkhauses.",
        "input_schema": {
            "type": "object",
            "properties": {"parkhaus_id": {"type": "string"}},
            "required": ["parkhaus_id"],
        },
    },
]


def _execute_tool(name: str, tool_input: dict) -> dict:
    if name == "get_forecast":
        return {"forecast": inference.forecast(
            tool_input["parkhaus_id"], tool_input.get("horizon_minutes", 240)
        )}
    if name == "get_current_occupancy":
        df = fetch_raw_occupancy(parkhaus_id=tool_input["parkhaus_id"])
        last = df.iloc[-1]
        return {
            "occupied_spots": int(last["occupied_spots"]),
            "total_spots": int(last["total_spots"]),
            "ts": str(last["ts"]),
        }
    raise ValueError(f"Unbekanntes Tool: {name}")


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not ENABLE_LLM_CHAT:
        raise HTTPException(503, "LLM-Chat ist deaktiviert (ENABLE_LLM_CHAT=false)")

    try:
        import anthropic
    except ImportError:
        raise HTTPException(500, "Paket 'anthropic' ist nicht installiert (pip install anthropic)")

    client = anthropic.Anthropic()  # nutzt ANTHROPIC_API_KEY aus der Umgebung
    system_prompt = (
        "Du bist der Assistent eines Parkhaus-Dashboards. Beantworte Fragen zur "
        "aktuellen und zukünftigen Belegung AUSSCHLIESSLICH auf Basis der Tool-Ergebnisse. "
        "Erfinde niemals Zahlen. Wenn eine parkhaus_id fehlt, frage danach."
    )

    messages = [{"role": "user", "content": req.message}]

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=500,
        system=system_prompt,
        tools=TOOLS,
        messages=messages,
    )

    # Tool-Use-Schleife
    while response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = _execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                })
        messages.append({"role": "user", "content": tool_results})
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=500,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

    reply_text = "".join(b.text for b in response.content if b.type == "text")
    return ChatResponse(reply=reply_text)
