from functions.torboxFunctions import getUserDownloads
from library.filesystem import MOUNT_METHOD, MOUNT_PATH, SYMLINK_PATH, SYMLINK_CREATION
from library.app import MOUNT_REFRESH_TIME
from library.torbox import TORBOX_API_KEY
from functions.databaseFunctions import getAllData, clearDatabase
import logging
from typing import List, Tuple
from enum import Enum
import asyncio
from config.settings import DownloadType
from database.crud import db



async def get_all_user_downloads_fresh() -> List[dict]:
    """
    Async version with database clearing
    Returns: List of DownloadItem objects
    """
    all_downloads = []
    logging.info("Fetching all user downloads with fresh data...")
    
    for download_type in DownloadType:
        try:
            # Clear existing data
            logging.debug(f"Clearing {download_type.value} cached data...")
            cleared_count = await db.clear_meta_items(download_type.value)
            logging.debug(f"Cleared {cleared_count} cached data...")
            
            # Fetch fresh downloads
            logging.debug(f"Fetching fresh {download_type.value} downloads...")
            downloads = await db.get_user_downloads(download_type.value)
            
            if not downloads:
                logging.info(f"No {download_type.value} downloads found.")
                continue
                
            all_downloads.extend(downloads)
            logging.debug(f"Fetched {len(downloads)} {download_type.value} downloads.")
            
        except Exception as e:
            logging.error(f"Error processing {download_type.value}: {str(e)}", exc_info=True)
            continue
            
    return all_downloads

async def get_all_user_downloads() -> List[dict]:
    """
    Async version using cached data
    Returns: List of DownloadItem objects
    """
    all_downloads = []
    
    for download_type in DownloadType:
        try:
            logging.debug(f"Fetching cached {download_type.value} downloads...")
            downloads = await db.get_cached_downloads(download_type.value)
            
            if not downloads:
                logging.debug(f"No cached {download_type.value} downloads found.")
                continue
                
            all_downloads.extend(downloads)
            logging.debug(f"Fetched {len(downloads)} cached {download_type.value} downloads.")
            
        except Exception as e:
            logging.error(f"Error fetching cached {download_type.value}: {str(e)}", exc_info=True)
            continue
            
    return all_downloads



async def getAllUserDownloadsFresh():
    all_downloads = []
    logging.info("Fetching all user downloads...")
    for download_type in DownloadType:
        logging.debug(f"Clearing database for {download_type.value}...")
        success, detail = clearDatabase(download_type.value)
        if not success:
            logging.error(f"Error clearing {download_type.value} database: {detail}")
            continue
        logging.debug(f"Fetching {download_type.value} downloads...")
        downloads, success, detail = getUserDownloads(download_type)
        if not success:
            logging.error(f"Error fetching {download_type.value}: {detail}")
            continue
        if not downloads:
            logging.info(f"No {download_type.value} downloads found.")
            continue
        all_downloads.extend(downloads)
        logging.debug(f"Fetched {len(downloads)} {download_type.value} downloads.")
    return all_downloads

def getAllUserDownloads():
    all_downloads = []
    for download_type in DownloadType:
        logging.debug(f"Fetching {download_type.value} downloads...")
        downloads, success, detail = getAllData(download_type.value)
        if not success:
            logging.error(f"Error fetching {download_type.value}: {detail}")
            continue
        all_downloads.extend(downloads)
        logging.debug(f"Fetched {len(downloads)} {download_type.value} downloads.")
    return all_downloads

