from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.database import get_db_dep, get_brapi_db_dep
from app.models.schemas import new_id

def make_crud_router(collection_name: str, create_model, out_model, use_brapi_db: bool = False):
    router = APIRouter()
    db_dep = get_brapi_db_dep if use_brapi_db else get_db_dep

    @router.get("")
    async def list_items(db=Depends(db_dep), user=Depends(get_current_user)):
        items = []
        async for doc in db[collection_name].find():
            doc["id"] = doc.pop("_id")
            items.append(doc)
        return items

    @router.post("", response_model=out_model)
    async def create_item(item: create_model, db=Depends(db_dep), user=Depends(get_current_user)):
        item_id = new_id()
        doc = item.model_dump()
        doc["_id"] = item_id
        await db[collection_name].insert_one(doc)
        doc["id"] = doc.pop("_id")
        return doc

    @router.delete("/{item_id}")
    async def delete_item(item_id: str, db=Depends(db_dep), user=Depends(get_current_user)):
        result = await db[collection_name].delete_one({"_id": item_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Not found")
        return {"ok": True}

    return router
