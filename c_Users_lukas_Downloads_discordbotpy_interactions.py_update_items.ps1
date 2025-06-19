Write-Host "====================================="
Write-Host "Ina's Bot - Item Data Updater (Windows)"
Write-Host "====================================="
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "INFO: Running scrape_items.py to fetch latest item data..."
python scrape_items.py
Write-Host "INFO: Running create_db.py to update database with new item data..."
python create_db.py
Write-Host "INFO: Item update process finished."