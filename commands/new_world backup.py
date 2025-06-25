import logging
import json
import re
from typing import Optional, Dict, Any

from interactions import (
    Extension, slash_command, slash_option, OptionType, SlashContext, AutocompleteContext, Embed, Permissions, Client, listen
)
import sqlite3 # For get_db_connection
import logging # Ensure logging is available for the new nwdb command logic

from db_utils import find_item_in_db, find_perk_in_db
from recipes import get_recipe, calculate_crafting_materials, track_recipe
from common_utils import scale_value_with_gs
from config import ITEMS_CSV_URL
from settings_manager import is_bot_manager
from config import BUILDS_FILE

# Define PERK_PRETTY outside the class if it's a global constant
PERK_PRETTY = {
    'PerkID_Artifact_Set1_HeavyChest': ("Artifact Set: Heavy Chest", "🟣"),
    'PerkID_Gem_EmptyGemSlot': ("Empty Gem Slot", "💠"),
}

MATERIAL_EMOJIS = {
    "prismatic leather": "🟣", "iron ingot": "⛓️", "leather": "🟤", "wood": "🪵",
    "fiber": "🧵", "cloth": "🧶", "stone": "🪨", "gold ingot": "🥇", "silver ingot": "🥈", "iron ore": "🪨", "starmetal ore": "🌟", "orichalcum ore": "💎"}

logger = logging.getLogger(__name__)

class NewWorldCommands(Extension):
    def __init__(self, bot: Client):
        self.bot = bot
        # Load items_updated.json once when the extension is initialized
        self.items_data_cache: Dict[str, Dict[str, Any]] = {} # Cache item data
        items_path = os.path.join(os.path.dirname(__file__), "items_updated.json") # Path to items_updated.json
        try:
            with open(items_path, "r", encoding="utf-8") as f:
                raw_items = json.load(f)
                self.items_data_cache = {item.get("Name", "").lower(): item for item in raw_items if isinstance(item, dict) and item.get("Name")}

            logger.info(f"Loaded {len(self.items_data_cache)} items into cache for crafting calculations.")
        except Exception as e:
            logger.error(f"Failed to load items_updated.json for crafting cache: {e}", exc_info=True)

    @slash_command(name="nwdb", description="Look up items from New World Database.")
    @slash_option("item_name", "The name of the item to look up", opt_type=OptionType.STRING, required=True, autocomplete=True)
    async def nwdb(self, ctx: SlashContext, item_name: str):
        """Lookup item from the New World item database."""
        await ctx.defer()
        item_results = await find_item_in_db(item_name, exact_match=True)
        if not item_results:
            item_results = await find_item_in_db(item_name, exact_match=False)
            if not item_results:
                await ctx.send(f"Item '{item_name}' not found.", ephemeral=True)
                return
        
        item = item_results[0] # Take the first match

        # Helper function to safely get values from item dictionary
        def get_any(item_dict, keys, default):
            """Helper to get value from item_dict using multiple possible keys (case-insensitive, sanitized).
            It tries to match the sanitized DB column name first, then original CSV header names."""
            for k_csv_original in keys:
                # Sanitize k_csv_original the same way create_db.py does for column names
                k_db = k_csv_original.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'percent')
                if k_db in item_dict and item_dict[k_db] is not None: # Check sanitized name
                    return item_dict[k_db]
                if k_csv_original in item_dict and item_dict[k_csv_original] is not None: # Check original name
                    return item_dict[k_csv_original]
            return default

        name = get_any(item, ['Name', 'name'], item_name)
        item_id_for_url = get_any(item, ['Item ID', 'ItemID', 'Item_ID'], None)
        description = get_any(item, ['Description', 'description', 'Flavor Text', 'Flavor_Text'], 'No description available.')
        rarity = get_any(item, ['Rarity', 'rarity'], 'Unknown')
        tier = get_any(item, ['Tier', 'tier'], 'Unknown')
        icon_path = get_any(item, ['Icon', 'icon', 'Icon Path', 'Icon_Path', 'icon_url'], None) # Added 'icon_url' from scraped data
        item_type_name = get_any(item, ['Item Type Name', 'Item_Type_Name'], 'Unknown Type')

        weight = get_any(item, ['Weight'], None)
        max_stack = get_any(item, ['Max Stack Size', 'Max_Stack_Size'], None)
        ingredient_categories_raw = get_any(item, ['Ingredient Categories', 'Ingredient_Categories'], None)
        gear_score = get_any(item, ['Gear Score', 'gear_score', 'GS', 'Gear_Score'], None)
        perks_raw = get_any(item, ['Perks', 'perks'], None)

        embed = Embed()
        embed.title = name
        if item_id_for_url:
            embed.url = f"https://nwdb.info/db/item/{str(item_id_for_url).strip()}"
        else:
            logger.warning(f"Could not find Item ID for '{name}' to create NWDB link.")

        # Determine embed color based on rarity
        rarity_colors = {
            'common': 0x808080,      # Grey
            'uncommon': 0x00FF00,    # Green
            'rare': 0x0000FF,        # Blue
            'epic': 0x800080,        # Purple
            'legendary': 0xFFA500,   # Orange
            'artifact': 0x9b59b6,    # interactions.py purple (or a distinct color)
        }
        embed.color = rarity_colors.get(str(rarity).lower(), 0x7289DA) # Default to Discord Blurple

        if icon_path:
            # Assuming icon_path is a full URL or a path that can be constructed into a URL
            # If it's just a path like "items/icons/item_icon_name", you might need a base URL
            # For now, assuming it's a direct URL or can be used as is.
            embed.set_thumbnail(url=str(icon_path).strip())
        
        embed.add_field(name="Rarity", value=str(rarity), inline=True)
        embed.add_field(name="Tier", value=str(tier), inline=True)
        embed.add_field(name="Type", value=str(item_type_name), inline=True)

        if weight is not None:
            embed.add_field(name="Weight", value=str(weight), inline=True)
        if max_stack:
            embed.add_field(name="Max Stack", value=str(max_stack), inline=True)

        if description and not str(description).startswith('Artifact_'):
            embed.add_field(name="Description", value=str(description), inline=False)
        
        if gear_score is not None: # Check for None, as 0 is a valid GS
            embed.add_field(name="Gear Score", value=str(gear_score), inline=True)
        
        if perks_raw: # Perks (if present)
            perk_lines = []
            for perk_entry in str(perks_raw).split(","):
                perk_entry = perk_entry.strip()
                if not perk_entry:
                    continue
                pretty, icon = PERK_PRETTY.get(perk_entry, (perk_entry, '•'))
                perk_lines.append(f"{icon} {pretty}")
            if perk_lines:
                embed.add_field(name="Perks", value="\n".join(perk_lines), inline=False)

        if ingredient_categories_raw: # Ingredient Types (if present)
            categories = [cat.strip() for cat in str(ingredient_categories_raw).split('|') if cat.strip()]
            if categories:
                embed.add_field(name="Ingredient Types", value=", ".join(categories), inline=False)

        # Crafting Info section
        is_recipe_item_flag = name.lower().startswith("recipe:")
        actual_item_name_from_recipe_item = None
        if is_recipe_item_flag:
            actual_item_name_from_recipe_item = name.lower().replace("recipe:", "").strip().title()
            embed.title = f"Recipe: {actual_item_name_from_recipe_item}"

        conn_check = None
        can_be_crafted_flag = False
        try:
            from db_utils import get_db_connection # Import here to avoid circular dependency if db_utils imports recipes
            conn_check = get_db_connection()
            cursor_check = conn_check.cursor()
            target_craft_check_name = actual_item_name_from_recipe_item if is_recipe_item_flag else name
            cursor_check.execute("SELECT 1 FROM recipes WHERE lower(output_item_name) = ?", (target_craft_check_name.lower(),))
            if cursor_check.fetchone():
                can_be_crafted_flag = True
        except sqlite3.Error as e:
            logger.warning(f"Could not check if item {target_craft_check_name} is craftable due to DB error: {e}")
        finally:
            if conn_check:
                conn_check.close()

        craft_status_lines = []
        if is_recipe_item_flag:
            craft_status_lines.append(f"📜 This is a recipe scroll for **{actual_item_name_from_recipe_item}**.")
            embed.set_footer(text=f"Type /recipe item_name:\"{actual_item_name_from_recipe_item}\" to see its crafting details!")
        elif can_be_crafted_flag:
            craft_status_lines.append("✅ Can be crafted.")
            embed.set_footer(text=f"Type /calculate_craft item_name:\"{name}\" to calculate resources!")

        if not is_recipe_item_flag and (ingredient_categories_raw or 'resource' in str(item_type_name).lower()):
            craft_status_lines.append("🛠️ Used as a crafting material.")

        if craft_status_lines:
            embed.add_field(name="Crafting Info", value="\n".join(craft_status_lines), inline=False)

        await ctx.send(embeds=embed)

    @nwdb.autocomplete("item_name")
    async def nwdb_autocomplete(self, ctx: AutocompleteContext): # Corrected type hint for Autocomplete
        search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
        if not search_term:
            return await ctx.send(choices=[])
        matches = await find_item_in_db(search_term, exact_match=False)
        choices = [{"name": row["Name"], "value": row["Name"]} for row in matches[:25]]
        await ctx.send(choices=choices)

    @slash_command(name="perk", description="Look up information about a specific New World perk.")
    @slash_option("perk_name", "The name of the perk to look up", opt_type=OptionType.STRING, required=True, autocomplete=True)
    async def perk(self, ctx: SlashContext, perk_name: str):
        """Lookup perk from the New World perk database."""
        await ctx.defer()
        perk_results = await find_perk_in_db(perk_name, exact_match=True)
        if not perk_results:
            perk_results = await find_perk_in_db(perk_name, exact_match=False)
            if not perk_results:
                await ctx.send(f"Perk '{perk_name}' not found in the database.", ephemeral=True)
                return
        
        perk = perk_results[0]
        description = scale_value_with_gs(str(perk.get('description', 'N/A')))
        embed = Embed(title=perk.get('name', perk_name), description=description, color=0x1ABC9C)
        if perk.get('icon_url'):
            embed.set_thumbnail(url=perk['icon_url'])
        
        embed.add_field(name="Type", value=str(perk.get('PerkType', 'N/A')), inline=True)
        if perk.get('id'):
            embed.add_field(name="NWDB Link", value=f"[View on NWDB](https://nwdb.info/db/perk/{perk['id']})", inline=True)
        
        await ctx.send(embeds=embed)

    @perk.autocomplete("perk_name")
    async def perk_autocomplete(self, ctx: AutocompleteContext): # Corrected type hint for Autocomplete
        """Autocomplete for perk names."""
        search_term = ctx.input_text
        if not search_term:
            return await ctx.send(choices=[])
            return
        matches = await find_perk_in_db(search_term, exact_match=False)
        choices = [{"name": row["name"], "value": row["name"]} for row in matches[:25]]
        await ctx.send(choices=choices)

    @slash_command(name="recipe", description="Show the full recipe breakdown for a craftable item.")
    @slash_option("item_name", "The name of the item to show the recipe for", opt_type=OptionType.STRING, required=True, autocomplete=True)
    async def recipe(self, ctx: SlashContext, item_name: str):
        """Show the full recipe breakdown for a craftable item."""
        await ctx.defer()
        recipe_dict = get_recipe(item_name)
        if not recipe_dict:
            await ctx.send(f"No recipe found for '{item_name}'.", ephemeral=True)
            return
        
        track_recipe(str(ctx.author.id), item_name, recipe_dict)
        
        embed = Embed(title=f"Recipe: {recipe_dict.get('output_item_name', item_name).title()}", color=0x9b59b6)
        embed.add_field(name="Station", value=str(recipe_dict.get("station", "-")), inline=True)
        embed.add_field(name="Skill", value=str(recipe_dict.get('skill', "-")), inline=True)
        
        ingredients = recipe_dict.get("ingredients", [])
        ing_lines = [f"• {ing.get('quantity', '?')} {ing.get('item', 'Unknown')}" for ing in ingredients]
        embed.add_field(name="Ingredients", value="\n".join(ing_lines) if ing_lines else "-", inline=False)

        # Add thumbnail for the crafted item
        crafted_item_name = recipe_dict.get('output_item_name', item_name)
        item_details_for_recipe = await find_item_in_db(crafted_item_name, exact_match=True)
        if item_details_for_recipe:
            icon_path = self.get_any(item_details_for_recipe[0], ['Icon', 'icon', 'Icon Path', 'Icon_Path', 'icon_url'], None)
            if icon_path:
                embed.set_thumbnail(url=str(icon_path).strip())
        
        await ctx.send(embeds=embed)

    @recipe.autocomplete("item_name")
    async def recipe_autocomplete(self, ctx: AutocompleteContext):
        """Autocomplete for recipe item names."""
        search_term = ctx.input_text
        if not search_term:
            return await ctx.send(choices=[])
            return
        matches = await find_item_in_db(search_term, exact_match=False)
        choices = [{"name": row["Name"], "value": row["Name"]} for row in matches[:25]]
        await ctx.send(choices=choices)

    @slash_command(name="calculate_craft", description="Calculate resources needed to craft an item.")
    @slash_option("item_name", "The name of the item to craft", opt_type=OptionType.STRING, required=True, autocomplete=True)
    @slash_option("amount", "How many to craft", opt_type=OptionType.INTEGER, required=False)

    async def calculate_craft(self, ctx: SlashContext, item_name: str, amount: int = 1):
        await ctx.defer()
        materials = calculate_crafting_materials(item_name, amount, include_intermediate=True)
        if not materials:
            await ctx.send(f"Could not calculate materials for '{item_name}'.", ephemeral=True)
            return
        
        embed = Embed(title=f"Materials for {amount}x {item_name.title()}", color=0x4CAF50)
        await self._send_calculate_craft_embed(ctx, item_name, amount, materials)

    @calculate_craft.autocomplete("item_name")



    async def calculate_craft_autocomplete(self, ctx: AutocompleteContext):
        search_term = ctx.input_text
        if not search_term:
            return await ctx.send(choices=[])
            return
        matches = await find_item_in_db(search_term, exact_match=False)
        choices = [{"name": row["Name"], "value": row["Name"]} for row in matches[:25]]
        await ctx.send(choices=choices)

    async def _send_calculate_craft_embed(self, ctx: SlashContext, item_name: str, amount: int, all_materials: Dict[str, int]):
        """Helper to send the beautified calculate_craft embed."""
        embed = Embed(title=f"Materials for {amount}x {item_name.title()}", color=0x4CAF50)

        # Add crafted item icon
        crafted_item_icon = None # Icon for the crafted item
        item_results = await find_item_in_db(item_name, exact_match=True)
        if item_results:
            crafted_item_icon = self.get_any(item_results[0], ['Icon', 'icon', 'Icon Path', 'Icon_Path', 'icon_url'], None)
        if crafted_item_icon:
            embed.set_thumbnail(url=str(crafted_item_icon).strip())

        # Calculate bonuses
        if total_bonus > 0:
            embed.add_field(name="Total Bonus", value=f"✨ {total_bonus:.1f}%", inline=True)

        embed.add_field(name="**Required Materials**", value="\u200b", inline=False)

        MATERIAL_EMOJIS = {
            "prismatic leather": "🟣", "iron ingot": "⛓️", "leather": "🟤", "wood": "🪵",
            "fiber": "🧵", "cloth": "🧶", "stone": "🪨", "gold ingot": "🥇",
            "silver ingot": "🥈", "iron ore": "🪨", "starmetal ore": "🌟", "orichalcum ore": "💎"
            # Add more common material emojis here
        }

        for mat_name, qty in all_materials.items():
            adjusted_qty = max(1, int(round(qty * bonus_factor))) if total_bonus > 0 else qty
            
            emoji = MATERIAL_EMOJIS.get(mat_name.lower(), "")
            
            # Try to get icon for this material from the pre-loaded cache
            material_icon_url = None
            material_data = self.items_data_cache.get(mat_name.lower())
            if material_data:
                material_icon_url = self.get_any(material_data, ['Icon', 'icon', 'Icon Path', 'Icon_Path', 'icon_url'], None)

            field_name = f"{emoji} {mat_name.title()}".strip()
            
            quantity_display = f"{qty} → **{adjusted_qty}**" if total_bonus > 0 else str(qty)

            if material_icon_url:
                # Discord embed field values do not support markdown links directly for images.
                # The best way to show an icon is in the name or as a separate field.
                # For now, we'll just display the quantity and rely on the emoji/name.
                # If you want clickable links, you'd need to put the link in the value and not use it for an image.
                field_value = f"Quantity: {quantity_display}"
            else:
                field_value = f"Quantity: {quantity_display}"

            embed.add_field(
                name=field_name,
                value=field_value,
                inline=True # Use inline to make it more compact
            )
        embed.set_footer(text="Bonuses reduce the required materials. Minimum per material is 1.")
        await ctx.send(embeds=embed)

    @slash_command(name="build", description="Manage saved New World builds.")
    async def build_group(self, ctx: SlashContext):
        pass

    @build_group.subcommand(sub_cmd_name="add", sub_cmd_description="Add a build from nw-buddy.de.")
    @slash_option("link", "The nw-buddy.de build link", opt_type=OptionType.STRING, required=True)
    @slash_option("name", "A name for this build", opt_type=OptionType.STRING, required=True)
    async def build_add(self, ctx: SlashContext, link: str, name: str):
        if not re.match(r"^https://(www\.)?nw-buddy.de/gearsets/", link):
            await ctx.send("Please provide a valid nw-buddy.de gearset link.", ephemeral=True)
            return
        
        try:
            with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
                builds = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            builds = []
        
        builds.append({"name": name, "link": link, "submitted_by": str(ctx.author.id)})
        
        with open(BUILDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(builds, f, indent=2)
            
        await ctx.send(f"Build '{name}' added!", ephemeral=True)

    @build_group.subcommand(sub_cmd_name="list", sub_cmd_description="Show a list of saved builds.")
    async def build_list(self, ctx: SlashContext):
        try:
            with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
                builds = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            builds = []

        if not builds:
            await ctx.send("No builds saved yet.", ephemeral=True)
            return

        embed = Embed(title="Saved Builds", color=0x3498db)
        for build in builds:
            submitter = f"<@{build.get('submitted_by', 'Unknown')}>"
            embed.add_field(name=build['name'], value=f"[Link]({build['link']}) by {submitter}", inline=False)
        
        await ctx.send(embeds=embed)

    @build_group.subcommand(sub_cmd_name="remove", sub_cmd_description="Remove a saved build.")
    @slash_option("name", "The name of the build to remove", opt_type=OptionType.STRING, required=True, autocomplete=True)
    async def build_remove(self, ctx: SlashContext, name: str):
        if not ctx.author.has_permission(Permissions.MANAGE_GUILD) and not is_bot_manager(int(ctx.author.id)):
            await ctx.send("You need 'Manage Server' permission or be a Bot Manager to use this command.", ephemeral=True)
            return

        try:
            with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
                builds = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            await ctx.send("No builds to remove.", ephemeral=True)
            return

        original_count = len(builds)
        builds_filtered = [b for b in builds if b.get("name", "").lower() != name.lower()]

        if len(builds_filtered) == original_count:
            await ctx.send(f"Build '{name}' not found.", ephemeral=True)
            return

        with open(BUILDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(builds_filtered, f, indent=2)
        
        await ctx.send(f"Build '{name}' removed.", ephemeral=True)

    @build_remove.autocomplete("name")
    async def build_remove_autocomplete(self, ctx: AutocompleteContext):
        try:
            with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
                builds = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            await ctx.send(choices=[])
            return
        
        search_term = ctx.input_text.lower()
        choices = [
            {"name": b["name"], "value": b["name"]}
            for b in builds if search_term in b.get("name", "").lower()
        ][:25]
        await ctx.send(choices=choices)

def setup(bot):
    NewWorldCommands(bot)