import httpx
import asyncio
import PTN
import os
import logging
import traceback
from typing import List, Dict, Optional, Tuple
from config.settings import settings, IDType, DownloadType
from functions.mediaFunctions import constructSeriesTitle, cleanTitle, cleanYear
from database.crud import db


async def process_file(item: Dict, file: Dict, download_type: DownloadType) -> Optional[Dict]:
    """Process a single file asynchronously and return the processed data"""
    if not file.get("mimetype", "").startswith("video/") or file.get("mimetype") not in settings.acceptable_mime_types:
        logging.debug(f"Skipping file {file.get('short_name')} with mimetype {file.get('mimetype')}")
        return None
    
    data = {
        "item_id": item.get("id"),
        "type": download_type.value,
        "folder_name": item.get("name"),
        "folder_hash": item.get("hash"),
        "file_id": file.get("id"),
        "file_name": file.get("short_name"),
        "file_size": file.get("size"),
        "file_mimetype": file.get("mimetype"),
        "path": file.get("name"),
        "download_link": f"https://api.torbox.app/v1/api/{download_type.value}/requestdl?token={settings.torbox_api_key}&{IDType[download_type.value].value}={item.get('id')}&file_id={file.get('id')}&redirect=true",
        "extension": os.path.splitext(file.get("short_name"))[-1],              
    }
    
    title_data = PTN.parse(file.get("short_name"))
    if item.get("name") == item.get("hash"):
        item["name"] = title_data.get("title", file.get("short_name"))

    metadata, success, detail = await search_metadata(
        title_data.get("title", file.get("short_name")),
        title_data,
        file.get("short_name"),
        f"{item.get('name')} {file.get('short_name')}"
    )
    data.update(metadata)
    logging.debug(f"Processing data {data}")
    await db.add_meta_item(data)
    return data


async def get_user_downloads(download_type: DownloadType) -> Tuple[List[Dict], bool, str]:
    """Fetch user downloads asynchronously with pagination"""
    offset = 0
    limit = 1000
    file_data = []
    
    async with settings.api_http_client as client:
        while True:
            params = {
                "limit": limit,
                "offset": offset,
                "bypass_cache": True,
            }
            try:
                response = await client.get(f"/{download_type.value}/mylist",params=params)
                response.raise_for_status()
                
                data = response.json().get("data", [])
                if not data:
                    break
                    
                file_data.extend(data)
                offset += limit
                if len(data) < limit:
                    break
                    
            except Exception as e:
                logging.error(f"Error fetching {download_type.value}: {e}")
                return None, False, f"Error fetching {download_type.value}: {e}"

    if not file_data:
        return None, True, f"No {download_type.value} found."
    
    logging.debug(f"Fetched {len(file_data)} {download_type.value} items from API.")
    
    # Process files concurrently
    tasks = []
    for item in file_data:
        if not item.get("cached", False):
            continue
        for file in item.get("files", []):
            tasks.append(process_file(item, file, download_type))
    
    # Gather all results
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter successful results
    files = [result for result in results if isinstance(result, dict)]
    
    # Handle errors
    for result in results:
        if isinstance(result, Exception):
            logging.error(f"Error processing file: {result}")
            logging.error(traceback.format_exc())
    
    return files, True, f"{download_type.value.capitalize()} fetched successfully."


async def search_metadata(query: str, title_data: Dict, file_name: str, full_title: str) -> Tuple[Dict, bool, str]:
    """Search metadata asynchronously"""
    base_metadata = {
        "metadata_title": cleanTitle(query),
        "metadata_link": None,
        "metadata_mediatype": "movie",
        "metadata_image": None,
        "metadata_backdrop": None,
        "metadata_years": None,
        "metadata_season": None,
        "metadata_episode": None,
        "metadata_filename": file_name,
        "metadata_rootfoldername": title_data.get("title", None),
    }
    
    extension = os.path.splitext(file_name)[-1]
    
    try:
        async with settings.search_api_http_client as client:
            response = await client.get(f"/meta/search/{full_title}",params={"type": "file"})
            response.raise_for_status()
            
            data = response.json().get("data", [])[0]
            title = cleanTitle(data.get("title"))
            base_metadata["metadata_title"] = title
            base_metadata["metadata_years"] = cleanYear(
                title_data.get("year", None) or data.get("releaseYears", None)
            )

            if data.get("type") in ("anime", "series"):
                series_season_episode = constructSeriesTitle(
                    season=title_data.get("season", None),
                    episode=title_data.get("episode", None)
                )
                file_name = f"{title} {series_season_episode}{extension}"
                base_metadata["metadata_foldername"] = constructSeriesTitle(
                    season=title_data.get("season", 1),
                    folder=True
                )
                base_metadata["metadata_season"] = title_data.get("season", 1)
                base_metadata["metadata_episode"] = title_data.get("episode")
            elif data.get("type") == "movie":
                file_name = f"{title} ({base_metadata['metadata_years']}){extension}"
            else:
                return base_metadata, False, "No metadata found."
                
            base_metadata.update({
                "metadata_filename": file_name,
                "metadata_mediatype": data.get("type"),
                "metadata_link": data.get("link"),
                "metadata_image": data.get("image"),
                "metadata_backdrop": data.get("backdrop"),
                "metadata_rootfoldername": f"{title} ({base_metadata['metadata_years']})"
            })
            
            return base_metadata, True, "Metadata found."
            
    except IndexError:
        return base_metadata, False, "No metadata found."
    except httpx.TimeoutException:
        return base_metadata, False, "Timeout searching metadata."
    except Exception as e:
        logging.error(f"Error searching metadata: {e}")
        logging.error(traceback.format_exc())
        return base_metadata, False, f"Error searching metadata: {e}"


async def get_download_link(url: str) -> str:
    """Get download link asynchronously"""
    async with settings.general_http_client as client:
        response = await client.get(url)
        if response.status_code in (301, 302, 303, 307, 308):
            return response.headers.get('Location', url)
        return url


async def download_file(url: str, size: int, offset: int = 0) -> bytes:
    """Download file chunk asynchronously"""
    headers = {
        "Range": f"bytes={offset}-{offset + size - 1}",
    }
    
    async with settings.general_http_client as client:
        response = await client.get(url, headers=headers)
        if response.status_code == httpx.codes.OK:
            return response.content
        elif response.status_code == httpx.codes.PARTIAL_CONTENT:
            return response.content
        else:
            logging.error(f"Error downloading file: {response.status_code}")
            raise Exception(f"Error downloading file: {response.status_code}")






