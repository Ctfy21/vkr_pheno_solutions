"""
BrAPI v2.1 compatible endpoints for PhenoPlant.
Spec: https://brapi.org/specification
"""
import math
from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.database import get_brapi_db_dep

router = APIRouter()


def brapi_response(data: list, page: int = 0, page_size: int = 1000):
    total_count = len(data)
    total_pages = max(1, math.ceil(total_count / page_size)) if total_count > 0 else 0
    start = page * page_size
    end = start + page_size
    paginated = data[start:end]
    return {
        "metadata": {
            "datafiles": [],
            "status": [{"message": "Request accepted", "messageType": "INFO"}],
            "pagination": {
                "currentPage": page,
                "pageSize": page_size,
                "totalCount": total_count,
                "totalPages": total_pages,
            },
        },
        "result": {"data": paginated},
    }


def brapi_single_response(data: dict):
    return {
        "metadata": {
            "datafiles": [],
            "status": [{"message": "Request accepted", "messageType": "INFO"}],
            "pagination": {
                "currentPage": 0,
                "pageSize": 1,
                "totalCount": 1,
                "totalPages": 1,
            },
        },
        "result": data,
    }


def str_id(doc: dict) -> str:
    val = doc.get("_id", "")
    return str(val)


@router.get("/serverinfo")
async def server_info():
    calls = [
        {"contentTypes": ["application/json"], "methods": ["GET"], "service": "/brapi/v2/programs", "versions": ["2.1"]},
        {"contentTypes": ["application/json"], "methods": ["GET"], "service": "/brapi/v2/trials", "versions": ["2.1"]},
        {"contentTypes": ["application/json"], "methods": ["GET"], "service": "/brapi/v2/studies", "versions": ["2.1"]},
        {"contentTypes": ["application/json"], "methods": ["GET"], "service": "/brapi/v2/studies/{studyDbId}", "versions": ["2.1"]},
        {"contentTypes": ["application/json"], "methods": ["GET"], "service": "/brapi/v2/observationunits", "versions": ["2.1"]},
        {"contentTypes": ["application/json"], "methods": ["GET"], "service": "/brapi/v2/observations", "versions": ["2.1"]},
        {"contentTypes": ["application/json"], "methods": ["GET"], "service": "/brapi/v2/variables", "versions": ["2.1"]},
        {"contentTypes": ["application/json"], "methods": ["GET"], "service": "/brapi/v2/germplasm", "versions": ["2.1"]},
        {"contentTypes": ["application/json"], "methods": ["GET"], "service": "/brapi/v2/serverinfo", "versions": ["2.1"]},
    ]
    return brapi_single_response({
        "contactEmail": "",
        "documentationURL": "https://brapi.org",
        "location": "PhenoPlant Instance",
        "organizationName": "PhenoPlant",
        "organizationURL": "",
        "serverDescription": "PhenoPlant BrAPI v2.1 Server",
        "serverName": "PhenoPlant",
        "calls": calls,
    })


@router.get("/programs")
async def list_programs(
    page: int = Query(0, ge=0),
    pageSize: int = Query(1000, ge=1, le=10000),
    db=Depends(get_brapi_db_dep),
):
    items = []
    async for doc in db["programs"].find():
        items.append({
            "programDbId": str_id(doc),
            "programName": doc.get("name", ""),
            "abbreviation": doc.get("abbreviation", ""),
            "objective": doc.get("objective", ""),
            "leadPersonDbId": doc.get("leadPerson", ""),
            "leadPersonName": doc.get("leadPerson", ""),
            "commonCropName": doc.get("crop", ""),
            "additionalInfo": {},
            "externalReferences": [],
        })
    return brapi_response(items, page, pageSize)


@router.get("/trials")
async def list_trials(
    programDbId: Optional[str] = None,
    page: int = Query(0, ge=0),
    pageSize: int = Query(1000, ge=1, le=10000),
    db=Depends(get_brapi_db_dep),
):
    query = {}
    if programDbId:
        query["programId"] = programDbId
    items = []
    async for doc in db["trials"].find(query):
        items.append({
            "trialDbId": str_id(doc),
            "trialName": doc.get("name", ""),
            "trialDescription": doc.get("description", ""),
            "programDbId": doc.get("programId", ""),
            "programName": "",
            "startDate": doc.get("startDate", ""),
            "endDate": doc.get("endDate", ""),
            "active": doc.get("active", True),
            "additionalInfo": {},
            "externalReferences": [],
        })
    return brapi_response(items, page, pageSize)


@router.get("/studies")
async def list_studies(
    trialDbId: Optional[str] = None,
    programDbId: Optional[str] = None,
    studyType: Optional[str] = None,
    page: int = Query(0, ge=0),
    pageSize: int = Query(1000, ge=1, le=10000),
    db=Depends(get_brapi_db_dep),
):
    query = {}
    if trialDbId:
        query["trialId"] = trialDbId
    if programDbId:
        query["programId"] = programDbId
    if studyType:
        query["studyType"] = studyType
    items = []
    async for doc in db["studies"].find(query):
        items.append(_study_to_brapi(doc))
    return brapi_response(items, page, pageSize)


@router.get("/studies/{studyDbId}")
async def get_study(studyDbId: str, db=Depends(get_brapi_db_dep)):
    doc = await db["studies"].find_one({"_id": studyDbId})
    if not doc:
        return {
            "metadata": {
                "datafiles": [],
                "status": [{"message": "Study not found", "messageType": "ERROR"}],
                "pagination": {"currentPage": 0, "pageSize": 0, "totalCount": 0, "totalPages": 0},
            },
            "result": {},
        }
    return brapi_single_response(_study_to_brapi(doc))


def _study_to_brapi(doc: dict) -> dict:
    return {
        "studyDbId": str_id(doc),
        "studyName": doc.get("name", ""),
        "studyDescription": doc.get("description", ""),
        "studyType": doc.get("studyType", ""),
        "trialDbId": doc.get("trialId", ""),
        "trialName": "",
        "startDate": doc.get("startDate", ""),
        "endDate": doc.get("endDate", ""),
        "locationDbId": doc.get("locationId", ""),
        "programDbId": doc.get("programId", ""),
        "active": doc.get("status", "") != "completed",
        "additionalInfo": {},
        "externalReferences": [],
        "observationVariableDbIds": doc.get("observationVariableIds", []),
    }


@router.get("/observationunits")
async def list_observation_units(
    studyDbId: Optional[str] = None,
    germplasmDbId: Optional[str] = None,
    page: int = Query(0, ge=0),
    pageSize: int = Query(1000, ge=1, le=10000),
    db=Depends(get_brapi_db_dep),
):
    query = {}
    if studyDbId:
        query["studyId"] = studyDbId
    if germplasmDbId:
        query["germplasmId"] = germplasmDbId
    items = []
    async for doc in db["observation_units"].find(query):
        items.append({
            "observationUnitDbId": str_id(doc),
            "observationUnitName": doc.get("name", ""),
            "studyDbId": doc.get("studyId", ""),
            "germplasmDbId": doc.get("germplasmId", ""),
            "observationUnitPosition": {
                "positionCoordinateX": doc.get("position", ""),
                "positionCoordinateXType": "GRID_COL",
                "positionCoordinateY": "",
                "positionCoordinateYType": "GRID_ROW",
            },
            "treatments": [{"factor": "treatment", "modality": doc.get("treatment", "")}] if doc.get("treatment") else [],
            "additionalInfo": {},
            "externalReferences": [],
        })
    return brapi_response(items, page, pageSize)


@router.get("/observations")
async def list_observations(
    studyDbId: Optional[str] = None,
    observationUnitDbId: Optional[str] = None,
    observationVariableDbId: Optional[str] = None,
    page: int = Query(0, ge=0),
    pageSize: int = Query(1000, ge=1, le=10000),
    db=Depends(get_brapi_db_dep),
):
    query = {}
    if observationUnitDbId:
        query["observationUnitId"] = observationUnitDbId
    if observationVariableDbId:
        query["variableId"] = observationVariableDbId

    ou_ids = None
    if studyDbId:
        ou_ids = []
        async for ou in db["observation_units"].find({"studyId": studyDbId}, {"_id": 1}):
            ou_ids.append(ou["_id"])
        query["observationUnitId"] = {"$in": ou_ids}

    items = []
    async for doc in db["observations"].find(query):
        items.append({
            "observationDbId": str_id(doc),
            "observationUnitDbId": doc.get("observationUnitId", ""),
            "observationVariableDbId": doc.get("variableId", ""),
            "observationVariableName": doc.get("variableName", ""),
            "value": doc.get("value", ""),
            "observationTimeStamp": doc.get("observationTimeStamp", ""),
            "collector": doc.get("collector", ""),
            "studyDbId": studyDbId or "",
            "additionalInfo": {},
            "externalReferences": [],
        })
    return brapi_response(items, page, pageSize)


@router.get("/variables")
async def list_variables(
    page: int = Query(0, ge=0),
    pageSize: int = Query(1000, ge=1, le=10000),
    db=Depends(get_brapi_db_dep),
):
    items = []
    async for doc in db["variables"].find():
        trait = await db["traits"].find_one({"_id": doc.get("traitId", "")}) or {}
        method = await db["methods"].find_one({"_id": doc.get("methodId", "")}) or {}
        scale = await db["scales"].find_one({"_id": doc.get("scaleId", "")}) or {}

        items.append({
            "observationVariableDbId": str_id(doc),
            "observationVariableName": doc.get("name", ""),
            "trait": {
                "traitDbId": doc.get("traitId", ""),
                "traitName": trait.get("traitName", ""),
                "traitDescription": trait.get("traitDescription", ""),
                "traitClass": trait.get("traitClass", ""),
            },
            "method": {
                "methodDbId": doc.get("methodId", ""),
                "methodName": method.get("methodName", ""),
                "methodClass": method.get("methodClass", ""),
                "description": method.get("description", ""),
            },
            "scale": {
                "scaleDbId": doc.get("scaleId", ""),
                "scaleName": scale.get("scaleName", ""),
                "dataType": scale.get("dataType", ""),
                "validValues": {"categories": scale.get("validValues", [])},
            },
            "ontologyReference": {
                "ontologyDbId": doc.get("coTermId", ""),
                "ontologyName": "",
                "version": "",
            },
            "additionalInfo": {},
            "externalReferences": [],
        })
    return brapi_response(items, page, pageSize)


@router.get("/germplasm")
async def list_germplasm(
    page: int = Query(0, ge=0),
    pageSize: int = Query(1000, ge=1, le=10000),
    db=Depends(get_brapi_db_dep),
):
    items = []
    async for doc in db["germplasm"].find():
        items.append({
            "germplasmDbId": str_id(doc),
            "germplasmName": doc.get("germplasmName", ""),
            "defaultDisplayName": doc.get("germplasmName", ""),
            "genus": doc.get("genus", ""),
            "species": doc.get("species", ""),
            "accessionNumber": doc.get("accessionNumber", ""),
            "pedigree": doc.get("pedigree", ""),
            "instituteCode": doc.get("instituteCode", ""),
            "additionalInfo": {},
            "externalReferences": [],
        })
    return brapi_response(items, page, pageSize)
