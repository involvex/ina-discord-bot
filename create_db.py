# create_db.py
import pandas as pd
import sqlite3
import os
import requests
from io import StringIO
import json # For serializing ingredients
from config import DB_NAME, ITEMS_CSV_URL # Import DB_NAME and ITEMS_CSV_URL
# The recipes table will be created, but populated by other means or remain available for future population.
# Define your CSV sources
CSV_SOURCES = {
    "items": ITEMS_CSV_URL, # Use the imported constant
    # "perks" will be handled specially from a local file perks_buddy.csv
    # "perks_legacy": "https://raw.githubusercontent.com/involvex/ina-discord-bot/main/perks_scraped.csv", # Kept for reference, but not used
}

def fetch_csv_data(url):
    print(f"Fetching CSV from {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching CSV from {url}: {e}")
        return None

def cleanup_items_csv():
    if os.path.exists(ITEMS_CSV_PATH):
        os.remove(ITEMS_CSV_PATH)
        print("Removed items.csv after DB population.")


def populate_db():
    conn = sqlite3.connect(DB_NAME)
    print(f"Connecting to and populating database: {DB_NAME}")
    cursor = conn.cursor()
    try:
        for table_name, csv_url in CSV_SOURCES.items(): # This loop will now only process "items"
            csv_data = fetch_csv_data(csv_url)
            if csv_data:
                try:
                    # Use StringIO to read the CSV string data into pandas
                    df = pd.read_csv(StringIO(csv_data), low_memory=False)
                    # Ensure column names are SQL-friendly (e.g., replace spaces with underscores)
                    df.columns = [col.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'percent') for col in df.columns]
                    df.to_sql(table_name, conn, if_exists="replace", index=False)
                    print(f"Successfully loaded data into '{table_name}' table.")
                except pd.errors.EmptyDataError:
                    print(f"Warning: CSV from {csv_url} for table '{table_name}' is empty or invalid.")
                except Exception as e:
                    print(f"Error processing CSV for table '{table_name}': {e}")

        # --- Populate perks table from local perks_buddy.csv ---
        perks_buddy_csv_path = "perks_buddy.csv" # Assumes it's in the same directory
        print(f"Attempting to load perks data from local file: {perks_buddy_csv_path}")
        if os.path.exists(perks_buddy_csv_path):
            try:
                df_perks_buddy = pd.read_csv(perks_buddy_csv_path, low_memory=False)
                
                # Define mapping from perks_buddy.csv columns to our DB schema
                # DB Column Name : CSV Column Name
                column_mapping = {
                    'id': 'Perk ID',
                    'name': 'Name', # Will use this directly. Consider cleaning " of the Artificer" if needed later.
                    'description': 'Description',
                    'PerkType': 'Type',
                    # 'icon_url' will be constructed
                    'ConditionText': 'Condition Event', # Or another relevant condition field from perks_buddy
                    'CompatibleEquipment': 'Item Class',
                    'ExclusiveLabels': 'Exclusive Labels', # This is often a comma-separated list
                    'ExclusiveLabel': 'Exclusive Labels', # Can reuse, or find a singular if available
                    'CraftModItem': 'Craft Mod', # This is the ID of the item that IS the craft mod
                    'GeneratedLabel': 'Category' # Or 'Display Name' if preferred and available
                }

                # Select and rename columns
                df_perks_for_db = pd.DataFrame()
                for db_col, csv_col in column_mapping.items():
                    if csv_col in df_perks_buddy.columns:
                        df_perks_for_db[db_col] = df_perks_buddy[csv_col]
                    else:
                        print(f"Warning: Column '{csv_col}' not found in {perks_buddy_csv_path} for DB column '{db_col}'. It will be missing.")
                        df_perks_for_db[db_col] = None # Add as None if missing

                # Construct icon_url
                if 'Icon Path' in df_perks_buddy.columns:
                    df_perks_for_db['icon_url'] = "https://cdn.nw-buddy.de/nw-data/live/" + df_perks_buddy['Icon Path'].astype(str)
                else:
                    print(f"Warning: 'Icon Path' column not found in {perks_buddy_csv_path}. icon_url will be empty.")
                    df_perks_for_db['icon_url'] = ''

                # Ensure all target DB columns exist in the DataFrame, even if some source CSV columns were missing
                target_db_cols = ['id', 'name', 'description', 'PerkType', 'icon_url', 'ConditionText', 'CompatibleEquipment', 'ExclusiveLabels', 'ExclusiveLabel', 'CraftModItem', 'GeneratedLabel']
                for col in target_db_cols:
                    if col not in df_perks_for_db.columns:
                        df_perks_for_db[col] = None

                df_perks_for_db.to_sql("perks", conn, if_exists="replace", index=False)
                print(f"Successfully loaded data into 'perks' table from {perks_buddy_csv_path}.")
            except Exception as e:
                print(f"Error processing {perks_buddy_csv_path} for table 'perks': {e}")
        else:
            print(f"Warning: {perks_buddy_csv_path} not found. 'perks' table will not be populated from this source.")

        # --- Ensure 'recipes' table exists (as before) ---
        print("Ensuring 'recipes' table exists...")
        try:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                output_item_name TEXT PRIMARY KEY,
                station TEXT,          -- Crafting station used
                skill TEXT,            -- Tradeskill involved (e.g., Weaponsmithing)
                skill_level INTEGER,   -- Required skill level
                tier INTEGER,          -- Tier of the crafted item or recipe
                ingredients TEXT,      -- JSON string of direct ingredients (quantity, item_name)
                raw_recipe_data TEXT   -- JSON string of the complete recipe data for flexible use
            )
            """)
            conn.commit()
            print(f"Table 'recipes' created or already exists. It will be populated if a dedicated recipe data source is provided or remains available for other mechanisms.")
        except Exception as e:
            print(f"Error populating 'recipes' table: {e}")
    finally:
        conn.close()
        print(f"Database population finished.")

if __name__ == "__main__":
    populate_db()
    cleanup_items_csv()