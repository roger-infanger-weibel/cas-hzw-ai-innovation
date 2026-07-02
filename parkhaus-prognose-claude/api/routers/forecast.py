from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from api import inference
from api.schemas import ForecastResponse, ForecastPoint

router = APIRouter(prefix="/parkhaus", tags=["forecast"])


@router.get("/{parkhaus_id}/prognose", response_model=ForecastResponse)
def get_forecast(parkhaus_id: str, horizon_minutes: int = 240):
    if horizon_minutes <= 0 or horizon_minutes > 8 * 60:
        raise HTTPException(400, "horizon_minutes muss zwischen 1 und 480 liegen")

    try:
        points = inference.forecast(parkhaus_id, horizon_minutes)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))

    return ForecastResponse(
        parkhaus_id=parkhaus_id,
        generated_at=datetime.now(timezone.utc),
        horizon_minutes=horizon_minutes,
        points=[ForecastPoint(**p) for p in points],
    )
