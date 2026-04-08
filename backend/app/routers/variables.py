from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.database import get_brapi_db_dep
from app.models.schemas import ObservationVariableCreate, ObservationVariableOut, new_id

router = APIRouter()


async def _populate_variable(db, doc: dict) -> dict:
    """Populate trait, method, scale into variable document."""
    doc["id"] = doc.pop("_id")
    trait_id = doc.get("traitId")
    method_id = doc.get("methodId")
    scale_id = doc.get("scaleId")

    if trait_id:
        trait = await db["traits"].find_one({"_id": trait_id})
        if trait:
            trait["id"] = trait.pop("_id")
            doc["trait"] = trait
    if method_id:
        method = await db["methods"].find_one({"_id": method_id})
        if method:
            method["id"] = method.pop("_id")
            doc["method"] = method
    if scale_id:
        scale = await db["scales"].find_one({"_id": scale_id})
        if scale:
            scale["id"] = scale.pop("_id")
            doc["scale"] = scale

    return doc


@router.get("")
async def list_variables(db=Depends(get_brapi_db_dep), user=Depends(get_current_user)):
    items = []
    async for doc in db["observation_variables"].find():
        populated = await _populate_variable(db, doc)
        items.append(populated)
    return items


@router.post("")
async def create_variable(item: ObservationVariableCreate, db=Depends(get_brapi_db_dep), user=Depends(get_current_user)):
    item_id = new_id()
    doc = item.model_dump()
    doc["_id"] = item_id
    await db["observation_variables"].insert_one(doc)
    doc_out = dict(doc)
    populated = await _populate_variable(db, doc_out)
    return populated


@router.delete("/{item_id}")
async def delete_variable(item_id: str, db=Depends(get_brapi_db_dep), user=Depends(get_current_user)):
    result = await db["observation_variables"].delete_one({"_id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}
