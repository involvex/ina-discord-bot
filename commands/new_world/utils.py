import logging
import json
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Global constants (moved to top)
PERK_PRETTY = {
    'PerkID_Artifact_Set1_HeavyChest': ("Artifact Set: Heavy Chest", "🟣"),
    'PerkID_Gem_EmptyGemSlot': ("Empty Gem Slot", "💠"),
    }

# Mapping for generic material names found in legacy crafting recipes to user-friendly names
GENERIC_MATERIAL_MAPPING = {
    "ingott1": "Iron Ingot",
    "ingott2": "Steel Ingot",
    "ingott3": "Starmetal Ingot",
    "ingott4": "Orichalcum Ingot",
    "ingott5": "Asmodeum", # This is a common guess for T5 ingot
    "ingott51": "Orichalcum Ingot", # Specific to Prismatic Ingot recipe in legacy CSV
    "ingott52": "Asmodeum", # Specific to Prismatic Ingot recipe in legacy CSV
    "oret5": "Orichalcum Ore", # New: Raw T5 Ore
    "reagentconvertert5": "Masterwork Material Converter", # New: T5 Reagent Converter
    "fluxreagentst5": "Obsidian Flux", # New: T5 Flux Reagents (assuming same as Obsidian Flux)
    "dungeondiamonds_flxpac_empyrean": "Empyrean Forge Materia", # New: Specific Dungeon Materia
    # Note: The quantity for DungeonDiamonds_FLXPac_Empyrean in Prismatic Ingot recipe
    "clotht51": "Phoenixweave", # New: T5.1 Cloth
    "clotht52": "Spinweave Cloth", # New: T5.2 Cloth
    "clothweavet5": "Wireweave", # New: T5 Cloth Weave
    # should be 1, not 455000. This appears to be a data error in the source.
    "leathert51": "Runic Leather", # New: T5.1 Leather
    "leathert52": "Dark Leather", # New: T5.2 Leather
    "tannint5": "Aged Tannin", # New: T5 Tannin
    "timbert51": "Glittering Ebony", # New: T5.1 Wood Planks
    "timbert52": "Runewood Planks", # New: T5.2 Wood Planks
    "sandpapert5": "Obsidian Sandpaper", # New: T5 Sandpaper
    "cinnabart1": "Cinnabar", # New: Raw Cinnabar
    "fluxt1": "Weak Solvent",
    "fluxt2": "Common Solvent",
    "fluxt3": "Strong Solvent",
    "fluxt4": "Pure Solvent",
    "fluxt5": "Obsidian Flux",
    "oret1": "Iron Ore",
    "charcoalt1": "Charcoal",
    "leather": "Leather", # Ensure common names are also mapped if they appear generically
    "cloth": "Cloth",
    "timber": "Timber",
    "metal": "Metal", # Generic metal
    "essencefiret1": "Fire Essence",
    "essencelifet1": "Life Essence",
    "essencewatert1": "Water Essence",
    "essencedeatht1": "Death Essence",
    "pearlt1": "Pearl",
}

# Corrected MATERIAL_EMOJIS definition
MATERIAL_EMOJIS = {
    "prismatic leather": "🟣", "iron ingot": "⛓️", "leather": "🟤", "wood": "🪵", # Line 74
    "fiber": "🧵", "cloth": "🧶", "stone": "🪨", "gold ingot": "🥇", "silver ingot": "🥈", "iron ore": "🪨", "starmetal ore": "🌟", "orichalcum ore": "💎", # Line 75 - Added comma here
    "steel ingot": "🔗", "starmetal ingot": "✨", "orichalcum ingot": "🔶", "asmodeum": "💎",
    "weak solvent": "🧪", "common solvent": "🧪", "strong solvent": "🧪", "pure solvent": "🧪", "obsidian flux": "🧪",
    "charcoal": "⚫", "fire essence": "🔥", "life essence": "💚", "water essence": "💧", "death essence": "💀",
    "pearl": "⚪", "timber": "🪵", "metal": "⚙️", "orichalcum ore": "🪨", "masterwork material converter": "⚙️",
    "cinnabar": "🔶", "empyrean forge materia": "💎", "runic leather": "🟪", "dark leather": "⚫", "aged tannin": "🍂",
    "phoenixweave": "🌈", "spinweave cloth": "🕸️", "wireweave": "🧶", "glittering ebony": "🪵",
    "runewood planks": "🪵", "obsidian sandpaper": " abrasive", # Add emojis for new generic names
}

# Add missing mappings for Prismatic materials
GENERIC_MATERIAL_MAPPING.update({
    "clotht53": "Prismatic Cloth",
    "leathert53": "Prismatic Leather",
    "timbert53": "Prismatic Planks",
    "blockt53": "Prismatic Block",
})

GENERIC_MATERIAL_MAPPING["obsidian sandpaper"] = "Obsidian Sandpaper"

# Global cache for items_updated.json
items_data_cache: Dict[str, Dict[str, Any]] = {}

# Load items_updated.json once when this module is imported
def _load_items_data_cache(): # Renamed from _load_items_data_cache to _load_all_items_data
    global items_data_cache
    # Adjust path to point to items_updated.json in the project root
    items_updated_path = os.path.join(os.path.dirname(__file__), "..", "..", "items_updated.json")
    nwdb_aliases_path = os.path.join(os.path.dirname(__file__), "..", "..", "nwdb_items_cache.json") # Path to aliases

    # 1. Load main items data from items_updated.json
    if not os.path.exists(items_updated_path):
        logger.error(f"items_updated.json not found at: {items_updated_path}")
        return # Exit if main data file is missing
    try:
        with open(items_updated_path, "r", encoding="utf-8") as f:
            raw_items = json.load(f)
            if isinstance(raw_items, list):
                for item in raw_items:
                    if not isinstance(item, dict):
                        continue
                    # Add by Name (canonical display name)
                    if item.get("Name"):
                        items_data_cache[item["Name"].lower()] = item
                    # Add by Item ID (internal ID) if different from Name and exists
                    if item.get("Item ID") and item["Item ID"].lower() != item.get("Name", "").lower():
                        items_data_cache[item["Item ID"].lower()] = item
            else:
                logger.error(f"items_updated.json content is not a list: {type(raw_items)}")
        logger.info(f"Loaded {len(items_data_cache)} items from items_updated.json into cache (initial pass with Name and Item ID).")
    except Exception as e:
        logger.error(f"Failed to load items_updated.json for crafting cache: {e}", exc_info=True)
        return # Exit if main data load fails

    # 2. Load and apply aliases from nwdb_items_cache.json
    if os.path.exists(nwdb_aliases_path):
        try:
            with open(nwdb_aliases_path, "r", encoding="utf-8") as f:
                aliases = json.load(f)
                if isinstance(aliases, dict):
                    aliases_added_count = 0
                    for alias_name, item_id_or_name in aliases.items():
                        alias_name_lower = alias_name.lower()
                        item_id_or_name_lower = item_id_or_name.lower()

                        # Find the actual item data using the canonical name/ID from the already loaded items_updated.json
                        actual_item_data = items_data_cache.get(canonical_id_or_name_lower) # Corrected variable name
                        
                        if actual_item_data and alias_name_lower not in items_data_cache: # Only add if it's a new alias, don't overwrite canonical names
                            items_data_cache[alias_name_lower] = actual_item_data
                            aliases_added_count += 1
                    logger.info(f"Loaded {aliases_added_count} aliases from nwdb_items_cache.json into cache.")
                else:
                    logger.error(f"nwdb_items_cache.json content is not a dictionary: {type(aliases)}")
        except Exception as e:
            logger.error(f"Failed to load nwdb_items_cache.json for aliases: {e}", exc_info=True)
    else:
        logger.info(f"nwdb_items_cache.json not found at: {nwdb_aliases_path}. Skipping alias loading.")

    # 3. Add aliases from GENERIC_MATERIAL_MAPPING
    # This ensures that if an internal name (e.g., "clotht53") exists in the cache,
    # its corresponding display name (e.g., "Prismatic Cloth") also becomes a key
    # pointing to the same item data.
    generic_aliases_added_count = 0
    for internal_name_lower, display_name in GENERIC_MATERIAL_MAPPING.items():
        if internal_name_lower in items_data_cache and display_name.lower() not in items_data_cache:
            items_data_cache[display_name.lower()] = items_data_cache[internal_name_lower]
            generic_aliases_added_count += 1
    logger.info(f"Added {generic_aliases_added_count} generic material aliases from GENERIC_MATERIAL_MAPPING to cache.")

    # Log total items in cache after loading both sources
    logger.info(f"Total {len(items_data_cache)} items (including aliases) in cache for crafting calculations.")

_load_items_data_cache() # Call on import

# Helper function to safely get values from item dictionary
def get_any(item_dict: Dict[str, Any], keys: List[str], default: Any) -> Any:
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

# Define PERK_PRETTY outside the class if it's a global constant
def resolve_item_name_for_lookup(item_name: str) -> str:
    """Resolves an item name, applying generic material mappings for lookup.
    This should be used before attempting to find a recipe or item details for a material or a user-provided item name.
    """
    original_name_lower = item_name.lower()

    # 1. Check generic material mapping (e.g., "ingott5" -> "Asmodeum")
    # This is for raw ingredient names from CSV/DB that are not proper item names.
    mapped_name = GENERIC_MATERIAL_MAPPING.get(original_name_lower)
    if mapped_name:
        return mapped_name

    # 2. Check items_data_cache for display name to internal ID mappings,
    # and then potentially resolve that internal ID if it's a generic one.
    item_data = items_data_cache.get(original_name_lower)
    if item_data:
        # If the item has an internal ID that maps to a generic material, use that.
        # This handles cases like "Prismatic Chain" (display name) -> "IngotT53" (internal ID) -> "Prismatic Ingot" (generic material name)
        internal_id = get_any(item_data, ['Item ID', 'ItemID', 'Item_ID'], None)
        if internal_id and str(internal_id).lower() in GENERIC_MATERIAL_MAPPING:
            return GENERIC_MATERIAL_MAPPING[str(internal_id).lower()]
        return get_any(item_data, ['Name', 'name'], item_name) # Return the canonical name from the data

    # 3. If not found in generic mapping or direct cache lookup, return original name
    return item_name