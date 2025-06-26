import sqlite3
import logging
from typing import Dict, Optional

from config import DB_NAME

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_item(item_name: str) -> Optional[Dict[str, str]]:
    """
    Retrieves item data from the SQLite database by item name.
    Returns a dictionary containing item data if found, otherwise None.
    """
    conn = None
    try:
        conn = sqlite3.connect(f'file:{DB_NAME}?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row  # This allows accessing columns by name
        cursor = conn.cursor()

        # Query the database for the item, case-insensitively
        cursor.execute("SELECT * FROM items WHERE lower(Name) = lower(?)", (item_name,))
        item_row = cursor.fetchone()

        if item_row:
            # Convert the sqlite3.Row object to a dictionary
            return dict(item_row)
        else:
            return None

    except sqlite3.Error as e:
        logger.error(f"Database error in get_item: {e}")
        return None
    finally:
        if conn:
            conn.close()
