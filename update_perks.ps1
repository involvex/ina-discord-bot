<#
.SYNOPSIS
    Updates the perks data by running a Python script and pushing changes to Git.
#>

# --- Configuration ---
# Define the path to your virtual environment's activate script
# Adjust this path if your virtual environment is named differently or located elsewhere
$VenvActivateScript = ".\venv\Scripts\Activate.ps1" 

# Navigate to the script's directory
Set-Location -Path "$(Split-Path -Path $MyInvocation.MyCommand.Path -Parent)"

# --- Activate Virtual Environment ---
if (Test-Path $VenvActivateScript) {
    Write-Host "Activating virtual environment: $VenvActivateScript" -ForegroundColor Cyan
    . $VenvActivateScript # Dot-source to execute in the current scope
} else {
    Write-Warning "Virtual environment activation script not found at '$VenvActivateScript'."
    Write-Warning "The script will attempt to run with the system's Python, which may not have all dependencies."
    # Consider exiting if the virtual environment is essential:
    # exit 1
}

# Run the Python script
python3 scrape_perks.py # Using python3 explicitly

# Check for and remove .git/index.lock file if it exists
$LockFile = ".git/index.lock"
if (Test-Path $LockFile) {
    Write-Host "Git index.lock file found. Attempting to remove it..."
    Remove-Item $LockFile -ErrorAction SilentlyContinue
    if (-not (Test-Path $LockFile)) {
        Write-Host "index.lock removed successfully."
    } else {
        Write-Warning "Failed to remove index.lock. Git operations might still fail."
    }
}

# Commit and push changes (ensure git is initialized in your project and you have proper permissions)
git add perks_scraped.csv
git commit -m "Update perks data (automated)"
git push