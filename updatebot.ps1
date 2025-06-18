#Requires -Version 5.1

<#
.SYNOPSIS
    Updates Ina's New World Bot by pulling the latest changes from the GitHub main branch.
.DESCRIPTION
    This script navigates to the bot's directory, fetches and pulls updates from
    the 'main' branch of the 'origin' remote. It also provides an option to
    update Python dependencies if a requirements.txt file exists.
.NOTES
    Author: Gemini Code Assist
    Ensure Git is installed and in your PATH.
    Run this script with PowerShell. You might need to set your execution policy:
    Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
#>

# --- Configuration ---
$BotDirectory = "c:\Users\lukas\Downloads\discordbotpy\interactions.py" # Your bot's local Git repository path
$GitBranch = "main"

# Optional: Path to your Python executable (if not in PATH or for specific venv)
# $PythonExecutable = "C:\path\to\your\python.exe"
# Optional: Path to your virtual environment's activate script (for pip in venv)
# $VenvActivateScript = "C:\path\to\your\venv\Scripts\Activate.ps1"

Write-Host "===================================" -ForegroundColor Green
Write-Host "Ina's New World Bot Updater" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""

# --- Check for Git ---
try {
    Get-Command git -ErrorAction Stop | Out-Null
    Write-Host "Git installation found."
}
catch {
    Write-Error "Git is not installed or not found in PATH. Please install Git and ensure it's added to your system's PATH."
    exit 1
}
Write-Host ""

# --- Navigate to Bot Directory ---
Write-Host "Navigating to bot directory: $BotDirectory"
if (-not (Test-Path $BotDirectory)) {
    Write-Error "Bot directory not found: $BotDirectory"
    exit 1
}

try {
    Set-Location -Path $BotDirectory -ErrorAction Stop
    Write-Host "Successfully navigated to bot directory: $(Get-Location)"
}
catch {
    Write-Error "Failed to navigate to bot directory: $BotDirectory. Error: $($_.Exception.Message)"
    exit 1
}
Write-Host ""

# --- Fetch latest changes from all remotes ---
Write-Host "Fetching latest updates from remote repository..."
try {
    git fetch --all --progress -ErrorAction Stop
    Write-Host "Fetch successful."
}
catch {
    Write-Error "Git fetch failed. Check your internet connection and Git configuration. Error: $($_.Exception.Message)"
    exit 1
}
Write-Host ""

# --- Ensure we are on the correct branch ---
Write-Host "Ensuring you are on the '$GitBranch' branch..."
try {
    $currentBranch = git rev-parse --abbrev-ref HEAD
    if ($currentBranch -ne $GitBranch) {
        Write-Host "Currently on branch '$currentBranch'. Attempting to checkout '$GitBranch'..."
        git checkout $GitBranch -ErrorAction Stop
    }
    Write-Host "Successfully on branch '$GitBranch'."
}
catch {
    Write-Warning "Failed to checkout branch '$GitBranch'. If you are on a different branch, pulling might have unexpected results. Error: $($_.Exception.Message)"
}
Write-Host ""

# --- Pull changes from the main branch of origin ---
Write-Host "Pulling changes from origin/$GitBranch..."
try {
    git pull origin $GitBranch --progress -ErrorAction Stop
    Write-Host "Successfully pulled latest changes."
}
catch {
    Write-Error "Git pull failed. You might have local changes that conflict. Please resolve conflicts manually or stash your changes (e.g., 'git stash') and try again. Error: $($_.Exception.Message)"
    exit 1
}
Write-Host ""

# --- (Optional) Update Python Dependencies ---
# If your project uses a requirements.txt, uncomment and adapt the following:
# $RequirementsFile = Join-Path -Path $BotDirectory -ChildPath "requirements.txt"
# if (Test-Path $RequirementsFile) {
#     Write-Host "Updating Python dependencies from requirements.txt..."
#     try {
#         # If using a specific python executable or virtual environment:
#         # & $PythonExecutable -m pip install -r $RequirementsFile -ErrorAction Stop
#         pip install -r $RequirementsFile -ErrorAction Stop # Assumes pip is in PATH and correct
#         Write-Host "Python dependencies updated successfully."
#     }
#     catch { Write-Warning "Failed to update Python dependencies. Error: $($_.Exception.Message)" }
# } else { Write-Host "No requirements.txt found, skipping dependency update." }
# Write-Host ""

Write-Host "===================================" -ForegroundColor Green
Write-Host "Update Complete!" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""
Write-Host "Please restart Ina's New World Bot for the changes to take effect." -ForegroundColor Yellow
Write-Host "If 'main.py', dependency files, or other critical code files were updated, a restart is necessary." -ForegroundColor Yellow
Write-Host ""

Read-Host -Prompt "Press Enter to exit"
