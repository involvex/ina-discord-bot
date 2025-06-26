import logging
from typing import Optional
import json

from interactions import (
    Extension,
    slash_command,
    slash_option,
    OptionType,
    AutocompleteContext,
    Embed,
    SlashContext,
)

from db_utils import find_item_in_db, find_perk_in_db, find_all_item_names_in_db
from common_utils import scale_value_with_gs
from recipes import get_recipe

from commands.new_world.utils import get_any, items_data_cache # Import the in-memory cache
logger = logging.getLogger(__name__)

class NewWorldItemCommands(Extension):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="nwdb", description="Look up items from New World Database.", dm_permission=False)
    @slash_option("item_name", "The name of the item to look up", opt_type=OptionType.STRING, required=True, autocomplete=True)
    async def nwdb(self, ctx: SlashContext, item_name: str):
        await ctx.defer()

        item = None
        # 1. First, try the fast in-memory cache
        item = items_data_cache.get(item_name.lower())

        # 2. If not in cache, fall back to the database for item details
        if not item:
            item_results = await find_item_in_db(item_name, exact_match=True)
            if not item_results:
                item_results = await find_item_in_db(item_name, exact_match=False)
            
            if item_results:
                item = item_results[0]
            
        # If we found the item, display its details
        if item:
            name = get_any(item, ['Name', 'name'], item_name)
            item_id_for_url = get_any(item, ['Item ID', 'ItemID', 'Item_ID'], None)
            description = get_any(item, ['Description', 'description', 'Flavor Text', 'Flavor_Text'], 'No description available.')
            rarity = get_any(item, ['Rarity', 'rarity'], 'Unknown')
            tier = get_any(item, ['Tier', 'tier'], 'Unknown')
            icon_url = get_any(item, ['Icon URL', 'Icon_URL'], None)
            if not icon_url: # If a full URL isn't provided, construct one from the path
                icon_path = get_any(item, ['Icon Path', 'Icon_Path', 'Icon', 'icon'], None)
                if icon_path and str(icon_path).strip():
                    icon_url = f"https://cdn.nw-buddy.de/nw-data/live/{str(icon_path).strip()}"

            item_type_name = get_any(item, ['Item Type Name', 'Item_Type_Name'], 'Unknown Type')
            weight = get_any(item, ['Weight'], None)
            max_stack = get_any(item, ['Max Stack Size', 'Max_Stack_Size'], None)
            gear_score = get_any(item, ['Gear Score', 'Gear_Score', 'GS'], None)
            perks_raw = get_any(item, ['Perks', 'perks'], None)

            embed = Embed(title=name, color=0x7289DA)
            if item_id_for_url:
                embed.url = f"https://nwdb.info/db/item/{str(item_id_for_url).strip()}"

            if icon_url and "http" in str(icon_url):
                embed.set_thumbnail(url=str(icon_url).strip())
            
            embed.add_field(name="Rarity", value=str(rarity), inline=True)
            embed.add_field(name="Tier", value=str(tier), inline=True)
            embed.add_field(name="Type", value=str(item_type_name), inline=True)

            if weight is not None:
                embed.add_field(name="Weight", value=str(weight), inline=True)
            if max_stack:
                embed.add_field(name="Max Stack", value=str(max_stack), inline=True)
            if gear_score is not None:
                embed.add_field(name="Gear Score", value=str(gear_score), inline=True)

            if description and not str(description).startswith('Artifact_'):
                embed.add_field(name="Description", value=str(description), inline=False)
            
            if perks_raw:
                perk_lines = []
                for perk_entry in str(perks_raw).split("|"):
                    perk_entry = perk_entry.strip()
                    if not perk_entry: continue
                    perk_lines.append(f"• {perk_entry}")
                if perk_lines:
                    embed.add_field(name="Perks", value="\n".join(perk_lines), inline=False)

            return await ctx.send(embeds=embed)

        # 3. If item is not found, send not found message.
        await ctx.send(f"Item '{item_name}' not found in the database.", ephemeral=True)

    @nwdb.autocomplete("item_name")
    async def nwdb_autocomplete(self, ctx: AutocompleteContext):
        search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
        if not search_term:
            await ctx.send(choices=[])
            return
        # Ensure find_all_item_names_in_db returns a list of strings, and filter out any None values.
        # Also ensure the name is not empty after stripping.
        matches = [name for name in await find_all_item_names_in_db(search_term) if name is not None and str(name).strip()]
        choices = [
            {"name": str(name), "value": str(name)} for name in matches[:25] # Limit to 25 choices.
        ]

        logging.info(f"Autocomplete: Search term '{search_term}' returned {len(choices)} choices.")
        await ctx.send(choices=choices)

def setup(bot):
    NewWorldItemCommands(bot)