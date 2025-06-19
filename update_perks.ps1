# --- Configuration ---
$VenvActivateScript = ".\venv\Scripts\Activate.ps1" 

Set-Location -Path "$(Split-Path -Path $MyInvocation.MyCommand.Path -Parent)"

$PythonExecutable = "python3"
$VenvActive = $false

# --- Activate Virtual Environment ---
if (Test-Path $VenvActivateScript) {
    Write-Host "Activating virtual environment: $VenvActivateScript" -ForegroundColor Cyan
    . $VenvActivateScript
    if ($env:VIRTUAL_ENV) {
        $VenvPythonPath = Join-Path -Path $env:VIRTUAL_ENV -ChildPath "Scripts\python.exe"
        if (Test-Path $VenvPythonPath) {
            $PythonExecutable = $VenvPythonPath
            $VenvActive = $true
            Write-Host "Using Python from venv: $PythonExecutable" -ForegroundColor Green
        }
    }
}

# --- Install/Update Dependencies ---
if (Test-Path "requirements.txt") {
    Write-Host "Installing dependencies from requirements.txt..."
    & $PythonExecutable -m pip install -r requirements.txt
}

# --- Run create_db.py ---
Write-Host "Running create_db.py to update database..."
& $PythonExecutable create_db.py 
if ($LASTEXITCODE -ne 0) {
    Write-Error "create_db.py failed. Aborting."
    exit 1
}

# --- Use VERSION file for versioning ---
$versionFilePath = Join-Path -Path $PSScriptRoot -ChildPath "VERSION"
if (Test-Path $versionFilePath) {
    $version = Get-Content -Path $versionFilePath -Raw
    Write-Host "Current version from VERSION file: $version"
} else {
    Write-Warning "VERSION file not found. Creating a default version 0.0.1."
    $version = "0.0.1"
    Set-Content -Path $versionFilePath -Value $version
}

# --- Optionally sync version to main.py or config.py ---
# Example for main.py:
$mainPyPath = Join-Path -Path $PSScriptRoot -ChildPath "main.py"
if (Test-Path $mainPyPath) {
    (Get-Content $mainPyPath) -replace '(__version__\s*=\s*")[^"]*(")', "`$1$version`$2" | Set-Content $mainPyPath
    Write-Host "Synced version to main.py: $version"
}

# --- Git operations ---
$LockFile = ".git/index.lock"
if (Test-Path $LockFile) {
    Write-Host "Removing .git/index.lock..."
    Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
}

git add perks_buddy.csv new_world_data.db VERSION
if ($LASTEXITCODE -eq 0) {
    $gitStatus = git status --porcelain perks_buddy.csv new_world_data.db
    if ($gitStatus) {
        Write-Host "Changes detected. Committing..."
        git commit -m "Update perks data (automated, version $version)"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Pushing changes..."
            git push
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Git operations completed successfully." -ForegroundColor Green
            } else {
                Write-Error "git push failed."
            }
        } else {
            Write-Error "git commit failed."
        }
    } else {
        Write-Host "No changes to commit." -ForegroundColor Yellow
    }
} else {
    Write-Error "git add failed."
}

Write-Host "Perk update script finished."