# PowerShell script to scrape all items from nwdb.info and save to items_updated.json

$allItems = @()
$page = 1
$continue = $true

while ($continue) {
    $url = "https://nwdb.info/db/items/page/$page.json"
    Write-Host "Fetching $url ..."
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -ErrorAction Stop
        $data = $response.Content | ConvertFrom-Json
        if ($null -eq $data -or $data.Count -eq 0) {
            $continue = $false
        } else {
            $allItems += $data
            if ($data.Count -lt 100) {
                $continue = $false
            } else {
                $page++
            }
        }
    } catch {
        Write-Host "Failed to fetch or parse page $page. Stopping."
        $continue = $false
    }
}

Write-Host "Saving $($allItems.Count) items to items_updated.json ..."
$allItems | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 items_updated.json
Write-Host "Done."
