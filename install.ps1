<#
.SYNOPSIS
    Password Manager MARK IV: one-step installer for Windows 10/11.

.DESCRIPTION
    Double-click install.bat, or run in PowerShell:
        powershell -ExecutionPolicy Bypass -File install.ps1 [-Reconfigure] [-Uninstall] [-NoLaunch]

    Installs Python, GnuPG and MySQL Server with winget. If no
    MySQL service exists yet, it initializes a local one named
    'PasswordManagerMySQL' that listens on 127.0.0.1 only. It then installs the
    app into its own virtualenv, builds a native PasswordManager.exe for this machine
    (PyInstaller), runs the guided setup, and adds Start Menu and Desktop shortcuts.
    It needs administrator rights and asks for them itself. Set PM_NO_BINARY=1 to skip
    the native build.
#>
[CmdletBinding()]
param(
    [switch]$Reconfigure,
    [switch]$Uninstall,
    [switch]$NoLaunch,
    [switch]$Pause   # keep the window open at the end (used by install.bat and self-elevation)
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$ProgressPreference = 'SilentlyContinue'

$AppName      = 'Password Manager'
$InstallDir   = Join-Path $env:LOCALAPPDATA 'PasswordManager\app'
$Venv         = Join-Path $InstallDir 'venv'
$VenvPython   = Join-Path $Venv 'Scripts\python.exe'
$VenvPythonW  = Join-Path $Venv 'Scripts\pythonw.exe'
$ConfigDir    = Join-Path $env:APPDATA 'PasswordManager'
$MySqlService = 'PasswordManagerMySQL'
$MySqlRoot    = Join-Path $env:ProgramData 'PasswordManager\mysql'
$SourceUrl    = if ($env:PM_SOURCE_URL) { $env:PM_SOURCE_URL } else { 'https://github.com/TGvenomYT/password-manager/archive/refs/heads/main.zip' }

function Write-Info([string]$Message) { Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Warn([string]$Message) { Write-Host "Warning: $Message" -ForegroundColor Yellow }

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    return ([Security.Principal.WindowsPrincipal]$identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Update-SessionPath {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = (@($machine, $user) | Where-Object { $_ }) -join ';'
}

function Install-WingetPackage([string]$Id) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is not available. Install 'App Installer' from the Microsoft Store, then run this again."
    }
    Write-Info "Installing $Id with winget..."
    # Output goes straight to the console (no pipe). GnuPG's installer leaves daemons running,
    # and those would hold a pipe open and hang the script.
    & winget install --id $Id --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        # Non-zero also means "already installed"; callers check for the binary instead.
        Write-Warn "winget exited with code $LASTEXITCODE for $Id."
    }
    Update-SessionPath
}

# Run a probe with native stderr ignored. Windows PowerShell 5.1 with ErrorActionPreference=Stop
# would otherwise turn harmless stderr output into a terminating error.
function Invoke-Probe([string]$Exe, [string[]]$Arguments) {
    $ErrorActionPreference = 'Continue'
    try {
        $out = & $Exe @Arguments 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { return (@($out)[-1]).ToString().Trim() }
    } catch { }
    return $null
}

function Find-Python {
    $probe = 'import sys, venv; assert sys.version_info >= (3, 9); print(sys.executable)'
    foreach ($candidate in @('py -3.13', 'py -3.12', 'py -3.11', 'py -3', 'python')) {
        $parts = $candidate -split ' '
        if (-not (Get-Command $parts[0] -ErrorAction SilentlyContinue)) { continue }
        $arguments = @($parts | Select-Object -Skip 1) + @('-c', $probe)
        $exe = Invoke-Probe $parts[0] $arguments
        # Skip the Microsoft Store "python" alias stub, which lives under WindowsApps.
        if ($exe -and (Test-Path $exe) -and ($exe -notmatch '\\WindowsApps\\')) { return $exe }
    }
    return $null
}

function Find-Gpg {
    $command = Get-Command gpg.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $paths = @()
    foreach ($base in @(${env:ProgramFiles(x86)}, $env:ProgramFiles, $env:LOCALAPPDATA)) {
        if ($base) { $paths += (Join-Path $base 'GnuPG\bin\gpg.exe') }
    }
    foreach ($path in $paths) { if (Test-Path $path) { return $path } }
    return $null
}

function Get-MySqlService {
    return Get-Service -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq $MySqlService -or $_.Name -match '^(MySQL|MariaDB)' } |
        Select-Object -First 1
}

function Find-Mysqld {
    foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (-not $base) { continue }
        $root = Join-Path $base 'MySQL'
        if (-not (Test-Path $root)) { continue }
        $hit = Get-ChildItem -Path $root -Filter mysqld.exe -Recurse -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending | Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}

function Wait-MySqlPort([int]$Seconds) {
    for ($i = 0; $i -lt $Seconds; $i++) {
        $client = New-Object System.Net.Sockets.TcpClient
        try { $client.Connect('127.0.0.1', 3306); return $true } catch { Start-Sleep -Seconds 1 } finally { $client.Dispose() }
    }
    return $false
}

function Install-MySql {
    $service = Get-MySqlService
    if ($service) {
        Write-Info "Using the existing MySQL service '$($service.Name)'."
    } else {
        $mysqld = Find-Mysqld
        if (-not $mysqld) {
            Install-WingetPackage 'Oracle.MySQL'
            $service = Get-MySqlService   # some MySQL installers register their own service
            $mysqld = Find-Mysqld
        }
        if (-not $service) {
            if (-not $mysqld) {
                throw 'MySQL Server could not be installed automatically. Install it from https://dev.mysql.com/downloads/mysql/ and run this again.'
            }
            # Initialize a private, localhost-only server. root starts with an empty password;
            # the setup step offers to set one.
            $basedir = Split-Path (Split-Path $mysqld -Parent) -Parent
            $datadir = Join-Path $MySqlRoot 'data'
            $ini = Join-Path $MySqlRoot 'my.ini'
            New-Item -ItemType Directory -Force -Path $MySqlRoot | Out-Null
            $iniText = @(
                '[mysqld]',
                "basedir=$($basedir -replace '\\', '/')",
                "datadir=$($datadir -replace '\\', '/')",
                'port=3306',
                'bind-address=127.0.0.1'
            ) -join "`r`n"
            # ASCII, because Windows PowerShell's UTF8 adds a BOM, which mysqld rejects.
            Set-Content -Path $ini -Value $iniText -Encoding Ascii
            if (-not (Test-Path (Join-Path $datadir 'mysql.ibd'))) {
                if (Test-Path $datadir) { Remove-Item -Recurse -Force $datadir }   # a failed earlier attempt
                Write-Info 'Initializing the MySQL data directory...'
                & $mysqld "--defaults-file=$ini" --initialize-insecure --console
                if ($LASTEXITCODE -ne 0) { throw "mysqld --initialize-insecure failed (exit $LASTEXITCODE)." }
            }
            Write-Info "Registering Windows service '$MySqlService'..."
            & $mysqld --install $MySqlService "--defaults-file=$ini"
            if ($LASTEXITCODE -ne 0) { throw "mysqld --install failed (exit $LASTEXITCODE)." }
            $service = Get-Service -Name $MySqlService
        }
    }
    if ($service.StartType -eq 'Disabled' -or $service.StartType -eq 'Manual') {
        Set-Service -Name $service.Name -StartupType Automatic
    }
    if ($service.Status -ne 'Running') {
        Write-Info "Starting $($service.Name)..."
        Start-Service -Name $service.Name
    }
    if (-not (Wait-MySqlPort 60)) { throw 'MySQL did not start listening on 127.0.0.1:3306.' }
}

function Resolve-Source {
    if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot 'pyproject.toml')) -and
        (Test-Path (Join-Path $PSScriptRoot 'password_manager'))) {
        return $PSScriptRoot
    }
    $tmp = Join-Path ([IO.Path]::GetTempPath()) ("pm-src-" + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tmp | Out-Null
    $zip = Join-Path $tmp 'src.zip'
    Write-Info "Downloading $SourceUrl"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $SourceUrl -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $tmp
    $dir = Get-ChildItem -Path $tmp -Directory | Select-Object -First 1
    return $dir.FullName
}

function Install-App([string]$Python, [string]$Source) {
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    if ((Test-Path $VenvPython) -and -not (Invoke-Probe $VenvPython @('-c', 'import sys; print(1)'))) {
        Write-Warn 'Existing environment is broken; recreating it.'
        Remove-Item -Recurse -Force $Venv
    }
    if (-not (Test-Path $VenvPython)) {
        & $Python -m venv $Venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the virtual environment.' }
    }
    # Build from a copy of just the package files so the source tree stays clean.
    $build = Join-Path ([IO.Path]::GetTempPath()) ("pm-build-" + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $build | Out-Null
    foreach ($item in @('pyproject.toml', 'readme.md', 'LICENSE', 'password_manager')) {
        Copy-Item -Recurse -Path (Join-Path $Source $item) -Destination $build
    }
    Write-Info "Installing the app into $Venv"
    & $VenvPython -m pip install --quiet --disable-pip-version-check --upgrade pip
    & $VenvPython -m pip install --quiet --disable-pip-version-check --upgrade $build
    $code = $LASTEXITCODE
    Remove-Item -Recurse -Force $build
    if ($code -ne 0) { throw 'pip install failed.' }
}

# Build a standalone PasswordManager.exe for this machine. It is used only if its self-test
# passes; otherwise the shortcuts run the app from the Python environment.
function Build-Binary([string]$Source) {
    if ($env:PM_NO_BINARY -eq '1') { return $null }
    Write-Info 'Building the native app for this machine (PyInstaller, about a minute)...'
    $ErrorActionPreference = 'Continue'
    $work = Join-Path ([IO.Path]::GetTempPath()) ("pm-pyi-" + [Guid]::NewGuid().ToString('N'))
    $log = Join-Path $InstallDir 'binary-build.log'
    try {
        & $VenvPython -m pip install --quiet --disable-pip-version-check 'pyinstaller>=6.11' *> $log
        if ($LASTEXITCODE -ne 0) { throw 'installing PyInstaller failed' }
        $spec = Join-Path $Source 'packaging\PasswordManager.spec'
        & $VenvPython -m PyInstaller --noconfirm --clean --log-level WARN --distpath "$work\dist" --workpath "$work\build" $spec *>> $log
        if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
        $built = Join-Path $work 'dist\PasswordManager.exe'
        # A windowed exe isn't waited for by '&', so use Start-Process -Wait for the exit code.
        $test = Start-Process -FilePath $built -ArgumentList '--self-test' -Wait -PassThru -WindowStyle Hidden
        if ($test.ExitCode -ne 0) { throw "self-test failed (exit $($test.ExitCode))" }
        $bin = Join-Path $InstallDir 'bin'
        New-Item -ItemType Directory -Force -Path $bin | Out-Null
        $exe = Join-Path $bin 'PasswordManager.exe'
        Copy-Item -Force -Path $built -Destination $exe
        Remove-Item -Force $log -ErrorAction SilentlyContinue
        return $exe
    } catch {
        Write-Warn "The native build didn't work here ($($_.Exception.Message); details: $log). Using the Python environment instead."
        return $null
    } finally {
        Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
    }
}

function New-Shortcut([string]$Path, [string]$Target, [string]$Arguments, [string]$Icon) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($Path)
    $shortcut.TargetPath = $Target
    $shortcut.Arguments = $Arguments
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.Description = 'Local encrypted password vault'
    if ($Icon) { $shortcut.IconLocation = "$Icon,0" }
    $shortcut.Save()
}

function Get-ShortcutPaths {
    return @(
        (Join-Path ([Environment]::GetFolderPath('Programs')) "$AppName.lnk"),
        (Join-Path ([Environment]::GetFolderPath('Desktop')) "$AppName.lnk")
    )
}

function Invoke-Main {
    if ($Uninstall) {
        if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
        foreach ($link in Get-ShortcutPaths) { if (Test-Path $link) { Remove-Item -Force $link } }
        Write-Info 'Removed the app. Your vault and settings were kept:'
        Write-Host "    - MySQL database 'password_manager' and MySQL user 'pm_app'"
        Write-Host "    - config + GPG credential in: $ConfigDir"
        Write-Host '  To erase everything, drop that database and user in MySQL and delete that folder.'
        return
    }

    $source = Resolve-Source

    $python = Find-Python
    if (-not $python) {
        Install-WingetPackage 'Python.Python.3.12'
        $python = Find-Python
        if (-not $python) { throw 'Python 3.9+ was not found after installing it. Open a new terminal and run this again.' }
    }
    Write-Info "Using Python: $python"

    if (-not (Find-Gpg)) {
        Install-WingetPackage 'GnuPG.GnuPG'
        if (-not (Find-Gpg)) { throw 'GnuPG was not found after installing it. Install it from https://gnupg.org/download/ and run this again.' }
    }

    Install-MySql
    Install-App $python $source
    $binary = Build-Binary $source

    $setupArgs = @('-m', 'password_manager', 'setup')
    if ($Reconfigure) { $setupArgs += '--reconfigure' }
    & $VenvPython @setupArgs
    if ($LASTEXITCODE -ne 0) { throw 'Setup did not complete. Fix the problem above and run the installer again.' }

    if ($binary) { $target = $binary; $targetArgs = '' } else { $target = $VenvPythonW; $targetArgs = '-m password_manager' }
    $icon = Join-Path $InstallDir 'icon.ico'
    Copy-Item -Force -Path (Join-Path $source 'packaging\icon.ico') -Destination $icon
    foreach ($link in Get-ShortcutPaths) { New-Shortcut $link $target $targetArgs $icon }
    $version = Invoke-Probe $VenvPython @('-c', 'import password_manager as p; print(p.__version__)')
    Write-Info "Password Manager $version is installed (Start Menu and Desktop shortcuts added)."
    if (-not $NoLaunch) {
        Write-Info 'Opening it now...'
        if ($binary) {
            Start-Process -FilePath $binary -WorkingDirectory $InstallDir
        } else {
            Start-Process -FilePath $VenvPythonW -ArgumentList '-m', 'password_manager' -WorkingDirectory $InstallDir
        }
    }
}

# --- elevation -----------------------------------------------------------------
if (-not (Test-Admin)) {
    if (-not $PSCommandPath) {
        throw 'Please run PowerShell as Administrator, then run this installer again.'
    }
    $relaunch = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-Pause')
    if ($Reconfigure) { $relaunch += '-Reconfigure' }
    if ($Uninstall) { $relaunch += '-Uninstall' }
    if ($NoLaunch) { $relaunch += '-NoLaunch' }
    Write-Info 'Asking for administrator rights...'
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $relaunch
    return
}

$failed = $false
try {
    Invoke-Main
} catch {
    $failed = $true
    Write-Host ''
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}
if ($Pause) {
    Write-Host ''
    Read-Host 'Press Enter to close this window' | Out-Null
}
if ($failed) { exit 1 }
