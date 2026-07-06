from datetime import datetime

from pydantic import BaseModel


class OccupancyPoint(BaseModel):
    ts: datetime
    occupied_spots: int
    total_spots: int
    occupancy_rate: float


class ForecastPoint(BaseModel):
    ts: datetime
    predicted_occupied_spots: float
    predicted_free_spots: float
    total_spots: int


class ForecastResponse(BaseModel):
    parkhaus_id: str
    generated_at: datetime
    horizon_minutes: int
    points: list[ForecastPoint]


class ChatRequest(BaseModel):
    message: str
    parkhaus_id: str | None = None


class ChatResponse(BaseModel):
    reply: str


class ParkhausInfo(BaseModel):
    id: str
    name: str | None = None
    city: str | None = None
