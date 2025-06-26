import logging
import json
import hashlib
import asyncio
import re
from typing import Optional, Dict, Any
from typing import Union, Dict, Any, Optional # Added Union, Dict, Any, Optional

from interactions import (
    Extension, slash_command, slash_option, OptionType, SlashContext, AutocompleteContext, Embed, Client, Button, ButtonStyle, component_callback, ComponentContext
) # Added Button, ButtonStyle, component_callback, ComponentContext

from db_utils import find_item_in_db, find_all_item_names_in_db
from recipes import get_recipe, calculate_crafting_materials, track_recipe
from commands.new_world.utils import get_any, items_data_cache, GENERIC_MATERIAL_MAPPING, resolve_item_name_for_lookup

logger = logging.getLogger(__name__)

class NewWorldCrafting(Extension):
    def __init__(self, bot: Client):
        self.bot = bot
        # Cache for button data to avoid long custom_ids
        self.button_data_cache: Dict[str, Dict[str, Any]] = {}

    def _generate_component_id(self, item_name: str, amount: int, fort_bonus: bool, armor_bonus: float, tradeskill: int, detailed: bool) -> str:
        data_string = f"{item_name}-{amount}-{fort_bonus}-{armor_bonus}-{tradeskill}-{detailed}"
        return hashlib.md5(data_string.encode()).hexdigest()

    @slash_command(name="recipe", description="Show the full recipe breakdown for a craftable item.")
    @slash_option("item_name", "The name of the item to show the recipe for", opt_type=OptionType.STRING, required=True, autocomplete=True)
    async def recipe(self, ctx: SlashContext, item_name: str):
        """Show the full recipe breakdown for a craftable item."""
        await ctx.defer()
        recipe_dict = await get_recipe(item_name)
        if not recipe_dict:
            await ctx.send(f"No recipe found for '{item_name}'.", ephemeral=True)
            return
        

        track_recipe(str(ctx.author.id), item_name, recipe_dict)
        
        # Use get_any for robustness, as recipe_dict might come from different sources
        output_item_name = get_any(recipe_dict, ['output_item_name', 'Name'], item_name).title()
        station = get_any(recipe_dict, ['station', 'Station'], '-')
        skill = get_any(recipe_dict, ['skill', 'tradeskill', 'Tradeskill'], '-')
        skill_level = get_any(recipe_dict, ['skill_level', 'tradeskillLevel', 'Recipe Level'], '-')
        tier = get_any(recipe_dict, ['tier', 'Tier'], '-')

        embed = Embed(title=f"Recipe: {output_item_name}", color=0x9b59b6)
        embed.add_field(name="Station", value=str(station), inline=True)
        embed.add_field(name="Skill", value=str(skill), inline=True)
        embed.add_field(name="Skill Level", value=str(skill_level), inline=True)
        embed.add_field(name="Tier", value=str(tier), inline=True)
        
        ingredients = recipe_dict.get("ingredients", [])
        ing_lines = [f"• {ing.get('quantity', '?')} {ing.get('item', 'Unknown')}" for ing in ingredients]
        embed.add_field(name="Ingredients", value="\n".join(ing_lines) if ing_lines else "-", inline=False)

        # Add thumbnail for the crafted item
        crafted_item_name = recipe_dict.get('output_item_name', item_name)
        item_details_for_recipe = await find_item_in_db(crafted_item_name, exact_match=True)
        if item_details_for_recipe:
            icon_path = get_any(item_details_for_recipe[0], ['Icon URL', 'icon_url', 'Icon', 'icon', 'Icon Path', 'Icon_Path'], None)
            if icon_path and isinstance(icon_path, str) and icon_path.lower().startswith("http"):
                try:
                    embed.set_thumbnail(url=str(icon_path).strip())
                except Exception as e:
                    logger.warning(f"Failed to set thumbnail for recipe '{item_name}' with URL '{icon_path}': {e}")
            else:
                logger.warning(f"Invalid icon path for recipe '{item_name}': {icon_path}")
        
        await ctx.send(embeds=embed)
        
    @recipe.autocomplete("item_name")
    async def recipe_autocomplete(self, ctx: AutocompleteContext):
        """Autocomplete for recipe item names."""
        search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
        if not search_term:
            return await ctx.send(choices=[])
        matches = await find_all_item_names_in_db(search_term) # This returns a list of strings
        choices = []
        for name in matches[:25]: # Limit to 25 choices for Discord autocomplete
            if name is not None and str(name).strip(): # Explicitly check for None and empty strings
                choices.append({"name": str(name), "value": str(name)})
        await ctx.send(choices=choices)

    @slash_command(name="calculate_craft", description="Calculate resources needed to craft an item.")
    @slash_option("item_name", "The name of the item to craft", opt_type=OptionType.STRING, required=True, autocomplete=True)
    @slash_option("amount", "How many to craft", opt_type=OptionType.INTEGER, required=False)
    @slash_option("fort_bonus", "Fort bonus (yes/no, optional)", opt_type=OptionType.BOOLEAN, required=False)
    @slash_option("armor_bonus", "Armor bonus % (2-10, optional)", opt_type=OptionType.NUMBER, required=False)
    @slash_option("tradeskill", "Tradeskill (1-250, optional)", opt_type=OptionType.INTEGER, required=False)
    async def calculate_craft(self, ctx: SlashContext, item_name: str, amount: int = 1, fort_bonus: bool = True, armor_bonus: float = 10.0, tradeskill: int = 250):
        await ctx.defer()

        # Resolve legacy item names (e.g., 'ingott5') to their proper names before calculation.
        resolved_item_name = resolve_item_name_for_lookup(item_name)

        materials = await calculate_crafting_materials(resolved_item_name, amount, include_intermediate=False) # Start with simple view
        if not materials:
            await ctx.send(f"Could not calculate materials for '{resolved_item_name}'. It might not be a craftable item.", ephemeral=True)
            return

        await self._send_calculate_craft_embed(ctx, resolved_item_name, amount, fort_bonus, armor_bonus, tradeskill, materials, detailed=False, is_button_click=False)

    @calculate_craft.autocomplete("item_name")
    async def calculate_craft_autocomplete(self, ctx: AutocompleteContext):
        search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
        if not search_term:
            return await ctx.send(choices=[])
        matches = await find_all_item_names_in_db(search_term) # This returns a list of strings
        choices = []
        for name in matches[:25]: # Limit to 25 choices for Discord autocomplete
            if name is not None and str(name).strip(): # Explicitly check for None and empty strings
                choices.append({"name": str(name), "value": str(name)})
        await ctx.send(choices=choices)

    @component_callback(re.compile(r"calc_(detail|simple)::([a-f0-9]{32})")) # Regex to capture the hash
    async def handle_craft_view_change(self, ctx: ComponentContext):
        """Handles the button click to toggle between simple and detailed craft views."""
        await ctx.defer(edit_origin=True)
        
        try:
            # Extract view_type and hash_id from custom_id using regex groups
            match = re.match(r"calc_(detail|simple)::([a-f0-9]{32})", ctx.custom_id)
            if not match:
                raise ValueError(f"Custom ID format mismatch: {ctx.custom_id}")

            view_type = match.group(1) # 'detail' or 'simple'
            hash_id = match.group(2) # The MD5 hash

            # Retrieve parameters from cache using the hash_id
            cached_data = self.button_data_cache.get(hash_id)
            if not cached_data:
                logger.error(f"No cached data found for hash_id: {hash_id}")
                await ctx.edit_origin(content="Error: Button data expired or not found. Please try the command again.", embeds=[], components=[])
                return

            item_name = cached_data['item_name']
            amount = cached_data['amount']
            fort_bonus = cached_data['fort_bonus']
            armor_bonus = cached_data['armor_bonus']
            tradeskill = cached_data['tradeskill']
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse custom_id '{ctx.custom_id}' or retrieve data: {e}")
            await ctx.edit_origin(content="Error processing your request. The button data seems to be invalid or expired.", embeds=[], components=[])
            return

        detailed = view_type == "detail"
        
        materials = await calculate_crafting_materials(item_name, amount, include_intermediate=detailed)
        
        if not materials:
            logger.warning(f"Recalculation of materials failed for '{item_name}', detailed={detailed}.")
            await ctx.edit_origin(content="Could not recalculate materials.", embeds=[], components=[])
            return
            
        await self._send_calculate_craft_embed(ctx, item_name, amount, fort_bonus, armor_bonus, tradeskill, materials, detailed=detailed, is_button_click=True)

    async def _send_calculate_craft_embed(self, ctx: Union[SlashContext, ComponentContext], item_name: str, amount: int, fort_bonus: bool, armor_bonus: float, tradeskill: int, all_materials: Dict[str, int], detailed: bool, is_button_click: bool = False):
        """Helper to send the beautified calculate_craft embed."""
        title_prefix = "Detailed Materials" if detailed else "Required Materials"
        embed = Embed(title=f"{title_prefix} for {amount}x {item_name.title()}", color=0x4CAF50)

        # Add crafted item icon
        logger.debug(f"Looking up icon for crafted item: {item_name}")
        crafted_item_icon = None
        item_results = await find_item_in_db(item_name, exact_match=True)
        if item_results:
            crafted_item_icon = get_any(item_results[0], ['Icon', 'icon', 'Icon Path', 'Icon_Path', 'icon_url'], None)
        if crafted_item_icon:
            embed.set_thumbnail(url=str(crafted_item_icon).strip())

        # Calculate bonuses
        # Note for recipes.py:
        # The `get_recipe` function (likely in recipes.py) should be updated to use
        # `resolve_item_name_for_lookup` for all ingredient names before performing
        # lookups or recursive calls. For example:
        # resolved_item_name = resolve_item_name_for_lookup(raw_item_name_from_csv)
        armor_bonus = max(0, min(armor_bonus or 0, 10))
        tradeskill = max(1, min(tradeskill or 1, 250))
        fort_bonus_pct = 10 if fort_bonus else 0
        tradeskill_bonus_pct = (tradeskill - 1) * (300 / 249) if tradeskill > 1 else 0
        total_bonus = fort_bonus_pct + armor_bonus + tradeskill_bonus_pct
        bonus_factor = 1 - (total_bonus / 100)

        embed.add_field(name="Target Amount", value=str(amount), inline=True)
        embed.add_field(name="Fort Bonus", value="✅ Yes" if fort_bonus else "❌ No", inline=True)
        if armor_bonus > 0:
            embed.add_field(name="Armor Bonus", value=f"🛡️ {armor_bonus:.1f}%", inline=True)
        if tradeskill > 1:
            embed.add_field(name="Tradeskill", value=f"🛠️ {tradeskill} ({tradeskill_bonus_pct:.1f}% bonus)", inline=True)
        
        if total_bonus > 0:
            embed.add_field(name="Total Bonus", value=f"✨ {total_bonus:.1f}%", inline=True)

        embed.add_field(name="**Required Materials**", value="\u200b", inline=False)

        for mat_name, qty in all_materials.items():
            adjusted_qty = max(1, int(round(qty * bonus_factor))) if total_bonus > 0 else qty

            # Try to get icon for this material from the pre-loaded cache
            # This logic already exists and is correct.
            material_icon_url = None
            material_data = items_data_cache.get(mat_name.lower())
            if material_data:
                material_icon_url = get_any(material_data, ['Icon', 'icon', 'Icon Path', 'Icon_Path', 'icon_url'], None)

            display_mat_name = GENERIC_MATERIAL_MAPPING.get(mat_name.lower(), mat_name)
            
            # The field name will just be the material name.
            field_name = display_mat_name.title().strip()
            
            quantity_display = f"{qty} → **{adjusted_qty}**" if total_bonus > 0 else str(qty)

            if material_icon_url:
                field_value = f"Quantity: {quantity_display}"
            else:
                field_value = f"Quantity: {quantity_display}"

            embed.add_field(
                name=field_name,
                value=field_value,
                inline=True
            )

        # Button logic
        if detailed:
            button_label = "Show Simple View"
            new_view_type = "simple"
        else:
            button_label = "Show Detailed Breakdown"
            new_view_type = "detail"
            
        # Generate the hash ID for the current set of parameters
        hash_id = self._generate_component_id(item_name, amount, fort_bonus, armor_bonus, tradeskill, detailed)
        button_custom_id = f"calc_{new_view_type}::{hash_id}"

        # Store the parameters in the cache using the hash_id
        self.button_data_cache[hash_id] = {
            'item_name': item_name,
            'amount': amount,
            'fort_bonus': fort_bonus,
            'armor_bonus': armor_bonus,
            'tradeskill': tradeskill,
            'detailed': detailed # Store the current detailed state as well
        }
        
        if len(button_custom_id) > 100:
            logger.warning(f"Generated custom_id exceeds 100 chars: {button_custom_id}")
            button = Button(style=ButtonStyle.SECONDARY, label="Breakdown Unavailable (ID too long)", disabled=True)
        else:
            button = Button(
                style=ButtonStyle.PRIMARY,
                label=button_label,
                custom_id=button_custom_id
            )
            
        embed.set_footer(text="Bonuses reduce the required materials. Minimum per material is 1.")

        
        if is_button_click:
            await ctx.edit_origin(embeds=[embed], components=[button])
        else:
            await ctx.send(embeds=[embed], components=[button])

def setup(bot: Client):
    NewWorldCrafting(bot)