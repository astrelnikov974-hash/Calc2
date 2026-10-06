$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "== AXUS Treolan Manager / Windows build ==" -ForegroundColor Cyan

py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean AXUS-Treolan-Manager.spec

if (-not (Test-Path ".\dist\AXUS-Treolan-Manager.exe")) {
    throw "EXE was not created."
}

Write-Host "EXE created: $PWD\dist\AXUS-Treolan-Manager.exe" -ForegroundColor Green
Write-Host "Now compile installer\AXUS-Treolan-Manager.iss with Inno Setup." -ForegroundColor Yellow
