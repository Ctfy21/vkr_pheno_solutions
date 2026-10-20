from datetime import datetime, timezone
import io
import json
import zipfile
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from app.analyze import measure_plant_height, plantcv_rgb_analysis, create_annotated_image
from app.auth import get_current_user
from app.database import get_db_dep, get_brapi_db_dep
from app.export import build_csv, build_pdf, build_xlsx
from app.image_meta import content_disposition, sha256_hex
from app.models.schemas import StudyCreate, StudyOut, new_id
from app.routers.export import build_export, export_response
from app.routers.images import public_image
from app.storage import StorageNotFound, get_storage_dep
from app.study_data import load_study_data
from app.trait_analysis import collect_records, summarize


class RunAnalysisRequest(BaseModel):
    solution_id: str
    folder_name: str

router = APIRouter()


@router.get("")
async def list_studies(brapi_db=Depends(get_brapi_db_dep), user=Depends(get_current_user)):
    items = []
    async for doc in brapi_db["studies"].find():
        doc["id"] = doc.pop("_id")
        items.append(doc)
    return items


@router.get("/{study_id}")
async def get_study(study_id: str, brapi_db=Depends(get_brapi_db_dep), user=Depends(get_current_user)):
    doc = await brapi_db["studies"].find_one({"_id": study_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Study not found")
    doc["id"] = doc.pop("_id")
    return doc


@router.get("/{study_id}/observation-units")
async def get_observation_units(study_id: str, brapi_db=Depends(get_brapi_db_dep), db=Depends(get_db_dep), user=Depends(get_current_user)):
    items = []
    async for doc in brapi_db["observation_units"].find({"studyId": study_id}):
        doc["id"] = doc.pop("_id")
        # Attach observations from brapi_db
        observations = []
        async for obs in brapi_db["observations"].find({"observationUnitId": doc["id"]}):
            obs["id"] = obs.pop("_id")
            observations.append(obs)
        doc["observations"] = observations
        # Attach images from local db
        imgs = []
        async for img in db["images"].find({"observationUnitId": doc["id"]}):
            imgs.append(public_image(img))
        doc["images"] = imgs
        items.append(doc)
    return items


@router.get("/{study_id}/images")
async def get_study_images(study_id: str, brapi_db=Depends(get_brapi_db_dep), db=Depends(get_db_dep), user=Depends(get_current_user)):
    ou_ids = []
    async for doc in brapi_db["observation_units"].find({"studyId": study_id}, {"_id": 1}):
        ou_ids.append(doc["_id"])
    items = {}
    if ou_ids:
        async for img in db["images"].find({"observationUnitId": {"$in": ou_ids}}):
            items[img["_id"]] = public_image(img)
    # Also get images linked directly by studyId
    async for img in db["images"].find({"studyId": study_id}):
        items.setdefault(img["_id"], public_image(img))
    return list(items.values())


@router.post("")
async def create_study(item: StudyCreate, brapi_db=Depends(get_brapi_db_dep), user=Depends(get_current_user)):
    study_id = new_id()
    doc = item.model_dump(by_alias=False, exclude={"plants"})
    doc["_id"] = study_id
    await brapi_db["studies"].insert_one(doc)

    plants = item.plants or []
    created_plants = 0
    for p in plants:
        if not p.name:
            continue
        ou_doc = {
            "_id": new_id(),
            "name": p.name,
            "studyId": study_id,
            "germplasmId": p.germplasm_id,
            "position": p.position,
            "treatment": p.treatment,
        }
        await brapi_db["observation_units"].insert_one(ou_doc)
        created_plants += 1

    if created_plants > 0:
        await brapi_db["studies"].update_one(
            {"_id": study_id},
            {"$set": {"plantCount": created_plants}},
        )
        doc["plantCount"] = created_plants

    doc["id"] = doc.pop("_id")
    return doc


@router.delete("/{item_id}")
async def delete_study(item_id: str, brapi_db=Depends(get_brapi_db_dep), user=Depends(get_current_user)):
    result = await brapi_db["studies"].delete_one({"_id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    await brapi_db["observation_units"].delete_many({"studyId": item_id})
    return {"ok": True}


# CropOntology term -> (metric produced by the algorithm, default unit)
METRIC_MAP = {
    "CO_321:0000020": ("height_cm", "см"),
    "CO_321:0000080": ("leaf_area_cm2", "см²"),
}
RAW_KEYS = ["height_cm", "leaf_area_cm2", "height_px", "green_area_px", "scale_px_per_cm", "height_ratio"]
RAW_KEYS_RGB = ["green_index", "compactness", "bbox_width_cm"]


def _pick_algorithm(solution: dict):
    """Choose the analysis function by the solution config, falling back to its name."""
    method = (solution.get("config") or {}).get("method", "")
    name = solution.get("name", "").lower()
    if method.startswith("plantcv_rgb") or "plantcv" in name or "rgb" in name:
        return plantcv_rgb_analysis
    return measure_plant_height


def _measurements(measurement: dict, output_vars: list) -> list:
    out = []
    for ov in output_vars:
        co_id = ov.get("coTermId", "")
        var_name = ov.get("name", "") or co_id
        metric, default_unit = METRIC_MAP.get(co_id, (None, ""))
        if metric is None:
            low = var_name.lower()
            metric = "leaf_area_cm2" if ("area" in low or "leaf" in low or "площад" in low) else "height_cm"
            default_unit = "см²" if metric == "leaf_area_cm2" else "см"
        value = float(measurement.get(metric, 0.0) or 0.0)
        unit = ov.get("unit") or default_unit
        out.append({
            "coTermId": co_id,
            "variableName": var_name,
            "value": round(value, 2),
            "unit": unit,
            "displayValue": f"{round(value, 2)} {unit}",
        })
    keys = RAW_KEYS + (RAW_KEYS_RGB if measurement.get("method", "").startswith("plantcv_rgb") else [])
    for key in keys:
        if key in measurement and not any(m["variableName"] == key for m in out):
            val = measurement[key]
            val = round(float(val), 4) if isinstance(val, float) else val
            out.append({"coTermId": "", "variableName": key, "value": val, "unit": "", "displayValue": str(val)})
    return out


@router.post("/{study_id}/run-analysis")
async def run_analysis(
    study_id: str,
    req: RunAnalysisRequest,
    db=Depends(get_db_dep),
    brapi_db=Depends(get_brapi_db_dep),
    storage=Depends(get_storage_dep),
    user=Depends(get_current_user),
):
    """Run a phenotyping solution on a folder of images and extract height and leaf area."""
    study = await brapi_db["studies"].find_one({"_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    solution = await db["phenotyping_solutions"].find_one({"_id": req.solution_id})
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    images = []
    async for img in db["images"].find({"studyId": study_id, "folderName": req.folder_name}).sort("capturedAt", 1):
        images.append(img)
    if not images:
        raise HTTPException(status_code=400, detail="No images in this folder")

    if study.get("status") == "draft":
        await brapi_db["studies"].update_one({"_id": study_id}, {"$set": {"status": "active"}})

    sol_config = solution.get("config", {})
    output_vars = solution.get("outputVariables", [])
    # No fixed scale in the solution: read it from the ruler in each image
    scale_px_per_cm = sol_config.get("scale_px_per_cm", 0.0)
    algorithm = _pick_algorithm(solution)

    run_id = new_id()
    run_doc = {
        "_id": run_id,
        "studyId": study_id,
        "solutionId": req.solution_id,
        "solutionName": solution.get("name", ""),
        "folderName": req.folder_name,
        "imageCount": len(images),
        "outputVariables": output_vars,
        "config": sol_config,
        "status": "completed",
        "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "createdBy": user.get("email", ""),
        "results": [],
    }

    for img in images:
        result_entry = {
            "imageId": img["_id"],
            "fileName": img.get("fileName", ""),
            "plantName": img.get("matchedPlantName", ""),
            "capturedAt": img.get("capturedAt", ""),
            "measurements": [],
            "metrics": {},
        }
        try:
            image_bytes = await storage.get(img.get("gridfsId", ""))
            if img.get("sha256") and sha256_hex(image_bytes) != img["sha256"]:
                raise ValueError("integrity check failed: stored file does not match its checksum")
            measurement = algorithm(image_bytes, scale_px_per_cm=scale_px_per_cm)
            if measurement.get("error"):
                raise ValueError(measurement["error"])
            result_entry["metrics"] = measurement
            try:
                annotated = create_annotated_image(image_bytes, measurement)
                result_entry["annotatedImageId"] = await storage.put(
                    f"annotated_{img.get('fileName', 'img')}", annotated,
                    metadata={"type": "annotated", "originalImageId": img["_id"], "studyId": study_id},
                )
            except Exception:
                pass
            result_entry["measurements"] = _measurements(measurement, output_vars)
            first = result_entry["measurements"][0] if result_entry["measurements"] else None
            result_entry["metric"] = first["variableName"] if first else "raw"
            result_entry["value"] = first["displayValue"] if first else ""
            await db["images"].update_one({"_id": img["_id"]}, {"$set": {"status": "processed"}})
        except StorageNotFound:
            result_entry["metric"] = "error"
            result_entry["value"] = "no file in storage"
        except Exception as e:
            result_entry["metric"] = "error"
            result_entry["value"] = str(e)
        run_doc["results"].append(result_entry)

    await db["analysis_runs"].insert_one(run_doc)
    await brapi_db["studies"].update_one({"_id": study_id}, {"$set": {"status": "completed"}})

    try:
        await db["notifications"].insert_one({
            "_id": new_id(),
            "userId": user.get("_id", ""),
            "type": "analysis_complete",
            "title": "Анализ завершён",
            "message": f"{solution.get('name', '')} \u2014 {len(images)} изображений",
            "read": False,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass

    return {"message": "Анализ завершён. Обработано " + str(len(images)) + " изображений.", "runId": run_id}


@router.get("/{study_id}/trait-summary")
async def get_trait_summary(study_id: str, db=Depends(get_db_dep), brapi_db=Depends(get_brapi_db_dep), user=Depends(get_current_user)):
    """Statistics for plant height and leaf area: groups, dynamics, growth rates, correlation."""
    data = await load_study_data(db, brapi_db, [study_id])
    if not data.studies:
        raise HTTPException(status_code=404, detail="Study not found")
    return summarize(collect_records(data.runs, data.images, data.plants))


@router.get("/{study_id}/export")
async def export_study(
    study_id: str,
    format: str = "xlsx",
    variables: str = "",
    date_from: str = "",
    date_to: str = "",
    db=Depends(get_db_dep),
    brapi_db=Depends(get_brapi_db_dep),
    storage=Depends(get_storage_dep),
    user=Depends(get_current_user),
):
    """Export one experiment: ?format=xlsx|pdf|csv|json&variables=name1,name2&date_from=YYYY-MM-DD."""
    names = [v.strip() for v in variables.split(",") if v.strip()]
    ds = await build_export(db, brapi_db, storage, user, [study_id], format,
                            variable_names=names, date_from=date_from, date_to=date_to)
    return export_response(ds, format)


@router.get("/{study_id}/export-zip")
async def export_zip(
    study_id: str,
    db=Depends(get_db_dep),
    brapi_db=Depends(get_brapi_db_dep),
    storage=Depends(get_storage_dep),
    user=Depends(get_current_user),
):
    """Full study package: tables, PDF report, original and annotated images, checksum manifest."""
    ds = await build_export(db, brapi_db, storage, user, [study_id], "pdf")
    manifest = {"study": ds.title, "generatedAt": ds.generated_at, "files": {}}
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        def add(path: str, data: bytes):
            zf.writestr(path, data)
            manifest["files"][path] = sha256_hex(data)

        add("results.csv", build_csv(ds))
        add("results.xlsx", build_xlsx(ds))
        add("report.pdf", build_pdf(ds))

        seen = set()
        data = await load_study_data(db, brapi_db, [study_id])
        for run in data.runs:
            folder = run.get("folderName") or "default"
            for res in run.get("results", []):
                file_name = res.get("fileName") or "image.jpg"
                img = data.images.get(res.get("imageId", ""))
                if img and img["_id"] not in seen and img.get("gridfsId"):
                    seen.add(img["_id"])
                    try:
                        add(f"dataset/{folder}/{file_name}", await storage.get(img["gridfsId"]))
                    except StorageNotFound:
                        pass
                if res.get("annotatedImageId"):
                    try:
                        add(f"results/{folder}/{file_name}", await storage.get(res["annotatedImageId"]))
                    except StorageNotFound:
                        pass
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    study_name = (ds.title or study_id).replace(" ", "_")
    return Response(
        content=zip_buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": content_disposition("attachment", f"{study_name}_export.zip")},
    )

@router.get("/{study_id}/analysis-runs")
async def get_analysis_runs(study_id: str, db=Depends(get_db_dep), user=Depends(get_current_user)):
    items = []
    async for doc in db["analysis_runs"].find({"studyId": study_id}).sort("createdAt", -1):
        doc["id"] = doc.pop("_id")
        items.append(doc)
    return items


@router.get("/{study_id}/matching-solutions")
async def get_matching_solutions(study_id: str, db=Depends(get_db_dep), brapi_db=Depends(get_brapi_db_dep), user=Depends(get_current_user)):
    study = await brapi_db["studies"].find_one({"_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    var_ids = study.get("observationVariableIds", [])
    if not var_ids:
        docs = []
        async for doc in db["phenotyping_solutions"].find().sort("createdAt", -1):
            doc["id"] = doc.pop("_id")
            docs.append(doc)
        return docs

    study_co_terms = set()
    async for var_doc in brapi_db["observation_variables"].find({"_id": {"$in": var_ids}}):
        co = var_doc.get("coTermId", "")
        if co:
            study_co_terms.add(co)

    if not study_co_terms:
        docs = []
        async for doc in db["phenotyping_solutions"].find().sort("createdAt", -1):
            doc["id"] = doc.pop("_id")
            docs.append(doc)
        return docs

    matched = []
    async for doc in db["phenotyping_solutions"].find().sort("createdAt", -1):
        output_vars = doc.get("outputVariables", [])
        sol_co_terms = {ov.get("coTermId", "") for ov in output_vars}
        if sol_co_terms & study_co_terms:
            doc["id"] = doc.pop("_id")
            matched.append(doc)
    return matched


@router.get("/{study_id}/export-results-csv")
async def export_results_csv(
    study_id: str,
    db=Depends(get_db_dep),
    brapi_db=Depends(get_brapi_db_dep),
    storage=Depends(get_storage_dep),
    user=Depends(get_current_user),
):
    ds = await build_export(db, brapi_db, storage, user, [study_id], "csv")
    if not ds.rows:
        raise HTTPException(status_code=404, detail="No analysis runs found")
    return export_response(ds, "csv")
