"""
Store crafting recipes for New World items
"""

import requests
from bs4 import BeautifulSoup
import json
import logging
import sqlite3
import aiosqlite
from typing import Optional, Dict, Any, Set

# This import assumes the project root is in sys.path, allowing top-level modules
# to import from sub-packages. This is a common pattern in bot structures.
from commands.new_world.utils import resolve_item_name_for_lookup
from typing import Optional, Dict, Any, Set
from config import DB_NAME, TRACKED_RECIPES_FILE # Import DB_NAME and TRACKED_RECIPES_FILE

def slugify_recipe_name(name: str) -> str:
    # Basic slugify: lowercase, replace spaces and special chars
    return name.lower().replace(' ', '').replace("'", "").replace('-', '').replace('.', '').replace(',', '').replace('(', '').replace(')', '')


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


async def get_recipe(item_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a recipe for the given item_name.
    It first tries the 'recipes' table (from nwdb.info, more comprehensive),
    then falls back to the 'parsed_recipes' table (from legacy CSV).
    Returns a dictionary with recipe details, or None if not found.
    """
    resolved_item_name = resolve_item_name_for_lookup(item_name)
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.cursor()

            # 1. Try to fetch from the 'recipes' table (from nwdb.info)
            await cursor.execute("SELECT raw_recipe_data FROM recipes WHERE lower(output_item_name) = ?", (resolved_item_name.lower(),))
            recipe_row = await cursor.fetchone()
        # 1. Try to fetch from the 'recipes' table (from nwdb.info)
        logging.debug(f"Querying 'recipes' table for '{resolved_item_name.lower()}'. Found: {bool(recipe_row)}")
        if recipe_row:
            try:
                # The 'raw_recipe_data' column stores the full JSON object from nwdb.info
                recipe_data = json.loads(recipe_row["raw_recipe_data"])

                # --- NORMALIZATION ---
                # Standardize the ingredient list to use 'item' and 'quantity' keys
                normalized_ingredients = []
                for ing in recipe_data.get('ingredients', []):
                    # nwdb.info uses 'name' and 'quantity', ensure they are present
                    if 'name' in ing and 'quantity' in ing:
                        # Resolve ingredient names from nwdb.info recipes as well, just in case
                        # (though nwdb.info names are usually clean, this adds robustness)
                        resolved_ing_name = resolve_item_name_for_lookup(ing['name'])
                        normalized_ingredients.append({'item': resolved_ing_name, 'quantity': ing['quantity']})
                recipe_data['ingredients'] = normalized_ingredients
                # --- END NORMALIZATION ---

                # Ensure 'output_item_name' is present, using input item_name as fallback
                recipe_data.setdefault('output_item_name', resolved_item_name) # Use resolved name for output
                return recipe_data
            except (json.JSONDecodeError, KeyError) as e:
                logging.error(f"Failed to parse raw_recipe_data JSON for '{resolved_item_name}' from 'recipes' table: {e}")
                return None # Return None if JSON parsing fails

        # 2. If not found in 'recipes' table, try the 'parsed_recipes' table (from legacy CSV)
        await cursor.execute("SELECT Name, Ingredients FROM parsed_recipes WHERE lower(Name) = ?", (resolved_item_name.lower(),))
        legacy_recipe_row = await cursor.fetchone()
        logging.debug(f"Querying 'parsed_recipes' table for '{resolved_item_name.lower()}'. Found: {bool(legacy_recipe_row)}")
        if legacy_recipe_row:
            try:
                ingredients_list = json.loads(legacy_recipe_row["Ingredients"])

                # --- NORMALIZATION ---
                # Standardize the ingredient list to use 'item' and 'quantity' keys
                normalized_ingredients = []
                for ing in ingredients_list:
                    # Legacy CSV uses 'item' and 'qty', ensure they are present
                    if 'item' in ing and 'qty' in ing:
                        # Crucially, resolve ingredient names from legacy CSV
                        resolved_ing_name = resolve_item_name_for_lookup(ing['item'])
                        normalized_ingredients.append({'item': resolved_ing_name, 'quantity': ing['qty']})
                # --- END NORMALIZATION ---
                
                return {"output_item_name": resolved_item_name, "ingredients": normalized_ingredients}
            except (json.JSONDecodeError, KeyError) as e:
                logging.error(f"Failed to parse Ingredients JSON for '{resolved_item_name}' from 'parsed_recipes' table: {e}")
                return None # Return None if JSON parsing fails
        logging.info(f"No recipe found for '{resolved_item_name}' in any table.")
        return None
    except aiosqlite.Error as e:
        logging.error(f"Database error in get_recipe for '{resolved_item_name}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error in get_recipe for '{item_name}': {e}", exc_info=True)
        return None


async def _calculate_materials_recursive(
    item_name: str, 
    quantity_needed: int, 
    recipe_cache: Dict[str, Optional[Dict[str, Any]]], 
    processed_for_cycle_detection: Set[str],
    depth: int = 0,
    max_depth: int = 20,  # Set a reasonable max depth
    unique_materials: set = None,
    
    max_unique_materials: int = 100
) -> Dict[str, int]:
    if unique_materials is None:
        unique_materials = set()
    if depth > max_depth:
        logging.warning(f"Max recursion depth reached for item: {item_name}. Treating as base material.") # Keep original name for logging context
        return {resolve_item_name_for_lookup(item_name): quantity_needed}
    
    # Resolve the item name at the start of each recursive call
    resolved_item_name = resolve_item_name_for_lookup(item_name)

    if resolved_item_name in processed_for_cycle_detection:
        logging.warning(f"Crafting cycle detected for item: {resolved_item_name}. Treating as base material.")
        return {resolved_item_name: quantity_needed}
    if len(unique_materials) > max_unique_materials:
        logging.warning(f"Max unique materials reached. Stopping recursion.")
        return {resolved_item_name: quantity_needed}

    processed_for_cycle_detection.add(resolved_item_name)
    unique_materials.add(resolved_item_name)

    # Always use the resolved name for cache operations
    if resolved_item_name in recipe_cache:
        recipe = recipe_cache[resolved_item_name]
    else:
        # Call get_recipe with the resolved name
        recipe = await get_recipe(resolved_item_name)
        recipe_cache[resolved_item_name] = recipe

    base_materials: Dict[str, int] = {}

    # If no recipe, treat as base material
    if not recipe or not recipe.get("ingredients"):
        base_materials[resolved_item_name] = base_materials.get(resolved_item_name, 0) + quantity_needed
    else:
        for ingredient_info in recipe["ingredients"]:

            # The ingredient name from the recipe should already be resolved by our improved get_recipe,
            # so no further resolution is strictly needed here.
            sub_item_name = ingredient_info["item"] 
            sub_item_quantity_per_craft = ingredient_info["quantity"]
            sub_item_total_needed = sub_item_quantity_per_craft * quantity_needed

            sub_materials_for_ingredient = await _calculate_materials_recursive(
                sub_item_name, sub_item_total_needed, recipe_cache, processed_for_cycle_detection, depth + 1, max_depth, unique_materials, max_unique_materials
            )
            for mat, qty in sub_materials_for_ingredient.items():
                base_materials[mat] = base_materials.get(mat, 0) + qty

    processed_for_cycle_detection.remove(resolved_item_name)
    return base_materials

async def calculate_crafting_materials(item_name: str, quantity: int = 1, include_intermediate: bool = False) -> Optional[Dict[str, int]]:
    logging.info(f"Calculating crafting materials for '{item_name}', quantity={quantity}, include_intermediate={include_intermediate}")
    # Resolve the initial item name before any calculations
    resolved_initial_item_name = resolve_item_name_for_lookup(item_name)
    try:
        if not include_intermediate:
            # For non-intermediate calculation, we still need to resolve the item name
            recipe = await get_recipe(resolved_initial_item_name)
            if not recipe:
                logging.info(f"No direct recipe found for '{resolved_initial_item_name}' for non-intermediate calculation.")
                return None # Or {item_name: quantity} if it should be treated as a base material
            
            logging.debug(f"Recipe found for '{resolved_initial_item_name}': {recipe}")
            materials: Dict[str, int] = {}
            for ing in recipe.get("ingredients", []):
                # Ingredient names from recipe should already be resolved by get_recipe
                materials[ing["item"]] = materials.get(ing["item"], 0) + (ing["quantity"] * quantity)
            logging.debug(f"Calculated materials for '{resolved_initial_item_name}': {materials}")
            return materials
        else:
            recipe_cache: Dict[str, Optional[Dict[str, Any]]] = {}
            processed_for_cycle_detection: Set[str] = set()
            # Limit recursion depth and unique materials to prevent OOM/crash
            logging.debug(f"Calling recursive material calculation for '{resolved_initial_item_name}'")

            return await _calculate_materials_recursive(
                resolved_initial_item_name, quantity, recipe_cache, processed_for_cycle_detection,
                depth=0, max_depth=20, unique_materials=set(), max_unique_materials=100
            )
    except Exception as e:
        logging.error(f"Error in calculate_crafting_materials for '{item_name}': {e}", exc_info=True)
        return None