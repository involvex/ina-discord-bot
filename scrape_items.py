import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import json
import logging

BASE_URL = "https://nwdb.info" # Keep this
OUTPUT_CSV_FILE = 'items_scraped.csv' # Output for create_db.py
OUTPUT_JSON_FILE = 'items_updated.json' # Output for commands/new_world/utils.py cache
INITIAL_MAX_PAGES_TO_SCRAPE = 70 # Initial upper limit, will be replaced by actual page count

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def sanitize_html_description(description_text):
    """
    Cleans up HTML description text.
    """
    if not description_text:
        return "No description available."
    # Replace <br> with newlines, then strip other HTML tags
    description_text = description_text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    description_text = re.sub(r'<[^>]+>', '', description_text) # Strip all other HTML tags
    # Replace multiple spaces/newlines
    description_text = re.sub(r'[ \t]+', ' ', description_text)
    description_text = re.sub(r'\s*\n\s*', '\n', description_text).strip()
    return description_text.strip()

def scrape_nwdb_items():
    """
    Scrapes item data from nwdb.info JSON endpoint and saves it to a CSV file.
    """
    all_items_data = []
    processed_item_ids = set()
    actual_page_count = INITIAL_MAX_PAGES_TO_SCRAPE

    logging.info(f"Starting item scraping from {BASE_URL}...")

    for page_num in range(1, actual_page_count + 1):
        current_url = f"{BASE_URL}/db/items/page/{page_num}.json"
        logging.info(f"Scraping page: {current_url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        retries = 3
        for attempt in range(retries):
            try:
                response = requests.get(current_url, headers=headers, timeout=20)
                response.raise_for_status()
                json_data = response.json()
                break # Success, break from retry loop
            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching page {current_url} (Attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2) # Wait before retrying
                else:
                    logging.error(f"Failed to fetch page {current_url} after {retries} attempts. Skipping.")
                    json_data = None # Indicate failure
                    break
            except requests.exceptions.JSONDecodeError:
                logging.error(f"Error decoding JSON from {current_url} (Attempt {attempt + 1}/{retries}). Content: {response.text[:200]}")
                json_data = None # Indicate failure
                break

        if json_data is None or not json_data.get('success') or not json_data.get('data'):
            logging.warning(f"Skipping page {page_num} due to fetch/parse failure or no data.")
            break # Stop if a page fails completely

        if page_num == 1 and json_data.get('pageCount'):
            actual_page_count = json_data['pageCount']
            logging.info(f"Total item pages to scrape: {actual_page_count}")

        page_had_new_items = False
        for item_entry in json_data['data']:
            try:
                item_id = item_entry.get('id')
                item_name = item_entry.get('name')

                if not item_id or not item_name:
                    logging.warning(f"Skipping entry with missing ID or Name: {item_entry}")
                    continue

                if item_id in processed_item_ids:
                    continue
                processed_item_ids.add(item_id)
                page_had_new_items = True

                perks_list = item_entry.get('perks', [])
                # Ensure perks_list contains only strings (perk IDs)
                processed_perks = []
                for perk_item in perks_list:
                    if isinstance(perk_item, dict) and 'id' in perk_item:
                        processed_perks.append(perk_item['id'])
                    elif isinstance(perk_item, str): # Handle cases where it might already be a string
                        processed_perks.append(perk_item)
                    else:
                        logging.warning(f"Unexpected perk format for item {item_name} ({item_id}): {perk_item}")
                description = sanitize_html_description(item_entry.get('description', ''))
                icon_path = item_entry.get('icon')
                icon_url = f"{BASE_URL}/images/{icon_path}.png" if icon_path else ""
                
                # Extracting various fields available in the item JSON
                item_data = {
                    'Item ID': item_id,
                    'Name': item_name,
                    'Description': description,
                    'Icon Path': icon_path, # Storing path for potential local use or reconstruction
                    'Icon URL': icon_url,
                    'Rarity': item_entry.get('rarity'),
                    'Tier': item_entry.get('tier'),
                    'Item Type Name': item_entry.get('typeName'), # e.g., "1H Sword", "Light Headwear"
                    'Item Class': "|".join(item_entry.get('itemClass', [])), # e.g. ["EquippableHead", "Armor", "Light"] -> "EquippableHead|Armor|Light"
                    'Weight': item_entry.get('weight'),
                    'Max Stack Size': item_entry.get('maxStackSize'),
                    'Gear Score': item_entry.get('gearScore'), # This might be a single value or null
                    'MinGS': item_entry.get('minGs'),
                    'MaxGS': item_entry.get('maxGs'),
                    'Perks': "|".join(processed_perks), # Use the processed list
                    'PerkBuckets': "|".join(item_entry.get('perkBuckets', [])), # List of perk bucket IDs
                    'Ingredient Categories': item_entry.get('ingredientCategories'), # Often a string like "secondaryitemcategory_cloth|tier1"
                    'Crafting Recipe': item_entry.get('craftingRecipe'), # ID of the recipe if craftable
                    'Armor Rating Scale Factor': item_entry.get('armorRatingScaleFactor'),
                    'Weapon Dmg Scale Factor': item_entry.get('weaponDmgScaleFactor')
                }
                all_items_data.append(item_data)

            except Exception as e:
                logging.error(f"Error processing an item entry on page {page_num}: {e}. Entry: {item_entry}", exc_info=True)
                continue
        
        if not page_had_new_items and page_num > 1: # Check if any new items were added from this page
            logging.info(f"No new items found on page {page_num}. Stopping.")
            break
        time.sleep(0.5) # Be respectful

    if not all_items_data:
        logging.warning("No item data was scraped.")
        return

    logging.info(f"Scraped {len(all_items_data)} items. Writing to {OUTPUT_CSV_FILE}...")
    
    # Write to CSV for create_db.py
    try:
        with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = list(all_items_data[0].keys()) # Get fieldnames from the first item
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_items_data)
        logging.info(f"Successfully wrote items to CSV: {OUTPUT_CSV_FILE}")
    except Exception as e:
        logging.error(f"Error writing CSV file {OUTPUT_CSV_FILE}: {e}")

    # Write to JSON for commands/new_world/utils.py cache
    try:
        with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_items_data, f, indent=2)
        logging.info(f"Successfully wrote items to JSON: {OUTPUT_JSON_FILE}")
    except Exception as e:
        logging.error(f"Error writing JSON file {OUTPUT_JSON_FILE}: {e}")

if __name__ == '__main__':
    scrape_nwdb_items()