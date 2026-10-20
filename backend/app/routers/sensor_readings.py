from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.database import get_db_dep
from app.image_meta import parse_datetime, to_utc_iso
from app.models.schemas import SensorReadingCreate, new_id

router = APIRouter()


@router.post("")
async def post_reading(reading: SensorReadingCreate, db=Depends(get_db_dep), user=Depends(get_current_user)):
    doc = reading.model_dump()
    if doc.get("timestamp"):
        ts = parse_datetime(doc["timestamp"])
        if ts is None:
            raise HTTPException(status_code=422, detail="timestamp must be ISO-8601 or Unix time")
    else:
        ts = datetime.now(timezone.utc)
    doc["timestamp"] = to_utc_iso(ts)
    # Naive UTC datetime for range queries when images are linked to readings
    doc["ts"] = ts.replace(tzinfo=None)
    doc["_id"] = new_id()
    await db.sensor_readings.insert_one(doc)
    doc.pop("ts")
    doc["id"] = doc.pop("_id")
    return doc


@router.get("")
async def list_readings(
    chamberId: str,
    sensorId: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db=Depends(get_db_dep),
    user=Depends(get_current_user),
):
    query: dict = {"chamberId": chamberId}
    if sensorId:
        query["sensorId"] = sensorId
    rng = {}
    if date_from and parse_datetime(date_from):
        rng["$gte"] = parse_datetime(date_from).replace(tzinfo=None)
    if date_to and parse_datetime(date_to):
        rng["$lte"] = parse_datetime(date_to).replace(tzinfo=None)
    if rng:
        query["ts"] = rng
    items = []
    async for doc in db.sensor_readings.find(query, {"ts": 0}).sort("timestamp", 1).limit(5000):
        doc["id"] = doc.pop("_id")
        items.append(doc)
    return items
