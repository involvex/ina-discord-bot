# Update getitems.py to correctly parse the CSV format
import csv
import os
import logging
from typing import Dict, Optional
import requests # For fetching from URL
import io # For reading string as file

from config import ITEMS_CSV_URL # Import ITEMS_CSV_URL
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_item_database() -> Dict[str, Dict[str, str]]:
    """
    Reads items from a remote CSV file (GitHub) and returns a dictionary of item data.
    Returns a dictionary with item names as keys and item data as values.
    """
    items_db = {}

    try:
        response = requests.get(ITEMS_CSV_URL, timeout=15)
        response.raise_for_status() # Raise an exception for HTTP errors
        
        # Use io.StringIO to treat the CSV string content as a file
        csv_content = response.text
        with io.StringIO(csv_content) as file:
            reader = csv.DictReader(file)
            
            if not reader.fieldnames:
                logger.error(f"CSV file '{csv_path}' is empty or has no header row.")
                return {}

            # Determine the item name column from the actual headers
            item_name_col_actual = None
            possible_name_headers = ["Name", "name", "ItemName", "item_name"] # Prioritize "Name"
            for header_candidate in possible_name_headers:
                if header_candidate in reader.fieldnames:
                    item_name_col_actual = header_candidate
                    break

            if not item_name_col_actual:
                logger.error(f"Could not find a suitable item name column (e.g., 'Name', 'name') in CSV headers: {reader.fieldnames} from URL {ITEMS_CSV_URL}")
                return {}

            logger.info(f"Using '{item_name_col_actual}' as the name column from remote CSV.")

            for row_idx, row in enumerate(reader, 1):
                raw_item_name = row.get(item_name_col_actual)

                if raw_item_name is None or not str(raw_item_name).strip():
                    logger.warning(f"Skipping row {row_idx} in '{csv_path}': item name in column '{item_name_col_actual}' is missing or empty.")
                    continue
                
                item_name_lower = str(raw_item_name).lower()

                if item_name_lower in items_db:
                     logger.warning(f"Duplicate item name '{item_name_lower}' (from '{raw_item_name}') found at row {row_idx} in '{csv_path}'. Overwriting previous entry.")

                # Populate with data using actual headers from the CSV sample
                items_db[item_name_lower] = {
                    'id': row.get('Item ID', ''),             # From CSV sample
                    'name': raw_item_name,                    # Original name from CSV
                    'description': row.get('Description', ''), # From CSV sample
                    'rarity': row.get('Rarity', ''),         # From CSV sample
                    'type': row.get('Item Type Name', '')     # From CSV sample
                    # Add other fields if necessary for getitems.py's purpose
                }
            logger.info(f"Loaded {len(items_db)} items from '{ITEMS_CSV_URL}' using get_item_database.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching items CSV from URL '{ITEMS_CSV_URL}': {e}")
        return {}
    except csv.Error as e:
        logger.error(f"Error parsing CSV data from '{ITEMS_CSV_URL}': {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error reading items database from '{ITEMS_CSV_URL}': {e}", exc_info=True)
        return {}

    return items_db

def add_item(item_data: Dict[str, str]) -> bool:
    """
    Adds a new item to the CSV database.
    Uses 'Name' from item_data for the item's identity.
    WARN: This function is NOT SUPPORTED when loading items from a remote URL.
    It is designed for local CSV files.
    Returns True if successful, False otherwise.
    """
    logger.error("add_item is not supported when items.csv is loaded from a remote URL. "
                   "This function requires a local, writable CSV file.")
    return False

def get_item(item_name: str) -> Optional[Dict[str, str]]:
    """
    Retrieves item data from the database by item name.
    Returns a dictionary containing item data if found, otherwise None.
    """
    items_db = get_item_database() # Relies on the fixed get_item_database
    return items_db.get(item_name.lower())
