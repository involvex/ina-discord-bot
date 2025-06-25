import logging
import re
from typing import Optional

from interactions import (
    Extension, slash_command, slash_option, OptionType, SlashContext, AutocompleteContext, Embed, Client
)

from db_utils import find_perk_in_db
from common_utils import scale_value_with_gs # Import scale_value_with_gs
from commands.new_world.utils import get_any, PERK_PRETTY # Import get_any and PERK_PRETTY

logger = logging.getLogger(__name__)

class NewWorldPerks(Extension):
    def __init__(self, bot: Client):
        self.bot = bot

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
        
        perk_info = perk_results[0]

        name_raw = get_any(perk_info, ['Name', 'PerkName', 'name'], perk_name)
        description_raw = get_any(perk_info, ['Description', 'Desc', 'description', 'DescText', 'EffectText'], 'No description available.')
        perk_type_raw = get_any(perk_info, ['Type', 'PerkType', 'Category'], 'Unknown Type')
        icon_url = get_any(perk_info, ['Icon', 'IconPath', 'icon_url'], None)
        perk_id = get_any(perk_info, ['PerkID', 'ID', 'id'], None)

        # Craft Mod specific info
        generated_label = get_any(perk_info, ['GeneratedLabel', 'PerkApplicationType'], None)
        craft_mod_item_name = get_any(perk_info, ['ItemName', 'IngredientName', 'CraftModItem'], None)
        condition = get_any(perk_info, ['ConditionDescription', 'ConditionText'], None)
        compatible_with_raw = get_any(perk_info, ['EquipType', 'CompatibleItemTypes', 'CompatibleEquipment'], None)
        exclusive_labels_raw = get_any(perk_info, ['ExclusiveLabels', 'ExclusiveLabel', 'MutatorGroup'], None)

        is_craft_mod = (generated_label and 'crafting mod' in str(generated_label).lower()) or \
                       ('craft mod' in str(perk_type_raw).lower())

        display_title = str(name_raw)
        if is_craft_mod and "craft mod" not in str(name_raw).lower():
            display_title = f"Craft Mod: {str(name_raw)}"

        embed = Embed(title=display_title, color=0x1ABC9C)
        if icon_url:
            embed.set_thumbnail(url=str(icon_url).strip())

        scaled_description = scale_value_with_gs(str(description_raw))
        perk_type_display = str(perk_type_raw).strip() if perk_type_raw and str(perk_type_raw).strip() else "Unknown Type"

        embed.add_field(name="Description", value=scaled_description, inline=False)
        embed.add_field(name="Type", value=perk_type_display, inline=True)

        if is_craft_mod and craft_mod_item_name and str(craft_mod_item_name).strip():
            embed.add_field(name="Crafted With / Source", value=str(craft_mod_item_name), inline=True)
        
        if re.search(r'\{\[.*?\]\}', str(description_raw)):
            embed.add_field(name="Scaling", value="Values scale with Gear Score (shown at 725 GS)", inline=True)

        embed.add_field(name="Condition", value=str(condition).strip() if condition else "-", inline=False)
        embed.add_field(name="Compatible With", value=", ".join([item.strip() for item in str(compatible_with_raw).split(',') if item.strip()]) if compatible_with_raw else "-", inline=False)
        embed.add_field(name="Exclusive Labels", value=", ".join([label.strip() for label in str(exclusive_labels_raw).split(',') if label.strip()]) if exclusive_labels_raw else "-", inline=True)

        if perk_id:
            embed.add_field(name="NWDB Link", value=f"[View on NWDB](https://nwdb.info/db/perk/{str(perk_id).strip()})", inline=True)
        else:
            embed.add_field(name="NWDB Link", value="Perk ID not found for direct link", inline=True)

        embed.set_footer(text="Perk information from local data. Values may scale with Gear Score in-game.")
        await ctx.send(embeds=embed)

    @perk.autocomplete("perk_name")
    async def perk_autocomplete(self, ctx: AutocompleteContext):
        """Autocomplete for perk names."""
        search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
        if not search_term: return await ctx.send(choices=[])
        matches = await find_perk_in_db(search_term, exact_match=False)
        choices = [
            {"name": str(name), "value": str(name)}
            for row in matches[:25]
            if (name := get_any(row, ['Name', 'name', 'PerkName'], None)) # Using get_any for robustness
        ]
        await ctx.send(choices=choices)

def setup(bot: Client):
    NewWorldPerks(bot)