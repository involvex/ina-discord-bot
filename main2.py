import platform # For OS detection
import unicodedata
import re
import items
import perks
# import items # No longer needed for direct data loading
# import perks # No longer needed for direct data loading
from interactions import Client, slash_command, slash_option, OptionType, Permissions, Embed, Activity, ActivityType, User, SlashContext, File, Member, ChannelType, Message, Role
from interactions.models.discord.channel import GuildText # For specific channel type checking
from typing import Optional
Unchanged linesDB_NAME = "new_world_data.db" # Path to your SQLite DB

def get_db_connection():
    # Check if DB exists, if not, try to create it by calling populate_db()
    # This is a simplified check; you might want more robust logic
    if not os.path.exists(DB_NAME):
        print(f"Database {DB_NAME} not found. Please run create_db.py first or integrate its logic.")
        logging.critical(f"CRITICAL: Database '{DB_NAME}' not found. The bot cannot function without it. Please run 'create_db.py' to generate the database.")
        # You could attempt to run the population logic here if appropriate
        # from create_db import populate_db
        # populate_db() # This might be too slow/memory intensive for startup

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # To access columns by name
    return conn

async def find_item_in_db(item_name_query: str):
    # Ensure DB exists before trying to connect
async def find_item_in_db(item_name_query: str, exact_match: bool = False):
    if not os.path.exists(DB_NAME):
        return None # Or an error message
        logging.error(f"find_item_in_db: Database {DB_NAME} not found.")
        return [] 

    conn = get_db_connection()
    results = []
    try:
        cursor = conn.cursor()
        # Adjust table and column names based on your CSV and create_db.py script
        # Example: Searching for an item by name in the 'items' table
        # Ensure the column name 'name' matches what's in your CSV/DB
        cursor.execute("SELECT * FROM items WHERE name LIKE ?", ('%' + item_name_query + '%',))
        # Column names are sanitized by create_db.py (e.g., 'Item Name' -> 'Item_Name').
        # We assume the primary human-readable name column is 'Name' after sanitization or was 'Name' in CSV.
        # If your CSV's main name column is different (e.g., "ItemName"), adjust "Name" below.
        # create_db.py does: col.replace(' ', '_')...
        # So if CSV had "Item Name", it becomes "Item_Name". If "Name", it's "Name".
        # We will use 'Name' as the primary lookup column.
        if exact_match:
             cursor.execute("SELECT * FROM items WHERE Name = ?", (item_name_query,))
        else:
             cursor.execute("SELECT * FROM items WHERE Name LIKE ?", ('%' + item_name_query + '%',))
        items = cursor.fetchall()
        results = [dict(row) for row in items]
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        # Handle specific errors, e.g., table not found if DB isn't populated
        logging.error(f"SQLite error in find_item_in_db: {e}")
        if "no such table" in str(e):
             print(f"Table not found. The database '{DB_NAME}' might be empty or not correctly populated.")
        return None # Indicate error or no data
             logging.error(f"Table 'items' not found in {DB_NAME}. Database might be empty or not correctly populated.")
        return [] 
    finally:
        if conn:
            conn.close()
    return results

# Your command would then call find_item_in_db(item_name)
async def find_perk_in_db(perk_name_query: str, exact_match: bool = False):
    if not os.path.exists(DB_NAME):
        logging.error(f"find_perk_in_db: Database {DB_NAME} not found.")
        return []
    conn = get_db_connection()
    results = []
    try:
        cursor = conn.cursor()
        # Assuming the main perk name column in perks.csv becomes 'Name' after sanitization by create_db.py.
        # Adjust 'Name' if your perk name column is different (e.g., "PerkName").
        if exact_match:
            cursor.execute("SELECT * FROM perks WHERE Name = ?", (perk_name_query,))
        else:
            cursor.execute("SELECT * FROM perks WHERE Name LIKE ?", ('%' + perk_name_query + '%',))
        perks_data = cursor.fetchall()
        results = [dict(row) for row in perks_data]
    except sqlite3.Error as e:
        logging.error(f"SQLite error in find_perk_in_db: {e}")
        if "no such table" in str(e):
            logging.error(f"Table 'perks' not found in {DB_NAME}. Database might be empty or not correctly populated.")
        return []
    finally:
        if conn:
            conn.close()
    return results


# Load environment variables from .env file
Unchanged lines]

# --- Global Data Stores ---
ITEM_DATA = {}
ALL_PERKS_DATA = {}
ITEM_ID_TO_NAME_MAP = {} # For mapping Item IDs to Names
# ITEM_DATA = {} # Replaced by SQLite DB
# ALL_PERKS_DATA = {} # Replaced by SQLite DB
# ITEM_ID_TO_NAME_MAP = {} # Replaced by SQLite DB queries or direct recipe data

# --- Master Settings Helper Functions ---
def load_master_settings():
Unchanged lines@slash_option("item_name", "The name of the item to look up", opt_type=OptionType.STRING, required=True, autocomplete=True)
async def nwdb(ctx, item_name: str):
    await ctx.defer() # Defer the response immediately
    # Load items from CSV
    # item_data = items.load_items_from_csv('items.csv') # No longer load here
    if not ITEM_DATA:
        await ctx.send("Item data is not loaded. Please try again later or contact an admin.", ephemeral=True)
        return
    item_name_lower = item_name.lower()
    if item_name_lower not in ITEM_DATA:

    item_results = await find_item_in_db(item_name, exact_match=True) # Autocomplete should give an exact name

    if not item_results:
        # Fallback to a LIKE search if exact match (from potential direct input) fails
        item_results = await find_item_in_db(item_name, exact_match=False)
        if not item_results:
            await ctx.send(f"Item '{item_name}' not found in the database.", ephemeral=True)
            return
    
    item = item_results[0] # Take the first match

    def get_any(item_dict, keys, default):
        for k_csv_original in keys:
            # Sanitize k_csv_original the same way create_db.py does for column names
            k_db = k_csv_original.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'percent')
            if k_db in item_dict and item_dict[k_db] is not None:
                return item_dict[k_db]
        return default

    name = get_any(item, ['Name', 'name'], item_name) # 'Name' is likely the sanitized column
    item_id_for_url = get_any(item, ['Item ID', 'ItemID'], None) # Becomes 'Item_ID' or 'ItemID'
    description = get_any(item, ['Description', 'description', 'Flavor Text'], 'No description available.') # 'Flavor_Text'
    rarity = get_any(item, ['Rarity', 'rarity'], 'Unknown')
    tier = get_any(item, ['Tier', 'tier'], 'Unknown')
    icon_url = get_any(item, ['Icon', 'icon', 'Icon Path'], None) # 'Icon_Path'
    
    # Build a NWDB-style embed
    embed = Embed()
    embed.title = name
    if item_id_for_url:
        # Ensure item_id_for_url is stripped of any potential non-URL safe characters if necessary,
        # though typically Item IDs are safe.
        embed.url = f"https://nwdb.info/db/item/{str(item_id_for_url).strip()}"
    else:
        logging.warning(f"Could not find Item ID for '{name}' to create NWDB link.")

    embed.color = 0x9b59b6 if str(rarity).lower() == 'artifact' else 0x7289da # Ensure rarity is string for .lower()
    if icon_url:
        embed.set_thumbnail(url=str(icon_url).strip()) # Ensure URL is string and stripped
    embed.add_field(name="Rarity", value=str(rarity), inline=True)
    embed.add_field(name="Tier", value=str(tier), inline=True)
    if description and not str(description).startswith('Artifact_'):
        embed.add_field(name="Description", value=str(description), inline=False)
    
    gear_score = get_any(item, ['Gear Score', 'gear_score', 'GS'], None) # Becomes 'Gear_Score'
    if gear_score:
        embed.add_field(name="Gear Score", value=str(gear_score), inline=True)
    
    # Perks (if present) - Assuming 'Perks' column contains comma-separated perk IDs/names
    perks_raw = get_any(item, ['Perks', 'perks'], None)
    PERK_PRETTY = { # This map might need to be more dynamic or comprehensive
        'PerkID_Artifact_Set1_HeavyChest': ("Artifact Set: Heavy Chest", "🟣"),
        'PerkID_Gem_EmptyGemSlot': ("Empty Gem Slot", "💠"),
        # ... more perk mappings
    }
    if perks_raw:
        perk_lines = []
        for perk_entry in str(perks_raw).split(","): # Ensure perks_raw is string
            perk_entry = perk_entry.strip()
            if not perk_entry:
                continue
            # Here, perk_entry might be a PerkID. You might need to look up its display name from the 'perks' table
            # For simplicity, using PERK_PRETTY or just the ID if not found.
            pretty_name, icon = PERK_PRETTY.get(perk_entry, (perk_entry, '•'))
            perk_lines.append(f"{icon} {pretty_name}")
        if perk_lines:
            embed.add_field(name="Perks", value="\n".join(perk_lines), inline=False)

    # Check if item is craftable by querying the recipes table
    conn_check = get_db_connection()
    is_craftable = False
    try:
        cursor_check = conn_check.cursor()
        # Use LIKE for item_name as recipe names might have slight variations or casing differences
        # Ensure 'output_item_name' is the correct column in your 'recipes' table
        cursor_check.execute("SELECT 1 FROM recipes WHERE output_item_name LIKE ?", (f'%{name}%',))
        if cursor_check.fetchone():
            is_craftable = True
    except sqlite3.Error as e:
        logging.warning(f"Could not check if item {name} is craftable due to DB error: {e}")
    finally:
        if conn_check:
            conn_check.close()

    if is_craftable:
        # Using f-string for item_name to ensure it's correctly part of the command example
        embed.set_footer(text=f"Type /calculate_craft item_name:\"{name}\" to calculate resources!")
    await ctx.send(embeds=embed)


@nwdb.autocomplete("item_name")
async def nwdb_autocomplete(ctx: SlashContext): # Added type hint for ctx
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    if not search_term: # If search term is empty, send no choices
        await ctx.send(choices=[])
        return

    conn = get_db_connection()
    choices = []
    try:
        cursor = conn.cursor()
        # Query the 'Name' column from the 'items' table. Adjust if your column name differs.
        # create_db.py sanitizes column names, so 'Name' should be correct if original was 'Name' or 'name'.
        cursor.execute("SELECT Name FROM items WHERE lower(Name) LIKE ? LIMIT 25", ('%' + search_term + '%',))
        matches = cursor.fetchall()
        # The value sent to the command should be the exact item name for easier lookup
        choices = [{"name": row["Name"], "value": row["Name"]} for row in matches]
    except sqlite3.Error as e:
        logging.error(f"SQLite error in nwdb_autocomplete: {e}")
    finally:
        if conn:
            conn.close()
    await ctx.send(choices=choices)

@slash_command(name="calculate_craft", description="Calculate all resources needed to craft an item, including intermediates.")
@slash_option("item_name", "The name of the item to craft", opt_type=OptionType.STRING, required=True, autocomplete=True)
@slash_option("amount", "How many to craft", opt_type=OptionType.INTEGER, required=False)
async def calculate_craft(ctx, item_name: str, amount: int = 1):
    await ctx.defer() 
    # IMPORTANT: get_recipe and calculate_crafting_materials in recipes.py
    # MUST be adapted to query the SQLite database instead of using in-memory dicts.
    # The following calls assume recipes.py has been updated.
    
    # Assuming get_recipe is adapted to use the database and returns a dict or None
    recipe_details = get_recipe(item_name) # This function needs to query DB_NAME

    if not recipe_details:
        await ctx.send(f"Item '{item_name}' not found in the database.", ephemeral=True)
        return
    item = ITEM_DATA[item_name_lower]
    def get_any(item, keys, default):
        for k in keys:
            if k in item and item[k]:
                return item[k]
        return default
    name = get_any(item, ['name', 'Name', 'Item Name'], item_name)
    item_id_for_url = get_any(item, ['Item ID', 'item_id'], None)

    description = get_any(item, ['description', 'Description', 'Flavor Text'], 'No description available.')
    rarity = get_any(item, ['rarity', 'Rarity'], 'Unknown')
    tier = get_any(item, ['tier', 'Tier'], 'Unknown')
    icon_url = get_any(item, ['icon', 'Icon', 'Icon Path', 'icon_url'], None)
    
    # Build a NWDB-style embed
    embed = Embed()
    embed.title = name
    if item_id_for_url:
        embed.url = f"https://nwdb.info/db/item/{item_id_for_url}"
    else:
        logging.warning(f"Could not find Item ID for '{name}' to create NWDB link.")

    embed.color = 0x9b59b6 if rarity.lower() == 'artifact' else 0x7289da
    if icon_url:
        embed.set_thumbnail(url=icon_url)
    embed.add_field(name="Rarity", value=rarity, inline=True)
    embed.add_field(name="Tier", value=tier, inline=True)
    if description and not description.startswith('Artifact_'):
        embed.add_field(name="Description", value=description, inline=False)
    # Add more NWDB-style fields if available
    # Example: Gear Score, Perks, etc.
    gear_score = get_any(item, ['gear_score', 'Gear Score', 'GS'], None)
    if gear_score:
        embed.add_field(name="Gear Score", value=str(gear_score), inline=True)
    # Perks (if present)
    perks = get_any(item, ['perks', 'Perks'], None)
    # Perk pretty names and icons mapping (expand as needed)
    PERK_PRETTY = {
        'PerkID_Artifact_Set1_HeavyChest': ("Artifact Set: Heavy Chest", "🟣"),
        'PerkID_Gem_EmptyGemSlot': ("Empty Gem Slot", "💠"),
        'PerkID_Armor_DefBasic': ("Basic Defense", "🛡️"),
        'PerkID_Armor_RangeDefense_Physical': ("Ranged Physical Defense", "🏹"),
        # Add more known perks here...
    }
    if perks:
        perk_lines = []
        for perk in str(perks).split(","):
            perk = perk.strip()
            if not perk:
                continue
            pretty, icon = PERK_PRETTY.get(perk, (perk, '•'))
            perk_lines.append(f"{icon} {pretty}")
        if perk_lines:
            embed.add_field(name="Perks", value="\n".join(perk_lines), inline=False)
    # If item is craftable, mention calculate_craft
    if get_recipe(item_name, ITEM_DATA, ITEM_ID_TO_NAME_MAP):
        embed.set_footer(text=f"Type /calculate_craft item_name:{item_name} amount:4 to calculate resources!")
    await ctx.send(embeds=embed)


@nwdb.autocomplete("item_name")
async def nwdb_autocomplete(ctx):
    # Provide autocomplete suggestions from items.csv
    if not ITEM_DATA:
        await ctx.send(choices=[])
        return

    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""

    if not search_term: # If search term is empty, send no choices or a placeholder
        await ctx.send(choices=[])
        # Or, send a placeholder:
        # await ctx.send(choices=[{"name": "Type an item name to search...", "value": "_placeholder_"}])
        return

    # Optimization: If search term is very short, it might still be too many matches.
    # For example, limit search if term is less than 2 or 3 characters.
    # For now, we'll proceed with the search but this is an area for further optimization if needed.

    matches_keys = []
    # ITEM_DATA.keys() are already lowercase
    for item_key_lower in ITEM_DATA.keys():
        if search_term in item_key_lower:
            matches_keys.append(item_key_lower)
            if len(matches_keys) >= 25: # Limit to 25 matches early
                break

    choices = []
    for match_key_lower in matches_keys: # Iterate only up to 25 found matches
        # Assuming item_data[match_key] is a dict containing item details
        # and has a field like 'Name' or 'name' for the display name.
        # Fallback to title-cased key if specific name field isn't found.
        item_details = ITEM_DATA.get(match_key_lower, {})
        # Use the 'name' field from the loaded item_data which should have original casing
        display_name = item_details.get('Name', item_details.get('name', match_key_lower.title()))
        choices.append({"name": display_name, "value": match_key_lower}) # Send the key (lowercase) as value

    # Discord allows max 25 choices
    await ctx.send(choices=choices)

@slash_command(name="calculate_craft", description="Calculate all resources needed to craft an item, including intermediates.")
@slash_option("item_name", "The name of the item to craft", opt_type=OptionType.STRING, required=True, autocomplete=True)
@slash_option("amount", "How many to craft", opt_type=OptionType.INTEGER, required=False)
async def calculate_craft(ctx, item_name: str, amount: int = 1):
    await ctx.defer() # Defer response
    recipe = get_recipe(item_name, ITEM_DATA, ITEM_ID_TO_NAME_MAP)
    if not recipe:
        await ctx.send(f"No recipe found for '{item_name}'.", ephemeral=True)
        return
    
    # Show all resources, including intermediates
    all_materials = calculate_crafting_materials(item_name, ITEM_DATA, ITEM_ID_TO_NAME_MAP, amount or 1, include_intermediate=True)
    # This function also needs to be adapted in recipes.py to use the DB
    all_materials = calculate_crafting_materials(item_name, amount or 1, include_intermediate=True)
    if not all_materials:
        await ctx.send(f"Could not calculate materials for '{item_name}'.", ephemeral=True)
        return
Unchanged lines

@calculate_craft.autocomplete("item_name")
async def calculate_craft_autocomplete(ctx):
async def calculate_craft_autocomplete(ctx: SlashContext): # Added type hint
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""

    if not search_term:
        await ctx.send(choices=[])
        return

    conn = get_db_connection()
    matches = []
    # RECIPES keys are already lowercase if defined consistently
    for recipe_key_lower in RECIPES.keys():
        if search_term in recipe_key_lower:
            matches.append(recipe_key_lower)
            if len(matches) >= 25:
                break
    
    choices = [{"name": name.title(), "value": name} for name in matches]
    try:
        cursor = conn.cursor()
        # Query 'output_item_name' from the 'recipes' table. This column is defined in create_db.py.
        cursor.execute("SELECT output_item_name FROM recipes WHERE lower(output_item_name) LIKE ? LIMIT 25", ('%' + search_term + '%',))
        db_matches = cursor.fetchall()
        # Ensure output_item_name is correctly cased for display and as the value.
        matches = [row["output_item_name"] for row in db_matches]
    except sqlite3.Error as e:
        logging.error(f"SQLite error in calculate_craft_autocomplete: {e}")
    finally:
        if conn:
            conn.close()
    choices = [{"name": name, "value": name} for name in matches]
    await ctx.send(choices=choices)


@slash_command(name="recipe", description="Show the full recipe breakdown for a craftable item and track it.")
@slash_option("item_name", "The name of the item to show the recipe for", opt_type=OptionType.STRING, required=True, autocomplete=True)
async def recipe(ctx, item_name: str):
    await ctx.defer() # Defer response

    from recipes import get_recipe, fetch_recipe_from_nwdb, track_recipe
    recipe = get_recipe(item_name, ITEM_DATA, ITEM_ID_TO_NAME_MAP)
    if not recipe:
        # Try to fetch from nwdb.info
        recipe = fetch_recipe_from_nwdb(item_name)
        if not recipe:
    await ctx.defer() 

    # from recipes import get_recipe, fetch_recipe_from_nwdb, track_recipe # Keep for track_recipe if used
    # track_recipe might need adaptation if it relies on the old global data structures.
    from recipes import track_recipe # Assuming track_recipe is adapted or its usage is reviewed

    conn = get_db_connection()
    recipe_json_str = None
    try:
        cursor = conn.cursor()
        # Fetch the 'raw_recipe_data' which stores the full recipe JSON.
        # Use LIKE for item_name to be more flexible with user input.
        cursor.execute("SELECT raw_recipe_data FROM recipes WHERE output_item_name LIKE ?", (f'%{item_name}%',))
        row = cursor.fetchone()
        if row:
            recipe_json_str = row["raw_recipe_data"]
    except sqlite3.Error as e:
        logging.error(f"SQLite error fetching recipe for '{item_name}': {e}")
    finally:
        if conn:
            conn.close()

    if not recipe_json_str:
        # Optionally, you could still call fetch_recipe_from_nwdb here as a fallback
        # from recipes import fetch_recipe_from_nwdb
        # recipe_dict = fetch_recipe_from_nwdb(item_name) # This would need to be async or run in executor
        # if not recipe_dict:
        await ctx.send(f"No recipe found for '{item_name}' in the local database.", ephemeral=True)
        return
        # else:
        #     await ctx.send(f"Recipe for '{item_name}' fetched from nwdb.info (external).") # If fetched

    try:
        recipe_dict = json.loads(recipe_json_str)
    except json.JSONDecodeError:
        logging.error(f"Failed to parse recipe JSON for '{item_name}' from database.")
        await ctx.send(f"Error retrieving recipe details for '{item_name}'.", ephemeral=True)
        return

    # Track the recipe for the user - ensure track_recipe is adapted for DB if it writes data
    user_id = str(ctx.author.id)
    track_recipe(user_id, item_name, recipe_dict) # Review track_recipe for DB compatibility

    embed = Embed()
    # Use .get() with a fallback to item_name for title, and .title() for consistent casing
    embed.title = f"Recipe: {recipe_dict.get('output_item_name', item_name).title()}"
    embed.color = 0x9b59b6 # Purple
    embed.add_field(name="Station", value=str(recipe_dict.get("station", "-")), inline=True)
    embed.add_field(name="Skill", value=str(recipe_dict.get('skill', "-")) , inline=True)
    embed.add_field(name="Skill Level", value=str(recipe_dict.get("skill_level", "-")), inline=True)
    embed.add_field(name="Tier", value=str(recipe_dict.get("tier", "-")), inline=True)
    
    ing_lines = []
    for ing in recipe_dict.get("ingredients", []):
        # Ensure quantity and item name are present and stringified
        ing_lines.append(f"• {ing.get('quantity', '?')} {str(ing.get('item', 'Unknown Ingredient'))}")
    embed.add_field(name="Ingredients", value="\n".join(ing_lines) if ing_lines else "-", inline=False)

    # Add NWDB link for the crafted item by looking up its Item ID from the 'items' table
    # The output_item_name from the recipe should match an item in the 'items' table.
    crafted_item_name = recipe_dict.get('output_item_name', item_name)
    item_details_for_recipe = await find_item_in_db(crafted_item_name, exact_match=True)
    if item_details_for_recipe:
        # find_item_in_db returns a list, take the first element.
        # Column name 'Item_ID' is based on create_db.py sanitizing 'Item ID'.
        item_id_for_url = item_details_for_recipe[0].get('Item_ID') 
        if item_id_for_url:
            embed.add_field(name="NWDB Link (Crafted Item)", value=f"[View on NWDB](https://nwdb.info/db/item/{str(item_id_for_url).strip()})", inline=False)

    await ctx.send(embeds=embed)


@recipe.autocomplete("item_name")
async def recipe_autocomplete(ctx: SlashContext): # Added type hint
    # This can reuse the logic from calculate_craft_autocomplete as both search craftable items
    await calculate_craft_autocomplete(ctx)

# --- Build Management Commands ---
@slash_command(name="build", description="Manage saved New World builds.")
async def build_group(ctx: SlashContext):
    """Base command for build management."""
    pass

@build_group.subcommand(sub_cmd_name="add", sub_cmd_description="Add a build from nw-buddy.de.")
@slash_option("link", "The nw-buddy.de build link", opt_type=OptionType.STRING, required=True)
@slash_option("name", "A name for this build", opt_type=OptionType.STRING, required=True)
@slash_option("keyperks", "Comma-separated list of key perks (optional, paste from Perk stacks)", opt_type=OptionType.STRING, required=False)
async def build_add(ctx: SlashContext, link: str, name: str, keyperks: str = None):
    import requests # Keep local import if only used here
    from bs4 import BeautifulSoup # Keep local import
    import re # Keep local import
    # Validate link
    if not re.match(r"^https://(www\.)?nw-buddy.de/gearsets/", link):
        await ctx.send("Please provide a valid nw-buddy.de gearset link.", ephemeral=True)
        return
    perks_list = []
    if keyperks:
        perks_list = [p.strip() for p in keyperks.split(',') if p.strip()]
    else:
        try:
            resp = requests.get(link, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                perk_header = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4'] and 'perk stacks' in tag.get_text(strip=True).lower())
                if perk_header:
                    next_elem = perk_header.find_next(['ul', 'div'])
                    if next_elem:
                        for li in next_elem.find_all(['li', 'div'], recursive=False): # recursive=False to get direct children
                            text = li.get_text(strip=True)
                            if text:
                                perks_list.append(text)
        except requests.RequestException as e_req: # More specific exception
            logging.warning(f"Could not fetch perks from nw-buddy for build '{name}': {e_req}")
        except Exception as e_parse: # Catch other parsing errors
            logging.warning(f"Error parsing perks from nw-buddy for build '{name}': {e_parse}")
            
    # Save build (BUILDS_FILE is still JSON, not part of SQLite DB for items/perks)
    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
            builds = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): # More specific exceptions
        builds = [] 
    builds.append({"name": name, "link": link, "keyperks": perks_list, "submitted_by": str(ctx.author.id)}) # Ensure ID is string
    with open(BUILDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(builds, f, indent=2)
    await ctx.send(f"Build '{name}' added!", ephemeral=True)


@build_group.subcommand(sub_cmd_name="list", sub_cmd_description="Show a list of saved builds.")
async def build_list(ctx: SlashContext):
    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
            builds = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        await ctx.send("No builds saved yet or build file is corrupted.", ephemeral=True)
        return
    if not builds:
        await ctx.send("No builds saved yet.", ephemeral=True)
        return
    embed = Embed(title="Saved Builds", color=0x3498db)
    for build_item in builds: # Renamed to avoid conflict with 'build' module/group
        submitter_id = build_item.get('submitted_by')
        submitter_mention = f"<@{submitter_id}>" if submitter_id else "Unknown User"
        try:
            if submitter_id:
                user = await bot.fetch_user(int(submitter_id)) # Ensure ID is int for fetch_user
                submitter_mention = user.mention if user else f"User ID: {submitter_id}"
        except Exception as e_fetch: 
            logging.warning(f"Could not fetch user {submitter_id} for build list: {e_fetch}")
            submitter_mention = f"User ID: {submitter_id}"
        
        perks_display = ', '.join(build_item.get('keyperks', [])) or '-'
        embed.add_field(name=build_item['name'], value=f"[Link]({build_item['link']})\nKey Perks: {perks_display}\nSubmitted by: {submitter_mention}", inline=False)
    await ctx.send(embeds=embed)


@build_group.subcommand(
    sub_cmd_name="remove",
    sub_cmd_description="Remove a saved build (requires 'Manage Server' permission)."
)
@slash_option(
    "name",
    description="The name of the build to remove",
    opt_type=OptionType.STRING,
    required=True,
    autocomplete=True
)
async def build_remove(ctx: SlashContext, name: str):
    if not ctx.author.has_permission(Permissions.MANAGE_GUILD) and not is_bot_manager(int(ctx.author.id)):
        await ctx.send("You need 'Manage Server' permission or be a Bot Manager to use this command.", ephemeral=True)
        return

    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
            builds = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        await ctx.send("No builds saved yet or build file is corrupted.", ephemeral=True)
        return

    original_length = len(builds)
    builds_filtered = [b for b in builds if b.get("name", "").lower() != name.lower()]

    if len(builds_filtered) == original_length:
        await ctx.send(f"Build '{name}' not found.", ephemeral=True)
        return

    try:
        with open(BUILDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(builds_filtered, f, indent=2)
        await ctx.send(f"Build '{name}' removed successfully.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error writing builds file after removing build: {e}")
        await ctx.send("An error occurred while trying to remove the build.", ephemeral=True)

@build_remove.autocomplete("name")
async def build_remove_autocomplete(ctx: SlashContext):
    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
            builds_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): 
        await ctx.send(choices=[])
        return 
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    matches = [build_item.get("name") for build_item in builds_data if build_item.get("name") and search_term in build_item.get("name", "").lower()]
    # Use set for unique names, then convert back to list for slicing
    unique_names = list(set(matches))
    choices = [{"name": build_name, "value": build_name} for build_name in unique_names[:25]] 
    await ctx.send(choices=choices)


@slash_command(name="perk", description="Look up information about a specific New World perk.")
@slash_option(
    "perk_name",
    description="The name of the perk to look up",
    opt_type=OptionType.STRING,
    required=True,
    autocomplete=True
)
async def perk_command(ctx, perk_name: str):
    await ctx.defer() # Defer as DB query might take a moment

    perk_results = await find_perk_in_db(perk_name, exact_match=True) 

    if not perk_results:
        perk_results = await find_perk_in_db(perk_name, exact_match=False) # Fallback for direct input
        if not perk_results:
            await ctx.send(f"No recipe found for '{item_name}'.", ephemeral=True)
            return
        else:
            await ctx.send(f"Recipe for '{item_name}' fetched from nwdb.info.")
    # Track the recipe for the user
    user_id = str(ctx.author.id)
    track_recipe(user_id, item_name, recipe)
    embed = Embed()
    embed.title = f"Recipe: {item_name.title()}"
    embed.color = 0x9b59b6
    embed.add_field(name="Station", value=recipe.get("station", "-"), inline=True)
    embed.add_field(name="Skill", value=f"{recipe.get('skill', '-')}" , inline=True)
    embed.add_field(name="Skill Level", value=str(recipe.get("skill_level", "-")), inline=True)
    embed.add_field(name="Tier", value=str(recipe.get("tier", "-")), inline=True)
    # Ingredients breakdown
    ing_lines = []
    for ing in recipe.get("ingredients", []):
        ing_lines.append(f"• {ing['quantity']} {ing['item']}")
    
    # Add NWDB link for the crafted item
    item_details_for_recipe = ITEM_DATA.get(item_name.lower())
    if item_details_for_recipe:
        item_id_for_url = item_details_for_recipe.get('Item ID')
        if item_id_for_url:
            embed.add_field(name="NWDB Link", value=f"[View on NWDB](https://nwdb.info/db/item/{item_id_for_url})", inline=False)

    embed.add_field(name="Ingredients", value="\n".join(ing_lines) or "-", inline=False)
    await ctx.send(embeds=embed)


@recipe.autocomplete("item_name")
async def recipe_autocomplete(ctx):
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""

    if not ITEM_DATA:
        await ctx.send(choices=[])
        return
    
    if not search_term:
        await ctx.send(choices=[])
        return

    matches_keys = []
    for item_key_lower in ITEM_DATA.keys(): # ITEM_DATA keys are already lowercase
        # We also want to check if the item is in RECIPES, as /recipe is for craftable items
        if search_term in item_key_lower and (item_key_lower in RECIPES or get_recipe(item_key_lower, ITEM_DATA, ITEM_ID_TO_NAME_MAP)): # Check if a recipe exists
            matches_keys.append(item_key_lower)
            if len(matches_keys) >= 25:
                break

    choices = []
    for match_key_lower in matches_keys:
        item_details = ITEM_DATA.get(match_key_lower, {})
        display_name = item_details.get('Name', item_details.get('name', match_key_lower.title()))
        choices.append({"name": display_name, "value": match_key_lower})

    await ctx.send(choices=choices)

# --- Build Management Commands ---
@slash_command(name="build", description="Manage saved New World builds.")
async def build_group(ctx: SlashContext):
    """Base command for build management."""
    pass

@build_group.subcommand(sub_cmd_name="add", sub_cmd_description="Add a build from nw-buddy.de.")
@slash_option("link", "The nw-buddy.de build link", opt_type=OptionType.STRING, required=True)
@slash_option("name", "A name for this build", opt_type=OptionType.STRING, required=True)
@slash_option("keyperks", "Comma-separated list of key perks (optional, paste from Perk stacks)", opt_type=OptionType.STRING, required=False)
async def build_add(ctx: SlashContext, link: str, name: str, keyperks: str = None):
    import requests
    from bs4 import BeautifulSoup
    import re
    # Validate link
    if not re.match(r"^https://(www\.)?nw-buddy.de/gearsets/", link):
        await ctx.send("Please provide a valid nw-buddy.de gearset link.", ephemeral=True)
        return
    perks_list = []
    if keyperks:
        perks_list = [p.strip() for p in keyperks.split(',') if p.strip()]
    else:
        try:
            resp = requests.get(link, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Look for 'Perk stacks' section
                perk_header = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4'] and 'perk stacks' in tag.get_text(strip=True).lower())
                if perk_header:
                    # Find the next ul or div after the header
                    next_elem = perk_header.find_next(['ul', 'div'])
                    if next_elem:
                        for li in next_elem.find_all(['li', 'div'], recursive=False):
                            text = li.get_text(strip=True)
                            if text:
                                perks_list.append(text)
        except Exception:
            pass
    # Save build
    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
            builds = json.load(f)
    except Exception:
        builds = [] # Initialize as an empty list if file not found or error
    builds.append({"name": name, "link": link, "keyperks": perks_list, "submitted_by": ctx.author.id})
    with open(BUILDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(builds, f, indent=2)
    await ctx.send(f"Build '{name}' added!", ephemeral=True)


@build_group.subcommand(sub_cmd_name="list", sub_cmd_description="Show a list of saved builds.")
async def build_list(ctx: SlashContext):
    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
            builds = json.load(f)
    except Exception:
        await ctx.send("No builds saved yet.", ephemeral=True)
        return
    if not builds:
        await ctx.send("No builds saved yet.", ephemeral=True)
        return
    embed = Embed()
    embed.title = "Saved Builds"
    embed.color = 0x3498db
    for build in builds:
        submitter_id = build.get('submitted_by')
        submitter_mention = f"<@{submitter_id}>" if submitter_id else "Unknown User"
        try:
            if submitter_id:
                user = await bot.fetch_user(submitter_id)
                submitter_mention = user.mention if user else f"User ID: {submitter_id}"
        except Exception: # Handle cases where user might not be fetchable
            submitter_mention = f"User ID: {submitter_id}"
        perks = ', '.join(build.get('keyperks', [])) or '-'
        embed.add_field(name=build['name'], value=f"[Link]({build['link']})\nKey Perks: {perks}\nSubmitted by: {submitter_mention}", inline=False)
    await ctx.send(embeds=embed)


@build_group.subcommand(
    sub_cmd_name="remove",
    sub_cmd_description="Remove a saved build (requires 'Manage Server' permission)."
)
@slash_option(
    "name",
    description="The name of the build to remove",
    opt_type=OptionType.STRING,
    required=True,
    autocomplete=True
)
async def build_remove(ctx: SlashContext, name: str):
    # Check for 'Manage Server' permission or if the user is a bot manager/owner
    if not ctx.author.has_permission(Permissions.MANAGE_GUILD) and not is_bot_manager(int(ctx.author.id)):
        await ctx.send("You need 'Manage Server' permission or be a Bot Manager to use this command.", ephemeral=True)
        return

    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
            builds = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        await ctx.send("No builds saved yet or build file is corrupted.", ephemeral=True)
        return

    original_length = len(builds)
    # Find the build by name (case-insensitive)
    builds_filtered = [b for b in builds if b.get("name", "").lower() != name.lower()]

    if len(builds_filtered) == original_length:
        await ctx.send(f"Build '{name}' not found.", ephemeral=True)
        return

    try:
        with open(BUILDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(builds_filtered, f, indent=2)
        await ctx.send(f"Build '{name}' removed successfully.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error writing builds file after removing build: {e}")
        await ctx.send("An error occurred while trying to remove the build.", ephemeral=True)

@build_remove.autocomplete("name")
async def build_remove_autocomplete(ctx: SlashContext):
    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
            builds_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): # Handle empty or corrupt file
        await ctx.send(choices=[])
        return # Ensure return after sending empty choices
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    matches = [build.get("name") for build in builds_data if build.get("name") and search_term in build.get("name", "").lower()]
    choices = [{"name": build_name, "value": build_name} for build_name in list(set(matches))[:25]] # Use set for unique names
    await ctx.send(choices=choices)


@slash_command(name="perk", description="Look up information about a specific New World perk.")
@slash_option(
    "perk_name",
    description="The name of the perk to look up",
    opt_type=OptionType.STRING,
    required=True,
    autocomplete=True
)
async def perk_command(ctx, perk_name: str):
    # all_perks_data = perks.load_perks_from_csv() # No longer load here
    if not ALL_PERKS_DATA:
        await ctx.send("Perk data is not loaded. Please try again later or contact an admin.", ephemeral=True)
        return

    perk_name_lower = perk_name.lower()
    if perk_name_lower not in ALL_PERKS_DATA:
    
    perk_info = perk_results[0] # Take the first match

    def get_any_perk_info(data_dict, keys, default):
        for k_csv_original in keys:
            # Sanitize k_csv_original the same way create_db.py does for column names
            k_db = k_csv_original.replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'percent')
            if k_db in data_dict and data_dict[k_db] is not None:
                return data_dict[k_db]
        return default

    # Use sanitized key names based on create_db.py logic
    name = get_any_perk_info(perk_info, ['Name', 'PerkName'], perk_name) # 'Name' or 'PerkName'
    description = get_any_perk_info(perk_info, ['Description', 'Desc'], 'No description available.')
    perk_type = get_any_perk_info(perk_info, ['Type', 'PerkType', 'Category'], 'Unknown Type') # 'PerkType'
    icon_url = get_any_perk_info(perk_info, ['Icon', 'IconPath'], None) # 'IconPath'
    perk_id = get_any_perk_info(perk_info, ['PerkID', 'ID'], None) # 'PerkID'

    embed = Embed(title=str(name), color=0x1ABC9C) # Teal
    if icon_url:
        embed.set_thumbnail(url=str(icon_url).strip())

    # Scale description if applicable (ensure scale_value_with_gs is robust)
    scaled_description = scale_value_with_gs(str(description)) # Ensure description is string
    embed.add_field(name="Description", value=scaled_description, inline=False)
    embed.add_field(name="Type", value=str(perk_type), inline=True)

    if perk_id:
        embed.add_field(name="NWDB Link", value=f"[View on NWDB](https://nwdb.info/db/perk/{str(perk_id).strip()})", inline=True)
    else:
        # If PerkID is not directly available, you might try to construct a search link
        # For now, just indicate not available
        embed.add_field(name="NWDB Link", value="ID not available for direct link", inline=True)

    embed.set_footer(text="Perk information from database. Values may scale with Gear Score in-game.")
    await ctx.send(embeds=embed)

def _eval_perk_expression(expr_str: str, gs_multiplier_val: float) -> str:
    """
    Safely evaluates a perk expression string after substituting perkMultiplier.
    Example: expr_str = "2.4 * perkMultiplier", gs_multiplier_val = 1.45
    """
    try:
        # Replace perkMultiplier with its numeric value
        eval_str = expr_str.replace("perkMultiplier", str(gs_multiplier_val))

        # Define a safe environment for eval
        allowed_globals = {"__builtins__": {}} # No builtins needed for simple arithmetic
        # Allow basic math functions if your expressions use them, e.g. math.floor, math.ceil
        # For "2.4 * 1.45", no extra locals are needed.
        allowed_locals = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}

        result = eval(eval_str, allowed_globals, allowed_locals)

        if isinstance(result, float):
            if result.is_integer():
                return str(int(result))
            # Format to a reasonable number of decimal places, remove trailing zeros
            formatted_result = f"{result:.3f}".rstrip('0').rstrip('.')
            return formatted_result
        return str(result)
    except Exception as e:
        logging.warning(f"Could not evaluate perk expression '{expr_str}' with multiplier {gs_multiplier_val}: {e}")
        # Return the original expression part to indicate an issue or a placeholder error.
        return f"[EVAL_ERROR: {expr_str}]" # Or simply expr_str

def scale_value_with_gs(base_value: Optional[str], gear_score: int = 725) -> str:
    """
    Scales numeric values within a perk description string based on Gear Score.
    Replaces placeholders like ${expression * perkMultiplier} or ${value} with their calculated/literal values.
    """
    if not base_value or not isinstance(base_value, str) or '${' not in base_value:
        return str(base_value) if base_value is not None else ""

    base_gs = 500  # Assume base values for perkMultiplier are for GS 500
    # Ensure gear_score is int for division
    gs_multiplier = int(gear_score) / base_gs 

    def replace_match(match):
        expression_inside_braces = match.group(1) # Content within ${...}
        return _eval_perk_expression(expression_inside_braces, gs_multiplier)

    return re.sub(r'\$\{(.*?)\}', replace_match, base_value)

@perk_command.autocomplete("perk_name")
async def perk_autocomplete(ctx: SlashContext): # Added type hint
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    if not search_term:
        await ctx.send(choices=[])
        return

    conn = get_db_connection()
    choices = []
    try:
        cursor = conn.cursor()
        # Query the 'Name' column from the 'perks' table. Adjust if your column name differs.
        # This assumes create_db.py stores the main perk name under a column like 'Name'.
        cursor.execute("SELECT Name FROM perks WHERE lower(Name) LIKE ? LIMIT 25", ('%' + search_term + '%',))
        db_matches = cursor.fetchall()
        # The value sent to the command should be the exact perk name for easier lookup
        choices = [{"name": row["Name"], "value": row["Name"]} for row in db_matches]
    except sqlite3.Error as e:
        logging.error(f"SQLite error in perk_autocomplete: {e}")
    finally:
        if conn:
            conn.close()
    await ctx.send(choices=choices)


@slash_command(name="about", description="Show information about Ina's New World Bot.")
async def about_command(ctx):
    embed = Embed(
        title="About Ina's New World Bot",
        description="Your friendly companion for all things Aeternum!",
        color=0x7289DA  # Discord Blurple
    )
    embed.add_field(
        name="Version",
        value=f"`{__version__}`",
        inline=True
    )
    embed.add_field(
        name="Creator",
        value="This bot was lovingly crafted by <@157968227106947072>.", # Bot owner ID
        inline=True 
    )
    embed.add_field(
        name="Credits & Data Sources",
        value="• Item, perk, and recipe data primarily sourced from community efforts and game files, often cross-referenced with NWDB.info.\n"
              "• Build functionality integrates with NW-Buddy.de.",
        inline=False
    )
    embed.set_footer(text="Ina's New World Bot is a fan-made project and is not affiliated with Amazon Games or New World.")
    await ctx.send(embeds=embed)

async def _perform_update_and_restart(slash_ctx: Optional[SlashContext] = None):
    """
    Handles the bot update process: executes the update script and stops the bot for restart.
    If slash_ctx is provided, sends feedback to the command invoker.
    Returns True if update script succeeded and bot stop was initiated, False otherwise.
    """
    # Determine OS and script details
    current_os = platform.system().lower()
    script_name = ""
    executable = ""
    script_args = []

    if "windows" in current_os:
        script_name = "update_bot.ps1"
        executable = "powershell.exe"
        # For PowerShell, -File should precede the script path.
        # -ExecutionPolicy Bypass might be needed if scripts are not signed.
        script_args = ['-ExecutionPolicy', 'Bypass', '-File', os.path.abspath(os.path.join(os.path.dirname(__file__), script_name))]
    elif "linux" in current_os:
        script_name = "update_bot.sh"
        executable = "/bin/bash" # or "bash" if it's in PATH
        script_args = [os.path.abspath(os.path.join(os.path.dirname(__file__), script_name))]
    else:
        if slash_ctx: # Check if slash_ctx is not None before sending
            await slash_ctx.send(f"Unsupported operating system for automatic updates: {current_os}", ephemeral=True)
        else:
            logging.error(f"Unsupported OS for automatic updates: {current_os}")
        return False # Return False as update cannot proceed

    script_path = script_args[-1] # The script path is the last element in script_args

    if not os.path.exists(script_path):
        error_msg = f"Update script not found at: {script_path}"
        logging.error(error_msg)
        if slash_ctx:
            await slash_ctx.send(f"Error: Update script not found: `{script_path}`.", ephemeral=True)
        return False

    initiator_desc = "Automatic update check"
    if slash_ctx and slash_ctx.author:
        initiator_desc = f"User {slash_ctx.author.username} ({slash_ctx.author.id})"

    try:
        logging.info(f"{initiator_desc} initiated bot update using {executable} with script: {script_path}")
        
        # For PowerShell, the script path is part of script_args.
        # For bash, script_args contains only the script path.
        # The command structure is: executable *unpacked_args_before_script script_path
        if "windows" in current_os:
            # ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-File', 'path/to/script.ps1']
            cmd_list = [executable] + script_args[:-1] + [script_args[-1]]
        else: # Linux
            # ['/bin/bash', 'path/to/script.sh']
            cmd_list = [executable] + script_args

        process = await asyncio.create_subprocess_exec(
            *cmd_list,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        stdout_str = stdout.decode('utf-8', errors='ignore').strip()
        stderr_str = stderr.decode('utf-8', errors='ignore').strip()

        if slash_ctx: 
            response_message = f"🚀 **Update Script Execution ({current_os.capitalize()})** 🚀\n"
            response_message += f"Script: `{os.path.basename(script_path)}`\n"
            if process.returncode == 0:
                response_message += "✅ Script executed successfully.\n"
            else:
                response_message += f"⚠️ Script finished with exit code: {process.returncode}.\n"
            
            max_log_section_length = 800 

            if stdout_str:
                response_message += f"**Output:**\n```\n{stdout_str[:max_log_section_length]}\n```\n"
                if len(stdout_str) > max_log_section_length:
                    response_message += f"... (output truncated)\n"
            if stderr_str:
                response_message += f"**Errors:**\n```\n{stderr_str[:max_log_section_length]}\n```\n"
                if len(stderr_str) > max_log_section_length:
                    response_message += f"... (errors truncated)\n"
            
            if process.returncode == 0:
                response_message += "\n✅ **Updates likely pulled. Attempting to apply by restarting the bot...**\n"
                response_message += "ℹ️ The bot will shut down. An external process manager (e.g., PM2, systemd, Docker restart policy) is required to bring it back online with the updates."
            else:
                response_message += "\n❌ **Update script failed. Bot will not restart.** Please check console logs for details."

            # Ensure message is not too long for Discord
            if len(response_message) > 1950: # Leave some buffer
                summary = (f"🚀 Update script finished (Code: {process.returncode}). "
                           f"Logs were too long. Check console/logs. ")
                if process.returncode == 0:
                    summary += "Bot will attempt restart."
                else:
                    summary += "Bot will NOT restart."
                await slash_ctx.send(summary, ephemeral=True)
            else:
                await slash_ctx.send(response_message, ephemeral=True)

        if process.returncode == 0:
            logging.info(f"Update script successful for {initiator_desc}. Stopping bot to apply updates.")
            if slash_ctx: await asyncio.sleep(3) 
            await bot.stop() # This stops the bot client
            # The script itself should exit after bot.stop() to allow process manager to restart
            # For automatic updates, this means the current process will end.
            if not slash_ctx: 
                logging.warning(f"Automatic update successful. Bot has been stopped for restart by process manager.")
            # sys.exit(0) # Consider if a clean exit is needed here for the script runner
            return True
        else:
            log_msg = f"Update script failed for {initiator_desc} with exit code {process.returncode}."
            if stdout_str: log_msg += f" Stdout: {stdout_str}"
            if stderr_str: log_msg += f" Stderr: {stderr_str}"
            logging.error(log_msg)
            if not slash_ctx: 
                 logging.error(f"Automatic update failed. Script exit code: {process.returncode}.")
            return False
    except FileNotFoundError as e_fnf: # Catch if executable (powershell/bash) is not found
        error_msg = f"Executable '{executable}' not found for update script. Ensure it's in PATH. Error: {e_fnf}"
        logging.error(error_msg, exc_info=True)
        if slash_ctx:
            await slash_ctx.send(error_msg, ephemeral=True)
        return False
    except Exception as e_general:
        error_msg = f"An error occurred while {initiator_desc} tried to run update script '{script_name}': {e_general}"
        logging.error(error_msg, exc_info=True)
        if slash_ctx:
            await slash_ctx.send(error_msg, ephemeral=True)
        return False

# --- Bot Management Commands ---
@slash_command(name="manage", description="Manage bot operations (restricted).")
async def manage_group(ctx: SlashContext):
    """Base command for bot management."""
    pass

@manage_group.subcommand(
    sub_cmd_name="update",
    sub_cmd_description="Pulls updates from GitHub and restarts the bot (Owner only)."
)
async def manage_update(ctx: SlashContext):
    if ctx.author.id != OWNER_ID:
        await ctx.send("You do not have permission to use this command.", ephemeral=True)
        return

    await ctx.defer(ephemeral=True) 
    update_success = await _perform_update_and_restart(slash_ctx=ctx)
    # Feedback is sent within _perform_update_and_restart
    # If not slash_ctx was used (automatic), logging handles it.

@manage_group.subcommand(
    sub_cmd_name="restart",
    sub_cmd_description="Shuts down the bot for manual restart (Bot Owner/Manager only)."
)
async def manage_restart(ctx: SlashContext):
    if not is_bot_manager(int(ctx.author.id)): # OWNER_ID is implicitly a manager via is_bot_manager
        await ctx.send("You do not have permission to use this command.", ephemeral=True)
        return

    guild_info = "a Direct Message"
    if ctx.guild: # Check if ctx.guild is not None
        guild_info = f"guild {ctx.guild.name} ({ctx.guild.id})"

    logging.info(f"Restart command initiated by {ctx.author.username} ({ctx.author.id}) in {guild_info}.")

    await ctx.send(
        "✅ Bot shutdown command acknowledged. "
        "The bot process will now attempt to stop.\n"
        "ℹ️ **An external process manager (e.g., PM2, systemd, Docker with restart policy) is required for it to come back online.**",
        ephemeral=True
    )
    await asyncio.sleep(1) # Short delay to ensure message is sent
    await bot.stop()
    # sys.exit(0) # Consider if a clean exit is needed for the script runner

# --- Settings Commands ---
@slash_command(name="settings", description="Manage bot settings (requires permissions).")
async def settings(ctx: SlashContext):
    """Base command for settings. Discord will typically show subcommands."""
    pass

@settings.subcommand(sub_cmd_name="permit", sub_cmd_description="Grants a user bot management permissions.")
@slash_option("user", "The user to grant permissions to.", opt_type=OptionType.USER, required=True)
async def settings_permit_subcommand(ctx: SlashContext, user: User): 
    if not ctx.author.has_permission(Permissions.ADMINISTRATOR) and ctx.author.id != OWNER_ID:
        await ctx.send("You need Administrator permissions or be the Bot Owner to use this command.", ephemeral=True)
        return

    if add_bot_manager(int(user.id)):
        await ctx.send(f"✅ {user.mention} has been granted bot management permissions.", ephemeral=True)
    else:
        await ctx.send(f"ℹ️ {user.mention} already has bot management permissions.", ephemeral=True)

@settings.subcommand(sub_cmd_name="unpermit", sub_cmd_description="Revokes a user's bot management permissions.")
@slash_option("user", "The user to revoke permissions from.", opt_type=OptionType.USER, required=True)
async def settings_unpermit_subcommand(ctx: SlashContext, user: User): 
    if not ctx.author.has_permission(Permissions.ADMINISTRATOR) and ctx.author.id != OWNER_ID:
        await ctx.send("You need Administrator permissions or be the Bot Owner to use this command.", ephemeral=True)
        return

    if int(user.id) == OWNER_ID:
        await ctx.send("🚫 The bot owner's permissions cannot be revoked.", ephemeral=True)
        return

    if remove_bot_manager(int(user.id)):
        await ctx.send(f"✅ {user.mention}'s bot management permissions have been revoked.", ephemeral=True)
    else:
        await ctx.send(f"ℹ️ {user.mention} does not have bot management permissions.", ephemeral=True)

@settings.subcommand(sub_cmd_name="listmanagers", sub_cmd_description="Lists users with bot management permissions.")
async def settings_listmanagers_subcommand(ctx: SlashContext): 
    if not ctx.author.has_permission(Permissions.ADMINISTRATOR) and not is_bot_manager(int(ctx.author.id)):
        await ctx.send("You need Administrator permissions or be a Bot Manager/Owner to use this command.", ephemeral=True)
        return

    managers = load_bot_managers()
    embed = Embed(title="👑 Bot Managers 👑", color=0xFFD700) # Gold

    owner_user = await bot.fetch_user(OWNER_ID)
    if owner_user:
        embed.add_field(name="Bot Owner (Implicit Manager)", value=owner_user.mention, inline=False)
    else: # Fallback if owner user object can't be fetched
        embed.add_field(name="Bot Owner (Implicit Manager)", value=f"ID: {OWNER_ID} (User details not found)", inline=False)

    if managers:
        manager_mentions = []
        for manager_id in managers:
            if manager_id == OWNER_ID: continue 
            try:
                user = await bot.fetch_user(manager_id)
                manager_mentions.append(user.mention if user else f"ID: {manager_id} (User details not found)")
            except Exception: # Catch errors during fetch_user
                manager_mentions.append(f"ID: {manager_id} (Error fetching user details)")
        embed.add_field(name="Permitted Managers", value="\n".join(manager_mentions) if manager_mentions else "No additional managers permitted.", inline=False)
    else:
        embed.add_field(name="Permitted Managers", value="No additional managers permitted.", inline=False)
    await ctx.send(embeds=embed, ephemeral=True)


# Refactored welcome messages settings command
@settings.subcommand(
    sub_cmd_name="welcomemessages", 
    sub_cmd_description="Manage welcome messages for new members (enable/disable/status)."
)
@slash_option(
    name="action",
    description="The action to perform for welcome messages.",
    opt_type=OptionType.STRING,
    required=True,
    choices=[
        {"name": "Enable Welcome Messages", "value": "enable"},
        {"name": "Disable Welcome Messages", "value": "disable"},
        {"name": "Show Welcome Message Status", "value": "status"},
    ]
)
@slash_option(
    "channel",
    "The text channel for welcome messages (required if action is 'enable').",
    opt_type=OptionType.CHANNEL,
    required=False, 
    channel_types=[ChannelType.GUILD_TEXT]
)
async def settings_welcomemessages_manager(ctx: SlashContext, action: str, channel: Optional[GuildText] = None):
    if not ctx.guild: # Ensure command is used in a guild
        await ctx.send("This command can only be used in a server.", ephemeral=True)
        return
    if not ctx.author.has_permission(Permissions.MANAGE_GUILD) and not is_bot_manager(int(ctx.author.id)):
        await ctx.send("You need 'Manage Server' permission or be a Bot Manager/Owner to use this command.", ephemeral=True)
        return

    action = action.lower() 

    if action == "enable":
        if not channel:
            await ctx.send("A channel is required to enable welcome messages. Please specify a channel.", ephemeral=True)
            return
        save_welcome_setting(str(ctx.guild.id), True, str(channel.id))
        await ctx.send(f"✅ Welcome messages are now **enabled** and will be sent to {channel.mention}.", ephemeral=True)
    elif action == "disable":
        save_welcome_setting(str(ctx.guild.id), False, None)
        await ctx.send("✅ Welcome messages are now **disabled** for this server.", ephemeral=True)
    elif action == "status":
        setting = get_welcome_setting(str(ctx.guild.id))
        if setting and setting.get("enabled") and setting.get("channel_id"):
            try:
                welcome_channel_obj = await bot.fetch_channel(int(setting['channel_id']))
                await ctx.send(f"ℹ️ Welcome messages are **enabled** and set to channel {welcome_channel_obj.mention}.", ephemeral=True)
            except Exception: # Catch if channel is deleted or bot lacks perms
                await ctx.send(f"ℹ️ Welcome messages are **enabled** and set to channel ID `{setting['channel_id']}` (channel might be deleted or inaccessible).", ephemeral=True)
        else:
            await ctx.send("ℹ️ Welcome messages are currently **disabled** for this server.", ephemeral=True)
    else:
        await ctx.send("Invalid action specified. Please use 'enable', 'disable', or 'status'.", ephemeral=True)

# Refactored logging settings command
@settings.subcommand(
    sub_cmd_name="logging", 
    sub_cmd_description="Manage server activity logging (enable/disable/status)."
)
@slash_option(
    name="action",
    description="The action to perform for server activity logging.",
    opt_type=OptionType.STRING,
    required=True,
    choices=[
        {"name": "Enable Logging", "value": "enable"},
        {"name": "Disable Logging", "value": "disable"},
        {"name": "Show Logging Status", "value": "status"},
    ]
)
@slash_option(
    "channel",
    "The text channel for logs (required if action is 'enable').",
    opt_type=OptionType.CHANNEL,
    required=False, 
    channel_types=[ChannelType.GUILD_TEXT]
)
async def settings_logging_manager(ctx: SlashContext, action: str, channel: Optional[GuildText] = None):
    if not ctx.guild: # Ensure command is used in a guild
        await ctx.send("This command can only be used in a server.", ephemeral=True)
        return
    if not ctx.author.has_permission(Permissions.MANAGE_GUILD) and not is_bot_manager(int(ctx.author.id)):
        await ctx.send("You need 'Manage Server' permission or be a Bot Manager/Owner to use this command.", ephemeral=True)
        return
    
    action = action.lower()

    if action == "enable":
        if not channel:
            await ctx.send("A channel is required to enable logging. Please specify a channel.", ephemeral=True)
            return
        save_logging_setting(str(ctx.guild.id), True, str(channel.id))
        await ctx.send(f"✅ Server activity logging is now **enabled** and will be sent to {channel.mention}.", ephemeral=True)
    elif action == "disable":
        save_logging_setting(str(ctx.guild.id), False, None)
        await ctx.send("✅ Server activity logging is now **disabled** for this server.", ephemeral=True)
    elif action == "status":
        setting = get_logging_setting(str(ctx.guild.id))
        if setting and setting.get("enabled") and setting.get("channel_id"):
            try:
                log_channel_obj = await bot.fetch_channel(int(setting['channel_id']))
                await ctx.send(f"ℹ️ Server activity logging is **enabled** and set to channel {log_channel_obj.mention}.", ephemeral=True)
            except Exception:
                await ctx.send(f"ℹ️ Server activity logging is **enabled** and set to channel ID `{setting['channel_id']}` (channel might be deleted or inaccessible).", ephemeral=True)
        else:
            await ctx.send("ℹ️ Server activity logging is currently **disabled** for this server.", ephemeral=True)
    else:
        await ctx.send("Invalid action specified. Please use 'enable', 'disable', or 'status'.", ephemeral=True)

SILLY_MENTION_RESPONSES = [
    "Did someone say my name? Or was it just the wind in Aeternum?",
    "You summoned me! What grand adventure awaits? Or do you just need help with `/help`?",
Unchanged lines        await asyncio.sleep(UPDATE_CHECK_INTERVAL_SECONDS)

def load_all_game_data():
    """Loads all necessary game data from CSV files into global variables."""
    global ITEM_DATA, ALL_PERKS_DATA, ITEM_ID_TO_NAME_MAP
    """
    Ensures the SQLite database file exists.
    The actual data loading into the DB is handled by create_db.py.
    """
    # global ITEM_DATA, ALL_PERKS_DATA, ITEM_ID_TO_NAME_MAP # These are no longer used
    logging.info("Starting to load game data...")

    # Define remote URLs for data files
    items_csv_source = "https://raw.githubusercontent.com/involvex/ina-discord-bot-/main/items.csv"
    # Assuming perks.csv is also hosted, replace with its actual URL or keep local path if necessary
    perks_csv_source = "https://raw.githubusercontent.com/involvex/ina-discord-bot-/main/perks.csv" # Placeholder URL
    # perks_csv_source = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'perks.csv') # If perks.csv remains local

    ITEM_DATA = items.load_items_from_csv(items_csv_source)
    if not ITEM_DATA:
        logging.error(f"CRITICAL: Failed to load item_data from {items_csv_source}! Item-related commands will fail.")
        ITEM_DATA = {} # Ensure it's an empty dict if loading fails
        ITEM_ID_TO_NAME_MAP = {}
    else:
        logging.info(f"Successfully loaded {len(ITEM_DATA)} items from {items_csv_source}.")
        # Populate ITEM_ID_TO_NAME_MAP
        ITEM_ID_TO_NAME_MAP = {
            row.get('Item ID'): row.get('Name') # Assuming 'Name' is the original cased name column
            for row in ITEM_DATA.values()
            if row.get('Item ID') and row.get('Name')
        }
        logging.info(f"Successfully created ITEM_ID_TO_NAME_MAP with {len(ITEM_ID_TO_NAME_MAP)} entries.")

    ALL_PERKS_DATA = perks.load_perks_from_csv(perks_csv_source) # Pass the source (URL or path)
    if not ALL_PERKS_DATA:
        logging.error(f"CRITICAL: Failed to load all_perks_data from {perks_csv_source}! Perk-related commands will fail.")
        ALL_PERKS_DATA = {} # Ensure it's an empty dict
    else:
        logging.info(f"Successfully loaded {len(ALL_PERKS_DATA)} perks from {perks_csv_source}.")
    if not os.path.exists(DB_NAME):
        logging.critical(
            f"CRITICAL: Database file '{DB_NAME}' not found. "
            f"The bot relies on this database for item, perk, and recipe data. "
            f"Please run 'python create_db.py' to generate or update the database before starting the bot."
        )
        # Consider exiting if the DB is essential for core functionality:
        # sys.exit(f"Database {DB_NAME} not found. Bot cannot start.")
    else:
        logging.info(f"Database '{DB_NAME}' found. Bot will use it for data lookups.")
+
     logging.info("Game data loading process complete.")
 
 @bot.event()
