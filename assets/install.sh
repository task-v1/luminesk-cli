#!/bin/sh
set -e

if [ -t 1 ]; then
    ESC=$(printf '\033')
    COLOR_RESET="${ESC}[0m"
    COLOR_BOLD="${ESC}[1m"

    COLOR_PRIMARY="${ESC}[38;2;255;0;88m"
    COLOR_SUCCESS="${ESC}[38;2;0;210;106m"
    COLOR_WARNING="${ESC}[38;2;255;200;61m"
    COLOR_SECONDARY="${ESC}[38;2;179;179;184m"
    COLOR_BORDER="${ESC}[38;2;42;42;48m"
else
    COLOR_RESET=""
    COLOR_BOLD=""
    COLOR_PRIMARY=""
    COLOR_SUCCESS=""
    COLOR_WARNING=""
    COLOR_SECONDARY=""
    COLOR_BORDER=""
fi

version_ge() {
    awk -v v1="$1" -v v2="$2" '
    BEGIN {
        n1=split(v1,a,".")
        n2=split(v2,b,".")
        n=(n1>n2?n1:n2)

        for(i=1;i<=n;i++){
            x=(a[i]==""?0:a[i])
            y=(b[i]==""?0:b[i])

            if(x>y) exit 0
            if(x<y) exit 1
        }
        exit 0
    }'
}

get_meta_val() {
    [ -f "$1" ] && grep -E "^$2=" "$1" | cut -d= -f2-
}

ASSUME_YES=false
DELETE_MODE=false
for arg in "$@"; do
    case "$arg" in
        -y|--yes) ASSUME_YES=true ;;
        -d|--delete) DELETE_MODE=true ;;
    esac
done

confirm() {
    if [ "$ASSUME_YES" = true ]; then return 0; fi
    if [ ! -t 0 ]; then
        echo "${COLOR_WARNING}Error: Standard input is not a terminal.${COLOR_RESET}" >&2
        exit 1
    fi
    printf "${COLOR_BOLD}%s [y/N]: ${COLOR_RESET}" "$1"
    read -r RESPONSE
    case "$RESPONSE" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

# Detect operating system
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "$OS" in
    linux*)  OS="linux" ;;
    darwin*) OS="darwin" ;;
    *) echo "${COLOR_PRIMARY}Error: Unsupported OS: $OS${COLOR_RESET}" >&2; exit 1 ;;
esac

# Detect architecture
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|amd64) ARCH="amd64" ;;
    arm64|aarch64) ARCH="arm64" ;;
    *) echo "${COLOR_PRIMARY}Error: Unsupported architecture: $ARCH${COLOR_RESET}" >&2; exit 1 ;;
esac

BINARY_NAME="luminesk-$OS-$ARCH"
DOWNLOAD_URL="https://github.com/task-v1/luminesk-cli/releases/latest/download/$BINARY_NAME"

INSTALL_DIR="/usr/local/bin"
USE_SUDO=""

require_sudo() {
    if ! command -v sudo >/dev/null 2>&1; then
        echo "${COLOR_PRIMARY}Error: sudo is required but not installed.${COLOR_RESET}" >&2
        exit 1
    fi
}

if [ "$(id -u)" -ne 0 ] && [ ! -w "$INSTALL_DIR" ]; then
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
else
    if [ "$(id -u)" -ne 0 ]; then
        require_sudo
        USE_SUDO="sudo"
    fi
fi
TARGET_PATH="$INSTALL_DIR/nesk"

# Paths to meta files (for system and user installation)
SYSTEM_META_DIR="/usr/local/share/luminesk"
USER_META_DIR="$HOME/.local/share/luminesk"
SYSTEM_META_FILE="$SYSTEM_META_DIR/.metadata_one_line"
USER_META_FILE="$USER_META_DIR/.metadata_one_line"

# Analyze the environment and check existing installations
echo "${COLOR_PRIMARY}Luminesk analyzing system environment...${COLOR_RESET}"

EXISTING_BIN=""
if command -v nesk >/dev/null 2>&1; then
    EXISTING_BIN="$(command -v nesk)"
fi

# Check for a meta file that confirms installation via this script
IS_SCRIPT_INSTALL=false
if [ -f "$SYSTEM_META_FILE" ] && [ "$(get_meta_val "$SYSTEM_META_FILE" "installed_via")" = "one-line-script" ]; then
    IS_SCRIPT_INSTALL=true
elif [ -f "$USER_META_FILE" ] && [ "$(get_meta_val "$USER_META_FILE" "installed_via")" = "one-line-script" ]; then
    IS_SCRIPT_INSTALL=true
fi

# Hard fail if the program exists but there is no meta file (blocks both installation and removal)
if [ -n "$EXISTING_BIN" ] && [ "$IS_SCRIPT_INSTALL" = false ]; then
    echo "${COLOR_BORDER}╭──────────────────────────────────────────────────────────${COLOR_RESET}"
    echo "${COLOR_BORDER}│${COLOR_RESET} ${COLOR_PRIMARY}${COLOR_BOLD}FOREIGN INSTALLATION DETECTED${COLOR_RESET}"
    echo "${COLOR_BORDER}├──────────────────────────────────────────────────────────${COLOR_RESET}"
    echo "${COLOR_BORDER}│${COLOR_RESET} 'nesk' is already installed at: ${COLOR_WARNING}$EXISTING_BIN${COLOR_RESET}"
    echo "${COLOR_BORDER}│${COLOR_RESET} It was NOT installed via this one-line script."
    echo "${COLOR_BORDER}│${COLOR_RESET}"
    echo "${COLOR_BORDER}│${COLOR_RESET} ${COLOR_BOLD}Please resolve this conflict manually!${COLOR_RESET}"
    echo "${COLOR_BORDER}│${COLOR_RESET} Depending on how you installed it, try checking:"
    echo "${COLOR_BORDER}│${COLOR_RESET}   • ${COLOR_SECONDARY}uv tool list${COLOR_RESET} / ${COLOR_SECONDARY}uvx${COLOR_RESET}"
    echo "${COLOR_BORDER}│${COLOR_RESET}   • ${COLOR_SECONDARY}pipx list${COLOR_RESET}"
    echo "${COLOR_BORDER}│${COLOR_RESET}   • ${COLOR_SECONDARY}pip list${COLOR_RESET}"
    echo "${COLOR_BORDER}│${COLOR_RESET}"
    echo "${COLOR_BORDER}│${COLOR_RESET} Clean up the previous installation and try again. <3"
    echo "${COLOR_BORDER}╰──────────────────────────────────────────────────────────${COLOR_RESET}"
    exit 1
fi

# --- UNINSTALL MODE (--delete / -d) ---
if [ "$DELETE_MODE" = true ]; then
    if [ -z "$EXISTING_BIN" ] && [ "$IS_SCRIPT_INSTALL" = false ]; then
        echo "${COLOR_WARNING}Luminesk is not installed on this system.${COLOR_RESET}"
        exit 0
    fi

    if ! confirm "Are you sure you want to completely remove Luminesk?"; then
        echo "Uninstallation cancelled."
        exit 0
    fi

    echo "Uninstalling Luminesk..."

    # Remove system components, if present
    if [ -f "$SYSTEM_META_FILE" ]; then
        DEL_SUDO=""
        if [ "$(id -u)" -ne 0 ]; then DEL_SUDO="sudo"; fi

        META_BIN="$(get_meta_val "$SYSTEM_META_FILE" "binary")"
        [ -z "$META_BIN" ] && META_BIN="/usr/local/bin/nesk"

        echo "Removing system binary and metadata..."
        $DEL_SUDO rm -f "$META_BIN"
        $DEL_SUDO rm -f "$SYSTEM_META_FILE"
        $DEL_SUDO rmdir "$SYSTEM_META_DIR" 2>/dev/null || true
    fi

    # Remove user components, if present
    if [ -f "$USER_META_FILE" ]; then
        META_BIN="$(get_meta_val "$USER_META_FILE" "binary")"
        [ -z "$META_BIN" ] && META_BIN="$HOME/.local/bin/nesk"

        echo "Removing user binary and metadata..."
        rm -f "$META_BIN"
        rm -f "$USER_META_FILE"
        rmdir "$USER_META_DIR" 2>/dev/null || true
    fi

    echo "${COLOR_SUCCESS}Success: Luminesk has been successfully uninstalled.${COLOR_RESET}"
    exit 0
fi
# ----------------------------------------

LOCAL_VER=""
if [ -n "$EXISTING_BIN" ]; then
    LOCAL_VER_RAW=$("$EXISTING_BIN" -v 2>/dev/null | grep -oE 'v[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n 1)
    LOCAL_VER="${LOCAL_VER_RAW#v}"
fi

REMOTE_VER=""
RELEASE_JSON=""

if command -v curl >/dev/null 2>&1; then
    RELEASE_JSON=$(curl -fsSL "https://api.github.com/repos/task-v1/luminesk-cli/releases/latest")
elif command -v wget >/dev/null 2>&1; then
    RELEASE_JSON=$(wget -qO- "https://api.github.com/repos/task-v1/luminesk-cli/releases/latest")
fi

if [ -n "$RELEASE_JSON" ]; then
    REMOTE_VER=$(echo "$RELEASE_JSON" | grep '"tag_name"' | sed -E 's/.*"v?([^"]+)".*/\1/' | head -n1)
fi

EXPECTED_SHA=""
if [ -n "$RELEASE_JSON" ]; then
    EXPECTED_SHA=$(echo "$RELEASE_JSON" | awk -v binary="$BINARY_NAME" '
        BEGIN { found=0 }
        {
            if ($0 ~ "\"name\"" && $0 ~ binary) {
                found = 1
            }
            if (found && $0 ~ "\"digest\"") {
                sub(/.*"digest"[ \t]*:[ \t]*/, "")
                sub(/.*sha256:/, "")
                sub(/[",].*/, "")
                gsub(/[ \t\r\n]/, "")
                print $0
                exit
            }
            if ($0 ~ /^    \}/ || $0 ~ /^    \},/) {
                found = 0
            }
        }
    ')
fi

NEEDS_UPDATE=false
STATUS_TXT="Not installed"
STATUS_COLOR="$COLOR_WARNING"

if [ -n "$LOCAL_VER" ]; then
    if [ -n "$REMOTE_VER" ]; then
        if [ "$LOCAL_VER" = "$REMOTE_VER" ]; then
            STATUS_TXT="Up to date (v$LOCAL_VER)"
            STATUS_COLOR="$COLOR_SUCCESS"
        else
            if version_ge "$REMOTE_VER" "$LOCAL_VER"; then
                STATUS_TXT="Outdated (v$LOCAL_VER -> v$REMOTE_VER)"
                STATUS_COLOR="$COLOR_PRIMARY"
                NEEDS_UPDATE=true
            else
                STATUS_TXT="Newer local (v$LOCAL_VER)"
                STATUS_COLOR="$COLOR_SUCCESS"
            fi
        fi
    else
        STATUS_TXT="Installed (v$LOCAL_VER)"
        STATUS_COLOR="$COLOR_SUCCESS"
    fi
fi

# Show environment analysis results
echo "${COLOR_BORDER}╭──────────────────────────────────────────────────────────${COLOR_RESET}"
printf "${COLOR_BORDER}│${COLOR_RESET} %-14s : %b%s%b\n" "Status" "$STATUS_COLOR" "$STATUS_TXT" "$COLOR_RESET"
printf "${COLOR_BORDER}│${COLOR_RESET} %-14s : %s\n" "System" "$OS-$ARCH"
echo "${COLOR_BORDER}╰──────────────────────────────────────────────────────────${COLOR_RESET}"

if [ "$NEEDS_UPDATE" = false ] && [ -n "$LOCAL_VER" ]; then
    echo "✨ Luminesk satisfies the latest release constraints."
    if ! confirm "Do you want to force reinstall/overwrite it?"; then
        echo "Installation cancelled."
        exit 0
    fi
fi

if [ "$(id -u)" -eq 0 ]; then
    echo "${COLOR_WARNING}WARNING: Running as root (UID 0) is discouraged.${COLOR_RESET}"
    if ! confirm "Are you sure you want to proceed as root?"; then
        echo "Installation cancelled."
        exit 0
    fi
fi

if ! confirm "Do you want to proceed with the installation?"; then
    echo "Installation cancelled."
    exit 0
fi

# Download and install the binary file
TEMP_FILE=""
cleanup() {
    if [ -n "$TEMP_FILE" ] && [ -f "$TEMP_FILE" ]; then
        rm -f "$TEMP_FILE"
    fi
}
trap cleanup EXIT INT TERM

echo "Downloading Luminesk binary ($BINARY_NAME)..."
TEMP_FILE="$(mktemp)"
chmod 600 "$TEMP_FILE"

# Added progress flags (-# for curl, --show-progress for wget)
if command -v curl >/dev/null 2>&1; then
    curl -fSL -# -o "$TEMP_FILE" "$DOWNLOAD_URL"
elif command -v wget >/dev/null 2>&1; then
    wget -q --show-progress -O "$TEMP_FILE" "$DOWNLOAD_URL"
else
    echo "${COLOR_PRIMARY}Error: curl or wget is required.${COLOR_RESET}" >&2
    exit 1
fi

if [ ! -s "$TEMP_FILE" ]; then
    echo "${COLOR_PRIMARY}Error: Downloaded file is empty.${COLOR_RESET}" >&2
    exit 1
fi

if command -v file >/dev/null 2>&1; then
    FILE_INFO=$(file "$TEMP_FILE")
    case "$FILE_INFO" in
        *HTML*|*XML*)
            echo "${COLOR_PRIMARY}Error: Downloaded file is not a binary executable.${COLOR_RESET}" >&2
            exit 1
            ;;
    esac
fi

if [ -n "$EXPECTED_SHA" ]; then
    echo "Verifying checksum..."
    ACTUAL_SHA=""
    if command -v sha256sum >/dev/null 2>&1; then
        ACTUAL_SHA=$(sha256sum "$TEMP_FILE" | awk '{print $1}')
    elif command -v shasum >/dev/null 2>&1; then
        ACTUAL_SHA=$(shasum -a 256 "$TEMP_FILE" | awk '{print $1}')
    fi

    if [ -n "$ACTUAL_SHA" ]; then
        if [ "$EXPECTED_SHA" != "$ACTUAL_SHA" ]; then
            echo "${COLOR_PRIMARY}Error: Checksum verification failed.${COLOR_RESET}" >&2
            echo "Expected: $EXPECTED_SHA" >&2
            echo "Actual:   $ACTUAL_SHA" >&2
            exit 1
        fi
        echo "${COLOR_SUCCESS}Checksum verified successfully.${COLOR_RESET}"
    else
        echo "${COLOR_WARNING}Warning: Could not verify checksum (sha256sum/shasum not found).${COLOR_RESET}"
    fi
fi

echo "Moving binary to target directory..."
$USE_SUDO mv "$TEMP_FILE" "$TARGET_PATH"
$USE_SUDO chmod 755 "$TARGET_PATH"

# Create metadata to track that the installation was performed via the one-line script
echo "Creating installation metadata..."
META_CONTENT="installed_via=one-line-script
version=${REMOTE_VER:-unknown}
binary=$TARGET_PATH
installed_at=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

if [ "$INSTALL_DIR" = "/usr/local/bin" ]; then
    $USE_SUDO mkdir -p "$SYSTEM_META_DIR"
    printf "%s\n" "$META_CONTENT" | $USE_SUDO tee "$SYSTEM_META_FILE" >/dev/null
else
    mkdir -p "$USER_META_DIR"
    printf "%s\n" "$META_CONTENT" > "$USER_META_FILE"
fi

echo "${COLOR_SUCCESS}Success: Luminesk has been successfully installed.${COLOR_RESET}"

case ":$PATH:" in
    *:"$INSTALL_DIR":*)
        echo "Run setup tasks with: nesk --help"
        ;;
    *)
        echo "${COLOR_WARNING}Warning: $INSTALL_DIR is not in your PATH environment variable.${COLOR_RESET}"
        ;;
esac

if [ "$OS" = "linux" ]; then
    echo ""
    echo "${COLOR_BOLD}💡 Tip on Docker File Permissions:${COLOR_RESET}"
    echo "Since Luminesk runs servers in Docker containers, files created by the server"
    echo "inside the container may be owned by root on the host machine. If you encounter"
    echo "'Permission Denied' errors when modifying server files, you can restore ownership by running:"
    echo "  ${COLOR_SECONDARY}sudo chown -R \$USER:\$USER /path/to/server/directory${COLOR_RESET}"
    echo ""
fi