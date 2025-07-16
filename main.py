from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import timedelta
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from database.crud import db
import uvicorn
import asyncio
import logging
from logging.config import dictConfig
from config.log_config import log_config
from routers import qbittorrent, sabnzbd, meta
from routers.auth import authenticate
from functions.appFunctions import bootUp, getMountMethod, getAllUserDownloadsFresh, getMountRefreshTime
from functions.databaseFunctions import closeAllDatabases
from sys import platform

# Apply logging config
dictConfig(log_config)

app = FastAPI(
    title="TMC",
    description="Torbox Media Center with added Symlink, qBittorrent and SABnzbd support and local API",
    version="2.0.0"
)

# Scheduler setup
scheduler = AsyncIOScheduler()

async def refresh_content():
    """Core refresh logic that respects OPERATION_MODE"""
    try:
        logging.info(f"Running refresh (mode: {settings.operation_mode})")
        
        if "torrent" in settings.operation_mode:
            await check_torrent_status()
        if "usenet" in settings.operation_mode:
            await check_usenet_status()
        if "mount" in settings.operation_mode:
            await refresh_mounts()
            
        logging.info("Refresh completed successfully")
    except Exception as e:
        logging.error(f"Refresh failed: {str(e)}", exc_info=True)



# Store settings in app state
@app.add_event_handler("startup")
async def startup_event():
    """Initialize application state"""
    logging.debug("Booting up...")
    logging.debug(f"Environment Variables passed to application:\n{settings}")
    app.state.settings = settings
    
    # Initialize scheduler if refresh enabled
    if settings.refresh_interval_minutes >= 5:  # Your minimum requirement
        scheduler.add_job(
            refresh_content,
            trigger=IntervalTrigger(
                minutes=settings.refresh_interval_minutes,
                jitter=30  # Prevents clustering
            ),
            max_instances=1,
            misfire_grace_time=60
        )
        scheduler.start()
        logging.info(f"Scheduled refresh every {settings.refresh_interval_minutes} minutes")

    # Initialize routers
    if settings.qb_enabled:
        app.include_router(
            qbittorrent.router,
            dependencies=[Depends(authenticate)]
        )
    if settings.nzb_enabled:
        app.include_router(
            sabnzbd.router,
            dependencies=[Depends(authenticate)]
        )
    app.include_router(
        meta.router,
        dependencies=[Depends(authenticate)]
    )


@app.add_event_handler("shutdown")
async def shutdown_event():
    """Cleanup resources"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
    await db.close()
    logging.info("Application shutdown complete")
    

# Include routers conditionally with auth
if settings.qb_enabled:
    app.include_router(
        qbittorrent.router,
        dependencies=[Depends(authenticate)]
    )
    logging.info(f"qBittorrent API enabled on {settings.qb_listen_ip}:{settings.qb_listen_port}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.listen_ip,
        port=settings.listen_port,
        log_config=log_config,  # Use our dictConfig
        log_level=settings.log_level.lower(),
        access_log=False  # We handle access logs ourselves
    )


    mount_method = getMountMethod()

    if mount_method == "strm":
        scheduler = BlockingScheduler()
    elif mount_method == "fuse":
        if platform == "win32":
            logging.error("The FUSE mount method is not supported on Windows. Please use the STRM mount method or run this application on a Linux system.")
            exit(1)
        scheduler = BackgroundScheduler()
    else:
        logging.error("Invalid mount method specified.")
        exit(1)

    user_downloads = getAllUserDownloadsFresh()

    scheduler.add_job(
        getAllUserDownloadsFresh,
        "interval",
        hours=getMountRefreshTime(),
        id="get_all_user_downloads_fresh",
    )

    try:
        logging.info("Starting scheduler and mounting...")
        if mount_method == "strm":
            from functions.stremFilesystemFunctions import runStrm
            runStrm()
            scheduler.add_job(
                runStrm,
                "interval",
                minutes=5,
                id="run_strm",
            )
            scheduler.start()
        elif mount_method == "fuse":
            from functions.fuseFilesystemFunctions import runFuse
            scheduler.start()
            runFuse()
    except (KeyboardInterrupt, SystemExit):
        if mount_method == "fuse":
            from functions.fuseFilesystemFunctions import unmountFuse
            unmountFuse()
        elif mount_method == "strm":
            from functions.stremFilesystemFunctions import unmountStrm
            unmountStrm()
        db.close()
        exit(0)