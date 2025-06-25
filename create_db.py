# create_db.py
import pandas as pd
import sqlite3
import os
import requests
import time # Import time for sleep
from io import StringIO
import csv
import json # For serializing ingredients
import re # For cleaning up ingredient names
import logging # Import logging module
from config import DB_NAME, ITEMS_CSV_URL, PERKS_SCRAPED_CSV_URL, LEGACY_CRAFTING_RECIPES_CSV_URL  # Import new URL

def parse_recipes(csv_data):
    """
    Parses CSV data containing crafting recipes and extracts relevant information.

    Args:
        csv_data (str): A string containing CSV data of crafting recipes.

    Returns:
        list: A list of dictionaries, where each dictionary represents a recipe
              with 'Name' and 'Ingredients' (a list of {item: qty} dictionaries).
    """
    recipes = []
    csvfile = StringIO(csv_data)
    reader = csv.DictReader(csvfile)

    for row in reader:
        recipe_name = row.get("Name")
        if not recipe_name:
            continue

        ingredients = []
        for i in range(1, 8): # Iterate through Ingredient1 to Ingredient7
            ingredient_key = f"Ingredient{i}"
            qty_key = f"Qty{i}"

            ingredient_name = row.get(ingredient_key)
            qty_str = row.get(qty_key)

            if ingredient_name and qty_str:
                try:
                    qty = int(qty_str)
                    if qty > 0: # Only add ingredients with positive quantities
                        ingredients.append({"item": ingredient_name, "qty": qty})
                except ValueError:
                    pass # Handle cases where Qty is not a valid integer
        if ingredients: # Only add recipes that have at least one ingredient
            recipes.append({"Name": recipe_name, "Ingredients": ingredients})
    return recipes

ITEMS_CSV_PATH = "items.csv" #https://raw.githubusercontent.com/involvex/ina-discord-bot/refs/heads/main/items.csv

def fetch_recipes_data(base_url="https://nwdb.info", retries=3, delay=0.5):
    all_recipes_data = []
    actual_page_count = 1 # Will be updated from first page
    logging.info(f"Starting recipe scraping from {base_url}/db/recipes...")

    for page_num in range(1, actual_page_count + 1):
        current_url = f"{base_url}/db/recipes/page/{page_num}.json"
        logging.info(f"Fetching recipe page: {current_url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        json_data = None
        for attempt in range(retries):
            try:
                response = requests.get(current_url, headers=headers, timeout=20)
                response.raise_for_status()
                json_data = response.json()
                break
            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching recipe page {current_url} (Attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    logging.error(f"Failed to fetch recipe page {current_url} after {retries} attempts. Skipping.")
                    json_data = None
                    break
            except json.JSONDecodeError:
                logging.error(f"Error decoding JSON from {current_url} (Attempt {attempt + 1}/{retries}). Content: {response.text[:200]}")
                json_data = None
                break

        if json_data is None or not json_data.get('success') or not json_data.get('data'):
            logging.warning(f"Skipping recipe page {page_num} due to fetch/parse failure or no data.")
            break

        if page_num == 1 and json_data.get('pageCount'):
            actual_page_count = json_data['pageCount']
            logging.info(f"Total recipe pages to scrape: {actual_page_count}")

        for recipe_entry in json_data['data']:
            try:
                output_item_name = recipe_entry.get('output', {}).get('name')
                if not output_item_name:
                    logging.warning(f"Skipping recipe entry with no output item name: {recipe_entry}")
                    continue

                ingredients = recipe_entry.get('ingredients', []) # Already a list of dicts
                all_recipes_data.append({
                    'output_item_name': output_item_name,
                    'station': recipe_entry.get('station'),
                    'skill': recipe_entry.get('tradeskill'),
                    'skill_level': recipe_entry.get('tradeskillLevel'),
                    'tier': recipe_entry.get('tier'),
                    'ingredients': json.dumps(ingredients),
                    'raw_recipe_data': json.dumps(recipe_entry)
                })
            except Exception as e:
                logging.error(f"Error processing recipe entry: {e}. Entry: {recipe_entry}", exc_info=True) # Added exc_info=True
        time.sleep(delay)

    logging.info(f"Scraped {len(all_recipes_data)} recipes.")
    return all_recipes_data

CSV_SOURCES = {
    "items": ITEMS_CSV_URL, # Use the imported constant
    # "perks" will be handled specially from a local file perks_buddy.csv
    # "perks_legacy": "https://raw.githubusercontent.com/involvex/ina-discord-bot/main/perks_scraped.csv", # Kept for reference, but not used
}

def fetch_csv_data(url, retries=3, delay=5):
    logging.info(f"Fetching CSV from {url}...")
    for i in range(retries):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()  # Raise an exception for HTTP errors
            # Save to disk for possible debugging, but will be deleted after DB population
            with open(ITEMS_CSV_PATH, "w", encoding="utf-8") as f:
                f.write(response.text)
            return response.text
        except requests.RequestException as e:
            logging.error(f"Error fetching CSV from {url}: {e}")
            if i < retries - 1:
                logging.warning(f"Retrying in {delay} seconds... (Attempt {i + 2}/{retries})")
                time.sleep(delay)
            else:
                logging.error(f"Failed to fetch CSV from {url} after {retries} attempts.")
                return None
    return None # Should not be reached, but for clarity

def cleanup_items_csv():
    if os.path.exists(ITEMS_CSV_PATH):
        os.remove(ITEMS_CSV_PATH) # Keep this as a print, as it's a final cleanup message
        logging.info("Removed items.csv after DB population.")


def populate_db():
    conn = sqlite3.connect(DB_NAME) # Keep this as a print, as it's a final cleanup message
    logging.info(f"Connecting to and populating database: {DB_NAME}")
    cursor = conn.cursor()
    try:
        # --- Populate items table ---
        # Force fetching items from remote URL by removing local scraped file if it exists
        scraped_items_path = 'items_scraped.csv'
        if os.path.exists(scraped_items_path):
            logging.info(f"Removing existing local '{scraped_items_path}' to force fresh download from remote URL.")
            os.remove(scraped_items_path)

        items_df = None
        logging.info(f"Fetching items data from remote URL: {ITEMS_CSV_URL}")
        csv_data = fetch_csv_data(ITEMS_CSV_URL)
        if csv_data:
            try:
                items_df = pd.read_csv(StringIO(csv_data), low_memory=False, encoding='utf-8')
            except pd.errors.EmptyDataError:
                logging.warning(f"CSV from {ITEMS_CSV_URL} for table 'items' is empty or invalid.")
            except Exception as e:
                logging.error(f"Error processing CSV for table 'items': {e}")

        if items_df is not None:
            try:
                items_df.columns = [col.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'percent') for col in items_df.columns]
                items_df.to_sql('items', conn, if_exists="replace", index=False)
                logging.info("Successfully loaded data into 'items' table.")
                logging.info("Creating index on 'items' table for faster lookups...")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_name_lower ON items (lower(Name))")
            except Exception as e:
                logging.error(f"Error loading items data into database: {e}", exc_info=True)
        else:
            logging.warning("Could not load any item data for the 'items' table.")

        # --- Populate perks table from scraped data (primary source) ---
        df_perks_final = pd.DataFrame()  # This will be the final DataFrame for the 'perks' table

        logging.info(f"Attempting to load perks data from scraped source: {PERKS_SCRAPED_CSV_URL}")
        scraped_perks_data = fetch_csv_data(PERKS_SCRAPED_CSV_URL)
        if scraped_perks_data:
            try:
                df_scraped_perks = pd.read_csv(StringIO(scraped_perks_data), low_memory=False)
                # Sanitize column names for DB
                df_scraped_perks.columns = [col.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'percent') for col in df_scraped_perks.columns]
                df_perks_final = df_scraped_perks.copy()
                logging.info(f"Successfully loaded initial 'perks' data from {PERKS_SCRAPED_CSV_URL}.")
            except Exception as e:
                logging.error(f"Error processing scraped perks data from {PERKS_SCRAPED_CSV_URL}: {e}", exc_info=True)
        else:
            logging.warning(f"Could not fetch scraped perks data from {PERKS_SCRAPED_CSV_URL}. 'perks' table might be incomplete.")

        # --- Supplement/Override perks table from local perks_buddy.csv (secondary source) ---
        perks_buddy_csv_path = "perks_buddy.csv"
        logging.info(f"Attempting to load and merge perks data from local file: {perks_buddy_csv_path}")
        if os.path.exists(perks_buddy_csv_path):
            try:
                df_perks_buddy = pd.read_csv(perks_buddy_csv_path, low_memory=False)
                
                # Construct icon_url from perks_buddy.csv if 'Icon Path' exists
                if 'Icon Path' in df_perks_buddy.columns:
                    df_perks_buddy['icon_url_from_buddy'] = "https://cdn.nw-buddy.de/nw-data/live/" + df_perks_buddy['Icon Path'].astype(str)
                else:
                    df_perks_buddy['icon_url_from_buddy'] = ''

                # Define columns to potentially override from perks_buddy.csv
                # These are the columns in the DB schema that perks_buddy.csv might provide better data for
                buddy_override_cols = {
                    'id': 'Perk ID',
                    'name': 'Name',
                    'description': 'Description',
                    'PerkType': 'Type',
                    'ConditionText': 'Condition Event',
                    'CompatibleEquipment': 'Item Class',
                    'ExclusiveLabels': 'Exclusive Labels',
                    'ExclusiveLabel': 'Exclusive Labels',
                    'CraftModItem': 'Craft Mod',
                    'GeneratedLabel': 'Category',
                    'icon_url': 'icon_url_from_buddy'  # This is the key for the constructed URL
                }

                # Prepare df_perks_buddy for merging by selecting and renaming columns
                df_buddy_processed = pd.DataFrame()
                for db_col, buddy_col in buddy_override_cols.items():
                    if buddy_col in df_perks_buddy.columns:
                        df_buddy_processed[db_col] = df_perks_buddy[buddy_col]
                    elif buddy_col == 'icon_url' and 'icon_url_from_buddy' in df_perks_buddy.columns:
                        df_buddy_processed[db_col] = df_perks_buddy['icon_url_from_buddy']
                    else:
                        df_buddy_processed[db_col] = None  # Column not found in buddy, will be NaN

                # Ensure 'id' column is present for merging
                if 'id' not in df_buddy_processed.columns and 'Perk ID' in df_perks_buddy.columns:
                    df_buddy_processed['id'] = df_perks_buddy['Perk ID']
                if 'id' not in df_buddy_processed.columns and 'id' in df_perks_buddy.columns:  # Fallback if 'Perk ID' not there
                    df_buddy_processed['id'] = df_perks_buddy['id']

                # If df_perks_final is empty, and buddy data is available, use buddy data as base
                if df_perks_final.empty and not df_buddy_processed.empty:
                    df_perks_final = df_buddy_processed.copy()
                    logging.info(f"Using {perks_buddy_csv_path} as the primary source for perks (scraped data not available).")
                elif not df_perks_final.empty and not df_buddy_processed.empty:
                    # Merge buddy data into final DataFrame, prioritizing buddy data
                    df_perks_final = df_buddy_processed.set_index('id').combine_first(df_perks_final.set_index('id')).reset_index()
                    logging.info(f"Successfully merged data from {perks_buddy_csv_path} into scraped perks data.")
                else:
                    logging.warning(f"{perks_buddy_csv_path} found, but no data to merge or primary data is missing.")
            except Exception as e:
                logging.error(f"Error processing {perks_buddy_csv_path} for table 'perks': {e}", exc_info=True)
        else:
            logging.warning(f"{perks_buddy_csv_path} not found. 'perks' table will not be populated from this source.")

        # Ensure all target DB columns exist in the final DataFrame, even if some sources were missing
        target_db_cols = ['id', 'name', 'description', 'PerkType', 'icon_url', 'ConditionText', 'CompatibleEquipment', 'ExclusiveLabels', 'ExclusiveLabel', 'CraftModItem', 'GeneratedLabel']
        for col in target_db_cols:
            if col not in df_perks_final.columns:
                df_perks_final[col] = None

        # Finally, write the combined DataFrame to SQL
        if not df_perks_final.empty:
            df_perks_final.to_sql("perks", conn, if_exists="replace", index=False)
            logging.info("Creating index on 'perks' table for faster lookups...")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_perks_name_lower ON perks (lower(name))")
            logging.info(f"Successfully loaded combined data into 'perks' table.")
        else:
            logging.warning("No data available to populate 'perks' table.")

        # --- Populate recipes table from nwdb.info/db/recipes ---
        logging.info("Populating 'recipes' table from nwdb.info/db/recipes...")
        recipes_data = fetch_recipes_data()
        if recipes_data:
            recipes_df = pd.DataFrame(recipes_data)
            # Ensure 'recipes' table schema is correct before inserting
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                output_item_name TEXT PRIMARY KEY,
                station TEXT,
                skill TEXT,
                skill_level INTEGER,
                tier INTEGER,
                ingredients TEXT,
                raw_recipe_data TEXT
            )
            """)
            recipes_df.to_sql('recipes', conn, if_exists='replace', index=False)
            logging.info(f"Successfully added {len(recipes_df)} recipes to the 'recipes' table.")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipes_output_item_name_lower ON recipes (lower(output_item_name))")

        # --- Populate parsed_recipes table from LEGACY_CRAFTING_RECIPES_CSV_URL ---
        logging.info(f"Populating 'parsed_recipes' table from {LEGACY_CRAFTING_RECIPES_CSV_URL}...")
        legacy_csv_data = fetch_csv_data(LEGACY_CRAFTING_RECIPES_CSV_URL)
        if legacy_csv_data:
            parsed_legacy_recipes = parse_recipes(legacy_csv_data)
            
            # Prepare data for DataFrame
            recipes_to_insert = []
            for recipe_entry in parsed_legacy_recipes:
                recipes_to_insert.append({
                    'Name': recipe_entry['Name'],
                    'Ingredients': json.dumps(recipe_entry['Ingredients']) # Store as JSON string
                })

            recipes_df = pd.DataFrame(recipes_to_insert)
            
            # Ensure 'parsed_recipes' table schema is correct before inserting
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS parsed_recipes (
                Name TEXT PRIMARY KEY,
                Ingredients TEXT
            )
            """)
            recipes_df.to_sql('parsed_recipes', conn, if_exists='replace', index=False)
            logging.info(f"Successfully added {len(recipes_df)} recipes to the 'parsed_recipes' table.")
            logging.info("Creating index on 'parsed_recipes' table for faster lookups...")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_parsed_recipes_name_lower ON parsed_recipes (lower(Name))")
        else:
            logging.warning("No legacy crafting recipe data fetched. 'parsed_recipes' table might be empty.")
    finally:
        conn.close()
        logging.info("Database population finished.")

if __name__ == "__main__":
    populate_db()
    cleanup_items_csv()