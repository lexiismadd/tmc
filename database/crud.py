import sqlite3
from pathlib import Path
from typing import List, Optional
from database.models import TorrentInfo, NZBInfo, DownloadStatus
from config.settings import settings
import logging
import json

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_path = Path(settings.symlink_path) / "torbox_emulator.db"
        self.conn = None
        self._initialize_db()

    async def _initialize_db(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Torrents table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS torrents (
            hash TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            size INTEGER NOT NULL,
            progress REAL NOT NULL,
            status TEXT NOT NULL,
            category TEXT NOT NULL,
            save_path TEXT NOT NULL,
            ratio REAL NOT NULL,
            added_on INTEGER NOT NULL,
            completed_on INTEGER
        )
        """)
        
        # NZB table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS nzbs (
            nzb_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            size INTEGER NOT NULL,
            progress REAL NOT NULL,
            status TEXT NOT NULL,
            category TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            added_on INTEGER NOT NULL,
            completed_on INTEGER
        )
        """)
        
        # tb_meta table which replaces tinydb in previous versions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tb_meta (
            item_id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            folder_name TEXT NOT NULL,
            folder_hash TEXT NOT NULL,
            file_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_mimetype TEXT NOT NULL,
            path TEXT NOT NULL,
            download_link TEXT NOT NULL,
            extension TEXT NOT NULL,
            metadata_title TEXT NOT NULL,
            metadata_link TEXT NOT NULL,
            metadata_mediatype TEXT NOT NULL,
            metadata_image TEXT NOT NULL,
            metadata_backdrop TEXT NOT NULL,
            metadata_years INTEGER,
            metadata_season INTEGER,
            metadata_episode TEXT,
            metadata_filename TEXT NOT NULL,
            metadata_rootfoldername TEXT NOT NULL,
            metadata_foldername TEXT,
            real_path TEXT NOT NULL,
            symlink_path TEXT NOT NULL,
            extra_json TEXT,
            UNIQUE(item_id, file_id)
        )
        """)
        
        self.conn.commit()

    async def add_torrent(self, torrent: TorrentInfo):
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO torrents VALUES (
            :hash, :name, :size, :progress, :status, 
            :category, :save_path, :ratio, :added_on, :completed_on
        )
        """, torrent.model_dump())
        self.conn.commit()

    async def get_torrent(self, torrent_hash: str) -> Optional[TorrentInfo]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM torrents WHERE hash = ?", (torrent_hash,))
        row = cursor.fetchone()
        return TorrentInfo(**row) if row else None

    async def get_torrents(
        self, 
        status: Optional[DownloadStatus] = None,
        category: Optional[str] = None
    ) -> List[TorrentInfo]:
        cursor = self.conn.cursor()
        query = "SELECT * FROM torrents"
        params = []
        
        if status or category:
            query += " WHERE "
            conditions = []
            if status:
                conditions.append("status = ?")
                params.append(status.value)
            if category:
                conditions.append("category = ?")
                params.append(category)
            query += " AND ".join(conditions)
        
        cursor.execute(query, params)
        return [TorrentInfo(**row) for row in cursor.fetchall()]

    async def update_torrent_status(self, torrent_hash: str, status: DownloadStatus):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE torrents SET status = ? WHERE hash = ?",
            (status.value, torrent_hash)
        )
        self.conn.commit()

    # Similar methods for NZB operations
    async def add_nzb(self, nzb: NZBInfo):
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO nzbs VALUES (
            :nzb_id, :name, :size, :progress, :status, 
            :category, :storage_path, :added_on, :completed_on
        )
        """, nzb.model_dump())
        self.conn.commit()

    async def get_nzb(self, nzb_id: str) -> Optional[NZBInfo]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM nzbs WHERE nzb_id = ?", (nzb_id,))
        row = cursor.fetchone()
        return NZBInfo(**row) if row else None



    async def close(self):
        if self.conn:
            self.conn.close()



    async def add_meta_item(self, item: dict):
        cursor = self.conn.cursor()
        
        # Extract known fields
        known_fields = {
            'item_id', 'type', 'folder_name', 'folder_hash', 'file_id',
            'file_name', 'file_size', 'file_mimetype', 'path', 'download_link',
            'extension', 'metadata_title', 'metadata_link', 'metadata_mediatype',
            'metadata_image', 'metadata_backdrop', 'metadata_years', 'metadata_season',
            'metadata_episode', 'metadata_filename', 'metadata_rootfoldername',
            'metadata_foldername', 'real_path', 'symlink_path'
        }
        
        # Separate known fields from extra fields
        db_fields = {k: v for k, v in item.items() if k in known_fields}
        extra_fields = {k: v for k, v in item.items() if k not in known_fields}
        
        # Handle metadata_episode array conversion
        metadata_episode = db_fields.get('metadata_episode')
        if isinstance(metadata_episode, list):
            db_fields['metadata_episode'] = ','.join(map(str, metadata_episode)) if metadata_episode else None
        
        # Serialize extra fields to JSON
        db_fields['extra_json'] = json.dumps(extra_fields) if extra_fields else None
        
        cursor.execute("""
        INSERT OR REPLACE INTO tb_meta VALUES (
            :item_id, :type, :folder_name, :folder_hash, :file_id, :file_name,
            :file_size, :file_mimetype, :path, :download_link, :extension,
            :metadata_title, :metadata_link, :metadata_mediatype, :metadata_image,
            :metadata_backdrop, :metadata_years, :metadata_season, :metadata_episode,
            :metadata_filename, :metadata_rootfoldername, :metadata_foldername,
            :real_path, :symlink_path, :extra_json
        )
        """, db_fields)
        self.conn.commit()


    async def get_meta_item(
        self,
        item_id: int | list[int] | None = None,
        file_id: int | None = None
    ) -> list[dict]:
        """
        Get one or more metadata items
        Args:
            item_id: None (all items), single ID, or list of IDs
            file_id: Optional file_id filter
        Returns:
            List of metadata dictionaries
        """
        cursor = self.conn.cursor()
        try:
            query = "SELECT * FROM tb_meta"
            params = []
            
            conditions = []
            if item_id is not None:
                if isinstance(item_id, int):
                    item_id = [item_id]
                conditions.append(f"item_id IN ({','.join(['?']*len(item_id))})")
                params.extend(item_id)
            
            if file_id is not None:
                conditions.append("file_id = ?")
                params.append(file_id)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            cursor.execute(query, params)
            results = []
            
            for row in cursor.fetchall():
                item = dict(row)
                if item.get('metadata_episode'):
                    item['metadata_episode'] = [int(ep) for ep in item['metadata_episode'].split(',')]
                if item.get('extra_json'):
                    item.update(json.loads(item['extra_json']))
                    del item['extra_json']
                results.append(item)
                
            return results
            
        except sqlite3.Error as e:
            logging.error(f"Error fetching meta items: {str(e)}")
            return []


    async def get_meta_items_by_type(self, record_type: str) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT * FROM tb_meta 
        WHERE type = ?
        ORDER BY metadata_title, metadata_season, metadata_episode
        """, (record_type,))
        
        items = []
        for row in cursor.fetchall():
            item = dict(row)
            if item.get('metadata_episode'):
                item['metadata_episode'] = [int(ep) for ep in item['metadata_episode'].split(',')]
            else:
                item['metadata_episode'] = None
            
            if item.get('extra_json'):
                extra_fields = json.loads(item['extra_json'])
                item.update(extra_fields)
                del item['extra_json']
            
            items.append(item)
        
        return items


    async def get_meta_items_by_mediatype(self, mediatype: str) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT * FROM tb_meta 
        WHERE metadata_mediatype = ?
        ORDER BY metadata_title, metadata_season, metadata_episode
        """, (mediatype,))
        
        items = []
        for row in cursor.fetchall():
            item = dict(row)
            if item.get('metadata_episode'):
                item['metadata_episode'] = [int(ep) for ep in item['metadata_episode'].split(',')]
            else:
                item['metadata_episode'] = None
            
            if item.get('extra_json'):
                extra_fields = json.loads(item['extra_json'])
                item.update(extra_fields)
                del item['extra_json']
            
            items.append(item)
        
        return items
    
    
    async def delete_meta_items(
        self,
        item_id: int | list[int],
        file_id: int | None = None,
        record_type: str | None = None
    ) -> int:
        """
        Delete one or multiple meta items with optional filters
        Args:
            item_id: Single ID or list of IDs
            file_id: Optional file_id filter (None for all files)
            record_type: Optional record_type filter (must match 'type' column exactly)
        Returns:
            Number of deleted rows
        """
        cursor = self.conn.cursor()
        try:
            if isinstance(item_id, int):
                item_id = [item_id]

            # Base query parts
            query = "DELETE FROM tb_meta WHERE item_id IN ({})".format(','.join(['?']*len(item_id)))
            params = list(item_id)  # Start with item_ids

            # Add optional filters
            conditions = []
            if file_id is not None:
                conditions.append("file_id = ?")
                params.append(file_id)
            if type is not None:
                conditions.append("type = ?")
                params.append(record_type)

            # Combine all conditions
            if conditions:
                query += " AND " + " AND ".join(conditions)

            # Execute with proper parameter binding
            cursor.execute(query, params)
            self.conn.commit()
            return cursor.rowcount

        except sqlite3.Error as e:
            logging.error(f"Error deleting meta items: {str(e)}")
            self.conn.rollback()
            return 0
        except Exception as e:
            logging.error(f"Unexpected error in delete_meta_items: {str(e)}")
            self.conn.rollback()
            return 0


    async def clear_meta_items(self, record_type: str) -> int:
        """
        Delete one or multiple meta items
        Args:
            item_id: Single ID or list of IDs
            file_id: Optional file_id filter (None for all files)
        Returns:
            Number of deleted rows
        """
        
        cursor = self.conn.cursor()
        try:
            query = """
                DELETE * FROM tb_meta 
                WHERE type = ?
                """, (record_type,)
            
            cursor.execute(query)
            self.conn.commit()
            return cursor.rowcount
            
        except sqlite3.Error as e:
            logging.error(f"Error deleting meta items: {str(e)}")
            self.conn.rollback()
            return 0
    


db = Database()
