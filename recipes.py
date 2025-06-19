"""
Store crafting recipes for New World items
"""

import requests
from bs4 import BeautifulSoup
import json
import logging
import sqlite3
from typing import Optional, Dict, Any, Set
from config import DB_NAME, TRACKED_RECIPES_FILE # Import DB_NAME and TRACKED_RECIPES_FILE

logging.basicConfig(level=logging.INFO) # Ensure logging is configured


def slugify_recipe_name(name: str) -> str:
    # Basic slugify: lowercase, replace spaces and special chars
    return name.lower().replace(' ', '').replace("'", "").replace('-', '').replace('.', '').replace(',', '').replace('(', '').replace(')', '')


def _get_db_connection() -> sqlite3.Connection:
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Access columns by name
    return conn


def fetch_recipe_from_nwdb(item_name: str):
    slug = slugify_recipe_name(item_name)
    url = f'https://nwdb.info/db/recipe/{slug}'
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Find ingredients section (look for 'Ingredients' header)
        ingredients = []
        ing_section = soup.find('h2', string=lambda s: isinstance(s, str) and 'Ingredients' in s)
        if ing_section:
            ul = ing_section.find_next('ul')
            if ul:
                for li in ul.find_all('li'):
                    text = li.get_text(strip=True)
                    if 'x' in text:
                        qty, item = text.split('x', 1)
                        ingredients.append({'item': item.strip(), 'quantity': int(qty.strip())})
        # Find station, skill, tier, etc. (optional, can be improved)
        return {
            'station': '-',
            'skill': '-',
            'skill_level': '-',
            'tier': '-',
            'ingredients': ingredients
        }
    except Exception as e:
        print(f"Error fetching recipe from nwdb: {e}")
        return None


def track_recipe(user_id: str, item_name: str, recipe: dict):
    try:
        with open(TRACKED_RECIPES_FILE, 'r', encoding='utf-8') as f:
            tracked = json.load(f)
    except Exception:
        tracked = {}
    if user_id not in tracked:
        tracked[user_id] = []
    tracked[user_id].append({'item_name': item_name, 'recipe': recipe})
    with open(TRACKED_RECIPES_FILE, 'w', encoding='utf-8') as f:
        json.dump(tracked, f, indent=2)


def get_tracked_recipes(user_id: str):
    try:
        with open(TRACKED_RECIPES_FILE, 'r', encoding='utf-8') as f:
            tracked = json.load(f)
        return tracked.get(user_id, [])
    except Exception:
        return []


# RECIPES dictionary is no longer used directly by get_recipe; data comes from DB.
# It's used by create_db.py to populate the database.

def _get_item_name_from_id(item_id: str, conn: sqlite3.Connection) -> str:
    """Helper to get item name from item ID using the provided DB connection."""
    try:
        cursor = conn.cursor()
        # Column names are sanitized by create_db.py (e.g., 'Item ID' -> 'Item_ID').
        cursor.execute("SELECT Name FROM items WHERE Item_ID = ?", (item_id,))
        row = cursor.fetchone()
        if row:
            return row["Name"]
        else:
            logging.warning(f"Could not resolve item ID '{item_id}' to an item name.")
            return item_id # Fallback to ID if not found
    except sqlite3.Error as e:
        logging.error(f"SQLite error resolving item ID '{item_id}': {e}")
        return item_id


def get_recipe(item_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a recipe for the given item_name from the database.
    It first checks the 'recipes' table, then tries to derive from the 'items' table.
    """
    item_name_lower = item_name.lower()
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        # 1. Try to fetch from 'recipes' table (preferred source)
        cursor.execute("SELECT raw_recipe_data FROM recipes WHERE lower(output_item_name) = ?", (item_name_lower,))
        recipe_row = cursor.fetchone()
        if recipe_row and recipe_row["raw_recipe_data"]:
            try:
                recipe_data = json.loads(recipe_row["raw_recipe_data"])
                # Ensure 'ingredients' key exists, defaulting to an empty list
                recipe_data.setdefault('ingredients', [])
                # Ensure 'output_item_name' is present, using input item_name as fallback
                recipe_data.setdefault('output_item_name', item_name)
                return recipe_data
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse recipe JSON for '{item_name}' from 'recipes' table: {e}")

        # 2. If not in 'recipes' table, try to derive from 'items' table
        # Column names are sanitized by create_db.py (e.g., 'Crafting Recipe' -> 'Crafting_Recipe')
        cursor.execute("SELECT Name, Crafting_Recipe, Required_Tradeskill_Rank, Tier FROM items WHERE lower(Name) = ?", (item_name_lower,))
        item_row = cursor.fetchone()

        if item_row and item_row["Crafting_Recipe"]:
            crafting_recipe_str = item_row["Crafting_Recipe"]
            parsed_ingredients = []
            try:
                ingredient_pairs = crafting_recipe_str.split(',')
                for pair in ingredient_pairs:
                    if not pair.strip(): continue
                    parts = pair.split(':', 1) # Split only on the first colon
                    if len(parts) == 2:
                        item_id_for_ingredient = parts[0].strip()
                        quantity_str = parts[1].strip()
                        quantity = int(quantity_str)
                        ingredient_name = _get_item_name_from_id(item_id_for_ingredient, conn)
                        parsed_ingredients.append({'item': ingredient_name, 'quantity': quantity})
                    else:
                        logging.warning(f"Malformed ingredient pair '{pair}' in DB recipe string for '{item_name}': '{crafting_recipe_str}'")
            except ValueError as e:
                logging.error(f"Error parsing quantity for '{item_name}' from items table: '{crafting_recipe_str}'. Error: {e}")
            except Exception as e:
                logging.error(f"Unexpected error parsing recipe string for '{item_name}' from items table: '{crafting_recipe_str}'. Error: {e}", exc_info=True)

            return {
                'output_item_name': item_row["Name"], # Use the name from the items table
                'station': '-', # Not directly available in this context
                'skill': 'Unknown', # Not directly available
                'skill_level': item_row.get('Required_Tradeskill_Rank', '-'),
                'tier': item_row.get('Tier', '-'),
                'ingredients': parsed_ingredients
            }
        
        logging.info(f"No recipe found for '{item_name}' in 'recipes' or 'items' table.")
        return None
    except sqlite3.Error as e:
        logging.error(f"Database error in get_recipe for '{item_name}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error in get_recipe for '{item_name}': {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()


def _calculate_materials_recursive(
    item_name: str, 
    quantity_needed: int, 
    recipe_cache: Dict[str, Optional[Dict[str, Any]]], 
    processed_for_cycle_detection: Set[str],
    depth: int = 0,
    max_depth: int = 20  # Set a reasonable max depth
) -> Dict[str, int]:
    if depth > max_depth:
        logging.warning(f"Max recursion depth reached for item: {item_name}. Treating as base material.")
        return {item_name: quantity_needed}
    if item_name in processed_for_cycle_detection:
        logging.warning(f"Crafting cycle detected for item: {item_name}. Treating as base material.")
        return {item_name: quantity_needed}

    processed_for_cycle_detection.add(item_name)
    recipe = recipe_cache.get(item_name)
    if item_name not in recipe_cache:
        recipe = get_recipe(item_name)
        recipe_cache[item_name] = recipe

    base_materials: Dict[str, int] = {}

    if not recipe or not recipe.get("ingredients"):
        base_materials[item_name] = base_materials.get(item_name, 0) + quantity_needed
    else:
        for ingredient_info in recipe["ingredients"]:
            sub_item_name = ingredient_info["item"]
            sub_item_quantity_per_craft = ingredient_info["quantity"]
            sub_item_total_needed = sub_item_quantity_per_craft * quantity_needed

            sub_materials_for_ingredient = _calculate_materials_recursive(
                sub_item_name, sub_item_total_needed, recipe_cache, processed_for_cycle_detection, depth + 1, max_depth
            )
            for mat, qty in sub_materials_for_ingredient.items():
                base_materials[mat] = base_materials.get(mat, 0) + qty

    processed_for_cycle_detection.remove(item_name)
    return base_materials

def calculate_crafting_materials(item_name: str, quantity: int = 1, include_intermediate: bool = False) -> Optional[Dict[str, int]]:
    try:
        if not include_intermediate:
            recipe = get_recipe(item_name)
            if not recipe:
                logging.info(f"No direct recipe found for '{item_name}' for non-intermediate calculation.")
                return None # Or {item_name: quantity} if it should be treated as a base material
            
            materials: Dict[str, int] = {}
            for ing in recipe.get("ingredients", []):
                materials[ing["item"]] = materials.get(ing["item"], 0) + (ing["quantity"] * quantity)
            return materials
        else:
            recipe_cache: Dict[str, Optional[Dict[str, Any]]] = {}
            processed_for_cycle_detection: Set[str] = set()
            # Limit recursion depth to prevent OOM/crash
            return _calculate_materials_recursive(item_name, quantity, recipe_cache, processed_for_cycle_detection, depth=0, max_depth=20)
    except Exception as e:
        logging.error(f"Error in calculate_crafting_materials for '{item_name}': {e}", exc_info=True)
        return None