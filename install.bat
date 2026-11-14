@echo off
rem Password Manager MARK IV: double-click to install on Windows.
rem Runs install.ps1, which asks for administrator rights itself.
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Pause %*
endlocal
