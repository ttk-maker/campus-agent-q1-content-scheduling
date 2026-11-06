$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
Write-Host 'Open http://127.0.0.1:8765/ after the server starts.'
py -3.10 -m src.web
