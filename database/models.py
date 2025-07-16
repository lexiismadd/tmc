from enum import Enum
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class MediaType(str, Enum):
    ANIME = "anime"
    SERIES = "series"
    MOVIE = "movie"

class DownloadStatus(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class DownloadType(str, Enum):
    TORRENTS = "torrents"
    USENET = "usenet"
    NZB = "nzb"
    WEBDL = "webdl"

class TorrentInfo(BaseModel):
    name: str
    hash: str
    size: int
    progress: float
    status: DownloadStatus
    category: str
    save_path: str
    ratio: float = 0.0
    added_on: int
    completed_on: Optional[int] = None

class NZBInfo(BaseModel):
    name: str
    nzb_id: str
    size: int
    progress: float
    status: DownloadStatus
    category: str
    storage_path: str
    added_on: int
    completed_on: Optional[int] = None
    
class MetaItem(BaseModel):
    item_id: int
    type: DownloadType  # "torrents", "usenet/nzb", "webdl"
    folder_name: str
    folder_hash: str
    file_id: int
    file_name: str
    file_size: int
    file_mimetype: str
    path: str
    download_link: str
    extension: str
    metadata_title: str
    metadata_link: str
    metadata_mediatype: MediaType
    metadata_image: Optional[str] = None
    metadata_backdrop: Optional[str] = None
    metadata_years: Optional[int] = None
    metadata_season: Optional[int] = None
    metadata_episode: Optional[List[int]] = None
    metadata_filename: str
    metadata_rootfoldername: str
    metadata_foldername: Optional[str] = None
    real_path: Optional[str] = None
    symlink_path: Optional[str] = None
    extra_json: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = 'allow'

