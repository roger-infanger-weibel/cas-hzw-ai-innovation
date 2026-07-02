from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import forecast, history, chat

app = FastAPI(
    title="Parkhaus-Prognose API",
    description="Liefert aktuelle Belegung und KI-Prognosen für Parkhäuser.",
    version="1.0.0",
)

# Für Produktion: allow_origins auf die konkrete Frontend-Domain einschränken
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(history.router)
app.include_router(forecast.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
