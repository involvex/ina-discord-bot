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

# Determine Python and Pip executables to use
$PythonExecutable = "python3" # Default if venv activation fails or is not used
$VenvActive = $false

# --- Activate Virtual Environment ---
if (Test-Path $VenvActivateScript) {
    Write-Host "Activating virtual environment: $VenvActivateScript" -ForegroundColor Cyan
    . $VenvActivateScript # Dot-source to execute in the current scope

    # After activation, VIRTUAL_ENV environment variable should be set
    if ($env:VIRTUAL_ENV) {
        Write-Host "Virtual environment appears active. VIRTUAL_ENV: $($env:VIRTUAL_ENV)" -ForegroundColor Green
        # Construct path to python.exe within the venv
        $VenvPythonPath = Join-Path -Path $env:VIRTUAL_ENV -ChildPath "Scripts\python.exe"
        if (Test-Path $VenvPythonPath) {
            $PythonExecutable = $VenvPythonPath
            $VenvActive = $true
            Write-Host "Using Python from venv: $PythonExecutable" -ForegroundColor Green
        } else {
            Write-Warning "VIRTUAL_ENV is set, but python.exe not found at '$VenvPythonPath'. Falling back to system '$($PythonExecutable)'."
        }
    } else {
        Write-Warning "Virtual environment activation script ran, but VIRTUAL_ENV is not set. Falling back to system '$($PythonExecutable)'."
    }
} else {
    Write-Warning "Virtual environment activation script not found at '$VenvActivateScript'."
    Write-Warning "The script will attempt to run with the system's Python, which may not have all dependencies."
    # Consider exiting if the virtual environment is essential:
    # exit 1
}

# --- Install/Update Dependencies (using the determined Python's pip) ---
if (Test-Path "requirements.txt") {
    Write-Host "Attempting to install/update dependencies from requirements.txt using '$PythonExecutable -m pip'..."
    & $PythonExecutable -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Failed to install/update dependencies. The scrape script might fail."
        # Optionally, exit here if dependencies are critical for scraping
        # exit 1
    } else {
        Write-Host "Dependencies checked/installed successfully." -ForegroundColor Green
    }
} else {
    Write-Warning "requirements.txt not found. Skipping dependency installation."
}

# --- Run the Python Scraper Script ---
Write-Host "Running Python script 'scrape_perks.py' using '$PythonExecutable'..."
& $PythonExecutable scrape_perks.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "Python script 'scrape_perks.py' completed successfully." -ForegroundColor Green
    Write-Host "Attempting to update database from scraped perks using '$PythonExecutable create_db.py'..."
    & $PythonExecutable create_db.py # Assuming create_db.py handles repopulation from the CSV
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Python script 'create_db.py' failed with exit code: $LASTEXITCODE. Database might not be up-to-date. Aborting Git operations for perks."
        exit 1 # Exit if DB update fails to prevent committing a CSV that doesn't match the DB state
    } else {
        Write-Host "Database update from perks completed successfully." -ForegroundColor Green
    }
} else {
    Write-Error "Python script 'scrape_perks.py' failed with exit code: $LASTEXITCODE. Aborting Git operations."
    exit 1 # Exit script if scraping fails
}

# Check for and remove .git/index.lock file if it exists
$LockFile = ".git/index.lock"
$LockFileRemovedSuccessfully = $true
if (Test-Path $LockFile) {
    Write-Host "Git index.lock file found. Attempting to remove it..."
    Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path $LockFile)) {
        Write-Host "index.lock removed successfully."
    } else {
        Write-Warning "Failed to remove index.lock. Git operations might still fail."
        $LockFileRemovedSuccessfully = $false
    }
}

# Commit and push changes (ensure git is initialized in your project and you have proper permissions)
if ($LockFileRemovedSuccessfully -or -not (Test-Path $LockFile)) {
    Write-Host "Attempting Git operations for perks_scraped.csv and new_world_data.db..."
    git add perks_scraped.csv new_world_data.db # Add both files
    if ($LASTEXITCODE -ne 0) {
        Write-Error "git add failed. Exit code: $LASTEXITCODE"
        # Decide if you want to exit here or allow script to finish
    } else {
        # Check if there are changes staged for commit
        $gitStatus = git status --porcelain perks_scraped.csv new_world_data.db
        if ($gitStatus) {
            Write-Host "Changes detected in perks_scraped.csv or new_world_data.db. Committing..."
            git commit -m "Update perks data (automated)"
            if ($LASTEXITCODE -ne 0) {
                Write-Error "git commit failed. Exit code: $LASTEXITCODE"
            } else {
                Write-Host "Pushing changes..."
                git push
                if ($LASTEXITCODE -ne 0) {
                    Write-Error "git push failed. Exit code: $LASTEXITCODE"
                } else {
                    Write-Host "Git operations completed successfully." -ForegroundColor Green
                }
            }
        } else {
            Write-Host "No changes to commit in perks_scraped.csv or new_world_data.db." -ForegroundColor Yellow
        }
    }
} else {
    Write-Error "Skipping Git operations because index.lock could not be cleared or reappeared."
}

Write-Host "Perk update script finished."