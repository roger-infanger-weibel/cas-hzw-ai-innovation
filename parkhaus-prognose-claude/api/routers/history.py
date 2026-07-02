from fastapi import APIRouter, HTTPException, Query

from data_pipeline.db import fetch_raw_occupancy, list_parkhaeuser
from api.schemas import OccupancyPoint

router = APIRouter(tags=["history"])


@router.get("/parkhaeuser", response_model=list[str])
def get_parkhaeuser():
    return list_parkhaeuser()


@router.get("/parkhaus/{parkhaus_id}/aktuell", response_model=OccupancyPoint)
def get_current(parkhaus_id: str):
    df = fetch_raw_occupancy(parkhaus_id=parkhaus_id)
    if df.empty:
        raise HTTPException(404, f"Keine Daten für '{parkhaus_id}'")
    last = df.iloc[-1]
    return OccupancyPoint(
        ts=last["ts"],
        occupied_spots=int(last["occupied_spots"]),
        total_spots=int(last["total_spots"]),
        occupancy_rate=round(last["occupied_spots"] / last["total_spots"], 3),
    )


@router.get("/parkhaus/{parkhaus_id}/verlauf", response_model=list[OccupancyPoint])
def get_history(
    parkhaus_id: str,
    von: str = Query(..., description="ISO-Datum, z.B. 2026-06-01"),
    bis: str = Query(..., description="ISO-Datum, z.B. 2026-06-30"),
):
    df = fetch_raw_occupancy(parkhaus_id=parkhaus_id, since=von, until=bis)
    if df.empty:
        raise HTTPException(404, "Keine Daten im angegebenen Zeitraum")

    return [
        OccupancyPoint(
            ts=row["ts"],
            occupied_spots=int(row["occupied_spots"]),
            total_spots=int(row["total_spots"]),
            occupancy_rate=round(row["occupied_spots"] / row["total_spots"], 3),
        )
        for _, row in df.iterrows()
    ]
