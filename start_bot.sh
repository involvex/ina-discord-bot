#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Navigate to the script's directory (which should be the bot's root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR" || { echo "ERROR: Failed to navigate to script directory in start_bot.sh." >&2; exit 1; }

VENV_PATH="./venv"
VenvActivateScript="$VENV_PATH/bin/activate"

# Activate virtual environment
if [ -f "$VenvActivateScript" ]; then
    echo "INFO: Activating virtual environment for bot startup: $VenvActivateScript"
    # shellcheck disable=SC1090
    source "$VenvActivateScript"
    if [ -z "$VIRTUAL_ENV" ]; then
        echo "ERROR: Virtual environment activation failed in start_bot.sh. This is critical. Exiting." >&2
        exit 1
    fi
else
    echo "ERROR: Virtual environment activate script not found at '$VenvActivateScript' in start_bot.sh. Cannot start bot." >&2
    exit 1
fi

# Start the main bot application
echo "INFO: Starting main.py..."
# Use exec to replace the current shell process with the python process.
# This is important for proper process management in environments like Pterodactyl.
exec python3 main.py
