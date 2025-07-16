from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from config.settings import settings
from database.models import NZBInfo, DownloadStatus
from database.crud import db
import hashlib
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/sabnzbd/api",
    tags=["SABnzbd"]
)

class AddNZBRequest(BaseModel):
    name: Optional[str] = None
    nzb: Optional[bytes] = None
    url: Optional[str] = None
    cat: Optional[str] = None
    script: Optional[str] = None
    priority: Optional[int] = None

@router.get("")
async def sabnzbd_api(
    mode: str,
    name: Optional[str] = None,
    nzb: Optional[str] = None,
    url: Optional[str] = None,
    cat: Optional[str] = None,
    apikey: Optional[str] = None,
    output: str = "json"
):
    if apikey != settings.nzb_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    if mode == "addurl":
        nzb_id = hashlib.sha256(url.encode()).hexdigest()
        name = name or url.split("/")[-1].split(".")[0] or "Unnamed NZB"
        
        category = cat or ""
        if category not in [settings.movies, settings.series]:
            category = ""
        
        nzb_info = NZBInfo(
            nzb_id=nzb_id,
            name=name,
            size=1024 * 1024 * 500,  # 500MB mock
            progress=0.0,
            status=DownloadStatus.QUEUED,
            category=category,
            storage_path=settings.nzb_tmp.as_posix(),
            added_on=int(datetime.now().timestamp())
        )
        await db.add_nzb(nzb_info)
        
        return {"status": True, "nzo_id": nzb_id}
    
    elif mode == "queue":
        nzbs = await db.get_nzbs()
        queue = {
            "version": "3.7.2",
            "queue": {
                "slots": [
                    {
                        "nzo_id": nzb.nzb_id,
                        "filename": nzb.name,
                        "cat": nzb.category,
                        "size": f"{nzb.size / (1024*1024):.2f} MB",
                        "percentage": f"{nzb.progress * 100:.1f}%",
                        "status": nzb.status.value,
                        "timeleft": "00:10:00"  # Mock
                    }
                    for nzb in nzbs
                ]
            }
        }
        return queue
    
    return {"status": False}

@router.post("/api")
async def sabnzbd_api_post(request: AddNZBRequest):
    if not any([request.nzb, request.url]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either nzb or url must be provided"
        )
    
    if request.url:
        nzb_id = hashlib.sha256(request.url.encode()).hexdigest()
        name = request.name or request.url.split("/")[-1].split(".")[0] or "Unnamed NZB"
    else:
        nzb_id = hashlib.sha256(request.nzb).hexdigest()
        name = request.name or "Uploaded NZB"
    
    category = request.cat or ""
    if category not in [settings.movies, settings.series]:
        category = ""
    
    nzb_info = NZBInfo(
        nzb_id=nzb_id,
        name=name,
        size=1024 * 1024 * 500,  # 500MB mock
        progress=0.0,
        status=DownloadStatus.QUEUED,
        category=category,
        storage_path=settings.nzb_tmp.as_posix(),
        added_on=int(datetime.now().timestamp()))
        
    await db.add_nzb(nzb_info)
    
    return JSONResponse(content={"status": True, "nzo_id": nzb_id})