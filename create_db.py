# create_db.py
import pandas as pd
import sqlite3
import os
import requests
import time # Import time for sleep
from io import StringIO
import json  # For serializing ingredients
from config import DB_NAME, ITEMS_CSV_URL, PERKS_SCRAPED_CSV_URL  # Import DB_NAME, ITEMS_CSV_URL, and PERKS_SCRAPED_CSV_URL

ITEMS_CSV_PATH = "items.csv"
# The recipes table will be created, but populated by other means or remain available for future population.
# Define your CSV sources
CSV_SOURCES = {
    "items": ITEMS_CSV_URL, # Use the imported constant
    # "perks" will be handled specially from a local file perks_buddy.csv
    # "perks_legacy": "https://raw.githubusercontent.com/involvex/ina-discord-bot/main/perks_scraped.csv", # Kept for reference, but not used
}

def fetch_csv_data(url, retries=3, delay=5):
    print(f"Fetching CSV from {url}...")
    for i in range(retries):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()  # Raise an exception for HTTP errors
            # Save to disk for possible debugging, but will be deleted after DB population
            with open(ITEMS_CSV_PATH, "w", encoding="utf-8") as f:
                f.write(response.text)
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching CSV from {url}: {e}")
            if i < retries - 1:
                print(f"Retrying in {delay} seconds... (Attempt {i + 2}/{retries})")
                time.sleep(delay)
            else:
                print(f"Failed to fetch CSV from {url} after {retries} attempts.")
                return None
    return None # Should not be reached, but for clarity

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

        # --- Populate perks table from scraped data (primary source) ---
        df_perks_final = pd.DataFrame()  # This will be the final DataFrame for the 'perks' table

        print(f"Attempting to load perks data from scraped source: {PERKS_SCRAPED_CSV_URL}")
        scraped_perks_data = fetch_csv_data(PERKS_SCRAPED_CSV_URL)
        if scraped_perks_data:
            try:
                df_scraped_perks = pd.read_csv(StringIO(scraped_perks_data), low_memory=False)
                # Sanitize column names for DB
                df_scraped_perks.columns = [col.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'percent') for col in df_scraped_perks.columns]
                df_perks_final = df_scraped_perks.copy()
                print(f"Successfully loaded initial 'perks' data from {PERKS_SCRAPED_CSV_URL}.")
            except Exception as e:
                print(f"Error processing scraped perks data from {PERKS_SCRAPED_CSV_URL}: {e}")
        else:
            print(f"Warning: Could not fetch scraped perks data from {PERKS_SCRAPED_CSV_URL}. 'perks' table might be incomplete.")

        # --- Supplement/Override perks table from local perks_buddy.csv (secondary source) ---
        perks_buddy_csv_path = "perks_buddy.csv"
        print(f"Attempting to load and merge perks data from local file: {perks_buddy_csv_path}")
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
                    print(f"Using {perks_buddy_csv_path} as the primary source for perks (scraped data not available).")
                elif not df_perks_final.empty and not df_buddy_processed.empty:
                    # Merge buddy data into final DataFrame, prioritizing buddy data
                    df_perks_final = df_buddy_processed.set_index('id').combine_first(df_perks_final.set_index('id')).reset_index()
                    print(f"Successfully merged data from {perks_buddy_csv_path} into scraped perks data.")
                else:
                    print(f"Warning: {perks_buddy_csv_path} found, but no data to merge or primary data is missing.")
            except Exception as e:
                print(f"Error processing {perks_buddy_csv_path} for table 'perks': {e}")
        else:
            print(f"Warning: {perks_buddy_csv_path} not found. 'perks' table will not be populated from this source.")

        # Ensure all target DB columns exist in the final DataFrame, even if some sources were missing
        target_db_cols = ['id', 'name', 'description', 'PerkType', 'icon_url', 'ConditionText', 'CompatibleEquipment', 'ExclusiveLabels', 'ExclusiveLabel', 'CraftModItem', 'GeneratedLabel']
        for col in target_db_cols:
            if col not in df_perks_final.columns:
                df_perks_final[col] = None

        # Finally, write the combined DataFrame to SQL
        if not df_perks_final.empty:
            df_perks_final.to_sql("perks", conn, if_exists="replace", index=False)
            print(f"Successfully loaded combined data into 'perks' table.")
        else:
            print(f"Warning: No data available to populate 'perks' table.")

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