import csv
import logging

logger = logging.getLogger(__name__)


def load_items_from_csv(csv_filepath: str) -> dict | None:
    """
    Loads item data from a CSV file into a dictionary.

    The item name, used as the key in the dictionary, is determined by
    looking for a column named 'name', 'item_name', or 'itemName' (case-insensitive).
    The entire row is stored as the value, with the item name itself converted to lowercase.

    Args:
        csv_filepath: The path to the CSV file.

    Returns:
        A dictionary mapping lowercase item names to their corresponding row data (as a dict),
        or None if loading fails.
    """
    items = {}
    try:
        with open(csv_filepath, mode='r', encoding='utf-8', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            
            if not reader.fieldnames:
                logger.error(f"CSV file '{csv_filepath}' is empty or has no header row.")
                return None

            # Determine the item name column
            item_name_column = None
            possible_names = ['name', 'item_name', 'itemName']

            # Normalize fieldnames from the CSV for comparison, but store original for access
            normalized_fieldnames = {f.lower(): f for f in reader.fieldnames}

            for potential_col_name in possible_names:
                if potential_col_name in normalized_fieldnames:
                    item_name_column = normalized_fieldnames[potential_col_name]
                    break
            
            if not item_name_column:
                logger.error(
                    f"No suitable item name column found in '{csv_filepath}'. "
                    f"Expected one of {possible_names}. Found: {reader.fieldnames}"
                )
                return None
            
            
            logger.info(f"Using '{item_name_column}' as the item name column from '{csv_filepath}'.")

            for row_number, row in enumerate(reader, 1):
                if item_name_column not in row or row[item_name_column] is None:
                    logger.warning(
                        f"Skipping row {row_number} in '{csv_filepath}': "
                        f"item name column '{item_name_column}' is missing or empty."
                    )
                    continue
                
                item_name = str(row[item_name_column]).lower()
                if not item_name: # Handle cases where item name might be an empty string after str().lower()
                    logger.warning(
                        f"Skipping row {row_number} in '{csv_filepath}': "
                        f"item name in column '{item_name_column}' is empty after processing."
                    )
                    continue

                if item_name in items:
                    logger.warning(
                        f"Duplicate item name '{item_name}' found in '{csv_filepath}' at row {row_number}. "
                        "Previous entry will be overwritten."
                    )
                items[item_name] = row
            
            if not items:
                logger.warning(f"No items were successfully loaded from '{csv_filepath}'. The file might be empty or all rows had issues.")
            else:
                logger.info(f"Successfully loaded {len(items)} items from '{csv_filepath}'.")

    except FileNotFoundError:
        logger.error(f"Error: The file {csv_filepath} was not found.")
        return None
    except ValueError as e:
        logger.error(f"A CSV-related error occurred while processing '{csv_filepath}': {e}")
        return None
    except IOError as e:
        logger.error(f"An I/O error occurred while reading '{csv_filepath}': {e}")
        return None
    except Exception as e:
        logger.exception(f"An unexpected error occurred while reading the CSV file '{csv_filepath}': {e}")
        return None
    return items

# Example usage:
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s') # Configure basic logging for the example
    items_data = load_items_from_csv('items.csv')
    if items_data:
        print(f"Loaded {len(items_data)} items from CSV.")
    else:
        print("Failed to load items.")
