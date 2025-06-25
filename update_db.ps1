# This script updates the local game database by first scraping the latest data
# for items, and then populating the SQLite database with it.

# Set the script's working directory to its own location
Set-Location -Path (Split-Path -Path $MyInvocation.MyCommand.Path -Parent)

# --- Configuration ---
$VenvActivateScript = ".\venv\Scripts\Activate.ps1"
$PythonExecutable = "python3" # Default to python3, will be overridden by venv if active

# --- Activate Virtual Environment ---
Write-Host "INFO: Attempting to activate virtual environment..." -ForegroundColor DarkCyan
if (Test-Path $VenvActivateScript) {
    Write-Host "INFO: Activating virtual environment: $VenvActivateScript" -ForegroundColor Cyan
    . $VenvActivateScript # Source the activate script
    if ($env:VIRTUAL_ENV) {
        $VenvPythonPath = Join-Path -Path $env:VIRTUAL_ENV -ChildPath "Scripts\python.exe"
        if (Test-Path $VenvPythonPath) {
            $PythonExecutable = $VenvPythonPath
            Write-Host "INFO: Using Python from venv: $PythonExecutable" -ForegroundColor Green
        }
    }
} else {
    Write-Warning "WARNING: Virtual environment activate script not found at '$VenvActivateScript'. Falling back to system python3."
}

# --- Step 1: Scrape latest item data ---
Write-Host "INFO: Step 1: Scraping latest item data from nwdb.info..."
& $PythonExecutable scrape_items.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Item scraping script failed with exit code $LASTEXITCODE. Aborting."
    exit 1
}
Write-Host "INFO: Item scraping completed."

# --- Step 2: Populate the database ---
Write-Host "INFO: Step 2: Populating the SQLite database with new data..."
& $PythonExecutable create_db.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Database population script failed with exit code $LASTEXITCODE. Aborting."
    exit 1
}
Write-Host "INFO: Database population completed successfully."

Write-Host "SUCCESS: Database update process finished." -ForegroundColor Green