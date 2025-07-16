from fastapi import APIRouter, HTTPException, Query, status, Depends
from routers.auth import authenticate
from typing import List, Optional
from database.crud import db
import logging

router = APIRouter(
    prefix="/api/v1",
    tags=["metadata"],
)

# CREATE
@router.post("/meta", status_code=status.HTTP_201_CREATED, dependencies=[Depends(authenticate)])
async def create_meta_item(item: dict):
    try:
        await db.add_meta_item(item)
        return {"status": "success", "item_id": item.get("item_id")}
    except Exception as e:
        logging.error(f"Create failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# READ (All variations)
@router.get("/meta", dependencies=[Depends(authenticate)])
async def get_all_items(
    type: Optional[str] = Query(None, description="Filter by type: 'torrents' or 'usenet'"),
    mediatype: Optional[str] = Query(None, description="Filter by media type: 'movie', 'series', 'anime'"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    items = await db.get_meta_items()
    
    # Apply filters
    if type:
        items = [i for i in items if i["type"] == type]
    if mediatype:
        items = [i for i in items if i.get("metadata_mediatype") == mediatype]
    
    return {
        "count": len(items),
        "limit": limit,
        "offset": offset,
        "items": items[offset:offset+limit]
    }

@router.get("/meta/{item_id}", dependencies=[Depends(authenticate)])
async def get_item(
    item_id: int,
    file_id: Optional[int] = Query(None, description="Specific file ID for multi-file items")
):
    items = await db.get_meta_items(item_id, file_id)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    return items[0]

# UPDATE
@router.put("/meta/{item_id}", dependencies=[Depends(authenticate)])
async def update_item(
    item_id: int,
    updates: dict,
    file_id: Optional[int] = Query(None)
):
    # Check existence first
    existing = await db.get_meta_items(item_id, file_id)
    if not existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    
    try:
        # Merge updates
        updated_item = {**existing[0], **updates}
        await db.add_meta_item(updated_item)  # Using add with replace
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Update failed: {str(e)}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

# DELETE
@router.delete("/meta/{item_id}", dependencies=[Depends(authenticate)])
async def delete_item(
    item_id: int,
    file_id: Optional[int] = Query(None),
    confirm: bool = Query(False, description="Must set to True to confirm deletion")
):
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add ?confirm=true to actually delete"
        )
    
    deleted = await db.delete_meta_items(item_id, file_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    
    return {"deleted": deleted}

@router.delete("/meta/batch", dependencies=[Depends(authenticate)])
async def batch_delete(
    item_ids: List[int] = Query(..., description="Comma-separated IDs"),
    file_id: Optional[int] = Query(None),
    confirm: bool = Query(False)
):
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add ?confirm=true to actually delete"
        )
    
    deleted = await db.delete_meta_items(item_ids, file_id)
    return {"deleted": deleted}