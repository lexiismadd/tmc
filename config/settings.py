from pydantic import BaseSettings, Field, field_validator, PositiveInt, ValidationInfo
from typing import List, Optional
from pathlib import Path
import logging
from enum import Enum
import httpx


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class OperationMode(str, Enum):
    MOUNT = "mount"
    SYMLINK = "symlink"
    TORRENT = "torrent"
    USENET = "usenet"

class DownloadType(Enum):
    TORRENT = "torrents"
    USENET = "usenet"
    WEBDL = "webdl"

class IDType(Enum):
    torrents = "torrent_id"
    usenet = "usenet_id"
    webdl = "web_id"

class SymlinkCreation(str, Enum):
    ONCE = "once"
    SPAWN = "spawn"
    ALWAYS = "always"

class MountMethod(str, Enum):
    STRM = "strm"
    FUSE = "fuse"

class MountRefreshTimes(Enum):
    # times are shown in minutes
    SLOW = 180    # 3h
    NORMAL = 120  # 2h 
    FAST = 60     # 1h
    INSTANT = 5   # 5m
    
class Settings(BaseSettings):
    # Main settings
    torbox_api_key: str = Field(..., env="TORBOX_API_KEY")
    prefer_cached: bool = Field(False, env="PREFER_CACHED")
    movies: str = Field(default='movies', env="MOVIES")
    series: str = Field(default='series', env="SERIES")
    log_level: LogLevel = Field(LogLevel.INFO, env="LOG_LEVEL")
    operation_mode: List[OperationMode] = Field(..., env="OPERATION_MODE")
    refresh_interval_minutes: Optional[PositiveInt] = Field(default=60, env="REFRESH_INTERVAL", description="How often to refresh data from Torbox in minutes (minimum 5min)")
    mount_refresh: Optional[MountRefreshTimes] = Field(None, env="MOUNT_REFRESH", description="Legacy variable that is only used if REFRESH_INTERVAL isn't supplied")
    api_key: str = Field(..., env="API_KEY")
    listen_ip: str = Field(default="0.0.0.0", env="LISTEN_IP")
    listen_port: PositiveInt = Field(default=9393, env="LISTEN_PORT")
    ip_whitelist: Optional[List[str]] = Field(
        default=None,
        env="IP_WHITELIST",
        description="Comma-separated IPs/CIDRs. Empty=allow all"
    )


    # Mount paths
    mount_method: Optional[MountMethod] = Field(None, env="MOUNT_METHOD")
    mount_path: Optional[Path] = Field(None, env="MOUNT_PATH")

    # Symlink settings
    symlink_creation: SymlinkCreation = Field(SymlinkCreation.ONCE, env="SYMLINK_CREATION")
    symlink_path: Path = Field(..., env="SYMLINK_PATH")

    # qBittorrent settings
    torrent_enabled: bool = Field(False, env="TORRENT_ENABLED")
    torrent_user: str = Field("admin", env="TORRENT_USER")
    torrent_pass: str = Field("adminpassword", env="TORRENT_PASS")
    torrent_tmp: Path = Field(Path("/tmp/torrents"), env="TORRENT_TMP")

    # SABnzbd settings
    nzb_enabled: bool = Field(False, env="NZB_ENABLED")
    nzb_key: str = Field("your_very_long_and_secure_sabnzbd_api_key_is_missing", env="NZB_KEY")
    nzb_tmp: Path = Field(Path("/tmp/usenet"), env="NZB_TMP")



    @field_validator('operation_mode', pre=True)
    def parse_operation_mode(cls, v):
        if isinstance(v, str):
            return [OperationMode(mode.strip()) for mode in v.split(",")]
        return v

    @field_validator('ip_whitelist', pre=True)
    def parse_whitelist(cls, v):
        if v == "":  # Explicit empty string means no restriction
            return None
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
        return v
    
    @field_validator('mount_path', 'symlink_path', 'torrent_tmp', 'nzb_tmp', pre=True)
    def validate_paths(cls, v: str | None, values: ValidationInfo) -> Path | None:
        if not v:
            return None
        
        try:
            path = Path(v).resolve()  # Convert to absolute path
            path.mkdir(parents=True, exist_ok=True)  # Make necessary folders
            
            # Create category subfolders for mount_path and symlink_path
            if values.field_name in ('mount_path', 'symlink_path'):
                movies_path = path / cls.movies
                series_path = path / cls.series
                movies_path.mkdir(parents=True, exist_ok=True)
                series_path.mkdir(parents=True, exist_ok=True)
            
            return path
        except (OSError, TypeError) as e:
            raise ValueError(f"Invalid path '{v}': {str(e)}")
    
    @field_validator('refresh_interval_minutes')
    def validate_refresh_interval(cls, v):
        if v < 5:
            raise ValueError("Refresh interval cannot be less than 5 minutes")
        return v
    
    @property
    def refresh_minutes(self) -> int:
        """Final refresh interval (guaranteed ≥5)"""
        if self.refresh_interval_minutes is not None:
            return self.refresh_interval_minutes
        return self.mount_refresh.value if isinstance(self.mount_refresh.value,int) and self.mount_refresh.value >= 5 else 60  # default 60mins

    
    @property
    def torbox_api_url(self) -> str:
        return "https://api.torbox.app/v1/api"
    
    @property
    def torbox_search_api_url(self) -> str:
        return "https://search-api.torbox.app"

    @property
    def torbox_search_api_url(self) -> str:
        return "https://search-api.torbox.app"

    @property
    def transport(self):
        return httpx.HTTPTransport(retries=5)

    @property
    def api_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
        base_url=self.torbox_api_url,
        headers={
            "Authorization": f"Bearer {self.torbox_api_key}",
            "User-Agent": "TorBox-Media-Center/1.0 TorBox/1.0",
        },
        timeout=httpx.Timeout(60),
        follow_redirects=True,
        transport=self.transport,
    )

    @property
    def search_api_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
        base_url=self.torbox_search_api_url,
        headers={
            "Authorization": f"Bearer {self.torbox_api_key}",
            "User-Agent": "TorBox-Media-Center/1.0 TorBox/1.0",
        },
        timeout=httpx.Timeout(60),
        follow_redirects=True,
        transport=self.transport,
    )

    @property
    def general_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {self.torbox_api_key}",
            "User-Agent": "TorBox-Media-Center/1.0 TorBox/1.0",
        },
        timeout=httpx.Timeout(60),
        follow_redirects=False,
        transport=self.transport,
    )
    
    @property
    def acceptable_mime_types(self) -> List:
        return [
            "video/x-matroska",
            "video/mp4",
        ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    

settings = Settings()
