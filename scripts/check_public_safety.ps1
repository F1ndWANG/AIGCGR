$ErrorActionPreference = "Stop"
$patterns = @(
  "sk-[A-Za-z0-9]{20,}",
  "[a-f0-9]{32}"
)

$files = Get-ChildItem -Recurse -File |
  Where-Object {
    $_.FullName -notmatch "\\.git\\" -and
    $_.FullName -notmatch "\\runtime\\" -and
    $_.FullName -notmatch "\\.pytest_cache\\" -and
    $_.FullName -notmatch "\\__pycache__\\" -and
    $_.Name -ne ".env"
  }

$matches = $files | Select-String -Pattern $patterns -AllMatches
if ($matches) {
  $matches | ForEach-Object {
    Write-Error ("Potential secret: {0}:{1}: {2}" -f $_.Path, $_.LineNumber, $_.Line.Trim())
  }
  exit 1
}

Write-Host "No public secret patterns found."
