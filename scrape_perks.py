import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import logging # Added for better logging

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

    # Replace multiple spaces/newlines with a single space or newline, but preserve intentional newlines from <br>
    description_text = description_text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    description_text = re.sub(r'[ \t]+', ' ', description_text) # Replace multiple spaces/tabs with single space
    description_text = re.sub(r'\s*\n\s*', '\n', description_text).strip() # Clean up newlines
    # This is a heuristic, might need refinement for specific perk descriptions
    if re.search(r'\d+(\.\d+)?%', description_text) and "scale with gear score" not in description_text.lower():
        if not description_text.endswith("."):
            description_text += "."
        description_text += " (Note: Actual values may scale with Gear Score.)"
        
    return description_text.strip()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def scrape_nwdb_perks():
    """
    Scrapes perk data from nwdb.info and saves it to a CSV file.
    """
    all_perks_data = []
    processed_perk_ids = set() # To avoid duplicates if a perk appears on multiple pages (unlikely but good practice)
    actual_page_count = INITIAL_MAX_PAGES_TO_SCRAPE

    logging.info(f"Starting perk scraping from {BASE_URL}...")

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
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error fetching page {current_url}: {http_err}")
            break 
        except requests.exceptions.RequestException as req_err:
            logging.error(f"Error fetching page {current_url}: {req_err}")
            break
        except requests.exceptions.JSONDecodeError as json_err:
            logging.error(f"Error decoding JSON from {current_url}. Content was: {response.text[:200]}... Error: {json_err}")
            # Save problematic content for debugging
            debug_html_filename = f"debug_page_{page_num}_non_json_content.html"
            try:
                with open(debug_html_filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"Content of page {page_num} saved to {debug_html_filename} for inspection.")
            except Exception as e_write:
                logging.error(f"Could not write debug HTML file: {e_write}")
            break

        if not json_data.get('success') or not json_data.get('data'):
            logging.warning(f"JSON response for page {page_num} indicates failure or no data.")
            break

        if page_num == 1 and json_data.get('pageCount'):
            actual_page_count = json_data['pageCount']
            logging.info(f"Total pages to scrape: {actual_page_count}")

        page_had_new_perks = False
        for perk_entry in json_data['data']:
            try:
                perk_id = perk_entry.get('id')
                perk_name = perk_entry.get('name')

                if not perk_id or not perk_name:
                    logging.warning(f"Skipping entry with missing ID or Name: {perk_entry}")
                    continue

                if perk_id in processed_perk_ids:
                    continue # Skip if already processed
                processed_perk_ids.add(perk_id)
                page_had_new_perks = True

                # Use 'searchGSFormulaReadable' if available and contains placeholders, otherwise 'description'
                # The 'searchGSFormulaReadable' often has the GS 700 scaled values, but we want the formula for our bot to scale
                # The raw 'description' field usually has the ${...perkMultiplier} placeholders.
                raw_description = perk_entry.get('description', "No description available.")
                perk_description = sanitize_json_description(raw_description)
                
                icon_path = perk_entry.get('icon')
                # Construct full icon URL: https://nwdb.info/images/ + icon_path + .png
                icon_url = f"{BASE_URL}/images/{icon_path}.png" if icon_path else ""

                # Extract new fields
                actual_perk_type = perk_entry.get('perkType') # More reliable type
                condition_text = perk_entry.get('condition')
                
                compatible_equipment_list = perk_entry.get('itemClass', [])
                compatible_equipment = ", ".join(compatible_equipment_list) if compatible_equipment_list else None
                
                exclusive_labels_list_json = perk_entry.get('exclusiveLabels', [])
                exclusive_labels = ", ".join(exclusive_labels_list_json) if exclusive_labels_list_json else None
                
                exclusive_label_single = perk_entry.get('exclusiveLabel')
                
                craft_mod_data = perk_entry.get('craftMod')
                craft_mod_item_name = craft_mod_data.get('name') if craft_mod_data else None
                
                generated_item_label = perk_entry.get('generatedLabel')

                all_perks_data.append({
                    'id': perk_id,
                    'name': perk_name,
                    'description': perk_description,
                    'PerkType': actual_perk_type, # Use the new column name
                    'icon_url': icon_url,
                    'ConditionText': condition_text,
                    'CompatibleEquipment': compatible_equipment,
                    'ExclusiveLabels': exclusive_labels,
                    'ExclusiveLabel': exclusive_label_single,
                    'CraftModItem': craft_mod_item_name,
                    'GeneratedLabel': generated_item_label
                })

            except Exception as e:
                logging.error(f"Error processing a perk entry on page {page_num}: {e}. Entry: {perk_entry}", exc_info=True)
                continue
        
        if not page_had_new_perks and page_num > 1:
            logging.info(f"No new perks found on page {page_num}. Stopping.")
            break

        # Be respectful to the server
        time.sleep(1) # Wait 1 second between page requests

    if not all_perks_data:
        print("No perk data was scraped.")
        logging.warning("No perk data was scraped.")
        return

    # Write to CSV
    logging.info(f"\nScraped {len(all_perks_data)} perks. Writing to {OUTPUT_CSV_FILE}...")
    try:
        with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            # Define fieldnames based on the keys in the dictionaries being written
            # Ensure all keys used in all_perks_data.append are listed here
            fieldnames = [
                'id', 'name', 'description', 'PerkType', 'icon_url', 
                'ConditionText', 'CompatibleEquipment', 'ExclusiveLabels', 
                'ExclusiveLabel', 'CraftModItem', 'GeneratedLabel'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for perk_data in all_perks_data:
                writer.writerow(perk_data)
        logging.info(f"Successfully wrote perks to {OUTPUT_CSV_FILE}")
    except IOError as e:
        logging.error(f"Error writing CSV file: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during CSV writing: {e}", exc_info=True)

if __name__ == '__main__':
    scrape_nwdb_perks()
