from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.database import get_db_dep
from app.models.schemas import SensorReadingCreate, new_id

router = APIRouter()

@router.post("")
async def post_reading(reading: SensorReadingCreate, db=Depends(get_db_dep), user=Depends(get_current_user)):
    doc = reading.model_dump()
    doc["_id"] = new_id()
    await db.sensor_readings.insert_one(doc)
    doc["id"] = doc.pop("_id")
    return doc
