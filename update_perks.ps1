<#
.SYNOPSIS
    Updates the perks data by running a Python script and pushing changes to Git.
#>

# Navigate to the script's directory
Set-Location -To "$(Split-Path -Path $MyInvocation.MyCommand.Path -Parent)"

# Activate virtual environment if necessary (adjust path as needed)
# . .\venv\Scripts\Activate.ps1

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