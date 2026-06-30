<#
.SYNOPSIS
    Luminesk One-Line Installer/Uninstaller for Windows.
.DESCRIPTION
    Handles installation, version checking, conflict detection, and uninstallation.
#>

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Initialize colors (ANSI Escape Sequences)
$esc = [char]27
$COLOR_RESET      = "${esc}[0m"
$COLOR_BOLD       = "${esc}[1m"
$COLOR_PRIMARY    = "${esc}[38;2;255;0;88m"
$COLOR_SUCCESS    = "${esc}[38;2;0;210;106m"
$COLOR_WARNING    = "${esc}[38;2;255;200;61m"
$COLOR_SECONDARY  = "${esc}[38;2;179;179;184m"
$COLOR_BORDER     = "${esc}[38;2;42;42;48m"

# Parse arguments
$ASSUME_YES = $false
$DELETE_MODE = $false
foreach ($arg in $args) {
    if ($arg -eq "-y" -or $arg -eq "--yes") { $ASSUME_YES = $true }
    if ($arg -eq "-d" -or $arg -eq "--delete") { $DELETE_MODE = $true }
}

function Get-MetaVal ($filePath, $key) {
    if (-not (Test-Path $filePath)) { return $null }
    $lines = Get-Content $filePath -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        if ($line -match "^$key=(.*)$") {
            return $Matches[1].Trim()
        }
    }
    return $null
}

function Confirm-Action ($Prompt) {
    if ($ASSUME_YES) { return $true }
    $msg = "${COLOR_BOLD}${Prompt} [y/N]: ${COLOR_RESET}"
    Write-Host $msg -NoNewline
    $response = Read-Host
    if ($response -match '^[yY](es)?$') { return $true }
    return $false
}

function Compare-SemVer ($v1, $v2) {
    try {
        $parsed1 = [version]$v1
        $parsed2 = [version]$v2
        return $parsed1.CompareTo($parsed2)
    } catch {
        return [string]::Compare($v1, $v2)
    }
}

# Determine architecture
$OS = "windows"
$rawArchCandidates = @($env:PROCESSOR_ARCHITEW6432, $env:PROCESSOR_ARCHITECTURE)
$RAW_ARCH = ""
foreach ($cand in $rawArchCandidates) {
    if ($cand) { $RAW_ARCH = $cand.ToLower(); break }
}

$ARCH = ""
switch ($RAW_ARCH) {
    "amd64"   { $ARCH = "amd64" }
    "x86_64"  { $ARCH = "amd64" }
    "x64"     { $ARCH = "amd64" }
    "arm64"   { $ARCH = "arm64" }
    default {
        $errMsg = "${COLOR_PRIMARY}Error: Unsupported architecture: ${RAW_ARCH}${COLOR_RESET}"
        Write-Error $errMsg
        exit 1
    }
}

$BINARY_NAME = "luminesk-$OS-$ARCH.exe"
$DOWNLOAD_URL = "https://github.com/task-v1/luminesk/releases/latest/download/$BINARY_NAME"

# Check administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($isAdmin) {
    $INSTALL_DIR = "$env:ProgramFiles\luminesk"
    $SYSTEM_META_DIR = "$env:ProgramData\luminesk"
    $SYSTEM_META_FILE = Join-Path $SYSTEM_META_DIR ".metadata_one_line"
} else {
    $INSTALL_DIR = "$HOME\.local\bin"
    $USER_META_DIR = "$HOME\.local\share\luminesk"
    $USER_META_FILE = Join-Path $USER_META_DIR ".metadata_one_line"
}
$TARGET_PATH = Join-Path $INSTALL_DIR "nesk.exe"

# Paths to check
$SYS_META = "$env:ProgramData\luminesk\.metadata_one_line"
$USR_META = "$HOME\.local\share\luminesk\.metadata_one_line"

# Analyze environment
Write-Host "${COLOR_PRIMARY}Luminesk analyzing system environment...${COLOR_RESET}"

$cmd = Get-Command nesk -ErrorAction SilentlyContinue
if (-not $cmd) { $cmd = Get-Command nesk.exe -ErrorAction SilentlyContinue }
$EXISTING_BIN = $null
if ($cmd) { $EXISTING_BIN = $cmd.Source }

$IS_SCRIPT_INSTALL = $false
if ((Test-Path $SYS_META) -and ((Get-MetaVal $SYS_META "installed_via") -eq "one-line-script")) {
    $IS_SCRIPT_INSTALL = $true
} elseif ((Test-Path $USR_META) -and ((Get-MetaVal $USR_META "installed_via") -eq "one-line-script")) {
    $IS_SCRIPT_INSTALL = $true
}

# Hard fail when a foreign installation is detected
if ($EXISTING_BIN -and -not $IS_SCRIPT_INSTALL) {
    Write-Host "${COLOR_BORDER}+----------------------------------------------------------${COLOR_RESET}"
    Write-Host "${COLOR_BORDER}|${COLOR_RESET} ${COLOR_PRIMARY}${COLOR_BOLD}FOREIGN INSTALLATION DETECTED${COLOR_RESET}"
    Write-Host "${COLOR_BORDER}+----------------------------------------------------------${COLOR_RESET}"
    Write-Host "${COLOR_BORDER}|${COLOR_RESET} 'nesk' is already installed at: ${COLOR_WARNING}${EXISTING_BIN}${COLOR_RESET}"
    Write-Host "${COLOR_BORDER}|${COLOR_RESET} It was NOT installed via this one-line script."
    Write-Host "${COLOR_BORDER}|${COLOR_RESET}"
    Write-Host "${COLOR_BORDER}|${COLOR_RESET} ${COLOR_BOLD}Please resolve this conflict manually!${COLOR_RESET}"
    Write-Host "${COLOR_BORDER}|${COLOR_RESET} Depending on how you installed it, try checking:"
    Write-Host "${COLOR_BORDER}|${COLOR_RESET}   - ${COLOR_SECONDARY}uv tool list${COLOR_RESET} / ${COLOR_SECONDARY}uvx${COLOR_RESET}"
    Write-Host "${COLOR_BORDER}|${COLOR_RESET}   - ${COLOR_SECONDARY}pipx list${COLOR_RESET}"
    Write-Host "${COLOR_BORDER}|${COLOR_RESET}   - ${COLOR_SECONDARY}pip list${COLOR_RESET}"
    Write-Host "${COLOR_BORDER}|${COLOR_RESET}"
    Write-Host "${COLOR_BORDER}|${COLOR_RESET} Clean up the previous installation and try again."
    Write-Host "${COLOR_BORDER}+----------------------------------------------------------${COLOR_RESET}"
    exit 1
}

# --- UNINSTALL MODE (-d / --delete) ---
if ($DELETE_MODE) {
    if (-not $EXISTING_BIN -and -not $IS_SCRIPT_INSTALL) {
        Write-Host "${COLOR_WARNING}Luminesk is not installed on this system.${COLOR_RESET}"
        exit 0
    }

    if (-not (Confirm-Action "Are you sure you want to completely remove Luminesk?")) {
        Write-Host "Uninstallation cancelled."
        exit 0
    }

    Write-Host "Uninstalling Luminesk..."

    # Remove user installation
    if (Test-Path $USR_META) {
        $metaBin = Get-MetaVal $USR_META "binary"
        if (-not $metaBin) { $metaBin = "$HOME\.local\bin\nesk.exe" }
        Write-Host "Removing user binary and metadata..."
        Remove-Item -Force $metaBin -ErrorAction SilentlyContinue
        Remove-Item -Force $USR_META -ErrorAction SilentlyContinue
        $parentDir = Split-Path $USR_META
        if ((Test-Path $parentDir) -and (Get-ChildItem $parentDir).Count -eq 0) {
            Remove-Item -Path $parentDir -ErrorAction SilentlyContinue
        }
    }

    # Remove system installation
    if (Test-Path $SYS_META) {
        $metaBin = Get-MetaVal $SYS_META "binary"
        if (-not $metaBin) { $metaBin = "$env:ProgramFiles\luminesk\nesk.exe" }
        Write-Host "Removing system binary and metadata..."
        Remove-Item -Force $metaBin -ErrorAction SilentlyContinue
        Remove-Item -Force $SYS_META -ErrorAction SilentlyContinue
        $parentDir = Split-Path $SYS_META
        if ((Test-Path $parentDir) -and (Get-ChildItem $parentDir).Count -eq 0) {
            Remove-Item -Path $parentDir -ErrorAction SilentlyContinue
        }
    }

    Write-Host "${COLOR_SUCCESS}Success: Luminesk has been successfully uninstalled.${COLOR_RESET}"
    exit 0
}
# ---------------------------------------

# Determine local version
$LOCAL_VER = ""
if ($EXISTING_BIN) {
    try {
        $rawVer = & $EXISTING_BIN -v 2>$null | Out-String
        if ($rawVer -match 'v?(\d+\.\d+(?:\.\d+)?)') { $LOCAL_VER = $Matches[1] }
    } catch {}
}

# Fetch release info from GitHub API
$REMOTE_VER = ""
$EXPECTED_SHA = ""
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $headers = @{ "User-Agent" = "Luminesk-Installer" }
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/task-v1/luminesk/releases/latest" -Headers $headers -ErrorAction Stop
    if ($release.tag_name -match 'v?(\d+\.\d+(?:\.\d+)?)') {
        $REMOTE_VER = $Matches[1]
    }
    if ($release.assets) {
        $targetAsset = $release.assets | Where-Object { $_.name -eq $BINARY_NAME }
        if ($targetAsset -and $targetAsset.digest) {
            $EXPECTED_SHA = $targetAsset.digest -replace '^sha256:', ''
        }
    }
} catch {}

$NEEDS_UPDATE = $false
$STATUS_TXT = "Not installed"
$STATUS_COLOR = $COLOR_WARNING

if ($LOCAL_VER) {
    if ($REMOTE_VER) {
        $cmp = Compare-SemVer $LOCAL_VER $REMOTE_VER
        if ($cmp -eq 0) {
            $STATUS_TXT = "Up to date (v$LOCAL_VER)"
            $STATUS_COLOR = $COLOR_SUCCESS
        } elseif ($cmp -lt 0) {
            $STATUS_TXT = "Outdated (v$LOCAL_VER -> v$REMOTE_VER)"
            $STATUS_COLOR = $COLOR_PRIMARY
            $NEEDS_UPDATE = $true
        } else {
            $STATUS_TXT = "Newer local (v$LOCAL_VER)"
            $STATUS_COLOR = $COLOR_SUCCESS
        }
    } else {
        $STATUS_TXT = "Installed (v$LOCAL_VER)"
        $STATUS_COLOR = $COLOR_SUCCESS
    }
}

# Output analysis results
Write-Host "${COLOR_BORDER}+----------------------------------------------------------${COLOR_RESET}"
$statusLine = "${COLOR_BORDER}|${COLOR_RESET} {0,-14} : {1}{2}{3}" -f "Status", $STATUS_COLOR, $STATUS_TXT, $COLOR_RESET
Write-Host $statusLine
Write-Host "${COLOR_BORDER}+----------------------------------------------------------${COLOR_RESET}"

if (-not $NEEDS_UPDATE -and $LOCAL_VER) {
    Write-Host "Luminesk satisfies the latest release constraints."
    if (-not (Confirm-Action "Do you want to force reinstall/overwrite it?")) {
        Write-Host "Installation cancelled."
        exit 0
    }
}

if (-not (Confirm-Action "Do you want to proceed with the installation?")) {
    Write-Host "Installation cancelled."
    exit 0
}

# Download and install binary
if (-not (Test-Path $INSTALL_DIR)) {
    New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
}

$tempFile = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName() + ".exe")

Write-Host "Downloading Luminesk binary ($BINARY_NAME)..."
try {
    $oldProgress = $ProgressPreference
    $ProgressPreference = "SilentlyContinue"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $webReqHeaders = @{ "User-Agent" = "Luminesk-Installer" }
    Invoke-WebRequest -Uri $DOWNLOAD_URL -OutFile $tempFile -UseBasicParsing -Headers $webReqHeaders
} catch {
    Write-Host "${COLOR_PRIMARY}Error downloading binary: $_${COLOR_RESET}"
    if (Test-Path $tempFile) { Remove-Item -Force $tempFile -ErrorAction SilentlyContinue }
    exit 1
} finally {
    $ProgressPreference = $oldProgress
}

if (-not (Test-Path $tempFile) -or (Get-Item $tempFile).Length -eq 0) {
    Write-Host "${COLOR_PRIMARY}Error: Downloaded file is empty or missing.${COLOR_RESET}"
    if (Test-Path $tempFile) { Remove-Item -Force $tempFile -ErrorAction SilentlyContinue }
    exit 1
}

if ($EXPECTED_SHA) {
    Write-Host "Verifying checksum..."
    $actualSha = (Get-FileHash -Path $tempFile -Algorithm SHA256).Hash.ToLower()
    if ($actualSha -ne $EXPECTED_SHA.ToLower()) {
        Write-Host "${COLOR_PRIMARY}Error: Checksum verification failed.${COLOR_RESET}"
        Write-Host "Expected: $EXPECTED_SHA"
        Write-Host "Actual:   $actualSha"
        Remove-Item -Force $tempFile -ErrorAction SilentlyContinue
        exit 1
    }
    Write-Host "${COLOR_SUCCESS}Checksum verified successfully.${COLOR_RESET}"
}

try {
    Move-Item -Path $tempFile -Destination $TARGET_PATH -Force
} catch {
    Write-Host "${COLOR_PRIMARY}Error moving binary to target path ${TARGET_PATH}: $_${COLOR_RESET}"
    if (Test-Path $tempFile) { Remove-Item -Force $tempFile -ErrorAction SilentlyContinue }
    exit 1
}

# Create proof metadata file
Write-Host "Creating installation metadata..."
$now = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
$metaDir = $USER_META_DIR
if ($isAdmin) { $metaDir = $SYSTEM_META_DIR }
$metaFile = $USER_META_FILE
if ($isAdmin) { $metaFile = $SYSTEM_META_FILE }

if (-not (Test-Path $metaDir)) { New-Item -ItemType Directory -Path $metaDir -Force | Out-Null }

$verStr = "unknown"
if ($REMOTE_VER) { $verStr = $REMOTE_VER }
$metaLines = @(
    "installed_via=one-line-script",
    "version=$verStr",
    "binary=$TARGET_PATH",
    "installed_at=$now"
)
[System.IO.File]::WriteAllLines($metaFile, $metaLines, [System.Text.Encoding]::UTF8)

Write-Host "${COLOR_SUCCESS}Success: Luminesk has been successfully installed.${COLOR_RESET}"

# Check PATH variable
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -like "*$INSTALL_DIR*") {
    Write-Host "Run setup tasks with: nesk --help"
} else {
    Write-Host "${COLOR_WARNING}Warning: ${INSTALL_DIR} is not in your PATH environment variable.${COLOR_RESET}"
    Write-Host "To add it, run this command in PowerShell as Administrator:"
    $envCmd = "  [Environment]::SetEnvironmentVariable(`"Path`", [Environment]::GetEnvironmentVariable(`"Path`",`"User`") + `";$INSTALL_DIR`", `"User`")"
    Write-Host $envCmd
}
