from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.database import get_db_dep
from app.models.schemas import new_id

router = APIRouter()


@router.get("")
async def list_notifications(db=Depends(get_db_dep), user=Depends(get_current_user)):
    """Get notifications for the current user, newest first."""
    user_id = user.get("_id", "")
    items = []
    async for doc in db["notifications"].find({"userId": user_id}).sort("createdAt", -1).limit(50):
        doc["id"] = doc.pop("_id")
        items.append(doc)
    return items


@router.get("/unread-count")
async def unread_count(db=Depends(get_db_dep), user=Depends(get_current_user)):
    """Get count of unread notifications."""
    user_id = user.get("_id", "")
    count = await db["notifications"].count_documents({"userId": user_id, "read": False})
    return {"count": count}


@router.put("/{notif_id}/read")
async def mark_read(notif_id: str, db=Depends(get_db_dep), user=Depends(get_current_user)):
    """Mark a notification as read."""
    result = await db["notifications"].update_one(
        {"_id": notif_id, "userId": user.get("_id", "")},
        {"$set": {"read": True}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"ok": True}


@router.put("/read-all")
async def mark_all_read(db=Depends(get_db_dep), user=Depends(get_current_user)):
    """Mark all notifications as read."""
    user_id = user.get("_id", "")
    await db["notifications"].update_many(
        {"userId": user_id, "read": False},
        {"$set": {"read": True}},
    )
    return {"ok": True}
