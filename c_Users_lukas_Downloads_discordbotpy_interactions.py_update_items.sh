#!/bin/bash
echo "==================================="
echo "Ina's Bot - Item Data Updater (Linux)"
echo "==================================="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "INFO: Running scrape_items.py to fetch latest item data..."
python3 scrape_items.py
echo "INFO: Running create_db.py to update database with new item data..."
python3 create_db.py
echo "INFO: Item update process finished."
exit 0
