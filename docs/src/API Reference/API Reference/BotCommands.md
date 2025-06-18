# Bot Commands

This page lists all the slash commands available with Ina's New World Bot.
For detailed usage of a specific command, you can type `/help [command_name]` in Discord.

## General Commands

*   **`/ping`**
    *   Description: Check if the bot is online.
    *   Usage: `/ping`
*   **`/help [command_name]`**
    *   Description: Show available commands or help for a specific command.
    *   Usage: `/help` or `/help <command_name>`
*   **`/petpet <user>`**
    *   Description: Give a New World petting ritual to a user!
    *   Usage: `/petpet <user>`
*   **`/calculate <expression>`**
    *   Description: Perform a calculation with New World magic!
    *   Usage: `/calculate <expression>`
*   **`/about`**
    *   Description: Show information about Ina's New World Bot.
    *   Usage: `/about`

## New World Specific Commands

*   **`/nwdb <item_name>`**
    *   Description: Look up items from New World Database.
    *   Usage: `/nwdb <item_name>`
*   **`/perk <perk_name>`**
    *   Description: Look up information about a specific New World perk.
    *   Usage: `/perk <perk_name>`
*   **`/recipe <item_name>`**
    *   Description: Show the full recipe breakdown for a craftable item.
    *   Usage: `/recipe <item_name>`
*   **`/calculate_craft <item_name> [amount]`**
    *   Description: Calculate resources needed to craft an item, including intermediates.
    *   Usage: `/calculate_craft <item_name> [amount]`

## Build Management

*   **`/build add <link> <name> [keyperks]`**
    *   Description: Add a build from nw-buddy.de.
    *   Usage: `/build add <link_to_nw-buddy_gearset> <your_build_name> [optional_comma_separated_key_perks]`
*   **`/build list`**
    *   Description: Show a list of saved builds.
    *   Usage: `/build list`
*   **`/build remove <name>`**
    *   Description: Remove a saved build.
    *   Usage: `/build remove <name_of_build_to_remove>`
    *   Permissions: Manage Server or Bot Manager

## Management & Settings Commands

These commands typically require specific permissions.

*   **`/manage update`**
    *   Description: Pulls updates from GitHub and restarts the bot.
    *   Usage: `/manage update`
    *   Permissions: Bot Owner
*   **`/manage restart`**
    *   Description: Shuts down the bot for manual restart.
    *   Usage: `/manage restart`
    *   Permissions: Bot Owner/Manager
*   **`/settings permit <user>`**
    *   Description: Grants a user bot management permissions.
    *   Usage: `/settings permit <user>`
    *   Permissions: Server Admin or Bot Owner
*   **`/settings unpermit <user>`**
    *   Description: Revokes a user's bot management permissions.
    *   Usage: `/settings unpermit <user>`
    *   Permissions: Server Admin or Bot Owner
*   **`/settings listmanagers`**
    *   Description: Lists users with bot management permissions.
    *   Usage: `/settings listmanagers`
    *   Permissions: Server Admin or Bot Manager/Owner
*   **`/settings welcomemessages <action> [channel]`**
    *   Description: Manage welcome messages for new members.
    *   Usage: `/settings welcomemessages <enable|disable|status> [channel_for_enable]`
    *   Permissions: Manage Server or Bot Manager/Owner
*   **`/settings logging <action> [channel]`**
    *   Description: Manage server activity logging.
    *   Usage: `/settings logging <enable|disable|status> [channel_for_enable]`
    *   Permissions: Manage Server or Bot Manager/Owner
