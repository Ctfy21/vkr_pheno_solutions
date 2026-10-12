import re
from datetime import datetime, timezone
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.auth import get_current_user
from app.config import PDF_MAX_THUMBNAILS
from app.database import get_brapi_db_dep, get_db_dep
from app.export import BUILDERS, MEDIA_TYPES, ExportDataset, build_dataset
from app.image_meta import content_disposition
from app.storage import StorageNotFound, get_storage_dep
from app.study_data import load_study_data

router = APIRouter()

ExportFormat = Literal["xlsx", "pdf", "csv", "json"]
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ExportRequest(BaseModel):
    format: ExportFormat = "xlsx"
    study_ids: List[str]
    variable_ids: List[str] = []
    variable_names: List[str] = []
    date_from: str = ""
    date_to: str = ""


def _check_date(value: str, field: str) -> str:
    value = (value or "").strip()
    if value and not _DATE_RE.match(value):
        raise HTTPException(status_code=422, detail=f"{field} must be YYYY-MM-DD")
    return value


def _thumbnail_order(rows: list) -> list:
    """Annotated rows, latest capture first, alternating treatment groups so each group is shown."""
    candidates = sorted((r for r in rows if r.get("annotatedImageId")),
                        key=lambda r: r.get("capturedAt") or "", reverse=True)
    queues: dict = {}
    for r in candidates:
        queues.setdefault(r.get("treatment") or "", []).append(r)
    ordered = []
    while any(queues.values()):
        for q in queues.values():
            if q:
                ordered.append(q.pop(0))
    return ordered


async def _thumbnails(storage, ds: ExportDataset) -> list:
    values = {(r["imageId"], r["trait"]): r["value"] for r in ds.records}
    thumbs = []
    for row in _thumbnail_order(ds.rows):
        if len(thumbs) >= PDF_MAX_THUMBNAILS:
            break
        file_id = row.get("annotatedImageId")
        if not file_id:
            continue
        try:
            data = await storage.get(file_id)
        except StorageNotFound:
            continue
        parts = [row["plant"] or row["image"], (row["capturedAt"] or "")[:10]]
        h, a = values.get((row["imageId"], "height")), values.get((row["imageId"], "leaf_area"))
        if h is not None:
            parts.append(f"высота {h:.1f} см".replace(".", ","))
        if a is not None:
            parts.append(f"площадь {a:.1f} см²".replace(".", ","))
        thumbs.append((" · ".join(p for p in parts if p), data))
    return thumbs


async def build_export(db, brapi_db, storage, user: dict, study_ids: List[str], fmt: str,
                       variable_ids: List[str] = (), variable_names: List[str] = (),
                       date_from: str = "", date_to: str = "") -> ExportDataset:
    if fmt not in BUILDERS:
        raise HTTPException(status_code=422, detail="format must be one of: " + ", ".join(BUILDERS))
    date_from = _check_date(date_from, "date_from")
    date_to = _check_date(date_to, "date_to")
    data = await load_study_data(db, brapi_db, list(study_ids))
    if not data.studies:
        raise HTTPException(status_code=404, detail="Study not found")

    names, co_terms = list(variable_names), []
    if variable_ids:
        async for var in brapi_db["observation_variables"].find({"_id": {"$in": list(variable_ids)}}):
            if var.get("name"):
                names.append(var["name"])
            if var.get("coTermId"):
                co_terms.append(var["coTermId"])

    ds = build_dataset(
        data.studies, data.runs, data.images, data.plants,
        variable_names=names, co_term_ids=co_terms, date_from=date_from, date_to=date_to,
        generated_by=user.get("email", "") or user.get("name", ""),
    )
    if fmt == "pdf":
        ds.thumbnails = await _thumbnails(storage, ds)
    return ds


def export_response(ds: ExportDataset, fmt: str) -> Response:
    content = BUILDERS[fmt](ds)
    base = re.sub(r"\s+", "_", ds.title)[:60] if len(ds.studies) == 1 else "phenotyping_export"
    filename = f"{base}_{datetime.now(timezone.utc):%Y%m%d}.{fmt}"
    return Response(
        content=content,
        media_type=MEDIA_TYPES[fmt],
        headers={"Content-Disposition": content_disposition("attachment", filename)},
    )


@router.post("")
async def export_studies(
    req: ExportRequest,
    db=Depends(get_db_dep),
    brapi_db=Depends(get_brapi_db_dep),
    storage=Depends(get_storage_dep),
    user=Depends(get_current_user),
):
    """Export results of one or several experiments to XLSX, PDF, CSV or BrAPI-style JSON."""
    if not req.study_ids:
        raise HTTPException(status_code=422, detail="Select at least one experiment")
    ds = await build_export(db, brapi_db, storage, user, req.study_ids, req.format,
                            req.variable_ids, req.variable_names, req.date_from, req.date_to)
    return export_response(ds, req.format)
