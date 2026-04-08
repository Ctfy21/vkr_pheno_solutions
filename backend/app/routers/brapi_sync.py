"""
BrAPI Sync - client for connecting to external BrAPI servers,
browsing their data, and importing into local PhenoPlant DB.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
from app.database import get_db_dep, get_brapi_db_dep
from app.models.schemas import new_id

router = APIRouter()

TIMEOUT = 30.0


class BrAPIServerCreate(BaseModel):
    name: str
    url: str
    description: str = ""


def _normalize_url(url: str) -> str:
    return url.rstrip("/")


async def _get_server(server_id: str, db):
    doc = await db["brapi_servers"].find_one({"_id": server_id})
    if not doc:
        raise HTTPException(status_code=404, detail="BrAPI server not found")
    return doc


async def _fetch_brapi(base_url: str, endpoint: str) -> dict:
    url = f"{_normalize_url(base_url)}/brapi/v2/{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"External server error: {e.response.status_code}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Cannot reach server: {str(e)}")


# --- CRUD for BrAPI servers (local DB) ---

@router.post("/brapi-servers")
async def add_server(item: BrAPIServerCreate, db=Depends(get_db_dep)):
    doc = item.model_dump()
    doc["_id"] = new_id()
    doc["url"] = _normalize_url(doc["url"])
    count = await db["brapi_servers"].count_documents({})
    doc["active"] = (count == 0)
    await db["brapi_servers"].insert_one(doc)
    doc["id"] = doc.pop("_id")
    return doc


@router.get("/brapi-servers")
async def list_servers(db=Depends(get_db_dep)):
    items = []
    async for doc in db["brapi_servers"].find():
        doc["id"] = doc.pop("_id")
        if "active" not in doc:
            doc["active"] = False
        items.append(doc)
    return items


@router.delete("/brapi-servers/{server_id}")
async def delete_server(server_id: str, db=Depends(get_db_dep)):
    doc = await db["brapi_servers"].find_one({"_id": server_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    was_active = doc.get("active", False)
    await db["brapi_servers"].delete_one({"_id": server_id})
    if was_active:
        first = await db["brapi_servers"].find_one()
        if first:
            await db["brapi_servers"].update_one({"_id": first["_id"]}, {"$set": {"active": True}})
    return {"ok": True}


@router.put("/brapi-servers/{server_id}/activate")
async def activate_server(server_id: str, db=Depends(get_db_dep)):
    server = await _get_server(server_id, db)
    await db["brapi_servers"].update_many({}, {"$set": {"active": False}})
    await db["brapi_servers"].update_one({"_id": server_id}, {"$set": {"active": True}})
    return {"ok": True, "activeServerId": server_id}


@router.get("/brapi-servers/active")
async def get_active_server(db=Depends(get_db_dep)):
    doc = await db["brapi_servers"].find_one({"active": True})
    if not doc:
        return None
    doc["id"] = doc.pop("_id")
    return doc


# --- Browse external server data ---

@router.get("/brapi-servers/{server_id}/programs")
async def browse_programs(server_id: str, db=Depends(get_db_dep)):
    server = await _get_server(server_id, db)
    data = await _fetch_brapi(server["url"], "programs")
    return data.get("result", {}).get("data", [])


@router.get("/brapi-servers/{server_id}/studies")
async def browse_studies(server_id: str, db=Depends(get_db_dep)):
    server = await _get_server(server_id, db)
    data = await _fetch_brapi(server["url"], "studies")
    return data.get("result", {}).get("data", [])


@router.get("/brapi-servers/{server_id}/variables")
async def browse_variables(server_id: str, db=Depends(get_db_dep)):
    server = await _get_server(server_id, db)
    data = await _fetch_brapi(server["url"], "variables")
    return data.get("result", {}).get("data", [])


# --- Import from external server (into brapi DB) ---

@router.post("/brapi-servers/{server_id}/import/programs")
async def import_programs(server_id: str, db=Depends(get_db_dep), brapi_db=Depends(get_brapi_db_dep)):
    server = await _get_server(server_id, db)
    data = await _fetch_brapi(server["url"], "programs")
    programs = data.get("result", {}).get("data", [])

    imported = 0
    for p in programs:
        doc = {
            "_id": new_id(),
            "name": p.get("programName", ""),
            "abbreviation": p.get("abbreviation", ""),
            "objective": p.get("objective", ""),
            "crop": p.get("commonCropName", ""),
            "leadPerson": p.get("leadPersonName", ""),
            "sourceServer": server["url"],
            "sourceId": p.get("programDbId", ""),
        }
        await brapi_db["programs"].insert_one(doc)
        imported += 1

    return {"imported": imported, "message": f"Imported {imported} programs"}


@router.post("/brapi-servers/{server_id}/import/studies")
async def import_studies(server_id: str, db=Depends(get_db_dep), brapi_db=Depends(get_brapi_db_dep)):
    server = await _get_server(server_id, db)
    data = await _fetch_brapi(server["url"], "studies")
    studies = data.get("result", {}).get("data", [])

    imported = 0
    for s in studies:
        doc = {
            "_id": new_id(),
            "name": s.get("studyName", ""),
            "description": s.get("studyDescription", ""),
            "studyType": s.get("studyType", ""),
            "trialId": "",
            "startDate": s.get("startDate", ""),
            "endDate": s.get("endDate", ""),
            "locationId": s.get("locationDbId", ""),
            "programId": s.get("programDbId", ""),
            "observationVariableIds": s.get("observationVariableDbIds", []),
            "status": "active" if s.get("active", True) else "completed",
            "plantCount": 0,
            "sourceServer": server["url"],
            "sourceId": s.get("studyDbId", ""),
        }
        await brapi_db["studies"].insert_one(doc)
        imported += 1

    return {"imported": imported, "message": f"Imported {imported} studies"}


@router.post("/brapi-servers/{server_id}/import/observations")
async def import_observations(server_id: str, studyDbId: Optional[str] = None, db=Depends(get_db_dep), brapi_db=Depends(get_brapi_db_dep)):
    server = await _get_server(server_id, db)
    endpoint = "observations"
    if studyDbId:
        endpoint += f"?studyDbId={studyDbId}"
    data = await _fetch_brapi(server["url"], endpoint)
    observations = data.get("result", {}).get("data", [])

    imported = 0
    for o in observations:
        doc = {
            "_id": new_id(),
            "observationUnitId": o.get("observationUnitDbId", ""),
            "variableId": o.get("observationVariableDbId", ""),
            "variableName": o.get("observationVariableName", ""),
            "value": str(o.get("value", "")),
            "observationTimeStamp": o.get("observationTimeStamp", ""),
            "collector": o.get("collector", ""),
            "sourceServer": server["url"],
            "sourceId": o.get("observationDbId", ""),
        }
        await brapi_db["observations"].insert_one(doc)
        imported += 1

    return {"imported": imported, "message": f"Imported {imported} observations"}
