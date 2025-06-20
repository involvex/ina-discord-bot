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
# $BotDirectory = "c:\Users\lukas\Downloads\discordbotpy\interactions.py" # Original Windows dev path
$BotDirectory = "/home/container/interactions.py" # Adjusted to reflect server structure, for context. PowerShell script is Windows-specific.
$GitBranch = "main"

# Optional: Path to your Python executable (if not in PATH or for specific venv)
# $PythonExecutable = "C:\path\to\your\python.exe"
# Optional: Path to your virtual environment's activate script (for pip in venv)
# $VenvActivateScript = "C:\path\to\your\venv\Scripts\Activate.ps1"

Write-Host "===================================" -ForegroundColor Green
Write-Host "Ina's New World Bot Updater" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""
# Get the directory of the script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Navigate to the script's directory (root of your Git repo)
Set-Location $ScriptDir

Write-Host "Starting forceful update..."

# Fetch all remote branches and tags
git fetch --all
if ($LASTEXITCODE -ne 0) {
  Write-Error "Error: git fetch failed."
  exit 1
}

# Hard reset the local main branch to match the remote origin/main
# Replace 'main' with your default branch name if it's different (e.g., master)
git reset --hard origin/main
if ($LASTEXITCODE -ne 0) {
  Write-Error "Error: git reset --hard origin/main failed."
  exit 1
}

# Remove untracked files and directories, including those in .gitignore
# Use with caution: -x also removes ignored files. If you don't want that, remove the 'x'.
git clean -fd # Changed -fdx to -fd to preserve ignored files like .env
if ($LASTEXITCODE -ne 0) {
  Write-Error "Error: git clean -fd failed."
  exit 1
}

Write-Host "Local repository forcefully updated to origin/main and cleaned."

# Optional: Reinstall dependencies if requirements.txt might have changed
if (Test-Path "requirements.txt") {
  Write-Host "Reinstalling dependencies from requirements.txt..."
  # Adjust pip command as needed (e.g., pip3, or path to venv pip)
  pip install -U -r requirements.txt
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Warning: pip install -r requirements.txt failed. Dependencies might be outdated."
    # Decide if this should be a fatal error (exit 1) or just a warning
  }
}

Write-Host "Update script completed. Bot will be restarted by the main Python script."
exit 0

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
    git fetch --all --progress
    if ($LASTEXITCODE -ne 0) {
        # Force a PowerShell terminating error if git command failed
        throw "Git fetch command failed with exit code $LASTEXITCODE."
    }
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
    # git rev-parse writes the branch name to STDOUT.
    # We need to capture it and trim any potential whitespace.
    $currentBranchOutput = git rev-parse --abbrev-ref HEAD
    if ($LASTEXITCODE -ne 0) {
        throw "git rev-parse --abbrev-ref HEAD failed with exit code $LASTEXITCODE."
    }
    $currentBranch = $currentBranchOutput.Trim()

    if ($currentBranch -ne $GitBranch) {
        Write-Host "Currently on branch '$currentBranch'. Attempting to checkout '$GitBranch'..."
        git checkout $GitBranch
        if ($LASTEXITCODE -ne 0) {
            throw "git checkout $GitBranch failed with exit code $LASTEXITCODE."
        }
    }
    Write-Host "Successfully on branch '$GitBranch'."
}
catch {
    # Make this a fatal error as failing to be on the correct branch is critical for an update script
    Write-Error "Failed to ensure the script is on branch '$GitBranch'. Update cannot proceed safely. Error: $($_.Exception.Message)"
    exit 1 # Exit the script
}
Write-Host ""

# --- Pull changes from the main branch of origin ---
Write-Host "Pulling changes from origin/$GitBranch..."
try {
    git pull origin $GitBranch --progress
    if ($LASTEXITCODE -ne 0) {
        throw "Git pull origin $GitBranch --progress failed with exit code $LASTEXITCODE."
    }
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