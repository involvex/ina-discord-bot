"""
Store crafting recipes for New World items
"""

import requests
from bs4 import BeautifulSoup
import json

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

# Add aliases after RECIPES is fully defined
RECIPES["gorgon's amulet"] = RECIPES["gorgonite amulet"]

def get_recipe(item_name: str, global_item_data: dict):
    # Try local recipes first
    recipe = RECIPES.get(item_name.lower())
    if recipe:
        return recipe
    # Try to get from items.csv if it has a recipe
    # Use the globally loaded item_data passed as an argument
    if global_item_data and item_name.lower() in global_item_data:
        row = global_item_data[item_name.lower()]
        # Try to extract recipe info if present
        if 'Crafting Recipe' in row and row['Crafting Recipe']:
            # This is a placeholder: you may need to parse the recipe string or link to a recipe id
            return {
                'station': row.get('Station', '-'),
                'skill': row.get('Required Tradeskill Rank', '-'),
                'skill_level': row.get('Required Tradeskill Rank', '-'),
                'tier': row.get('Tier', '-'),
                'ingredients': []  # Could be parsed if format is known
            }
    return None


def calculate_crafting_materials(item_name: str, global_item_data: dict, quantity: int = 1, include_intermediate: bool = False):
    recipe = get_recipe(item_name, global_item_data)
    if not recipe:
        return None
    materials = {}
    for ing in recipe["ingredients"]:
        materials[ing["item"]] = ing["quantity"] * quantity
    return materials