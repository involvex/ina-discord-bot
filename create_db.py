# create_db.py
import pandas as pd
import sqlite3
import os
import requests
from io import StringIO

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
    print(f"Populating database: {DB_NAME}")
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
    finally:
        conn.close()
        print(f"Database population finished.")

if __name__ == "__main__":
    populate_db()
