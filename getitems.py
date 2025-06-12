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
    csv_path = os.path.join(os.path.dirname(__file__), 'items.csv')
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                item_name = row.get('name', '').lower()
                if item_name:
                    items_db[item_name] = {
                        'id': row.get('id', ''),
                        'name': row.get('name', ''),
                        'description': row.get('description', ''),
                        'rarity': row.get('rarity', ''),
                        'type': row.get('type', '')
                    }
            logger.info(f"Loaded {len(items_db)} items from database")
    except FileNotFoundError:
        logger.warning("Items database not found. Creating new file.")
        headers = ['id', 'name', 'description', 'rarity', 'type']
        try:
            with open(csv_path, 'w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()
        except Exception as e:
            logger.error(f"Failed to create items database: {e}")
            return {}
    except Exception as e:
        logger.error(f"Error reading items database: {e}")
        return {}

    return items_db

def add_item(item_data: Dict[str, str]) -> bool:
    """
    Adds a new item to the CSV database.
    Returns True if successful, False otherwise.
    """
    csv_path = os.path.join(os.path.dirname(__file__), 'items.csv')
    headers = ['id', 'name', 'description', 'rarity', 'type']
    
    try:
        if not all(key in item_data for key in headers):
            logger.error("Missing required fields in item data")
            return False
            
        # Read existing items to check for duplicates
        items = get_item_database()
        if item_data.get('name', '').lower() in items:
            logger.warning(f"Item {item_data['name']} already exists in database")
            return False
            
        with open(csv_path, 'a', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writerow(item_data)
            logger.info(f"Successfully added item: {item_data['name']}")
        return True
    except Exception as e:
        logger.error(f"Error adding item to database: {e}")
        return False

def get_item(item_name: str) -> Optional[Dict[str, str]]:
    """
    Retrieves item data from the database by item name.
    Returns a dictionary containing item data if found, otherwise None.
    """
    items_db = get_item_database()
    return items_db.get(item_name.lower())
