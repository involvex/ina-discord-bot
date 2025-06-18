import requests
from bs4 import BeautifulSoup
import csv
import time
import re

BASE_URL = "https://nwdb.info"
OUTPUT_CSV_FILE = 'perks_scraped.csv'
INITIAL_MAX_PAGES_TO_SCRAPE = 25 # Initial upper limit, will be replaced by actual page count

def sanitize_json_description(description_text):
    """
    Cleans up the description text from JSON, replaces placeholders,
    and adds the (Note: Actual values may scale with Gear Score.) if applicable.
    """
    if not description_text:
        return "No description available."

    # Replace placeholders like ${value} with value
    description_text = re.sub(r'\$\{\s*(\d+(\.\d+)?)\s*\}', r'\1', description_text)

    # Replace multiple spaces/newlines with a single space or newline
    description_text = re.sub(r'\s*\n\s*', '\n', description_text)
    description_text = re.sub(r' +', ' ', description_text)
    # Add the gear score scaling note if numbers are present and it's not already there
    # This is a heuristic, might need refinement for specific perk descriptions
    if re.search(r'\d+(\.\d+)?%', description_text) and "scale with gear score" not in description_text.lower():
        if not description_text.endswith("."):
            description_text += "."
        description_text += " (Note: Actual values may scale with Gear Score.)"
        
    return description_text.strip()

def scrape_nwdb_perks():
    """
    Scrapes perk data from nwdb.info and saves it to a CSV file.
    """
    all_perks_data = []
    processed_perk_ids = set() # To avoid duplicates if a perk appears on multiple pages (unlikely but good practice)
    actual_page_count = INITIAL_MAX_PAGES_TO_SCRAPE

    print(f"Starting perk scraping from {BASE_URL}...")

    for page_num in range(1, actual_page_count + 1):
        current_url = f"{BASE_URL}/db/perks/page/{page_num}.json" # Fetch JSON endpoint
        print(f"Scraping page: {current_url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            response = requests.get(current_url, headers=headers, timeout=15)
            response.raise_for_status() 
            json_data = response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error fetching page {current_url}: {e}")
            break 
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {current_url}: {e}")
            break
        except requests.exceptions.JSONDecodeError:
            print(f"Error decoding JSON from {current_url}. Content was: {response.text[:200]}...")
            # Save problematic content for debugging
            debug_html_filename = f"debug_page_{page_num}_non_json_content.html"
            try:
                with open(debug_html_filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"Content of page {page_num} saved to {debug_html_filename} for inspection.")
            except Exception as e_write:
                print(f"Could not write debug HTML file: {e_write}")
            break

        if not json_data.get('success') or not json_data.get('data'):
            print(f"JSON response for page {page_num} indicates failure or no data.")
            break

        if page_num == 1 and json_data.get('pageCount'):
            actual_page_count = json_data['pageCount']
            print(f"Total pages to scrape: {actual_page_count}")

        page_had_new_perks = False
        for perk_entry in json_data['data']:
            try:
                perk_id = perk_entry.get('id')
                perk_name = perk_entry.get('name')

                if not perk_id or not perk_name:
                    print(f"Skipping entry with missing ID or Name: {perk_entry}")
                    continue

                if perk_id in processed_perk_ids:
                    continue # Skip if already processed
                processed_perk_ids.add(perk_id)
                page_had_new_perks = True

                perk_description = sanitize_json_description(perk_entry.get('description'))
                
                icon_path = perk_entry.get('icon')
                # Construct full icon URL: https://nwdb.info/images/ + icon_path + .png
                icon_url = f"{BASE_URL}/images/{icon_path}.png" if icon_path else ""

                # Perk Type - this is not directly in the list JSON, so we make a guess or use a placeholder
                perk_type = "Unknown Perk Type"
                if perk_entry.get("perkMod") and isinstance(perk_entry["perkMod"], dict):
                    item_type = perk_entry["perkMod"].get("itemType", "").lower()
                    mod_name = perk_entry["perkMod"].get("name", "").lower()
                    if "gem" in item_type or "cut" in mod_name or "gem" in mod_name:
                        perk_type = "Gem Perk"
                elif "weapon" in perk_name.lower() or any(wp_type in perk_id.lower() for wp_type in ["sword", "axe", "hammer", "bow", "musket", "staff", "gauntlet", "hatchet", "spear", "rapier", "blunderbuss", "flail"]):
                    perk_type = "Weapon Perk"
                elif "armor" in perk_name.lower() or any(arm_type in perk_id.lower() for arm_type in ["ward", "resilient", "freedom", "refreshing"]):
                     perk_type = "Armor Perk"
                elif "luck" in perk_id.lower() or "gathering" in perk_id.lower():
                    perk_type = "Gathering Perk"

                all_perks_data.append({
                    'id': perk_id,
                    'name': perk_name,
                    'description': perk_description,
                    'type': perk_type,
                    'icon_url': icon_url
                })

            except Exception as e:
                print(f"Error processing a perk entry on page {page_num}: {e}. Entry: {perk_entry}")
                continue
        
        if not page_had_new_perks and page_num > 1:
            print(f"No new perks found on page {page_num}. Stopping.")
            break

        # Be respectful to the server
        time.sleep(1) # Wait 1 second between page requests

    if not all_perks_data:
        print("No perk data was scraped.")
        return

    # Write to CSV
    print(f"\nScraped {len(all_perks_data)} perks. Writing to {OUTPUT_CSV_FILE}...")
    try:
        with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['id', 'name', 'description', 'type', 'icon_url']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for perk_data in all_perks_data:
                writer.writerow(perk_data)
        print(f"Successfully wrote perks to {OUTPUT_CSV_FILE}")
    except IOError as e:
        print(f"Error writing CSV file: {e}")

if __name__ == '__main__':
    scrape_nwdb_perks()
