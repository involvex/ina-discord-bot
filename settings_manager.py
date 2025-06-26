import json
import os
from typing import Optional, List, Dict, Any
from config import MASTER_SETTINGS_FILE, OWNER_ID # Import constants

def load_master_settings() -> Dict[str, Any]:
    """Loads all settings from the master JSON file. Creates it with defaults if not found."""
    try:
        with open(MASTER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        default_settings = {
            "bot_managers": [],
            "guild_settings": {},
            "dev_mode_enabled": False # New default setting for auto-updates
        }
        save_master_settings(default_settings)
        return default_settings

def save_master_settings(settings_data: Dict[str, Any]):
    """Saves the provided settings data to the master JSON file."""
    with open(MASTER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings_data, f, indent=4)

def load_bot_managers() -> List[int]:
    settings = load_master_settings()
    return settings.get("bot_managers", [])

def save_bot_managers(managers_list: List[int]):
    settings = load_master_settings()
    settings["bot_managers"] = managers_list
    save_master_settings(settings)

def save_welcome_setting(guild_id: str, enabled: bool, channel_id: Optional[str]):
    settings = load_master_settings()
    guild_id_str = str(guild_id)
    guild_specific_settings = settings.setdefault("guild_settings", {})
    this_guild_settings = guild_specific_settings.setdefault(guild_id_str, {})
    this_guild_settings["welcome"] = {
        "enabled": enabled,
        "channel_id": str(channel_id) if channel_id else None
    }
    save_master_settings(settings)

def get_welcome_setting(guild_id: str) -> Optional[Dict[str, Any]]:
    settings = load_master_settings()
    return settings.get("guild_settings", {}).get(str(guild_id), {}).get("welcome")

def save_logging_setting(guild_id: str, enabled: bool, channel_id: Optional[str]):
    settings = load_master_settings()
    guild_id_str = str(guild_id)
    guild_specific_settings = settings.setdefault("guild_settings", {})
    this_guild_settings = guild_specific_settings.setdefault(guild_id_str, {})
    this_guild_settings["logging"] = {
        "enabled": enabled,
        "channel_id": str(channel_id) if channel_id else None
    }
    save_master_settings(settings)

def get_logging_setting(guild_id: str) -> Optional[Dict[str, Any]]:
    settings = load_master_settings()
    return settings.get("guild_settings", {}).get(str(guild_id), {}).get("logging")

def is_bot_manager(user_id: int) -> bool: # owner_id_param removed
    if user_id == OWNER_ID: # Use imported OWNER_ID
        return True
    managers = load_bot_managers()
    return user_id in managers

def add_bot_manager(user_id: int) -> bool:
    managers = load_bot_managers()
    if user_id not in managers:
        managers.append(user_id)
        save_bot_managers(managers)
        return True
    return False

def get_dev_mode_setting() -> bool:
    """Retrieves the current dev mode setting."""
    settings = load_master_settings()
    return settings.get("dev_mode_enabled", False)

def set_dev_mode_setting(enabled: bool):
    """Sets the dev mode setting."""
    settings = load_master_settings()
    settings["dev_mode_enabled"] = enabled
    save_master_settings(settings)

def remove_bot_manager(user_id: int) -> bool:
    managers = load_bot_managers()
    if user_id in managers:
        managers.remove(user_id)
        save_bot_managers(managers)
        return True
    return False