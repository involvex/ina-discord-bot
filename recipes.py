"""
Store crafting recipes for New World items
"""

import requests
from bs4 import BeautifulSoup
import json
import logging
import sqlite3
import aiosqlite # Using aiosqlite for async DB operations
from typing import Optional, Dict, Any, Set

# This import assumes the project root is in sys.path, allowing top-level modules
# to import from sub-packages. This is a common pattern in bot structures.
from commands.new_world.utils import resolve_item_name_for_lookup
from typing import Optional, Dict, Any, Set
from typing import Optional, Dict, Any, Set, List
from config import DB_NAME, TRACKED_RECIPES_FILE

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

async def get_all_recipe_names() -> List[str]:
    """
    Fetches all unique recipe output names from both 'recipes' and 'parsed_recipes' tables.
    """
    recipe_names = set()
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.cursor() as cursor:
                # Get names from 'recipes' table
                await cursor.execute("SELECT DISTINCT output_item_name FROM recipes")
                for row in await cursor.fetchall():
                    if row['output_item_name']:
                        recipe_names.add(row['output_item_name'])
                
                # Get names from 'parsed_recipes' table
                await cursor.execute("SELECT DISTINCT Name FROM parsed_recipes")
                for row in await cursor.fetchall():
                    if row['Name']:
                        recipe_names.add(row['Name'])
        
    except aiosqlite.Error as e:
        logging.error(f"Database error in get_all_recipe_names: {e}")
    except Exception as e:
        logging.error(f"Unexpected error in get_all_recipe_names: {e}", exc_info=True)
    
    return sorted(list(recipe_names))


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
            conn.row_factory = aiosqlite.Row  # Set row_factory on the connection
            async with conn.cursor() as cursor:  # Use async with for cursor as well.
                # All operations that use 'cursor' should be within this 'async with cursor' block.

                # 1. Try to fetch from the 'recipes' table (from nwdb.info)
                await cursor.execute("SELECT raw_recipe_data FROM recipes WHERE lower(output_item_name) = ?", (resolved_item_name.lower(),))
                recipe_row = await cursor.fetchone()

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
                        recipe_data.setdefault('output_item_name', resolved_item_name)  # Use resolved name for output
                        return recipe_data
                    except (json.JSONDecodeError, KeyError) as e:
                        logging.error(f"Failed to parse raw_recipe_data JSON for '{resolved_item_name}' from 'recipes' table: {e}", exc_info=True)
                        return None  # Return None if JSON parsing fails

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
                        logging.error(f"Failed to parse Ingredients JSON for '{resolved_item_name}' from 'parsed_recipes' table: {e}", exc_info=True)
                        logging.debug(f"Raw Ingredients data that failed to parse: {legacy_recipe_row.get('Ingredients')}")
                        return None  # Return None if JSON parsing fails
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
            if not recipe or not recipe.get("ingredients"): # If no recipe or no ingredients, treat as base material
                logging.info(f"No direct recipe found or no ingredients for '{resolved_initial_item_name}' for non-intermediate calculation. Treating as base material.")
                return {resolved_initial_item_name: quantity}
            
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

# --- Discord Bot Commands (NewWorldCrafting Extension) ---
from interactions import Extension, slash_command, slash_option, OptionType, SlashContext, Embed, EmbedField, AutocompleteContext

class NewWorldCrafting(Extension):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="recipe", description="Shows the crafting recipe for an item.")
    @slash_option(
        name="item_name",
        description="The name of the item to look up.",
        opt_type=OptionType.STRING,
        required=True,
        autocomplete=True # Enable autocomplete for this option
    )
    async def recipe(self, ctx: SlashContext, item_name: str):
        await ctx.defer() # Defer the response as lookup might take time

        recipe_data = await get_recipe(item_name)

        if not recipe_data:
            await ctx.send(f"Sorry, I couldn't find a recipe for '{item_name}'. Please check the spelling or try a different item. (e.g., 'Iron Ingot' instead of 'Iron')")
            return

        embed = Embed(
            title=f"Crafting Recipe for {recipe_data.get('output_item_name', item_name)}",
            color=0x00ff00 # Green color
        )

        # Safely get ingredients. get_recipe should return a list, but add a check for robustness.
        ingredients = recipe_data.get('ingredients', [])
        
        # Ensure ingredients is a list (it should be from get_recipe's json.loads)
        # This check is primarily for robustness against malformed data, as get_recipe should return a list
        if isinstance(ingredients, str):
            try:
                ingredients = json.loads(ingredients)
            except json.JSONDecodeError:
                logging.error(f"Failed to decode ingredients JSON for {item_name}: {ingredients}")
                ingredients = [] # Fallback to empty list on decode error

        # Format ingredients for display, providing a fallback string if empty
        if ingredients:
            ingredients_str = "\n".join([f"{ing.get('quantity', 1)}x {ing.get('item', 'Unknown Item')}" for ing in ingredients])
        else:
            ingredients_str = "No ingredients required."

        embed.add_field(name="Ingredients", value=ingredients_str, inline=False)

        # Add other fields, ensuring they also have non-empty fallback values
        # Assuming 'station', 'skill', 'skill_level', 'tier' are also present in recipe_data
        embed.add_field(name="Crafting Station", value=recipe_data.get('station', 'Not specified'), inline=True)
        
        skill_info = []
        if recipe_data.get('skill'):
            skill_info.append(recipe_data['skill'])
        if recipe_data.get('skill_level'):
            skill_info.append(f"(Level {recipe_data['skill_level']})")
        embed.add_field(name="Skill Required", value=" ".join(skill_info) or "Not specified", inline=True)

        embed.add_field(name="Tier", value=str(recipe_data.get('tier', 'Not specified')), inline=True)

        await ctx.send(embeds=embed)

    @slash_command(name="calculate_craft", description="Calculate all base materials needed for an item.")
    @slash_option(
        name="item_name",
        description="The name of the item to calculate materials for.",
        opt_type=OptionType.STRING,
        required=True,
        autocomplete=True
    )
    @slash_option(
        name="amount",
        description="The amount you want to craft.",
        opt_type=OptionType.INTEGER,
        required=False
    )
    async def calculate_craft(self, ctx: SlashContext, item_name: str, amount: int = 1):
        await ctx.defer()

        materials = await calculate_crafting_materials(item_name, amount, include_intermediate=True)

        if not materials:
            await ctx.send(f"Could not calculate materials for '{item_name}'. It might not be a craftable item or an error occurred.", ephemeral=True)
            return

        embed = Embed(
            title=f"Base Materials for {amount}x {item_name}",
            color=0x3498DB # Blue color
        )

        description_lines = []
        for material, quantity in sorted(materials.items()):
            description_lines.append(f"• **{quantity}x** {material}")

        if description_lines:
            embed.description = "\n".join(description_lines)
        else:
            embed.description = "No base materials required or found."

        await ctx.send(embeds=embed)

    @recipe.autocomplete("item_name")
    async def recipe_autocomplete(self, ctx: AutocompleteContext):
        """
        Provides autocomplete suggestions for the item_name option in the /recipe command.
        """
        search_term = ctx.input_text.lower()
        
        # Fetch all unique recipe names from the database
        all_recipe_names = await get_all_recipe_names() 

        choices = []
        for name in all_recipe_names:
            if search_term in name.lower():
                choices.append({"name": name, "value": name})
            if len(choices) >= 25: # Discord API limit for autocomplete choices
                break
        
        await ctx.send(choices=choices)

    # Reuse the same autocomplete logic for the new command
    @calculate_craft.autocomplete("item_name")
    async def calculate_craft_autocomplete(self, ctx: AutocompleteContext):
        return await self.recipe_autocomplete(ctx)

def setup(bot):
    NewWorldCrafting(bot)