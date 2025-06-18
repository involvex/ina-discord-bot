# Update getitems.py to correctly parse the CSV format
import csv
import os
import logging
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_item_database() -> Dict[str, Dict[str, str]]:
    """
    Reads items from CSV file and returns a dictionary of item data.
    Returns a dictionary with item names as keys and item data as values.
    """
    items_db = {}
    # Robust path, assuming items.csv is in the same directory as getitems.py
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'items.csv')

    try:
        with open(csv_path, 'r', encoding='utf-8', newline='') as file:
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
                logger.error(f"Could not find a suitable item name column (e.g., 'Name', 'name') in CSV headers: {reader.fieldnames} in file {csv_path}")
                return {}

            logger.info(f"Using '{item_name_col_actual}' as the name column from '{csv_path}'.")

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
            logger.info(f"Loaded {len(items_db)} items from '{csv_path}' using get_item_database.")
    except FileNotFoundError:
        logger.error(f"Items database file not found: {csv_path}. This function does not create it.")
        return {}
    except Exception as e:
        logger.error(f"Error reading items database from '{csv_path}': {e}", exc_info=True)
        return {}

    return items_db

def add_item(item_data: Dict[str, str]) -> bool:
    """
    Adds a new item to the CSV database.
    Uses 'Name' from item_data for the item's identity.
    Writes a predefined set of columns if creating a new file.
    WARN: This function is simplified for complex CSVs. It may not preserve all columns.
    Returns True if successful, False otherwise.
    """
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'items.csv')
    
    # Define the headers this function knows how to write, based on sample.
    writable_headers = ['Name', 'Item ID', 'Description', 'Rarity', 'Item Type Name']

    item_name_to_add = item_data.get('Name')
    if not item_name_to_add:
        logger.error("Item data must include a 'Name' field with a non-empty value.")
        return False

    file_exists = os.path.isfile(csv_path)
    is_file_empty = not file_exists or os.path.getsize(csv_path) == 0

    try:
        if file_exists and not is_file_empty:
            existing_items = get_item_database() # Uses corrected name detection
            if item_name_to_add.lower() in existing_items:
                logger.warning(f"Item '{item_name_to_add}' already exists in database. Not adding.")
                return False
            
        with open(csv_path, 'a', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=writable_headers)
            
            if is_file_empty:
                writer.writeheader()
            
            row_to_write = {header: item_data.get(header, '') for header in writable_headers}
            writer.writerow(row_to_write)
            
            logger.info(f"Successfully added/appended item: '{item_name_to_add}' to '{csv_path}'. Only columns {writable_headers} were processed.")
        return True
    except Exception as e:
        logger.error(f"Error adding item '{item_name_to_add}' to database '{csv_path}': {e}", exc_info=True)
        return False

def get_item(item_name: str) -> Optional[Dict[str, str]]:
    """
    Retrieves item data from the database by item name.
    Returns a dictionary containing item data if found, otherwise None.
    """
    items_db = get_item_database() # Relies on the fixed get_item_database
    return items_db.get(item_name.lower())
