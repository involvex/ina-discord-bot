"""
Store crafting recipes for New World items
"""

import requests
from bs4 import BeautifulSoup
import json
import logging

TRACKED_RECIPES_FILE = 'tracked_recipes.json'


def slugify_recipe_name(name: str) -> str:
    # Basic slugify: lowercase, replace spaces and special chars
    return name.lower().replace(' ', '').replace("'", "").replace('-', '').replace('.', '').replace(',', '').replace('(', '').replace(')', '')


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


RECIPES = {
    "iron ingot": {
        "station": "Smelter",
        "skill": "Smelting",
        "skill_level": 0,
        "tier": 2,
        "ingredients": [
            {"item": "Iron Ore", "quantity": 4}
        ]
    },
    "gorgonite amulet": {
        "station": "Outfitting Station",
        "skill": "Jewelcrafting",
        "skill_level": 250,
        "tier": 5,
        "ingredients": [
            {"item": "Gorgon's Eye", "quantity": 1},
            {"item": "Prismatic Chain", "quantity": 1},
            {"item": "Prismatic Setting", "quantity": 1},
            {"item": "Prismatic Ingot", "quantity": 6},
        ]
    },
    # ... other recipes ...
}


def get_recipe(item_name: str, global_item_data: dict, item_id_to_name_map: dict):
    # Try local recipes first
    item_name_lower = item_name.lower()
    if item_name_lower in RECIPES:
        return RECIPES[item_name_lower]

    # Try to get from items.csv if it has a recipe
    if global_item_data and item_name_lower in global_item_data:
        row = global_item_data[item_name_lower]
        crafting_recipe_str = row.get('Crafting Recipe')

        if crafting_recipe_str:
            parsed_ingredients = []
            try:
                ingredient_pairs = crafting_recipe_str.split(',')
                for pair in ingredient_pairs:
                    if not pair.strip(): # Skip empty parts if any (e.g., trailing comma)
                        continue
                    parts = pair.split(':')
                    if len(parts) == 2:
                        item_id_for_ingredient = parts[0].strip()
                        quantity_str = parts[1].strip()
                        quantity = int(quantity_str)

                        # Resolve item_id_for_ingredient to actual name using item_id_to_name_map
                        ingredient_name = item_id_to_name_map.get(item_id_for_ingredient, item_id_for_ingredient)
                        parsed_ingredients.append({'item': ingredient_name, 'quantity': quantity})
                    else:
                        logging.warning(f"Malformed ingredient pair '{pair}' in recipe string for '{item_name}': '{crafting_recipe_str}'")
            except ValueError as e:
                logging.error(f"Error parsing quantity in recipe string for '{item_name}': '{crafting_recipe_str}'. Error: {e}")
                # Decide if you want to return partial recipe or None
            except Exception as e:
                logging.error(f"Unexpected error parsing recipe string for '{item_name}': '{crafting_recipe_str}'. Error: {e}")

            # Station and Skill Name are not directly available in items.csv for the item itself.
            # Required Tradeskill Rank is the skill level.
            return {
                'station': '-', # Not directly available in item's row in items.csv
                'skill': 'Unknown', # Skill name not directly available in item's row
                'skill_level': row.get('Required Tradeskill Rank', '-'),
                'tier': row.get('Tier', '-'),
                'ingredients': parsed_ingredients
            }
    return None


def calculate_crafting_materials(item_name: str, global_item_data: dict, item_id_to_name_map: dict, quantity: int = 1, include_intermediate: bool = False):
    # Note: This function currently only calculates direct materials.
    # A full recursive calculation for `include_intermediate=True` is more complex.
    recipe = get_recipe(item_name, global_item_data, item_id_to_name_map)
    if not recipe:
        return None
    materials = {}
    for ing in recipe.get("ingredients", []):
        materials[ing["item"]] = materials.get(ing["item"], 0) + (ing["quantity"] * quantity)
    return materials