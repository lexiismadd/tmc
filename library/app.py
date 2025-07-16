import os
from dotenv import load_dotenv
from enum import Enum
import logging

load_dotenv()

class MountRefreshTimes(Enum):
    # times are shown in hours
    slow = 3 # 3 hours
    normal = 2 # 2 hours
    fast = 1 # 1 hour
    instant = 0.10 # 6 minutes
    
class LogLevels(Enum):
    debug = logging.DEBUG
    info = logging.INFO
    warning = logging.WARNING
    error = logging.ERROR
    critical = logging.CRITICAL
    

class tmc_operation_modes(Enum):
    mount = "mount"
    symlink = "symlink" # both mount points and symlinks
    torrent = "torrent"
    usenet = "usenet"

MOUNT_REFRESH_TIME = os.getenv("MOUNT_REFRESH_TIME", MountRefreshTimes.fast.name)
MOUNT_REFRESH_TIME = MOUNT_REFRESH_TIME.lower()
assert MOUNT_REFRESH_TIME in [e.name for e in MountRefreshTimes], f"Invalid mount refresh time: {MOUNT_REFRESH_TIME}. Valid options are: {[e.name for e in MountRefreshTimes]}"

MOUNT_REFRESH_TIME = MountRefreshTimes[MOUNT_REFRESH_TIME].value


LOG_LEVEL = os.getenv("LOG_LEVEL", LogLevels.warning.name)
if os.getenv("DEBUG_MODE", False) in [True,'true']: LOG_LEVEL = LogLevels.debug.name # For legacy versions of TMC
assert LOG_LEVEL in [e.name for e in LogLevels], f"Invalid log level: {LOG_LEVEL}. Valid options are: {[e.name for e in LogLevels]}"
