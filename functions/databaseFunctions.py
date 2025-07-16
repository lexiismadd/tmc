import threading
import logging
from database.crud import db



def clearDatabase(type: str):
    """
    Clears the entire cache database
    """
    try:
        db.clear_meta_items(type)
        return True, "Database cleared successfully."
    except Exception as e:
        return False, f"Error clearing the database: {e}"

def insertData(data: dict):
    """
    Inserts data into the cache database - simply redirects v1 calls to v2
    """
    try:
        db.add_meta_item(data)
        return True, "Data inserted successfully."
    except Exception as e:
        return False, f"Error inserting data. {e}"
    

def deleteData(data: dict, record_type: str):
    """
    Deletes data from the database - simply redirects v1 calls to v2
    """
    try:
        db.delete_meta_items(item_id=data.get('item_id'), record_type=record_type)
        return True, "Data removed successfully."
    except Exception as e:
        return False, f"Error removing data. {e}"
    
def getAllData(type: str):
    """
    Retrieves all data from the database - simply redirects v1 calls to v2
    """
    try:
        data = db.get_meta_items_by_type(record_type=type)
        return data, True, "Data retrieved successfully."
    except Exception as e:
        return None, False, f"Error retrieving data. {e}"

def closeAllDatabases():
    """
    Closes all database connections - simply redirects v1 calls to v2
    """
    try:
        db.close()
        return True, f"Closed database connections."
    except Exception as e:
        return False, f"Error closing database: {e}"
    