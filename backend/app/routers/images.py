"""
Image collection module.

Every uploaded image is validated by its file signature, fingerprinted with
SHA-256, bound to its capture time (EXIF → client file time → upload time)
and stored in GridFS together with the checksum. Downloads require either a
Bearer token or a short-lived HMAC-signed link and are checked against the
stored checksum, so silently corrupted or substituted files are never served.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.auth import get_current_user, get_optional_user, require_any_role
from app.config import (
    IMAGE_MAX_BYTES,
    IMAGE_MAX_MB,
    SENSOR_WINDOW_MINUTES,
    SIGNED_URL_SECRET,
    SIGNED_URL_TTL_SECONDS,
)
from app.database import get_brapi_db_dep, get_db_dep
from app.image_meta import (
    content_disposition,
    detect_image_type,
    parse_datetime,
    read_exif,
    resolve_capture_time,
    safe_filename,
    sha256_hex,
    sign_link,
    to_utc_iso,
    verify_link,
)
from app.models.schemas import new_id
from app.storage import StorageNotFound, get_storage_dep

router = APIRouter()

API_PREFIX = "/api/images"
KIND_ORIGINAL = "original"
KIND_ANNOTATED = "annotated"
MAX_SIGNED_PER_REQUEST = 2000


class RejectedFile(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class SignedUrlRequest(BaseModel):
    imageIds: List[str] = []
    annotatedIds: List[str] = []


def signed_url(kind: str, file_id: str) -> str:
    expires, sig = sign_link(SIGNED_URL_SECRET, kind, file_id, SIGNED_URL_TTL_SECONDS)
    path = "file" if kind == KIND_ORIGINAL else "annotated"
    return f"{API_PREFIX}/{path}/{file_id}?exp={expires}&sig={sig}"


def match_plant(file_name: str, plants: List[tuple]) -> tuple:
    """Find the plant whose name occurs in the file name; the longest name wins (P10 over P1)."""
    base = file_name.rsplit(".", 1)[0].lower()
    best = ("", "")
    for name, plant_id in plants:
        if name and name.lower() in base and len(name) > len(best[0]):
            best = (name, plant_id)
    return best


def _naive_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def public_image(doc: dict, with_url: bool = True) -> dict:
    out = dict(doc)
    out["id"] = out.pop("_id")
    out.pop("capturedAtTs", None)
    if with_url and out.get("gridfsId"):
        out["url"] = signed_url(KIND_ORIGINAL, out["id"])
    return out


async def _audit(db, action: str, user: Optional[dict], request: Optional[Request], image_id: str = "", study_id: str = "", **details):
    await db["image_audit"].insert_one({
        "_id": new_id(),
        "action": action,
        "imageId": image_id,
        "studyId": study_id,
        "userId": (user or {}).get("_id", ""),
        "userEmail": (user or {}).get("email", ""),
        "ip": request.client.host if request is not None and request.client else "",
        "at": to_utc_iso(datetime.now(timezone.utc)),
        "details": details,
    })


async def _read_limited(file: UploadFile) -> bytes:
    data = await file.read(IMAGE_MAX_BYTES + 1)
    if len(data) > IMAGE_MAX_BYTES:
        raise RejectedFile(413, f"Файл больше {IMAGE_MAX_MB} МБ")
    return data


async def _ingest(
    db,
    storage,
    *,
    data: bytes,
    file_name: Optional[str],
    study_id: str,
    folder_name: str,
    observation_unit_id: str,
    plant_name: str,
    client_time,
    user: dict,
    request: Request,
) -> dict:
    name = safe_filename(file_name)
    if not data:
        raise RejectedFile(400, "Пустой файл")
    mime = detect_image_type(data)
    if mime is None:
        raise RejectedFile(415, "Неподдерживаемый формат: принимаются JPEG, PNG, TIFF, BMP и WebP")

    digest = sha256_hex(data)
    if study_id:
        existing = await db["images"].find_one({"studyId": study_id, "sha256": digest})
        if existing:
            out = public_image(existing)
            out["duplicate"] = True
            out["uploadedName"] = name
            return out

    now = datetime.now(timezone.utc)
    exif = read_exif(data)
    captured_at, source = resolve_capture_time(exif.get("capturedAt"), parse_datetime(client_time), now)

    image_id = new_id()
    grid_id = await storage.put(name, data, metadata={
        "image_id": image_id,
        "mimeType": mime,
        "sha256": digest,
        "studyId": study_id,
    })
    doc = {
        "_id": image_id,
        "fileName": name,
        "mimeType": mime,
        "size": len(data),
        "sha256": digest,
        "observationUnitId": observation_unit_id,
        "matchedPlantName": plant_name,
        "studyId": study_id,
        "folderName": folder_name,
        "gridfsId": grid_id,
        "status": "pending",
        "capturedAt": to_utc_iso(captured_at),
        "capturedAtTs": _naive_utc(captured_at),
        "capturedAtSource": source,
        "uploadedAt": to_utc_iso(now),
        "uploadedBy": user.get("email", "") or user.get("_id", ""),
        "width": exif.get("width"),
        "height": exif.get("height"),
        "cameraMake": exif.get("cameraMake", ""),
        "cameraModel": exif.get("cameraModel", ""),
    }
    await db["images"].insert_one(doc)
    await _audit(db, "upload", user, request, image_id, study_id, sha256=digest, size=len(data), capturedAtSource=source)
    return public_image(doc)


async def _ingest_many(db, storage, files, captured_at, *, study_id, folder_name, plant_lookup, user, request):
    times = captured_at if len(captured_at) == len(files) else [None] * len(files)
    results = []
    for file, client_time in zip(files, times):
        try:
            data = await _read_limited(file)
            ou_id, plant_name = plant_lookup(file.filename or "")
            results.append(await _ingest(
                db, storage,
                data=data, file_name=file.filename, study_id=study_id, folder_name=folder_name,
                observation_unit_id=ou_id, plant_name=plant_name, client_time=client_time,
                user=user, request=request,
            ))
        except RejectedFile as e:
            await _audit(db, "upload_rejected", user, request, "", study_id, fileName=safe_filename(file.filename), reason=e.detail)
            results.append({
                "fileName": safe_filename(file.filename),
                "status": "rejected",
                "error": e.detail,
            })
    return results


@router.post("/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    observationUnitId: str = Form(""),
    studyId: str = Form(""),
    folderName: str = Form(""),
    capturedAt: str = Form(""),
    db=Depends(get_db_dep),
    storage=Depends(get_storage_dep),
    user=Depends(get_current_user),
):
    try:
        data = await _read_limited(file)
        return await _ingest(
            db, storage,
            data=data, file_name=file.filename, study_id=studyId, folder_name=folderName,
            observation_unit_id=observationUnitId, plant_name="", client_time=capturedAt,
            user=user, request=request,
        )
    except RejectedFile as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/upload-batch")
async def upload_batch(
    request: Request,
    files: List[UploadFile] = File(...),
    studyId: str = Form(""),
    folderName: str = Form(""),
    capturedAt: List[str] = Form(default=[]),
    db=Depends(get_db_dep),
    brapi_db=Depends(get_brapi_db_dep),
    storage=Depends(get_storage_dep),
    user=Depends(get_current_user),
):
    plants = []
    if studyId:
        async for ou in brapi_db["observation_units"].find({"studyId": studyId}, {"name": 1}):
            plants.append((ou.get("name", ""), ou["_id"]))

    def lookup(file_name):
        name, plant_id = match_plant(file_name, plants)
        return plant_id, name

    return await _ingest_many(
        db, storage, files, capturedAt,
        study_id=studyId, folder_name=folderName, plant_lookup=lookup, user=user, request=request,
    )


@router.post("/upload-plant")
async def upload_plant_images(
    request: Request,
    files: List[UploadFile] = File(...),
    studyId: str = Form(""),
    folderName: str = Form(""),
    observationUnitId: str = Form(""),
    capturedAt: List[str] = Form(default=[]),
    db=Depends(get_db_dep),
    brapi_db=Depends(get_brapi_db_dep),
    storage=Depends(get_storage_dep),
    user=Depends(get_current_user),
):
    plant_name = ""
    if observationUnitId:
        ou = await brapi_db["observation_units"].find_one({"_id": observationUnitId})
        if ou:
            plant_name = ou.get("name", "")

    return await _ingest_many(
        db, storage, files, capturedAt,
        study_id=studyId, folder_name=folderName,
        plant_lookup=lambda _name: (observationUnitId, plant_name),
        user=user, request=request,
    )


@router.get("/by-study/{study_id}")
async def get_images_by_study(study_id: str, db=Depends(get_db_dep), user=Depends(get_current_user)):
    items = []
    async for img in db["images"].find({"studyId": study_id}).sort("capturedAt", 1):
        items.append(public_image(img))
    return items


@router.post("/signed-urls")
async def get_signed_urls(req: SignedUrlRequest, user=Depends(get_current_user)):
    """Issue short-lived links for <img> tags, which cannot send an Authorization header."""
    if len(req.imageIds) + len(req.annotatedIds) > MAX_SIGNED_PER_REQUEST:
        raise HTTPException(status_code=400, detail=f"At most {MAX_SIGNED_PER_REQUEST} links per request")
    return {
        "expiresIn": SIGNED_URL_TTL_SECONDS,
        "images": {i: signed_url(KIND_ORIGINAL, i) for i in dict.fromkeys(req.imageIds) if i},
        "annotated": {i: signed_url(KIND_ANNOTATED, i) for i in dict.fromkeys(req.annotatedIds) if i},
    }


async def _authorize_download(db, request, user, kind, file_id, exp, sig):
    if user is not None:
        return
    if exp and sig and verify_link(SIGNED_URL_SECRET, kind, file_id, exp, sig):
        return
    await _audit(db, "download_denied", None, request, file_id if kind == KIND_ORIGINAL else "", kind=kind)
    raise HTTPException(status_code=401, detail="Signed link is missing, invalid or expired")


def _binary_response(data: bytes, mime: str, file_name: str, digest: str) -> Response:
    return Response(
        content=data,
        media_type=mime,
        headers={
            "Content-Disposition": content_disposition("inline", file_name),
            "X-Content-SHA256": digest,
            "ETag": f"\"{digest}\"",
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/file/{image_id}")
async def get_image_file(
    image_id: str,
    request: Request,
    exp: Optional[str] = None,
    sig: Optional[str] = None,
    db=Depends(get_db_dep),
    storage=Depends(get_storage_dep),
    user=Depends(get_optional_user),
):
    """Serve the original image after checking access and the stored SHA-256."""
    await _authorize_download(db, request, user, KIND_ORIGINAL, image_id, exp, sig)
    doc = await db["images"].find_one({"_id": image_id})
    if not doc or not doc.get("gridfsId"):
        raise HTTPException(status_code=404, detail="Image not found")
    try:
        data = await storage.get(doc["gridfsId"])
    except StorageNotFound:
        raise HTTPException(status_code=404, detail="File not found in storage")

    digest = sha256_hex(data)
    if doc.get("sha256") and doc["sha256"] != digest:
        await _audit(db, "integrity_failed", user, request, image_id, doc.get("studyId", ""), expected=doc["sha256"], actual=digest)
        raise HTTPException(status_code=409, detail="Stored file does not match its checksum")
    return _binary_response(data, doc.get("mimeType") or "application/octet-stream", doc.get("fileName", "image"), digest)


@router.get("/annotated/{gridfs_id}")
async def get_annotated_image(
    gridfs_id: str,
    request: Request,
    exp: Optional[str] = None,
    sig: Optional[str] = None,
    db=Depends(get_db_dep),
    storage=Depends(get_storage_dep),
    user=Depends(get_optional_user),
):
    """Serve an annotated image produced by an analysis run."""
    await _authorize_download(db, request, user, KIND_ANNOTATED, gridfs_id, exp, sig)
    try:
        data = await storage.get(gridfs_id)
    except StorageNotFound:
        raise HTTPException(status_code=404, detail="Annotated image not found")
    return _binary_response(data, "image/jpeg", "annotated.jpg", sha256_hex(data))


@router.get("/timeline/{study_id}")
async def get_timeline(study_id: str, db=Depends(get_db_dep), user=Depends(get_current_user)):
    """Images of a study grouped by capture date — the time axis of the experiment."""
    days: dict = {}
    undated = 0
    async for img in db["images"].find({"studyId": study_id}):
        captured = img.get("capturedAt") or ""
        if not captured:
            undated += 1
            continue
        day = days.setdefault(captured[:10], {"count": 0, "plants": set(), "folders": set(), "first": captured, "last": captured})
        day["count"] += 1
        if img.get("observationUnitId"):
            day["plants"].add(img["observationUnitId"])
        if img.get("folderName"):
            day["folders"].add(img["folderName"])
        day["first"] = min(day["first"], captured)
        day["last"] = max(day["last"], captured)
    return {
        "studyId": study_id,
        "undated": undated,
        "days": [
            {
                "date": date,
                "count": d["count"],
                "plants": len(d["plants"]),
                "folders": sorted(d["folders"]),
                "firstAt": d["first"],
                "lastAt": d["last"],
            }
            for date, d in sorted(days.items())
        ],
    }


@router.get("/integrity/{study_id}")
async def check_study_integrity(
    study_id: str,
    request: Request,
    db=Depends(get_db_dep),
    storage=Depends(get_storage_dep),
    user=Depends(get_current_user),
):
    """Re-hash every stored image of a study and compare with the checksums saved at upload."""
    report = {"studyId": study_id, "checked": 0, "ok": 0, "legacy": 0, "failed": [], "missing": []}
    async for img in db["images"].find({"studyId": study_id}):
        report["checked"] += 1
        try:
            data = await storage.get(img.get("gridfsId", ""))
        except StorageNotFound:
            report["missing"].append(img["_id"])
            continue
        if not img.get("sha256"):
            report["legacy"] += 1
        elif sha256_hex(data) == img["sha256"]:
            report["ok"] += 1
        else:
            report["failed"].append(img["_id"])
    report["checkedAt"] = to_utc_iso(datetime.now(timezone.utc))
    await _audit(db, "integrity_check", user, request, "", study_id,
                 checked=report["checked"], failed=len(report["failed"]), missing=len(report["missing"]))
    return report


@router.get("/{image_id}/verify")
async def verify_image(
    image_id: str,
    request: Request,
    db=Depends(get_db_dep),
    storage=Depends(get_storage_dep),
    user=Depends(get_current_user),
):
    doc = await db["images"].find_one({"_id": image_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Image not found")
    try:
        actual = sha256_hex(await storage.get(doc.get("gridfsId", "")))
    except StorageNotFound:
        raise HTTPException(status_code=404, detail="File not found in storage")
    expected = doc.get("sha256")
    ok = None if not expected else expected == actual
    checked_at = to_utc_iso(datetime.now(timezone.utc))
    await db["images"].update_one({"_id": image_id}, {"$set": {"integrityOk": ok, "integrityCheckedAt": checked_at}})
    await _audit(db, "verify", user, request, image_id, doc.get("studyId", ""), ok=ok)
    return {"imageId": image_id, "ok": ok, "expected": expected, "actual": actual, "checkedAt": checked_at}


@router.get("/{image_id}/environment")
async def get_image_environment(
    image_id: str,
    db=Depends(get_db_dep),
    brapi_db=Depends(get_brapi_db_dep),
    user=Depends(get_current_user),
):
    """Climate-chamber readings recorded closest to the moment the image was captured."""
    doc = await db["images"].find_one({"_id": image_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Image not found")
    captured = parse_datetime(doc.get("capturedAt"))
    study = await brapi_db["studies"].find_one({"_id": doc.get("studyId", "")}) if doc.get("studyId") else None
    chamber_id = (study or {}).get("climateChamberId") or ""
    result = {"imageId": image_id, "capturedAt": doc.get("capturedAt"), "chamberId": chamber_id or None,
              "windowMinutes": SENSOR_WINDOW_MINUTES, "readings": []}
    if not captured or not chamber_id:
        return result

    chamber = await db["climate_chambers"].find_one({"_id": chamber_id}) or {}
    sensors = {s.get("id"): s for s in chamber.get("sensors", [])}
    window = timedelta(minutes=SENSOR_WINDOW_MINUTES)
    center = _naive_utc(captured)
    nearest: dict = {}
    async for r in db["sensor_readings"].find({
        "chamberId": chamber_id,
        "ts": {"$gte": center - window, "$lte": center + window},
    }):
        delta = abs((r["ts"] - center).total_seconds())
        sid = r.get("sensorId", "")
        if sid not in nearest or delta < nearest[sid][0]:
            nearest[sid] = (delta, r)
    for sid, (delta, r) in sorted(nearest.items()):
        sensor = sensors.get(sid, {})
        result["readings"].append({
            "sensorId": sid,
            "name": sensor.get("name", sid),
            "type": sensor.get("type", ""),
            "unit": sensor.get("unit", ""),
            "value": r.get("value"),
            "timestamp": r.get("timestamp"),
            "deltaSeconds": int(delta),
        })
    return result


@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    request: Request,
    db=Depends(get_db_dep),
    storage=Depends(get_storage_dep),
    user=Depends(require_any_role("admin", "researcher")),
):
    doc = await db["images"].find_one({"_id": image_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if doc.get("gridfsId"):
        await storage.delete(doc["gridfsId"])
    await db["images"].delete_one({"_id": image_id})
    await _audit(db, "delete", user, request, image_id, doc.get("studyId", ""),
                 fileName=doc.get("fileName", ""), sha256=doc.get("sha256", ""))
    return {"ok": True}
