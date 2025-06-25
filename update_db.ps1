# This script updates the local game database by first scraping the latest data
# for items, and then populating the SQLite database with it.

# Get the directory where the script is located to ensure other scripts are found correctly.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# --- Configuration ---
# Ensure this points to your Python executable.
# If 'python' is in your PATH, this is usually sufficient.
$PythonExecutable = "python"

# --- Step 1: Scrape latest item data ---
Write-Host "Step 1: Scraping latest item data from nwdb.info..."
$ScrapeItemsScript = Join-Path $ScriptDir "scrape_items.py"
& $PythonExecutable $ScrapeItemsScript
if ($LASTEXITCODE -ne 0) {
    Write-Error "Item scraping script failed with exit code $LASTEXITCODE. Aborting."
    exit 1
}
Write-Host "Item scraping completed."

# --- Step 2: Populate the database ---
Write-Host "Step 2: Populating the SQLite database with new data..."
$CreateDbScript = Join-Path $ScriptDir "create_db.py"
& $PythonExecutable $CreateDbScript
if ($LASTEXITCODE -ne 0) {
    Write-Error "Database population script failed with exit code $LASTEXITCODE. Aborting."
    exit 1
}
Write-Host "Database population completed successfully."

Write-Host "Database update process finished." -ForegroundColor Green