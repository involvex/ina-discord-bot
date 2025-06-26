# create_db.py
import pandas as pd
import sqlite3
import os
import requests
import time # Import time for sleep
from io import StringIO
import csv
import json # For serializing/deserializing ingredients
import re # For cleaning up ingredient names
import logging # Import logging module
from config import DB_NAME, ITEMS_CSV_URL, PERKS_SCRAPED_CSV_URL, CRAFTING_RECIPES_CSV_URL
from scrape_items import scrape_nwdb_items, OUTPUT_CSV_FILE as SCRAPED_ITEMS_CSV

ITEMS_CSV_PATH = "items.csv" #https://raw.githubusercontent.com/involvex/ina-discord-bot/refs/heads/beta/items.csv

def fetch_csv_data(url, retries=3, delay=5, save_path=None):
    logging.info(f"Fetching CSV from {url}...")
    for i in range(retries):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()  # Raise an exception for HTTP errors
            # Save to disk for possible debugging, but will be deleted after DB population
            if save_path:
                with open(save_path, "w", encoding="utf-8") as f:
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

def fetch_and_parse_crafting_recipes(url: str, retries=3, delay=0.5):
    logging.info(f"Fetching crafting recipes from {url}...")
    csv_data = fetch_csv_data(url, retries=retries, delay=delay)
    if not csv_data:
        logging.error("Failed to fetch crafting recipe CSV data.")
        return []

    recipes_for_db = []
    reader = csv.DictReader(StringIO(csv_data))
    for row in reader:
        output_item_name = row.get("Name")
        if not output_item_name:
            continue

        ingredients = []
        for i in range(1, 8):
            ing_name = row.get(f"Ingredient{i}")
            ing_qty_str = row.get(f"Qty{i}")
            if ing_name and ing_qty_str:
                try:
                    ing_qty = int(ing_qty_str)
                    if ing_qty > 0:
                        ingredients.append({"item": ing_name, "quantity": ing_qty})
                except (ValueError, TypeError):
                    continue

        recipes_for_db.append({
            'output_item_name': output_item_name,
            'station': row.get('CraftingStation'),
            'skill': row.get('Tradeskill'),
            'skill_level': row.get('Level'),
            'tier': row.get('Tier'),
            'ingredients': json.dumps(ingredients),
            'raw_recipe_data': json.dumps(row) # Store the whole row for full context
        })
    return recipes_for_db

def populate_parsed_recipes_table(conn):
    """
    Populates the 'parsed_recipes' table from a legacy CSV URL.
    This function is designed to handle CSVs with 'Name', 'IngredientX', and 'QtyX' columns.
    """
    logging.info(f"Populating 'parsed_recipes' table from {LEGACY_CRAFTING_RECIPES_CSV_URL}...")
    legacy_recipes_csv_data = fetch_csv_data(LEGACY_CRAFTING_RECIPES_CSV_URL)
    if not legacy_recipes_csv_data:
        logging.warning("Failed to fetch legacy crafting recipe CSV data. 'parsed_recipes' table will not be created or populated.")
        return

    parsed_recipes_for_db = []
    reader = csv.DictReader(StringIO(legacy_recipes_csv_data))
    for row in reader:
        output_item_name = row.get("Name")
        if not output_item_name:
            continue

        ingredients = []
        # Assuming the legacy CSV has IngredientX and QtyX columns, similar to CRAFTING_RECIPES_CSV_URL
        for i in range(1, 8): # Assuming up to 7 ingredients
            ing_name = row.get(f"Ingredient{i}")
            ing_qty_str = row.get(f"Qty{i}")
            if ing_name and ing_qty_str:
                try:
                    ing_qty = int(ing_qty_str)
                    if ing_qty > 0:
                        ingredients.append({"item": ing_name, "quantity": ing_qty}) # Use 'quantity' for consistency
                except (ValueError, TypeError):
                    continue

        parsed_recipes_for_db.append({
            'Name': output_item_name, # Use 'Name' as expected by recipes.py fallback
            'Ingredients': json.dumps(ingredients) # Store ingredients as JSON string
        })

    if parsed_recipes_for_db:
        parsed_recipes_df = pd.DataFrame(parsed_recipes_for_db)
        parsed_recipes_df.to_sql('parsed_recipes', conn, if_exists="replace", index=False)
        cursor = conn.cursor() # Get cursor to create index
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parsed_recipes_name_lower ON parsed_recipes (lower(Name))")
        logging.info(f"Successfully loaded {len(parsed_recipes_df)} recipes into 'parsed_recipes' table.")
    else:
        logging.warning("No recipes found in legacy CSV for 'parsed_recipes' table.")

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

        # --- Populate items table from GitHub CSV ---
        logging.info(f"Fetching comprehensive item data from {ITEMS_CSV_URL}...")
        items_csv_data = fetch_csv_data(ITEMS_CSV_URL, save_path=ITEMS_CSV_PATH)
        if items_csv_data:
            try:
                # Use the locally saved file from fetch_csv_data
                items_df = pd.read_csv(ITEMS_CSV_PATH, low_memory=False, encoding='utf-8')
                items_df.columns = [col.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'percent') for col in items_df.columns]
                items_df.to_sql('items', conn, if_exists="replace", index=False)
                logging.info("Successfully loaded data into 'items' table.")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_name_lower ON items (lower(Name))")
            except Exception as e:
                logging.error(f"Error processing or loading items data from {ITEMS_CSV_PATH}: {e}", exc_info=True)
        else:
            logging.error(f"Failed to fetch item data from the URL. 'items' table will be empty.")

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

        # --- Populate recipes table from GitHub CSV ---
        recipes_data_for_db = fetch_and_parse_crafting_recipes(CRAFTING_RECIPES_CSV_URL)
        if recipes_data_for_db:
            recipes_df = pd.DataFrame(recipes_data_for_db)
            recipes_df.to_sql('recipes', conn, if_exists='replace', index=False)
            logging.info(f"Successfully added {len(recipes_df)} recipes to the 'recipes' table from GitHub CSV.")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipes_output_item_name_lower ON recipes (lower(output_item_name))")
        else:
            logging.warning("No recipes loaded from GitHub CSV. 'recipes' table might be empty.")

        # --- Populate parsed_recipes table from legacy CSV ---
        populate_parsed_recipes_table(conn)

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