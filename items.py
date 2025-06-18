import csv
import logging
import requests
import io

logger = logging.getLogger(__name__)

def _process_csv_data(reader, items_dict: dict, source_description_for_log: str) -> bool:
    """
    Helper function to process the CSV data from a reader and populate items_dict.
    Returns True if processing was attempted, False if critical setup like header/name column failed.
    """
    if not reader.fieldnames:
        logger.error(f"CSV from '{source_description_for_log}' is empty or has no header row.")
        return False

    item_name_column = None
    possible_names = ['name', 'item_name', 'itemName']
    normalized_fieldnames = {f.lower(): f for f in reader.fieldnames}

    for potential_col_name in possible_names:
        if potential_col_name in normalized_fieldnames:
            item_name_column = normalized_fieldnames[potential_col_name]
            break
    
    if not item_name_column:
        logger.error(
            f"No suitable item name column found in CSV from '{source_description_for_log}'. "
            f"Expected one of {possible_names}. Found: {reader.fieldnames}"
        )
        return False
            
    logger.info(f"Using '{item_name_column}' as the item name column from '{source_description_for_log}'.")
    items_loaded_count = 0
    for row_number, row in enumerate(reader, 1):
        if item_name_column not in row or row[item_name_column] is None:
            logger.warning(
                f"Skipping row {row_number} in CSV from '{source_description_for_log}': "
                f"item name column '{item_name_column}' is missing or empty."
            )
            continue
        
        item_name = str(row[item_name_column]).lower()
        if not item_name:
            logger.warning(
                f"Skipping row {row_number} in CSV from '{source_description_for_log}': "
                f"item name in column '{item_name_column}' is empty after processing."
            )
            continue

        if item_name in items_dict:
            logger.warning(
                f"Duplicate item name '{item_name}' found in CSV from '{source_description_for_log}' at row {row_number}. "
                "Previous entry will be overwritten."
            )
        items_dict[item_name] = row
        items_loaded_count +=1
    
    if not items_loaded_count:
        logger.warning(f"No items were successfully loaded from '{source_description_for_log}'. The file might be empty or all rows had issues.")
    else:
        logger.info(f"Successfully loaded {items_loaded_count} items from '{source_description_for_log}'.")
    return True

def load_items_from_csv(source_path_or_url: str) -> dict | None:
    """
    Loads item data from a CSV file into a dictionary.

    The item name, used as the key in the dictionary, is determined by
    looking for a column named 'name', 'item_name', or 'itemName' (case-insensitive).
    The entire row is stored as the value, with the item name itself converted to lowercase.

    Args:
        source_path_or_url: The local file path or URL to the CSV file.

    Returns:
        A dictionary mapping lowercase item names to their corresponding row data (as a dict),
        or None if loading fails.
    """
    items = {}
    try:
        if source_path_or_url.startswith(('http://', 'https://')):
            logger.info(f"Fetching items CSV from URL: {source_path_or_url}")
            response = requests.get(source_path_or_url, timeout=15)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            with io.StringIO(response.text) as csv_stream:
                reader = csv.DictReader(csv_stream)
                if not _process_csv_data(reader, items, source_path_or_url):
                    return None # Helper indicated a critical processing issue
        else:
            logger.info(f"Reading items CSV from local file: {source_path_or_url}")
            with open(source_path_or_url, mode='r', encoding='utf-8', newline='') as csv_file:
                reader = csv.DictReader(csv_file)
                if not _process_csv_data(reader, items, source_path_or_url):
                    return None # Helper indicated a critical processing issue
        
        return items

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching CSV from URL '{source_path_or_url}': {e}")
        return None
    except FileNotFoundError:
        logger.error(f"Error: The local CSV file '{source_path_or_url}' was not found.")
        return None
    except ValueError as e:
        logger.error(f"A CSV-related error occurred while processing '{source_path_or_url}': {e}")
        return None
    except IOError as e:
        logger.error(f"An I/O error occurred with '{source_path_or_url}': {e}")
        return None
    except Exception as e:
        logger.exception(f"An unexpected error occurred while loading items from '{source_path_or_url}': {e}")
        return None

# Example usage:
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s') # Configure basic logging for the example
    items_data = load_items_from_csv('items.csv')
    if items_data:
        print(f"Loaded {len(items_data)} items from CSV.")
    else:
        print("Failed to load items.")
