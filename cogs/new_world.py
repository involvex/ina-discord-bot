import json
import logging
import re
import requests
from bs4 import BeautifulSoup
from interactions import slash_command, slash_option, OptionType, Embed, Permissions

from bot_client import bot
from config import BUILDS_FILE
import items # Your existing items.py
import perks as perks_module # Your existing perks.py, aliased to avoid conflict
from recipes import get_recipe, calculate_crafting_materials, RECIPES, fetch_recipe_from_nwdb, track_recipe
from utils.perk_scaler import scale_value_with_gs # Using the refactored perk scaler

# Perk pretty names and icons mapping (expand as needed)
PERK_PRETTY_NAMES = {
    'PerkID_Artifact_Set1_HeavyChest': ("Artifact Set: Heavy Chest", "🟣"),
    'PerkID_Gem_EmptyGemSlot': ("Empty Gem Slot", "💠"),
    'PerkID_Armor_DefBasic': ("Basic Defense", "🛡️"),
    'PerkID_Armor_RangeDefense_Physical': ("Ranged Physical Defense", "🏹"),
    # Add more known perks here...
}

@slash_command("nwdb", description="Look up items from New World Database.")
@slash_option("item_name", "The name of the item to look up", opt_type=OptionType.STRING, required=True, autocomplete=True)
async def nwdb(ctx, item_name: str):
    item_data = items.load_items_from_csv('items.csv')
    if not item_data:
        await ctx.send("Could not load item data.", ephemeral=True)
        return
    item_name_lower = item_name.lower()
    if item_name_lower not in item_data:
        await ctx.send(f"Item '{item_name}' not found in the database.", ephemeral=True)
        return
    item_info = item_data[item_name_lower]

    def get_any(data, keys, default):
        for k in keys:
            if k in data and data[k]: return data[k]
        return default

    name = get_any(item_info, ['name', 'Name', 'Item Name'], item_name)
    description = get_any(item_info, ['description', 'Description', 'Flavor Text'], 'No description available.')
    rarity = get_any(item_info, ['rarity', 'Rarity'], 'Unknown')
    tier = get_any(item_info, ['tier', 'Tier'], 'Unknown')
    icon_url = get_any(item_info, ['icon', 'Icon', 'Icon Path', 'icon_url'], None)

    embed = Embed(title=name, color=0x9b59b6 if rarity.lower() == 'artifact' else 0x7289DA)
    if icon_url: embed.set_thumbnail(url=icon_url)
    embed.add_field(name="Rarity", value=rarity, inline=True)
    embed.add_field(name="Tier", value=tier, inline=True)
    if description and not description.startswith('Artifact_'):
        embed.add_field(name="Description", value=description, inline=False)

    gear_score = get_any(item_info, ['gear_score', 'Gear Score', 'GS'], None)
    if gear_score: embed.add_field(name="Gear Score", value=str(gear_score), inline=True)

    perks_data = get_any(item_info, ['perks', 'Perks'], None)
    if perks_data:
        perk_lines = []
        for perk_id_str in str(perks_data).split(","):
            perk_id_str = perk_id_str.strip()
            if not perk_id_str: continue
            pretty_name, icon = PERK_PRETTY_NAMES.get(perk_id_str, (perk_id_str, '•'))
            perk_lines.append(f"{icon} {pretty_name}")
        if perk_lines: embed.add_field(name="Perks", value="\n".join(perk_lines), inline=False)

    if get_recipe(item_name):
        embed.set_footer(text=f"Type /calculate_craft item_name:{item_name} amount:1 to calculate resources!")
    await ctx.send(embeds=embed)

@nwdb.autocomplete("item_name")
async def nwdb_autocomplete(ctx):
    item_data = items.load_items_from_csv('items.csv')
    if not item_data: await ctx.send(choices=[]); return
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    matches = [name for name in item_data.keys() if search_term in name]
    choices = [{"name": name.title(), "value": name} for name in list(matches)[:25]] # Show title cased name
    await ctx.send(choices=choices)

@slash_command("calculate_craft", description="Calculate all resources needed to craft an item, including intermediates.")
@slash_option("item_name", "The name of the item to craft", opt_type=OptionType.STRING, required=True, autocomplete=True)
@slash_option("amount", "How many to craft", opt_type=OptionType.INTEGER, required=False)
async def calculate_craft(ctx, item_name: str, amount: int = 1):
    recipe = get_recipe(item_name)
    if not recipe:
        await ctx.send(f"No recipe found for '{item_name}'.", ephemeral=True)
        return
    all_materials = calculate_crafting_materials(item_name, amount or 1, include_intermediate=True)
    if not all_materials:
        await ctx.send(f"Could not calculate materials for '{item_name}'.", ephemeral=True)
        return
    lines = [f"To craft {amount or 1} **{item_name.title()}** you need (including intermediates):"]
    for mat, qty in all_materials.items():
        lines.append(f"• {qty} {mat.title()}")
    await ctx.send("\n".join(lines))

@calculate_craft.autocomplete("item_name")
async def calculate_craft_autocomplete(ctx):
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    matches = [name for name in RECIPES.keys() if search_term in name]
    choices = [{"name": name.title(), "value": name} for name in list(matches)[:25]]
    await ctx.send(choices=choices)

@slash_command("recipe", description="Show the full recipe breakdown for a craftable item and track it.")
@slash_option("item_name", "The name of the item to show the recipe for", opt_type=OptionType.STRING, required=True, autocomplete=True)
async def recipe_command(ctx, item_name: str): # Renamed to avoid conflict with recipes module
    recipe_data = get_recipe(item_name)
    if not recipe_data:
        recipe_data = fetch_recipe_from_nwdb(item_name)
        if not recipe_data:
            await ctx.send(f"No recipe found for '{item_name}'.", ephemeral=True)
            return
        # else: await ctx.send(f"Recipe for '{item_name}' fetched from nwdb.info.", ephemeral=True) # Optional feedback

    user_id = str(ctx.author.id)
    track_recipe(user_id, item_name, recipe_data)
    embed = Embed(title=f"Recipe: {item_name.title()}", color=0x9b59b6)
    embed.add_field(name="Station", value=recipe_data.get("station", "-"), inline=True)
    embed.add_field(name="Skill", value=f"{recipe_data.get('skill', '-')}", inline=True)
    embed.add_field(name="Skill Level", value=str(recipe_data.get("skill_level", "-")), inline=True)
    embed.add_field(name="Tier", value=str(recipe_data.get("tier", "-")), inline=True)
    ing_lines = [f"• {ing['quantity']} {ing['item'].title()}" for ing in recipe_data.get("ingredients", [])]
    embed.add_field(name="Ingredients", value="\n".join(ing_lines) or "-", inline=False)
    await ctx.send(embeds=embed)

@recipe_command.autocomplete("item_name")
async def recipe_autocomplete(ctx):
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    item_data = items.load_items_from_csv('items.csv') # Assuming all craftable items are in items.csv
    if not item_data: await ctx.send(choices=[]); return
    # Filter for items that are known to be craftable or just general items
    matches = [name for name in RECIPES.keys() if search_term in name] # Prioritize known recipes
    for name in item_data.keys(): # Add other items that might be fetchable
        if search_term in name and name not in matches:
            matches.append(name)
    choices = [{"name": name.title(), "value": name} for name in list(set(matches))[:25]]
    await ctx.send(choices=choices)

@slash_command("addbuild", description="Add a build from nw-buddy.de with a name and optional key perks.")
@slash_option("link", "The nw-buddy.de build link", opt_type=OptionType.STRING, required=True)
@slash_option("name", "A name for this build", opt_type=OptionType.STRING, required=True)
@slash_option("keyperks", "Comma-separated list of key perks (optional, paste from Perk stacks)", opt_type=OptionType.STRING, required=False)
async def addbuild(ctx, link: str, name: str, keyperks: str = None):
    if not re.match(r"^https://(www\.)?nw-buddy.de/gearsets/", link):
        await ctx.send("Please provide a valid nw-buddy.de gearset link.", ephemeral=True)
        return
    perks_list = [p.strip() for p in keyperks.split(',') if p.strip()] if keyperks else []
    # Simplified perk fetching for now, as original was complex and might fail silently
    # Consider adding a note if perks couldn't be auto-fetched.

    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f: builds = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): builds = []
    builds.append({"name": name, "link": link, "keyperks": perks_list})
    with open(BUILDS_FILE, 'w', encoding='utf-8') as f: json.dump(builds, f, indent=2)
    await ctx.send(f"Build '{name}' added!", ephemeral=True)

@slash_command("builds", description="Show a list of saved builds.")
async def builds(ctx):
    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f: build_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): build_list = []
    if not build_list: await ctx.send("No builds saved yet.", ephemeral=True); return

    embed = Embed(title="Saved Builds", color=0x3498db)
    for build in build_list:
        perks_str = ', '.join(build.get('keyperks', [])) or '-'
        embed.add_field(name=build['name'], value=f"[Link]({build['link']})\nKey Perks: {perks_str}", inline=False)
    await ctx.send(embeds=embed)

@slash_command("removebuild", description="Remove a saved build (requires 'Manage Server' permission).", default_member_permissions=Permissions.MANAGE_GUILD)
@slash_option("name", "The name of the build to remove", opt_type=OptionType.STRING, required=True, autocomplete=True)
async def removebuild(ctx, name: str):
    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f: build_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): await ctx.send("No builds file found.", ephemeral=True); return

    original_length = len(build_list)
    builds_filtered = [b for b in build_list if b.get("name", "").lower() != name.lower()]
    if len(builds_filtered) == original_length: await ctx.send(f"Build '{name}' not found.", ephemeral=True); return

    with open(BUILDS_FILE, 'w', encoding='utf-8') as f: json.dump(builds_filtered, f, indent=2)
    await ctx.send(f"Build '{name}' removed successfully.", ephemeral=True)

@removebuild.autocomplete("name")
async def removebuild_autocomplete(ctx):
    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f: builds_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): await ctx.send(choices=[]); return
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    matches = [b.get("name") for b in builds_data if b.get("name") and search_term in b.get("name", "").lower()]
    choices = [{"name": bn, "value": bn} for bn in list(set(matches))[:25]]
    await ctx.send(choices=choices)

@slash_command("perk", description="Look up information about a specific New World perk.")
@slash_option("perk_name", "The name of the perk to look up", opt_type=OptionType.STRING, required=True, autocomplete=True)
async def perk_command(ctx, perk_name: str):
    all_perks_data = perks_module.load_perks_from_csv()
    if not all_perks_data: await ctx.send("Could not load perk data.", ephemeral=True); return

    perk_name_lower = perk_name.lower()
    # Find the perk by matching against the original name or a lowercased key
    found_perk_info = None
    for key, p_info in all_perks_data.items():
        if p_info.get('name', '').lower() == perk_name_lower or key == perk_name_lower:
            found_perk_info = p_info
            break
    if not found_perk_info:
        # Fallback: if user entered a display name, try to find its key
        for key, p_info in all_perks_data.items():
             if perk_name.lower() == p_info.get('name','').lower():
                 found_perk_info = p_info
                 perk_name = p_info.get('name', perk_name) # Use the display name
                 break
    if not found_perk_info:
        await ctx.send(f"Perk '{perk_name}' not found.", ephemeral=True); return

    def get_any_perk(data, keys, default): # Adjusted for perk data structure
        for k_csv in keys:
            for actual_key in data.keys():
                if actual_key.lower() == k_csv.lower() and data[actual_key]: return data[actual_key]
        return default

    name_val = get_any_perk(found_perk_info, ['name', 'perkname'], perk_name)
    desc_val = get_any_perk(found_perk_info, ['description', 'desc'], 'No description available.')
    type_val = get_any_perk(found_perk_info, ['type', 'perktype', 'category'], 'Unknown Type')
    icon_val = get_any_perk(found_perk_info, ['icon_url', 'icon'], None)
    id_val = get_any_perk(found_perk_info, ['id', 'perkid'], None)

    embed = Embed(title=name_val, color=0x1ABC9C)
    if icon_val: embed.set_thumbnail(url=icon_val)
    embed.add_field(name="Description", value=scale_value_with_gs(desc_val), inline=False) # Apply scaling
    embed.add_field(name="Type", value=type_val, inline=True)
    if id_val: embed.add_field(name="NWDB Link", value=f"[View on NWDB](https://nwdb.info/db/perk/{id_val})", inline=True)
    else: embed.add_field(name="ID", value="Not available", inline=True)
    embed.set_footer(text="Perk information from local data. Values may scale with Gear Score in-game.")
    await ctx.send(embeds=embed)

@perk_command.autocomplete("perk_name")
async def perk_autocomplete(ctx):
    all_perks_data = perks_module.load_perks_from_csv()
    if not all_perks_data: await ctx.send(choices=[]); return
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    matches = []
    for perk_data_dict in all_perks_data.values(): # Iterate through dict values
        display_name = perk_data_dict.get('name', perk_data_dict.get('Name', 'Unknown Perk'))
        if search_term in display_name.lower():
            matches.append({"name": display_name, "value": display_name})
    unique_matches = [dict(t) for t in {tuple(d.items()) for d in matches}] # Ensure unique dicts
    await ctx.send(choices=unique_matches[:25])