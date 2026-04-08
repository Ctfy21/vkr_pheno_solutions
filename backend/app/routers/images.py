import io
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.auth import get_current_user
from app.database import get_db_dep
from app.models.schemas import new_id
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

router = APIRouter()


async def _get_gridfs(db):
    return AsyncIOMotorGridFSBucket(db)


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    observationUnitId: str = "",
    db=Depends(get_db_dep),
    user=Depends(get_current_user),
):
    fs = await _get_gridfs(db)
    content = await file.read()
    image_id = new_id()
    grid_id = await fs.upload_from_stream(
        file.filename or "unnamed",
        io.BytesIO(content),
        metadata={"image_id": image_id, "mimeType": file.content_type},
    )
    doc = {
        "_id": image_id,
        "fileName": file.filename,
        "mimeType": file.content_type,
        "observationUnitId": observationUnitId,
        "gridfsId": str(grid_id),
        "size": len(content),
    }
    await db.images.insert_one(doc)
    doc["id"] = doc.pop("_id")
    return doc


@router.post("/upload-batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    studyId: str = Form(""),
    folderName: str = Form(""),
    db=Depends(get_db_dep),
    user=Depends(get_current_user),
):
    fs = await _get_gridfs(db)

    # Get plants for filename matching
    plants_map = {}
    if studyId:
        async for ou in db["observation_units"].find({"studyId": studyId}):
            plants_map[ou.get("name", "").lower()] = ou["_id"]

    results = []
    for file in files:
        content = await file.read()
        image_id = new_id()
        grid_id = await fs.upload_from_stream(
            file.filename or "unnamed",
            io.BytesIO(content),
            metadata={"image_id": image_id, "mimeType": file.content_type},
        )

        # Match filename to plant
        base = (file.filename or "").rsplit(".", 1)[0]
        matched_ou_id = ""
        matched_plant_name = ""
        for plant_name, plant_id in plants_map.items():
            if plant_name in base.lower():
                matched_ou_id = plant_id
                matched_plant_name = plant_name
                break

        doc = {
            "_id": image_id,
            "fileName": file.filename,
            "mimeType": file.content_type,
            "observationUnitId": matched_ou_id,
            "matchedPlantName": matched_plant_name,
            "studyId": studyId,
            "folderName": folderName,
            "gridfsId": str(grid_id),
            "size": len(content),
            "status": "pending",
        }
        await db.images.insert_one(doc)
        doc["id"] = doc.pop("_id")
        results.append(doc)

    return results


@router.post("/upload-plant")
async def upload_plant_images(
    files: List[UploadFile] = File(...),
    studyId: str = Form(""),
    folderName: str = Form(""),
    observationUnitId: str = Form(""),
    db=Depends(get_db_dep),
    user=Depends(get_current_user),
):
    fs = await _get_gridfs(db)
    plant_name = ""
    if observationUnitId:
        ou = await db["observation_units"].find_one({"_id": observationUnitId})
        if ou:
            plant_name = ou.get("name", "")

    results = []
    for file in files:
        content = await file.read()
        image_id = new_id()
        grid_id = await fs.upload_from_stream(
            file.filename or "unnamed",
            io.BytesIO(content),
            metadata={"image_id": image_id, "mimeType": file.content_type},
        )
        doc = {
            "_id": image_id,
            "fileName": file.filename,
            "mimeType": file.content_type,
            "observationUnitId": observationUnitId,
            "matchedPlantName": plant_name,
            "studyId": studyId,
            "folderName": folderName,
            "gridfsId": str(grid_id),
            "size": len(content),
            "status": "pending",
        }
        await db.images.insert_one(doc)
        doc["id"] = doc.pop("_id")
        results.append(doc)

    return results


@router.get("/by-study/{study_id}")
async def get_images_by_study(study_id: str, db=Depends(get_db_dep), user=Depends(get_current_user)):
    items = []
    async for img in db["images"].find({"studyId": study_id}):
        img["id"] = img.pop("_id")
        items.append(img)
    return items


@router.get("/file/{image_id}")
async def get_image_file(image_id: str, db=Depends(get_db_dep)):
    """Serve image file from GridFS."""
    doc = await db["images"].find_one({"_id": image_id})
    if not doc or not doc.get("gridfsId"):
        raise HTTPException(status_code=404, detail="Image not found")
    from bson import ObjectId
    fs = await _get_gridfs(db)
    try:
        stream = await fs.open_download_stream(ObjectId(doc["gridfsId"]))
        data = await stream.read()
        return StreamingResponse(
            io.BytesIO(data),
            media_type=doc.get("mimeType", "image/jpeg"),
            headers={"Content-Disposition": f"inline; filename={doc.get('fileName', 'image')}"},
        )
    except Exception:
        raise HTTPException(status_code=404, detail="File not found in storage")




@router.get("/annotated/{gridfs_id}")
async def get_annotated_image(gridfs_id: str, db=Depends(get_db_dep)):
    """Serve annotated image directly from GridFS by its ObjectId."""
    from bson import ObjectId
    fs = await _get_gridfs(db)
    try:
        stream = await fs.open_download_stream(ObjectId(gridfs_id))
        data = await stream.read()
        return StreamingResponse(
            io.BytesIO(data),
            media_type="image/jpeg",
            headers={"Content-Disposition": "inline; filename=annotated.jpg"},
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Annotated image not found")

@router.delete("/{image_id}")
async def delete_image(image_id: str, db=Depends(get_db_dep), user=Depends(get_current_user)):
    doc = await db["images"].find_one({"_id": image_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    # Delete from GridFS
    if doc.get("gridfsId"):
        from bson import ObjectId
        fs = await _get_gridfs(db)
        try:
            await fs.delete(ObjectId(doc["gridfsId"]))
        except Exception:
            pass
    await db["images"].delete_one({"_id": image_id})
    return {"ok": True}
