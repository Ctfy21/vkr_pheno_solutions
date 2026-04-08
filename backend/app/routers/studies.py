from datetime import datetime, timezone
import csv
import io
import zipfile
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.auth import get_current_user
from app.database import get_db_dep, get_brapi_db_dep
from app.models.schemas import StudyCreate, StudyOut, new_id


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
            img["id"] = img.pop("_id")
            imgs.append(img)
        doc["images"] = imgs
        items.append(doc)
    return items


@router.get("/{study_id}/images")
async def get_study_images(study_id: str, brapi_db=Depends(get_brapi_db_dep), db=Depends(get_db_dep), user=Depends(get_current_user)):
    ou_ids = []
    async for doc in brapi_db["observation_units"].find({"studyId": study_id}, {"_id": 1}):
        ou_ids.append(doc["_id"])
    items = []
    if ou_ids:
        async for img in db["images"].find({"observationUnitId": {"$in": ou_ids}}):
            img["id"] = img.pop("_id")
            items.append(img)
    # Also get images linked directly by studyId
    async for img in db["images"].find({"studyId": study_id}):
        img["id"] = img.pop("_id")
        if not any(i["id"] == img["id"] for i in items):
            items.append(img)
    return items


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


@router.post("/{study_id}/run-analysis")
async def run_analysis(study_id: str, req: RunAnalysisRequest, db=Depends(get_db_dep), brapi_db=Depends(get_brapi_db_dep), user=Depends(get_current_user)):
    """Run a phenotyping solution on a folder of images."""
    study = await brapi_db["studies"].find_one({"_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    solution = await db["phenotyping_solutions"].find_one({"_id": req.solution_id})
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    images = []
    async for img in db["images"].find({"studyId": study_id, "folderName": req.folder_name}):
        img["id"] = img.pop("_id")
        images.append(img)

    if not images:
        raise HTTPException(status_code=400, detail="No images in this folder")

    if study.get("status") == "draft":
        await brapi_db["studies"].update_one({"_id": study_id}, {"$set": {"status": "active"}})

    sol_config = solution.get("config", {})
    output_vars = solution.get("outputVariables", [])
    scale_px_per_cm = sol_config.get("scale_px_per_cm", 10.0)

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

    from bson import ObjectId
    from motor.motor_asyncio import AsyncIOMotorGridFSBucket
    from app.analyze import measure_plant_height, plantcv_rgb_analysis, create_annotated_image

    fs = AsyncIOMotorGridFSBucket(db)

    for img in images:
        plant_name = img.get("matchedPlantName", "")
        gridfs_id = img.get("gridfsId")

        result_entry = {
            "imageId": img["id"],
            "fileName": img.get("fileName", ""),
            "plantName": plant_name,
            "measurements": [],
            "metrics": {},
        }

        if gridfs_id:
            try:
                stream = await fs.open_download_stream(ObjectId(gridfs_id))
                image_bytes = await stream.read()
                sol_name = solution.get("name", "")
                if "PlantCV" in sol_name or "RGB" in sol_name or "plantcv" in sol_name.lower() or "rgb" in sol_name.lower():
                    measurement = plantcv_rgb_analysis(image_bytes, scale_px_per_cm=scale_px_per_cm)
                else:
                    measurement = measure_plant_height(image_bytes, scale_px_per_cm=scale_px_per_cm)
                result_entry["metrics"] = measurement

                try:
                    annotated_bytes = create_annotated_image(image_bytes, measurement)
                    ann_id = await fs.upload_from_stream(
                        f"annotated_{img.get('fileName', 'img')}",
                        annotated_bytes,
                        metadata={"type": "annotated", "originalImageId": img["id"], "studyId": study_id}
                    )
                    result_entry["annotatedImageId"] = str(ann_id)
                except Exception:
                    pass

                is_plantcv = measurement.get("method", "").startswith("plantcv_rgb")
                if is_plantcv:
                    metric_map = {
                        "CO_321:0000020": ("height_cm", "cm"),
                        "CO_321:0000080": ("leaf_area_cm2", "cm2"),
                    }
                else:
                    metric_map = {
                        "CO_321:0000020": ("height_cm", "cm"),
                        "CO_321:0000080": ("green_area_px", "px"),
                    }
                for ov in output_vars:
                    co_id = ov.get("coTermId", "")
                    unit = ov.get("unit", "")
                    var_name = ov.get("name", "")

                    mapped = metric_map.get(co_id)
                    if mapped:
                        value = measurement.get(mapped[0], 0.0)
                        if not unit:
                            unit = mapped[1]
                    elif "height" in var_name.lower():
                        value = measurement.get("height_cm", 0.0)
                    elif "area" in var_name.lower() or "leaf" in var_name.lower():
                        value = measurement.get("green_area_px", 0)
                    else:
                        value = measurement.get("height_cm", 0.0)

                    result_entry["measurements"].append({
                        "coTermId": co_id,
                        "variableName": var_name,
                        "value": round(float(value), 2),
                        "unit": unit,
                        "displayValue": f"{round(float(value), 2)} {unit}",
                    })

                raw_keys = ["height_px", "height_cm", "green_area_px", "scale_px_per_cm", "height_ratio"]
                if measurement.get("method", "").startswith("plantcv_rgb"):
                    raw_keys.extend(["leaf_area_cm2", "green_index", "compactness", "bbox_width_cm"])
                for key in raw_keys:
                    if key in measurement and not any(m["variableName"] == key for m in result_entry["measurements"]):
                        val = measurement[key]
                        result_entry["measurements"].append({
                            "coTermId": "",
                            "variableName": key,
                            "value": round(float(val), 4) if isinstance(val, float) else val,
                            "unit": "",
                            "displayValue": str(round(float(val), 4) if isinstance(val, float) else val),
                        })

                if result_entry["measurements"]:
                    m = result_entry["measurements"][0]
                    result_entry["metric"] = m["variableName"]
                    result_entry["value"] = m["displayValue"]
                else:
                    result_entry["metric"] = "raw"
                    result_entry["value"] = str(measurement)

                await db["images"].update_one(
                    {"_id": img["id"]},
                    {"$set": {"status": "processed"}},
                )
            except Exception as e:
                result_entry["metric"] = "error"
                result_entry["value"] = str(e)
        else:
            result_entry["metric"] = "error"
            result_entry["value"] = "no file in storage"

        run_doc["results"].append(result_entry)

    await db["analysis_runs"].insert_one(run_doc)

    await brapi_db["studies"].update_one({"_id": study_id}, {"$set": {"status": "completed"}})

    # Create notification
    try:
        notif_doc = {
            "_id": new_id(),
            "userId": user.get("_id", ""),
            "type": "analysis_complete",
            "title": "Анализ завершён",
            "message": f"{solution.get('name', '')} \u2014 {len(images)} изображений",
            "read": False,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        await db["notifications"].insert_one(notif_doc)
    except Exception:
        pass

    run_doc["id"] = run_doc.pop("_id")
    return {"message": "Анализ завершён. Обработано " + str(len(images)) + " изображений.", "runId": run_id}


@router.get("/{study_id}/export-zip")
async def export_zip(study_id: str, db=Depends(get_db_dep), brapi_db=Depends(get_brapi_db_dep), user=Depends(get_current_user)):
    """Export full study results as ZIP."""
    from bson import ObjectId
    from motor.motor_asyncio import AsyncIOMotorGridFSBucket
    import openpyxl

    study = await brapi_db["studies"].find_one({"_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    runs = []
    async for doc in db["analysis_runs"].find({"studyId": study_id}).sort("createdAt", -1):
        runs.append(doc)

    all_var_names = []
    for run in runs:
        for res in run.get("results", []):
            for m in res.get("measurements", []):
                vn = m.get("variableName", "")
                if vn and vn not in all_var_names:
                    all_var_names.append(vn)

    csv_output = io.StringIO()
    writer = csv.writer(csv_output)
    header = ["run_id", "run_date", "solution", "folder", "image", "plant"] + all_var_names
    writer.writerow(header)

    csv_rows = []
    for run in runs:
        run_id = run.get("_id", "")
        run_date = run.get("createdAt", "")
        solution = run.get("solutionName", "")
        folder = run.get("folderName", "")
        for res in run.get("results", []):
            row = [run_id, run_date, solution, folder, res.get("fileName", ""), res.get("plantName", "")]
            var_vals = {}
            for m in res.get("measurements", []):
                var_vals[m.get("variableName", "")] = m.get("value", "")
            for vn in all_var_names:
                row.append(var_vals.get(vn, ""))
            writer.writerow(row)
            csv_rows.append(row)

    csv_bytes = csv_output.getvalue().encode("utf-8-sig")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Results"
    ws.append(header)
    for row in csv_rows:
        ws.append(row)
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)
    xlsx_buf = io.BytesIO()
    wb.save(xlsx_buf)
    xlsx_bytes = xlsx_buf.getvalue()

    fs = AsyncIOMotorGridFSBucket(db)
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("results.csv", csv_bytes)
        zf.writestr("results.xlsx", xlsx_bytes)

        seen_originals = set()
        for run in runs:
            folder_name = run.get("folderName", "default")
            for res in run.get("results", []):
                file_name = res.get("fileName", "unknown.jpg")
                image_id = res.get("imageId", "")
                annotated_id = res.get("annotatedImageId", "")

                if image_id and image_id not in seen_originals:
                    seen_originals.add(image_id)
                    img_doc = await db["images"].find_one({"_id": image_id})
                    if img_doc and img_doc.get("gridfsId"):
                        try:
                            stream = await fs.open_download_stream(ObjectId(img_doc["gridfsId"]))
                            data = await stream.read()
                            zf.writestr(f"dataset/{folder_name}/{file_name}", data)
                        except Exception:
                            pass

                if annotated_id:
                    try:
                        stream = await fs.open_download_stream(ObjectId(annotated_id))
                        data = await stream.read()
                        zf.writestr(f"results/{folder_name}/{file_name}", data)
                    except Exception:
                        pass

    zip_bytes = zip_buf.getvalue()
    study_name = study.get("name", study_id).replace(" ", "_")
    filename = f"{study_name}_export.zip"

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
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
async def export_results_csv(study_id: str, db=Depends(get_db_dep), brapi_db=Depends(get_brapi_db_dep), user=Depends(get_current_user)):
    study = await brapi_db["studies"].find_one({"_id": study_id})
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    runs = []
    async for doc in db["analysis_runs"].find({"studyId": study_id}).sort("createdAt", -1):
        runs.append(doc)

    if not runs:
        raise HTTPException(status_code=404, detail="No analysis runs found")

    all_var_names = []
    for run in runs:
        for res in run.get("results", []):
            for m in res.get("measurements", []):
                vn = m.get("variableName", "")
                if vn and vn not in all_var_names:
                    all_var_names.append(vn)

    output = io.StringIO()
    writer = csv.writer(output)
    header = ["run_id", "run_date", "solution", "folder", "image", "plant"] + all_var_names
    writer.writerow(header)

    for run in runs:
        run_id = run.get("_id", "")
        run_date = run.get("createdAt", "")
        solution = run.get("solutionName", "")
        folder = run.get("folderName", "")
        for res in run.get("results", []):
            row = [run_id, run_date, solution, folder, res.get("fileName", ""), res.get("plantName", "")]
            var_vals = {}
            for m in res.get("measurements", []):
                var_vals[m.get("variableName", "")] = m.get("value", "")
            for vn in all_var_names:
                row.append(var_vals.get(vn, ""))
            writer.writerow(row)

    csv_bytes = output.getvalue().encode("utf-8-sig")
    filename = f"results_{study_id}.csv"
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
