# create_db.py
import pandas as pd
import sqlite3
import os
import requests
from io import StringIO
import json # For serializing ingredients

# Attempt to import RECIPES from your recipes module
from recipes import RECIPES # Assuming RECIPES is a dict in recipes.py

DB_NAME = "new_world_data.db"
# Define your CSV sources
CSV_SOURCES = {
    "items": "https://raw.githubusercontent.com/involvex/ina-discord-bot-/main/items.csv",
    "perks": "https://raw.githubusercontent.com/involvex/ina-discord-bot-/main/perks.csv", # Assuming a similar URL for perks
    # Add other CSVs if needed
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

def populate_db():
    conn = sqlite3.connect(DB_NAME)
    print(f"Connecting to and populating database: {DB_NAME}")
    try:
        for table_name, csv_url in CSV_SOURCES.items():
            csv_data = fetch_csv_data(csv_url)
            if csv_data:
                try:
                    # Use StringIO to read the CSV string data into pandas
                    df = pd.read_csv(StringIO(csv_data))
                    # Ensure column names are SQL-friendly (e.g., replace spaces with underscores)
                    df.columns = [col.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'percent') for col in df.columns]
                    df.to_sql(table_name, conn, if_exists="replace", index=False)
                    print(f"Successfully loaded data into '{table_name}' table.")
                except pd.errors.EmptyDataError:
                    print(f"Warning: CSV from {csv_url} for table '{table_name}' is empty or invalid.")
                except Exception as e:
                    print(f"Error processing CSV for table '{table_name}': {e}")

        # Populate recipes table from the RECIPES dictionary
        print("Populating 'recipes' table...")
        cursor = conn.cursor()
        try:
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
            for recipe_name_key, recipe_data in RECIPES.items():
                # Ensure ingredients are stored as a JSON string
                ingredients_json = json.dumps(recipe_data.get("ingredients", []))
                raw_data_json = json.dumps(recipe_data) # Store the whole recipe for flexibility
                cursor.execute("INSERT OR REPLACE INTO recipes (output_item_name, station, skill, skill_level, tier, ingredients, raw_recipe_data) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (recipe_data.get("output_item_name", recipe_name_key), recipe_data.get("station"), recipe_data.get("skill"), recipe_data.get("skill_level"), recipe_data.get("tier"), ingredients_json, raw_data_json))
            conn.commit()
            print(f"Successfully loaded {len(RECIPES)} recipes into 'recipes' table.")
        except Exception as e:
            print(f"Error populating 'recipes' table: {e}")
    finally:
        conn.close()
        print(f"Database population finished.")

if __name__ == "__main__":
    populate_db()
