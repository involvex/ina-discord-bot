import logging
import json
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Global cache for items_updated.json
items_data_cache: Dict[str, Dict[str, Any]] = {}

# Load items_updated.json once when this module is imported
def _load_items_data_cache():
    global items_data_cache
    # Adjust path to point to items_updated.json in the project root
    items_path = os.path.join(os.path.dirname(__file__), "..", "..", "items_updated.json")
    if not os.path.exists(items_path):
        logger.error(f"items_updated.json not found at: {items_path}")
        return
    try:
        with open(items_path, "r", encoding="utf-8") as f:
            raw_items = json.load(f)
            if isinstance(raw_items, list):
                items_data_cache = {item.get("Name", "").lower(): item for item in raw_items if isinstance(item, dict) and item.get("Name")}
            else:
                logger.error(f"items_updated.json content is not a list: {type(raw_items)}")
        logger.info(f"Loaded {len(items_data_cache)} items into cache for crafting calculations.")
    except Exception as e:
        logger.error(f"Failed to load items_updated.json for crafting cache: {e}", exc_info=True)

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
    This should be used before attempting to find a recipe or item details for a material.
    """
    # Check if the item_name (case-insensitive) exists in the mapping
    return GENERIC_MATERIAL_MAPPING.get(item_name.lower(), item_name)


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
} # Corrected: "obsidian sandpaper": "Obsidian Sandpaper",

GENERIC_MATERIAL_MAPPING["obsidian sandpaper"] = "Obsidian Sandpaper"