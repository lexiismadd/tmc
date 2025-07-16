from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from config.settings import settings
from database.models import TorrentInfo, DownloadStatus
from database.crud import db
import hashlib
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2",
    tags=["torrents"]
)

class LoginRequest(BaseModel):
    username: str
    password: str

class AddTorrentRequest(BaseModel):
    urls: Optional[str] = None
    torrents: Optional[List[bytes]] = None
    savepath: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    skip_checking: Optional[bool] = False
    paused: Optional[bool] = False
    root_folder: Optional[bool] = None
    rename: Optional[str] = None
    upLimit: Optional[int] = -1
    dlLimit: Optional[int] = -1

@router.post("/auth/login")
async def login(credentials: LoginRequest):
    if credentials.username == settings.qb_user and credentials.password == settings.qb_pass:
        return JSONResponse(content="Ok.", status_code=status.HTTP_200_OK)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User's IP is banned for too many failed login attempts"
    )

@router.get("/auth/logout")
async def logout():
    return JSONResponse(content="Ok.", status_code=status.HTTP_200_OK)

@router.get("/torrents/info")
async def get_torrents_info(
    filter: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    reverse: Optional[bool] = Query(None),
    limit: Optional[int] = Query(None),
    offset: Optional[int] = Query(None),
    hashes: Optional[str] = Query(None)
):
    torrents = await db.get_torrents()
    
    # Apply filters
    if filter:
        if filter == "downloading":
            torrents = [t for t in torrents if t.status == DownloadStatus.DOWNLOADING]
        elif filter == "completed":
            torrents = [t for t in torrents if t.status == DownloadStatus.COMPLETED]
    
    if category:
        torrents = [t for t in torrents if t.category == category]
    
    if hashes:
        requested_hashes = hashes.split("|")
        torrents = [t for t in torrents if t.hash in requested_hashes]
    
    # Convert to dict for compatibility
    result = [t.model_dump() for t in torrents]
    
    # Apply sorting
    if sort:
        reverse_sort = reverse if reverse is not None else False
        result.sort(key=lambda x: x.get(sort, ""), reverse=reverse_sort)
    
    # Apply pagination
    if offset is not None and limit is not None:
        result = result[offset:offset+limit]
    
    return result

@router.post("/torrents/add")
async def add_torrents(request: AddTorrentRequest):
    if request.urls:
        for url in request.urls.split("\n"):
            if url.strip():
                torrent_hash = hashlib.sha256(url.encode()).hexdigest()
                name = url.split("/")[-1].split(".")[0] or "Unnamed Torrent"
                
                category = request.category or ""
                if category not in [settings.movies, settings.series]:
                    category = ""
                
                torrent = TorrentInfo(
                    name=name,
                    hash=torrent_hash,
                    size=1024 * 1024 * 500,  # 500MB mock
                    progress=0.0,
                    status=DownloadStatus.PAUSED if request.paused else DownloadStatus.QUEUED,
                    category=category,
                    save_path=request.savepath or settings.qb_tmp.as_posix(),
                    added_on=int(datetime.now().timestamp())
                )
                await db.add_torrent(torrent)
    
    return JSONResponse(content="Ok.", status_code=status.HTTP_200_OK)

# Additional endpoints can be added similarly