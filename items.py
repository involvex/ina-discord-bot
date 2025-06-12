import csv

def load_items_from_csv(csv_filepath):
    """Loads item data from a CSV file into a dictionary."""
    items = {}
    try:
        with open(csv_filepath, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Determine the item name column
            item_name_column = None
            possible_names = ['name', 'item_name', 'itemName']
            for col in reader.fieldnames:
                if col.lower() in possible_names:
                    item_name_column = col
                    break
            
            if not item_name_column:
                raise ValueError("No suitable item name column found (name, item_name, itemName).")
            
            for row in reader:
                item_name = row[item_name_column].lower()
                items[item_name] = row
    except FileNotFoundError:
        print(f"Error: The file {csv_filepath} was not found.")
        return None
    except ValueError as e:
        print(f"An error occurred: {e}")
        return None
    except Exception as e:
        print(f"An error occurred while reading the CSV file: {e}")
        return None
    return items

# Example usage:
# items = load_items_from_csv('items.csv')
# if items:
#     print(f"Loaded {len(items)} items from CSV.")
# else:
#     print("Failed to load items.")
