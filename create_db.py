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
from scrape_items import scrape_nwdb_items, OUTPUT_CSV_FILE as SCRAPED_ITEMS_CSV

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

ITEMS_CSV_PATH = "items.csv" #https://raw.githubusercontent.com/involvex/ina-discord-bot/refs/heads/beta/items.csv

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
    # "perks_legacy": "https://raw.githubusercontent.com/involvex/ina-discord-bot/beta/perks_scraped.csv", # Kept for reference, but not used
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
    """
    Atomically creates and populates the database. It builds a temporary database
    and only replaces the main database file upon successful completion.
    This prevents a corrupted/empty database from being used by the bot.
    """
    temp_db_name = f"{DB_NAME}.tmp"
    conn = None

    # Clean up old temp file if it exists from a previous failed run
    if os.path.exists(temp_db_name):
        os.remove(temp_db_name)

    try:
        conn = sqlite3.connect(temp_db_name)
        logging.info(f"Connecting to and populating temporary database: {temp_db_name}")
        cursor = conn.cursor()

        # --- Populate items table ---
        logging.info("Running item scraper...")
        scrape_nwdb_items()
        if os.path.exists(SCRAPED_ITEMS_CSV):
            try:
                items_df = pd.read_csv(SCRAPED_ITEMS_CSV, low_memory=False, encoding='utf-8')
                items_df.columns = [col.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'percent') for col in items_df.columns]
                items_df.to_sql('items', conn, if_exists="replace", index=False)
                logging.info("Successfully loaded data into 'items' table.")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_name_lower ON items (lower(Name))")
            except Exception as e:
                logging.error(f"Error processing or loading items data: {e}", exc_info=True)
        else:
            logging.warning(f"Scraped items file '{SCRAPED_ITEMS_CSV}' not found. 'items' table will be empty.")

        # --- Populate perks table ---
        df_perks_final = pd.DataFrame()  # This will be the final DataFrame for the 'perks' table
        scraped_perks_data = fetch_csv_data(PERKS_SCRAPED_CSV_URL)
        if scraped_perks_data:
            try:
                df_scraped_perks = pd.read_csv(StringIO(scraped_perks_data), low_memory=False)
                df_scraped_perks.columns = [col.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'percent') for col in df_scraped_perks.columns]
                df_perks_final = df_scraped_perks.copy()
            except Exception as e:
                logging.error(f"Error processing scraped perks data from {PERKS_SCRAPED_CSV_URL}: {e}", exc_info=True)

        perks_buddy_csv_path = "perks_buddy.csv"
        if os.path.exists(perks_buddy_csv_path):
            try:
                df_perks_buddy = pd.read_csv(perks_buddy_csv_path, low_memory=False)
                if 'Icon Path' in df_perks_buddy.columns:
                    df_perks_buddy['icon_url_from_buddy'] = "https://cdn.nw-buddy.de/nw-data/live/" + df_perks_buddy['Icon Path'].astype(str)
                else:
                    df_perks_buddy['icon_url_from_buddy'] = ''
                buddy_override_cols = {'id': 'Perk ID', 'name': 'Name', 'description': 'Description', 'PerkType': 'Type', 'ConditionText': 'Condition Event', 'CompatibleEquipment': 'Item Class', 'ExclusiveLabels': 'Exclusive Labels', 'ExclusiveLabel': 'Exclusive Labels', 'CraftModItem': 'Craft Mod', 'GeneratedLabel': 'Category', 'icon_url': 'icon_url_from_buddy'}
                df_buddy_processed = pd.DataFrame()
                for db_col, buddy_col in buddy_override_cols.items():
                    if buddy_col in df_perks_buddy.columns:
                        df_buddy_processed[db_col] = df_perks_buddy[buddy_col]
                if df_perks_final.empty and not df_buddy_processed.empty:
                    df_perks_final = df_buddy_processed.copy()
                elif not df_perks_final.empty and not df_buddy_processed.empty:
                    df_perks_final = df_buddy_processed.set_index('id').combine_first(df_perks_final.set_index('id')).reset_index()
            except Exception as e:
                logging.error(f"Error processing {perks_buddy_csv_path} for table 'perks': {e}", exc_info=True)

        target_db_cols = ['id', 'name', 'description', 'PerkType', 'icon_url', 'ConditionText', 'CompatibleEquipment', 'ExclusiveLabels', 'ExclusiveLabel', 'CraftModItem', 'GeneratedLabel']
        for col in target_db_cols:
            if col not in df_perks_final.columns:
                df_perks_final[col] = None
        if not df_perks_final.empty:
            df_perks_final.to_sql("perks", conn, if_exists="replace", index=False)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_perks_name_lower ON perks (lower(name))")
            logging.info(f"Successfully loaded combined data into 'perks' table.")

        # --- Populate recipes table ---
        recipes_data = fetch_recipes_data()
        if recipes_data:
            recipes_df = pd.DataFrame(recipes_data)
            recipes_df.to_sql('recipes', conn, if_exists='replace', index=False)
            logging.info(f"Successfully added {len(recipes_df)} recipes to the 'recipes' table.")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipes_output_item_name_lower ON recipes (lower(output_item_name))")

        # --- Populate parsed_recipes table (legacy) ---
        legacy_csv_data = fetch_csv_data(LEGACY_CRAFTING_RECIPES_CSV_URL)
        if legacy_csv_data:
            parsed_legacy_recipes = parse_recipes(legacy_csv_data)
            recipes_to_insert = [{'Name': r['Name'], 'Ingredients': json.dumps(r['Ingredients'])} for r in parsed_legacy_recipes]
            recipes_df = pd.DataFrame(recipes_to_insert)
            recipes_df.to_sql('parsed_recipes', conn, if_exists='replace', index=False)
            logging.info(f"Successfully added {len(recipes_df)} recipes to the 'parsed_recipes' table.")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_parsed_recipes_name_lower ON parsed_recipes (lower(Name))")

        logging.info("All tables created and indexed in temporary database.")

    except Exception as e:
        logging.error(f"A critical error occurred during database population: {e}", exc_info=True)
        if conn:
            conn.close()
        if os.path.exists(temp_db_name):
            os.remove(temp_db_name)
            logging.info(f"Removed failed temporary database: {temp_db_name}")
        raise  # Re-raise the exception so the caller in main.py knows it failed.
    else:
        # This block runs only if the try block completes without exceptions
        if conn:
            conn.close()
        # Atomically replace the old DB with the new one
        if os.path.exists(DB_NAME):
            os.remove(DB_NAME)
        os.rename(temp_db_name, DB_NAME)
        logging.info(f"Successfully replaced '{DB_NAME}' with newly populated database.")
    finally:
        logging.info("Database population process finished.")

if __name__ == "__main__":
    populate_db()
    cleanup_items_csv()