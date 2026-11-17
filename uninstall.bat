@echo off
rem Password Manager MARK IV: uninstall on Windows.
rem
rem   uninstall.bat        Remove the app and its shortcuts. Your vault and settings are kept,
rem                        so running install.bat again picks up where you left off.
rem   uninstall.bat /all   Also erase your settings and your vault (every saved password).
rem                        Asks you to type ERASE first. Run it as administrator.
rem
rem Plain cmd on purpose: it works even where PowerShell scripts are blocked.
setlocal EnableExtensions DisableDelayedExpansion
title Password Manager uninstaller

set "APP_DIR=%LOCALAPPDATA%\PasswordManager"
set "CONFIG_DIR=%APPDATA%\PasswordManager"
set "MYSQL_SERVICE=PasswordManagerMySQL"
set "MYSQL_DIR=%ProgramData%\PasswordManager"
set "ALL=0"
set "NOPAUSE=0"
set "FAILED=0"

:args
if "%~1"=="" goto :args_done
if /i "%~1"=="/all" set "ALL=1"
if /i "%~1"=="--all" set "ALL=1"
if /i "%~1"=="/nopause" set "NOPAUSE=1"
if /i "%~1"=="/?" goto :usage
if /i "%~1"=="--help" goto :usage
shift
goto :args
:args_done

if "%ALL%"=="0" goto :start
net session >nul 2>&1
if not errorlevel 1 goto :confirm_all
echo Erasing everything needs administrator rights.
echo Right-click uninstall.bat and choose "Run as administrator", or run it from an
echo administrator terminal:  uninstall.bat /all
set "FAILED=1"
goto :finish

:confirm_all
echo.
echo This erases your vault: every saved password, your master password and recovery key,
echo your settings and GPG-protected database login, and the private MySQL server that the
echo installer created. It cannot be undone.
echo.
set "CONFIRM="
set /p "CONFIRM=Type ERASE to continue, or press Enter to cancel: "
if "%CONFIRM%"=="ERASE" goto :start
echo Cancelled. Nothing was removed.
goto :finish

:start
echo.
echo ==^> Closing Password Manager if it is open...
powershell -NoProfile -Command "Get-Process | Where-Object { $_.Path -and $_.Path -like ($env:LOCALAPPDATA + '\PasswordManager\*') } | Stop-Process -Force" >nul 2>&1

echo ==^> Removing the shortcuts...
set "PROGRAMS_DIR="
set "DESKTOP_DIR="
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Programs')"`) do set "PROGRAMS_DIR=%%P"
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP_DIR=%%P"
if not defined PROGRAMS_DIR set "PROGRAMS_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
if not defined DESKTOP_DIR set "DESKTOP_DIR=%USERPROFILE%\Desktop"
if exist "%PROGRAMS_DIR%\Password Manager.lnk" del /f /q "%PROGRAMS_DIR%\Password Manager.lnk"
if exist "%DESKTOP_DIR%\Password Manager.lnk" del /f /q "%DESKTOP_DIR%\Password Manager.lnk"

echo ==^> Removing the app...
if not exist "%APP_DIR%" goto :app_gone
rmdir /s /q "%APP_DIR%"
if not exist "%APP_DIR%" goto :app_gone
echo Warning: some files in "%APP_DIR%" are still in use and were not removed.
echo          Restart the PC, then run uninstall.bat again.
set "FAILED=1"
goto :app_done
:app_gone
echo     Removed "%APP_DIR%"
:app_done

if "%ALL%"=="1" goto :erase_all
echo.
echo Done. Your vault and settings were kept:
echo     - MySQL database 'password_manager' and MySQL user 'pm_app'
echo     - settings and GPG-protected database login in "%CONFIG_DIR%"
echo Run install.bat to install again. To erase everything instead, run:  uninstall.bat /all
goto :finish

:erase_all
echo ==^> Removing your settings...
if not exist "%CONFIG_DIR%" goto :config_gone
rmdir /s /q "%CONFIG_DIR%"
if not exist "%CONFIG_DIR%" goto :config_gone
echo Warning: could not remove "%CONFIG_DIR%".
set "FAILED=1"
goto :config_done
:config_gone
echo     Removed "%CONFIG_DIR%"
:config_done

echo ==^> Removing the vault database...
sc query "%MYSQL_SERVICE%" >nul 2>&1
if errorlevel 1 goto :shared_mysql
rem The installer made this server only for Password Manager, so removing it removes the
rem password_manager database and the pm_app user with it.
net stop "%MYSQL_SERVICE%" >nul 2>&1
sc delete "%MYSQL_SERVICE%" >nul 2>&1
if exist "%MYSQL_DIR%" rmdir /s /q "%MYSQL_DIR%"
if exist "%MYSQL_DIR%" goto :mysql_dir_left
echo     Removed the private MySQL server "%MYSQL_SERVICE%" and its data.
goto :all_done
:mysql_dir_left
echo Warning: could not remove "%MYSQL_DIR%". Restart the PC and delete that folder.
set "FAILED=1"
goto :all_done

:shared_mysql
echo     Your vault is in a MySQL server that other programs may use, so it was left alone.
echo     To erase it, run these in MySQL as root:
echo         DROP DATABASE password_manager;
echo         DROP USER 'pm_app'@'localhost';

:all_done
echo.
echo Done. Python, GnuPG and MySQL Server are still installed; remove them in
echo Settings ^> Apps if nothing else uses them.
goto :finish

:usage
echo Usage:
echo   uninstall.bat        Remove the app and shortcuts; keep your vault and settings.
echo   uninstall.bat /all   Also erase your settings and vault. Run as administrator.
goto :finish

:finish
echo.
if "%NOPAUSE%"=="0" pause
endlocal & exit /b %FAILED%
