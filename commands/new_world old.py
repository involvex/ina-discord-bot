import json
import logging
from typing import Optional

from interactions import (
    Extension,
    slash_command,
    slash_option,
    OptionType,
    AutocompleteContext,
    Embed,
    SlashContext,
)

from db_utils import find_item_in_db, get_db_connection
import sqlite3 # Added for nwdb_autocomplete
from recipes import get_recipe, calculate_crafting_materials, track_recipe
from bot_client import bot

class NewWorldCommands(Extension):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="recipe", description="Show the full recipe breakdown for a craftable item and track it.", dm_permission=False)
    @slash_option("item_name", "The name of the item to show the recipe for", opt_type=OptionType.STRING, required=True, autocomplete=True)
    async def recipe(self, ctx: SlashContext, item_name: str):
        await ctx.defer()

        recipe_dict = None
        try:
            recipe_dict = get_recipe(item_name)
        except Exception as e:
            logging.error(f"Unexpected error in /recipe calling get_recipe for '{item_name}': {e}", exc_info=True)
            await ctx.send(f"An unexpected error occurred while fetching recipe details for '{item_name}'. Please contact an admin.", ephemeral=True)
            return

        if not recipe_dict:
            await ctx.send(f"No recipe found for '{item_name}' in the local database or item data.", ephemeral=True)
            return

        user_id = str(ctx.author.id)
        try:
            track_recipe(user_id, item_name, recipe_dict)
        except Exception as e:
            logging.error(f"Error calling track_recipe for user {user_id}, item {item_name}: {e}", exc_info=True)

        embed = Embed()
        embed.title = f"Recipe: {recipe_dict.get('output_item_name', item_name).title()}"
        embed.color = 0x9b59b6
        embed.add_field(name="Station", value=str(recipe_dict.get("station", "-")), inline=True)
        embed.add_field(name="Skill", value=str(recipe_dict.get('skill', "-")) , inline=True)
        embed.add_field(name="Skill Level", value=str(recipe_dict.get("skill_level", "-")), inline=True)
        embed.add_field(name="Tier", value=str(recipe_dict.get("tier", "-")), inline=True)
        
        ing_lines = []
        for ing in recipe_dict.get("ingredients", []):
            ing_lines.append(f"• {ing.get('quantity', '?')} {str(ing.get('item', 'Unknown Ingredient'))}")
        embed.add_field(name="Ingredients", value="\n".join(ing_lines) if ing_lines else "-", inline=False)

        crafted_item_name = recipe_dict.get('output_item_name', item_name)
        item_details_for_recipe = await find_item_in_db(crafted_item_name, exact_match=True)
        if item_details_for_recipe:
            item_id_for_url = item_details_for_recipe[0].get('Item_ID')
            if item_id_for_url:
                embed.add_field(name="NWDB Link (Crafted Item)", value=f"[View on NWDB](https://nwdb.info/db/item/{str(item_id_for_url).strip()})", inline=False)

        await ctx.send(embeds=embed)

    @recipe.autocomplete("item_name")
    async def recipe_autocomplete(self, ctx: AutocompleteContext):
        search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
        if not search_term:
            await ctx.send(choices=[])
            return
        items = await find_item_in_db(search_term, exact_match=False)
        choices = [{"name": item["Name"], "value": item["Name"]} for item in items[:25]]
        await ctx.send(choices=choices)


    @slash_command(name="calculate_craft", description="Calculate all resources needed to craft an item, including intermediates.", dm_permission=False)
    @slash_option("item_name", "The name of the item to craft", opt_type=OptionType.STRING, required=True, autocomplete=True)
    @slash_option("amount", "How many to craft", opt_type=OptionType.INTEGER, required=False)
    @slash_option("fort_bonus", "Fort bonus (yes/no, optional)", opt_type=OptionType.BOOLEAN, required=False)
    @slash_option("armor_bonus", "Armor bonus % (2-10, optional)", opt_type=OptionType.NUMBER, required=False)
    @slash_option("tradeskill", "Tradeskill (1-250, optional)", opt_type=OptionType.INTEGER, required=False)
    async def calculate_craft(self, ctx: SlashContext, item_name: str, amount: int = 1, fort_bonus: bool = False, armor_bonus: float = 0.0, tradeskill: int = 1):
        await ctx.defer()

        recipe_details = get_recipe(item_name)
        if not recipe_details:
            await ctx.send(f"Recipe for '{item_name}' not found or item is not craftable.", ephemeral=True)
            return

        all_materials = calculate_crafting_materials(item_name, amount, include_intermediate=True)
        if not all_materials:
            await ctx.send(f"Could not calculate materials for '{item_name}'. Ensure it's a craftable item with a known recipe.", ephemeral=True)
            return

        # Apply bonuses
        armor_bonus = max(0, min(armor_bonus or 0, 10))
        tradeskill = max(1, min(tradeskill or 1, 250))
        fort_bonus_pct = 10 if fort_bonus else 0
        tradeskill_bonus_pct = (tradeskill - 1) * (300 / 249) if tradeskill > 1 else 0 # Approximation
        total_bonus = fort_bonus_pct + armor_bonus + tradeskill_bonus_pct
        bonus_factor = 1 - (total_bonus / 100)

        embed = Embed()
        embed.title = f"Crafting: {item_name.title()}"
        embed.color = 0x4CAF50
        embed.add_field(name="Amount", value=str(amount), inline=True)
        embed.add_field(name="Fort Bonus", value="Yes" if fort_bonus else "No", inline=True)
        if armor_bonus:
            embed.add_field(name="Armor Bonus", value=f"{armor_bonus:.1f}%", inline=True)
        if tradeskill:
            embed.add_field(name="Tradeskill", value=f"{tradeskill} ({tradeskill_bonus_pct:.1f}% bonus)", inline=True)

        crafted_item_icon = None
        try:
            item_results = await find_item_in_db(item_name, exact_match=True)
            if item_results:
                # DB columns are sanitized, e.g. 'Icon URL' -> 'Icon_URL'
                crafted_item_icon = item_results[0].get("Icon_URL") or item_results[0].get("Icon")
        except Exception as e:
            logging.warning(f"Could not fetch icon for crafted item '{item_name}': {e}")

        if crafted_item_icon:
            embed.set_thumbnail(url=crafted_item_icon)

        MATERIAL_EMOJIS = {
            "prismatic leather": "🟣", "iron ingot": "⛓️", "leather": "🟤",
            "wood": "🪵", "fiber": "🧵", "cloth": "🧶", "stone": "🪨",
            "gold ingot": "🥇", "silver ingot": "🥈",
        }

        if not all_materials:
            all_materials = {item_name: amount}

        embed.add_field(name="**Base Materials**", value=f"Showing all raw materials needed. Bonus: `{total_bonus:.1f}%`", inline=False)

        material_lines = []
        for mat, qty in all_materials.items():
            adj_qty = max(1, int(round(qty * bonus_factor)))
            emoji = MATERIAL_EMOJIS.get(mat.lower(), "•")

            quantity_display = f"{qty} → **{adj_qty}**" if (fort_bonus or armor_bonus or tradeskill > 1) else str(qty)
            material_lines.append(f"{emoji} {mat.title()}: {quantity_display}")

        # To avoid hitting Discord's field value limit, chunk the materials if necessary
        material_text = "\n".join(material_lines)
        if len(material_text) > 1024:
            # Simple split, can be improved to split on newlines
            chunks = [material_text[i:i+1020] for i in range(0, len(material_text), 1020)]
            for i, chunk in enumerate(chunks):
                embed.add_field(
                    name=f"Materials (Part {i+1})" if i > 0 else "\u200b",
                    value=chunk,
                    inline=False
                )
        else:
             embed.add_field(
                name="\u200b", # Zero-width space for spacing
                value=material_text,
                inline=False
            )

        embed.set_footer(text="Bonuses reduce required materials. Minimum per material is 1.")
        await ctx.send(embeds=embed)

    @calculate_craft.autocomplete("item_name")
    async def calculate_craft_autocomplete(self, ctx: AutocompleteContext):
        search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
        if not search_term:
            await ctx.send(choices=[])
            return

        conn = get_db_connection()
        choices = []
        try:
            cursor = conn.cursor()
            # Search both items and recipes for craftable items
            # Using UNION to combine results might be complex, so two queries is simpler here.
            # Prioritize items that are outputs of recipes.
            cursor.execute("SELECT output_item_name FROM recipes WHERE lower(output_item_name) LIKE ? LIMIT 15", ('%' + search_term + '%',))
            recipe_matches = cursor.fetchall()
            
            # Also check items that are craftable but might not be in the recipes table directly
            cursor.execute("SELECT Name FROM items WHERE lower(Name) LIKE ? AND Crafting_Recipe IS NOT NULL LIMIT 15", ('%' + search_term + '%',))
            item_matches = cursor.fetchall()

            # Combine and unique the names
            all_names = {row[0] for row in recipe_matches}
            all_names.update({row["Name"] for row in item_matches})

            choices = [{"name": name, "value": name} for name in sorted(list(all_names))[:25]]

        except Exception as e:
            logging.error(f"Error in calculate_craft_autocomplete: {e}")
        finally:
            pass  # The database connection is managed globally by db_utils
        await ctx.send(choices=choices)

def setup(bot):
    NewWorldCommands(bot)