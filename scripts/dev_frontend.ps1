$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\frontend"
python -m http.server 5173
