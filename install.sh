#!/usr/bin/env bash
# =============================================================================
# Orbit Platform — Unified Installer
# Modules: Webex Calling, Microsoft Teams, Cisco UC (CUCM/Unity/IM&P/Expressway)
#
# GUI-based installer using whiptail for terminal UI.
# Supports: Ubuntu 20.04/22.04/24.04, Debian 11/12,
#           RHEL/CentOS/Rocky/AlmaLinux 8/9
#
# Run as: sudo bash install.sh
# =============================================================================

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[  OK]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
die()     { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

# ── Root check ────────────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && die "This script must be run as root: sudo bash install.sh"

# ── Ensure whiptail or dialog is available ────────────────────────────────────
if command -v whiptail &>/dev/null; then
    DIALOG=whiptail
elif command -v dialog &>/dev/null; then
    DIALOG=dialog
else
    echo "Installing whiptail..."
    if command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y -qq whiptail
    elif command -v dnf &>/dev/null; then
        dnf install -y -q newt
    elif command -v yum &>/dev/null; then
        yum install -y -q newt
    fi
    DIALOG=whiptail
fi

# ── Dimensions ────────────────────────────────────────────────────────────────
TERM_H=$(tput lines 2>/dev/null || echo 24)
TERM_W=$(tput cols  2>/dev/null || echo 80)
DLG_H=$((TERM_H - 4))
DLG_W=$((TERM_W - 10))
[[ $DLG_H -gt 30 ]] && DLG_H=30
[[ $DLG_W -gt 78 ]] && DLG_W=78
[[ $DLG_H -lt 20 ]] && DLG_H=20
[[ $DLG_W -lt 60 ]] && DLG_W=60

# ── Script directory (where modules live) ─────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULES_DIR="${SCRIPT_DIR}/modules"

# ── Validate modules directory ────────────────────────────────────────────────
[[ ! -d "${MODULES_DIR}" ]] && die "modules/ directory not found in ${SCRIPT_DIR}"

# ── Constants ─────────────────────────────────────────────────────────────────
ORBIT_BASE="/opt/orbit"
ORBIT_USER="orbit"
ORBIT_GROUP="orbit"
ORBIT_LOG="/var/log/orbit"
INSTALL_LOG="/tmp/orbit-install.log"

# ── Start logging ─────────────────────────────────────────────────────────────
mkdir -p "$(dirname "${INSTALL_LOG}")"
exec > >(tee -a "${INSTALL_LOG}") 2>&1

# =============================================================================
# SCREEN 1: Welcome
# =============================================================================
${DIALOG} --title "  Orbit Platform Installer  " --msgbox "\
Welcome to the Orbit Platform Installer!

This installer will guide you through setting up one or more
of the following communication management modules:

  1. Webex Calling   — Cisco Webex Calling management
  2. Microsoft Teams — Microsoft Teams administration
  3. Cisco UC        — CUCM, Unity, IM&P, Expressway

You can install any combination of modules. Each module runs
as an independent Flask application with its own database,
background workers, and web interface.

Press OK to continue." $DLG_H $DLG_W

# =============================================================================
# SCREEN 2: Module Selection (checklist)
# =============================================================================
MODULES_SELECTED=$( ${DIALOG} --title "  Module Selection  " \
    --checklist "\nSelect the modules you want to install.\nUse SPACE to select/deselect, TAB to move, ENTER to confirm.\n" \
    $DLG_H $DLG_W 3 \
    "webex-calling"  "Webex Calling Management        " OFF \
    "teams-hub"      "Microsoft Teams Administration   " OFF \
    "cisco-uc"       "Cisco UC (CUCM/Unity/IM&P/Expy) " OFF \
    3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

# Remove quotes from whiptail output
MODULES_SELECTED=$(echo "${MODULES_SELECTED}" | tr -d '"')

[[ -z "${MODULES_SELECTED}" ]] && {
    ${DIALOG} --title "  No Modules Selected  " --msgbox \
        "You did not select any modules. Installation cancelled." 8 $DLG_W
    exit 0
}

# Validate selected modules exist on disk
for mod in ${MODULES_SELECTED}; do
    [[ ! -d "${MODULES_DIR}/${mod}" ]] && \
        die "Module directory not found: ${MODULES_DIR}/${mod}"
done

# Build a summary string
MOD_SUMMARY=""
INSTALL_WEBEX=false; INSTALL_TEAMS=false; INSTALL_CISCO=false
for mod in ${MODULES_SELECTED}; do
    case "${mod}" in
        webex-calling) INSTALL_WEBEX=true;  MOD_SUMMARY="${MOD_SUMMARY}\n  - Webex Calling" ;;
        teams-hub)     INSTALL_TEAMS=true;  MOD_SUMMARY="${MOD_SUMMARY}\n  - Microsoft Teams" ;;
        cisco-uc)      INSTALL_CISCO=true;  MOD_SUMMARY="${MOD_SUMMARY}\n  - Cisco UC" ;;
    esac
done

# =============================================================================
# SCREEN 3: Installation Directory
# =============================================================================
ORBIT_BASE=$( ${DIALOG} --title "  Installation Directory  " \
    --inputbox "\nEnter the base installation directory.\nEach module will be installed as a subdirectory.\n" \
    12 $DLG_W "/opt/orbit" \
    3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

# =============================================================================
# SCREEN 4: Server Configuration
# =============================================================================
DEFAULT_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
DEFAULT_IP="${DEFAULT_IP:-127.0.0.1}"

SERVER_FQDN=$( ${DIALOG} --title "  Server Configuration  " \
    --inputbox "\nEnter the server FQDN or IP address.\nThis will be used for TLS certificate generation and Nginx config.\n" \
    12 $DLG_W "${DEFAULT_IP}" \
    3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

# =============================================================================
# SCREEN 5: Platform Admin Credentials (Web GUI)
# =============================================================================
ADMIN_USER=$( ${DIALOG} --title "  Web Admin Account (1/3)  " \
    --inputbox "\nEnter the platform administrator username.\nThis account will have full access to all installed modules.\n" \
    12 $DLG_W "admin" \
    3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

ADMIN_EMAIL=$( ${DIALOG} --title "  Web Admin Account (2/3)  " \
    --inputbox "\nEnter the platform administrator email address.\n" \
    10 $DLG_W "admin@${SERVER_FQDN}" \
    3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

while true; do
    ADMIN_PASS=$( ${DIALOG} --title "  Web Admin Account (3/3)  " \
        --passwordbox "\nEnter the platform administrator password.\n(Minimum 8 characters)\n" \
        12 $DLG_W \
        3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

    if [[ ${#ADMIN_PASS} -lt 8 ]]; then
        ${DIALOG} --title "  Password Too Short  " --msgbox \
            "Password must be at least 8 characters. Please try again." 8 $DLG_W
        continue
    fi

    ADMIN_PASS2=$( ${DIALOG} --title "  Confirm Password  " \
        --passwordbox "\nRe-enter the administrator password to confirm.\n" \
        10 $DLG_W \
        3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

    if [[ "${ADMIN_PASS}" != "${ADMIN_PASS2}" ]]; then
        ${DIALOG} --title "  Password Mismatch  " --msgbox \
            "Passwords do not match. Please try again." 8 $DLG_W
        continue
    fi
    break
done

# =============================================================================
# SCREEN 6: CLI Admin Credentials (SSH)
# =============================================================================
CLI_ADMIN_USER=$( ${DIALOG} --title "  CLI Admin Account (1/2)  " \
    --inputbox "\nEnter the CLI administrator username for SSH access.\nRoot SSH login will be disabled after setup.\n" \
    12 $DLG_W "orbitadmin" \
    3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

while true; do
    CLI_ADMIN_PASS=$( ${DIALOG} --title "  CLI Admin Account (2/2)  " \
        --passwordbox "\nEnter the CLI administrator password.\n(Minimum 8 characters)\n" \
        12 $DLG_W \
        3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

    if [[ ${#CLI_ADMIN_PASS} -lt 8 ]]; then
        ${DIALOG} --title "  Password Too Short  " --msgbox \
            "Password must be at least 8 characters. Please try again." 8 $DLG_W
        continue
    fi

    CLI_ADMIN_PASS2=$( ${DIALOG} --title "  Confirm CLI Password  " \
        --passwordbox "\nRe-enter the CLI administrator password.\n" \
        10 $DLG_W \
        3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

    if [[ "${CLI_ADMIN_PASS}" != "${CLI_ADMIN_PASS2}" ]]; then
        ${DIALOG} --title "  Password Mismatch  " --msgbox \
            "Passwords do not match. Please try again." 8 $DLG_W
        continue
    fi
    break
done

# =============================================================================
# SCREEN 7: Webex Calling Credentials (if selected)
# =============================================================================
WEBEX_CLIENT_ID=""; WEBEX_CLIENT_SECRET=""; WEBEX_ORG_ID=""

if ${INSTALL_WEBEX}; then
    WEBEX_CLIENT_ID=$( ${DIALOG} --title "  Webex Calling — API Credentials (1/3)  " \
        --inputbox "\nEnter your Webex Integration Client ID.\n(From developer.webex.com)\n" \
        12 $DLG_W "" \
        3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

    WEBEX_CLIENT_SECRET=$( ${DIALOG} --title "  Webex Calling — API Credentials (2/3)  " \
        --passwordbox "\nEnter your Webex Integration Client Secret.\n" \
        10 $DLG_W \
        3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

    WEBEX_ORG_ID=$( ${DIALOG} --title "  Webex Calling — API Credentials (3/3)  " \
        --inputbox "\nEnter your Webex Organization ID.\n(Leave blank to configure later)\n" \
        12 $DLG_W "" \
        3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }
fi

# =============================================================================
# SCREEN 8: Microsoft Teams Credentials (if selected)
# =============================================================================
AZURE_TENANT_ID=""; AZURE_CLIENT_ID=""; AZURE_CLIENT_SECRET=""

if ${INSTALL_TEAMS}; then
    AZURE_TENANT_ID=$( ${DIALOG} --title "  Microsoft Teams — Azure AD (1/3)  " \
        --inputbox "\nEnter your Azure AD Tenant ID.\n(From portal.azure.com > Azure Active Directory)\n" \
        12 $DLG_W "" \
        3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

    AZURE_CLIENT_ID=$( ${DIALOG} --title "  Microsoft Teams — Azure AD (2/3)  " \
        --inputbox "\nEnter your Azure AD Application (Client) ID.\n(From your App Registration)\n" \
        12 $DLG_W "" \
        3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

    AZURE_CLIENT_SECRET=$( ${DIALOG} --title "  Microsoft Teams — Azure AD (3/3)  " \
        --passwordbox "\nEnter your Azure AD Client Secret.\n" \
        10 $DLG_W \
        3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }
fi

# =============================================================================
# SCREEN 9: Cisco UC Credentials (if selected)
# =============================================================================
CUCM_HOST=""; CUCM_USER_CRED=""; CUCM_PASS=""; CUCM_VERSION=""
UNITY_HOST=""; UNITY_USER_CRED=""; UNITY_PASS=""
IMP_HOST=""; IMP_USER_CRED=""; IMP_PASS=""
EXPY_HOST=""; EXPY_USER_CRED=""; EXPY_PASS=""

if ${INSTALL_CISCO}; then
    # CUCM
    ${DIALOG} --title "  Cisco UC — CUCM Configuration  " --yesno \
        "\nWould you like to configure CUCM (Call Manager) now?\n\nYou can also configure this later from the web interface." \
        10 $DLG_W && {

        CUCM_HOST=$( ${DIALOG} --title "  CUCM (1/4)  " \
            --inputbox "\nEnter CUCM Publisher hostname or IP address.\n" \
            10 $DLG_W "" \
            3>&1 1>&2 2>&3 ) || true

        CUCM_USER_CRED=$( ${DIALOG} --title "  CUCM (2/4)  " \
            --inputbox "\nEnter CUCM AXL admin username.\n" \
            10 $DLG_W "administrator" \
            3>&1 1>&2 2>&3 ) || true

        CUCM_PASS=$( ${DIALOG} --title "  CUCM (3/4)  " \
            --passwordbox "\nEnter CUCM AXL admin password.\n" \
            10 $DLG_W \
            3>&1 1>&2 2>&3 ) || true

        CUCM_VERSION=$( ${DIALOG} --title "  CUCM (4/4)  " \
            --inputbox "\nEnter CUCM AXL schema version.\n" \
            10 $DLG_W "14.0" \
            3>&1 1>&2 2>&3 ) || true
    } || true

    # Unity Connection
    ${DIALOG} --title "  Cisco UC — Unity Connection  " --yesno \
        "\nWould you like to configure Unity Connection now?\n\nYou can also configure this later from the web interface." \
        10 $DLG_W && {

        UNITY_HOST=$( ${DIALOG} --title "  Unity Connection (1/3)  " \
            --inputbox "\nEnter Unity Connection hostname or IP address.\n" \
            10 $DLG_W "" \
            3>&1 1>&2 2>&3 ) || true

        UNITY_USER_CRED=$( ${DIALOG} --title "  Unity Connection (2/3)  " \
            --inputbox "\nEnter Unity Connection admin username.\n" \
            10 $DLG_W "administrator" \
            3>&1 1>&2 2>&3 ) || true

        UNITY_PASS=$( ${DIALOG} --title "  Unity Connection (3/3)  " \
            --passwordbox "\nEnter Unity Connection admin password.\n" \
            10 $DLG_W \
            3>&1 1>&2 2>&3 ) || true
    } || true

    # IM&P
    ${DIALOG} --title "  Cisco UC — IM & Presence  " --yesno \
        "\nWould you like to configure IM & Presence now?\n\nYou can also configure this later from the web interface." \
        10 $DLG_W && {

        IMP_HOST=$( ${DIALOG} --title "  IM & Presence (1/3)  " \
            --inputbox "\nEnter IM&P server hostname or IP address.\n" \
            10 $DLG_W "" \
            3>&1 1>&2 2>&3 ) || true

        IMP_USER_CRED=$( ${DIALOG} --title "  IM & Presence (2/3)  " \
            --inputbox "\nEnter IM&P admin username.\n" \
            10 $DLG_W "administrator" \
            3>&1 1>&2 2>&3 ) || true

        IMP_PASS=$( ${DIALOG} --title "  IM & Presence (3/3)  " \
            --passwordbox "\nEnter IM&P admin password.\n" \
            10 $DLG_W \
            3>&1 1>&2 2>&3 ) || true
    } || true

    # Expressway
    ${DIALOG} --title "  Cisco UC — Expressway  " --yesno \
        "\nWould you like to configure Expressway now?\n\nYou can also configure this later from the web interface." \
        10 $DLG_W && {

        EXPY_HOST=$( ${DIALOG} --title "  Expressway (1/3)  " \
            --inputbox "\nEnter Expressway hostname or IP address.\n" \
            10 $DLG_W "" \
            3>&1 1>&2 2>&3 ) || true

        EXPY_USER_CRED=$( ${DIALOG} --title "  Expressway (2/3)  " \
            --inputbox "\nEnter Expressway admin username.\n" \
            10 $DLG_W "admin" \
            3>&1 1>&2 2>&3 ) || true

        EXPY_PASS=$( ${DIALOG} --title "  Expressway (3/3)  " \
            --passwordbox "\nEnter Expressway admin password.\n" \
            10 $DLG_W \
            3>&1 1>&2 2>&3 ) || true
    } || true
fi

# =============================================================================
# SCREEN 10: Port Configuration
# =============================================================================
PORT_WEBEX=8001; PORT_TEAMS=8002; PORT_CISCO=8003

if ${INSTALL_WEBEX}; then
    PORT_WEBEX=$( ${DIALOG} --title "  Port Configuration  " \
        --inputbox "\nEnter the internal port for Webex Calling module.\n" \
        10 $DLG_W "8001" \
        3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }
fi

if ${INSTALL_TEAMS}; then
    PORT_TEAMS=$( ${DIALOG} --title "  Port Configuration  " \
        --inputbox "\nEnter the internal port for Microsoft Teams module.\n" \
        10 $DLG_W "8002" \
        3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }
fi

if ${INSTALL_CISCO}; then
    PORT_CISCO=$( ${DIALOG} --title "  Port Configuration  " \
        --inputbox "\nEnter the internal port for Cisco UC module.\n" \
        10 $DLG_W "8003" \
        3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }
fi

# =============================================================================
# SCREEN 11: Worker Configuration
# =============================================================================
CPU_COUNT=$(nproc 2>/dev/null || echo 2)
REC_GUNICORN=$(( CPU_COUNT * 2 + 1 ))
REC_CELERY=$(( CPU_COUNT > 4 ? 4 : CPU_COUNT ))

GUNICORN_WORKERS=$( ${DIALOG} --title "  Worker Configuration (1/2)  " \
    --inputbox "\nGunicorn workers per module.\n(Recommended: ${REC_GUNICORN} for ${CPU_COUNT} CPUs)\n" \
    12 $DLG_W "${REC_GUNICORN}" \
    3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

CELERY_CONCURRENCY=$( ${DIALOG} --title "  Worker Configuration (2/2)  " \
    --inputbox "\nCelery worker concurrency per module.\n(Recommended: ${REC_CELERY} for ${CPU_COUNT} CPUs)\n" \
    12 $DLG_W "${REC_CELERY}" \
    3>&1 1>&2 2>&3 ) || { echo "Installation cancelled."; exit 0; }

# =============================================================================
# SCREEN 12: Confirmation
# =============================================================================
CONFIRM_MSG="Please review your configuration:\n\n"
CONFIRM_MSG+="  Installation directory: ${ORBIT_BASE}\n"
CONFIRM_MSG+="  Server FQDN/IP:        ${SERVER_FQDN}\n"
CONFIRM_MSG+="  Web Admin:             ${ADMIN_USER} (${ADMIN_EMAIL})\n"
CONFIRM_MSG+="  CLI Admin:             ${CLI_ADMIN_USER}\n"
CONFIRM_MSG+="  Gunicorn workers:      ${GUNICORN_WORKERS}\n"
CONFIRM_MSG+="  Celery concurrency:    ${CELERY_CONCURRENCY}\n\n"
CONFIRM_MSG+="  Modules to install:${MOD_SUMMARY}\n\n"

if ${INSTALL_WEBEX}; then
    CONFIRM_MSG+="  Webex port: ${PORT_WEBEX}"
    [[ -n "${WEBEX_CLIENT_ID}" ]] && CONFIRM_MSG+="  (API configured)"
    CONFIRM_MSG+="\n"
fi
if ${INSTALL_TEAMS}; then
    CONFIRM_MSG+="  Teams port: ${PORT_TEAMS}"
    [[ -n "${AZURE_TENANT_ID}" ]] && CONFIRM_MSG+="  (Azure AD configured)"
    CONFIRM_MSG+="\n"
fi
if ${INSTALL_CISCO}; then
    CONFIRM_MSG+="  Cisco UC port: ${PORT_CISCO}"
    [[ -n "${CUCM_HOST}" ]] && CONFIRM_MSG+="  (CUCM configured)"
    CONFIRM_MSG+="\n"
fi

CONFIRM_MSG+="\nProceed with installation?"

${DIALOG} --title "  Confirm Installation  " --yesno "${CONFIRM_MSG}" $DLG_H $DLG_W \
    || { echo "Installation cancelled."; exit 0; }

# =============================================================================
# ═══════════════════════════════════════════════════════════════════════════════
# INSTALLATION BEGINS
# ═══════════════════════════════════════════════════════════════════════════════
# =============================================================================

clear
echo -e "${BOLD}${BLUE}"
cat << 'BANNER'
   ____       _     _ _
  / __ \     | |   (_) |
 | |  | |_ __| |__  _| |_
 | |  | | '__| '_ \| | __|
 | |__| | |  | |_) | | |_
  \____/|_|  |_.__/|_|\__|

  Unified Communications Platform
  Installer v2.0.0
BANNER
echo -e "${NC}"
info "Install log: ${INSTALL_LOG}"
echo ""

# ── OS Detection ──────────────────────────────────────────────────────────────
info "Detecting operating system..."

if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS_ID="${ID}"
    OS_VERSION="${VERSION_ID%%.*}"
    OS_LIKE="${ID_LIKE:-}"
    success "Detected: ${PRETTY_NAME}"
else
    die "Cannot detect OS — /etc/os-release not found."
fi

case "${OS_ID}" in
    ubuntu|debian)           PKG_MANAGER="apt" ;;
    rhel|centos|rocky|almalinux|fedora) PKG_MANAGER="dnf" ;;
    *)
        if [[ "${OS_LIKE}" == *debian* ]]; then
            PKG_MANAGER="apt"
        elif [[ "${OS_LIKE}" == *rhel* ]]; then
            PKG_MANAGER="dnf"
        else
            die "Unsupported OS: ${OS_ID}."
        fi ;;
esac
info "Package manager: ${PKG_MANAGER}"

# ── Generate Secrets ──────────────────────────────────────────────────────────
info "Generating secrets..."

DB_PASS_WEBEX=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 40)
DB_PASS_TEAMS=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 40)
DB_PASS_CISCO=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 40)
SECRET_KEY_WEBEX=$(openssl rand -hex 64)
SECRET_KEY_TEAMS=$(openssl rand -hex 64)
SECRET_KEY_CISCO=$(openssl rand -hex 64)
REDIS_PASS=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 30)

success "Secrets generated."

# ── Install System Packages ──────────────────────────────────────────────────
info "Installing system packages (this may take a few minutes)..."

install_apt() {
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq \
        python3 python3-venv python3-dev python3-pip \
        nginx \
        postgresql postgresql-contrib \
        redis-server \
        certbot python3-certbot-nginx \
        openssl \
        libpq-dev libssl-dev libffi-dev \
        build-essential gcc \
        git curl wget \
        logrotate acl net-tools
    success "APT packages installed."
}

install_dnf() {
    dnf update -y -q
    dnf install -y -q epel-release 2>/dev/null || true
    dnf install -y -q \
        python3 python3-devel python3-pip \
        nginx \
        postgresql postgresql-server postgresql-contrib postgresql-devel \
        redis \
        certbot python3-certbot-nginx \
        openssl openssl-devel libffi-devel \
        gcc gcc-c++ make \
        git curl wget \
        logrotate acl net-tools
    success "DNF packages installed."
}

case "${PKG_MANAGER}" in
    apt) install_apt ;;
    dnf) install_dnf ;;
esac

# ── Verify Python ─────────────────────────────────────────────────────────────
PYTHON_BIN=$(command -v python3 || die "Python 3 not found after install.")
PY_VERSION=$(${PYTHON_BIN} -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python: ${PY_VERSION} (${PYTHON_BIN})"

# ── PostgreSQL Setup ──────────────────────────────────────────────────────────
info "Configuring PostgreSQL..."

if [[ "${PKG_MANAGER}" == "dnf" ]]; then
    postgresql-setup --initdb 2>/dev/null || true
fi

systemctl enable postgresql --now
sleep 3

setup_pg_db() {
    local db_name="$1" db_user="$2" db_pass="$3"
    sudo -u postgres psql -v ON_ERROR_STOP=1 <<EOSQL
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${db_user}') THEN
      CREATE ROLE ${db_user} LOGIN PASSWORD '${db_pass}';
   END IF;
END
\$\$;
SELECT 'CREATE DATABASE ${db_name} OWNER ${db_user}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${db_name}');
EOSQL
    sudo -u postgres createdb -O "${db_user}" "${db_name}" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${db_name} TO ${db_user};" 2>/dev/null || true
}

${INSTALL_WEBEX} && setup_pg_db "orbit_webex" "orbit_webex" "${DB_PASS_WEBEX}" && \
    success "PostgreSQL: orbit_webex database ready."
${INSTALL_TEAMS} && setup_pg_db "orbit_teams" "orbit_teams" "${DB_PASS_TEAMS}" && \
    success "PostgreSQL: orbit_teams database ready."
${INSTALL_CISCO} && setup_pg_db "orbit_cisco" "orbit_cisco" "${DB_PASS_CISCO}" && \
    success "PostgreSQL: orbit_cisco database ready."

# Ensure MD5 auth
PG_HBA=$(sudo -u postgres psql -t -c "SHOW hba_file;" | xargs)
if ! grep -q "orbit_" "${PG_HBA}" 2>/dev/null; then
    echo "host  all  orbit_webex  127.0.0.1/32  md5" >> "${PG_HBA}"
    echo "host  all  orbit_teams  127.0.0.1/32  md5" >> "${PG_HBA}"
    echo "host  all  orbit_cisco  127.0.0.1/32  md5" >> "${PG_HBA}"
    echo "host  all  orbit_webex  ::1/128       md5" >> "${PG_HBA}"
    echo "host  all  orbit_teams  ::1/128       md5" >> "${PG_HBA}"
    echo "host  all  orbit_cisco  ::1/128       md5" >> "${PG_HBA}"
    systemctl reload postgresql
fi
success "PostgreSQL configured."

# ── Redis Setup ───────────────────────────────────────────────────────────────
info "Configuring Redis..."

REDIS_CONF="/etc/redis/redis.conf"
[[ ! -f "${REDIS_CONF}" ]] && REDIS_CONF="/etc/redis.conf"

if [[ -f "${REDIS_CONF}" ]]; then
    sed -i "s/^# requirepass .*/requirepass ${REDIS_PASS}/" "${REDIS_CONF}"
    sed -i "s/^requirepass .*/requirepass ${REDIS_PASS}/" "${REDIS_CONF}"
    grep -q "^requirepass" "${REDIS_CONF}" || echo "requirepass ${REDIS_PASS}" >> "${REDIS_CONF}"
    sed -i "s/^bind .*/bind 127.0.0.1 ::1/" "${REDIS_CONF}"
    grep -q "^maxmemory " "${REDIS_CONF}" || echo "maxmemory 512mb" >> "${REDIS_CONF}"
    grep -q "^maxmemory-policy" "${REDIS_CONF}" || echo "maxmemory-policy allkeys-lru" >> "${REDIS_CONF}"
fi

systemctl enable redis-server --now 2>/dev/null || systemctl enable redis --now 2>/dev/null
systemctl restart redis-server 2>/dev/null || systemctl restart redis 2>/dev/null
success "Redis configured with password auth."

# ── System Users ──────────────────────────────────────────────────────────────
info "Creating system users..."

if ! id "${ORBIT_USER}" &>/dev/null; then
    useradd --system --no-create-home --home-dir "${ORBIT_BASE}" --shell /usr/sbin/nologin "${ORBIT_USER}"
    success "Created service user: ${ORBIT_USER}"
fi

if ! id "${CLI_ADMIN_USER}" &>/dev/null; then
    useradd --create-home --shell /bin/bash --comment "Orbit CLI Administrator" "${CLI_ADMIN_USER}"
    success "Created CLI admin: ${CLI_ADMIN_USER}"
fi
echo "${CLI_ADMIN_USER}:${CLI_ADMIN_PASS}" | chpasswd

# Restricted sudo for orbit services
cat > "/etc/sudoers.d/orbit-cli-admin" << SUDO_EOF
${CLI_ADMIN_USER} ALL=(ALL) NOPASSWD: /bin/systemctl start orbit-*, /bin/systemctl stop orbit-*, /bin/systemctl restart orbit-*, /bin/systemctl status orbit-*, /bin/systemctl reload orbit-*
${CLI_ADMIN_USER} ALL=(ALL) NOPASSWD: /usr/bin/journalctl -u orbit-*
SUDO_EOF
chmod 0440 "/etc/sudoers.d/orbit-cli-admin"

# Disable root SSH
SSHD_CONF="/etc/ssh/sshd_config"
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' "${SSHD_CONF}"
grep -q "^PermitRootLogin" "${SSHD_CONF}" || echo "PermitRootLogin no" >> "${SSHD_CONF}"
systemctl reload sshd 2>/dev/null || systemctl reload ssh 2>/dev/null || true
success "Root SSH login disabled."

# ── Directory Structure ───────────────────────────────────────────────────────
info "Creating directory structure..."

mkdir -p "${ORBIT_BASE}" "${ORBIT_LOG}"

# ── Self-Signed TLS Certificate ──────────────────────────────────────────────
info "Generating self-signed TLS certificate..."

SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
mkdir -p "${ORBIT_BASE}/certs"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "${ORBIT_BASE}/certs/orbit.key" \
    -out    "${ORBIT_BASE}/certs/orbit.crt" \
    -subj   "/C=US/ST=State/L=City/O=Orbit/OU=IT/CN=${SERVER_FQDN}" \
    -addext "subjectAltName=DNS:${SERVER_FQDN},IP:${SERVER_IP:-127.0.0.1}" \
    2>/dev/null

chmod 600 "${ORBIT_BASE}/certs/orbit.key"
success "TLS certificate generated."

# =============================================================================
# MODULE INSTALLATION FUNCTION
# =============================================================================
install_module() {
    local MOD_NAME="$1"
    local MOD_LABEL="$2"
    local MOD_PORT="$3"
    local DB_NAME="$4"
    local DB_USER="$5"
    local DB_PASS="$6"
    local SECRET_KEY="$7"
    local MOD_SRC="${MODULES_DIR}/${MOD_NAME}"
    local MOD_DST="${ORBIT_BASE}/${MOD_NAME}"
    local MOD_VENV="${MOD_DST}/venv"

    echo ""
    echo -e "${BOLD}${BLUE}━━━ Installing ${MOD_LABEL} ━━━${NC}"

    # Copy module files
    info "Copying ${MOD_LABEL} files..."
    cp -r "${MOD_SRC}" "${MOD_DST}"
    success "Files copied to ${MOD_DST}"

    # Create virtual environment
    info "Creating Python virtual environment..."
    ${PYTHON_BIN} -m venv "${MOD_VENV}"
    "${MOD_VENV}/bin/pip" install --upgrade pip setuptools wheel -q
    success "Virtual environment ready."

    # Install dependencies
    info "Installing Python packages for ${MOD_LABEL}..."
    "${MOD_VENV}/bin/pip" install -r "${MOD_DST}/requirements.txt" --no-cache-dir -q \
        || die "Failed to install packages for ${MOD_LABEL}."
    "${MOD_VENV}/bin/pip" install gevent -q
    success "Packages installed."

    # Generate .env file
    info "Generating .env configuration..."

    local FERNET_KEY
    FERNET_KEY=$("${MOD_VENV}/bin/python" -c \
        "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" \
        2>/dev/null || openssl rand -base64 32)

    cat > "${MOD_DST}/.env" <<ENVEOF
# Orbit Platform — ${MOD_LABEL} Configuration
# Generated by installer on $(date -Iseconds)

FLASK_ENV=production
SECRET_KEY=${SECRET_KEY}
FERNET_KEY=${FERNET_KEY}

# Database
DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}

# Redis
CELERY_BROKER_URL=redis://:${REDIS_PASS}@127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://:${REDIS_PASS}@127.0.0.1:6379/1
CACHE_REDIS_URL=redis://:${REDIS_PASS}@127.0.0.1:6379/2

# Server
SERVER_NAME=${SERVER_FQDN}
APP_PORT=${MOD_PORT}
ENVEOF

    # Module-specific .env additions
    case "${MOD_NAME}" in
        webex-calling)
            cat >> "${MOD_DST}/.env" <<ENVEOF

# Webex API
WEBEX_CLIENT_ID=${WEBEX_CLIENT_ID}
WEBEX_CLIENT_SECRET=${WEBEX_CLIENT_SECRET}
WEBEX_ORG_ID=${WEBEX_ORG_ID}
ENVEOF
            ;;
        teams-hub)
            cat >> "${MOD_DST}/.env" <<ENVEOF

# Azure AD / Microsoft Graph
AZURE_TENANT_ID=${AZURE_TENANT_ID}
AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
AZURE_CLIENT_SECRET=${AZURE_CLIENT_SECRET}
ENVEOF
            ;;
        cisco-uc)
            cat >> "${MOD_DST}/.env" <<ENVEOF

# CUCM
CUCM_HOST=${CUCM_HOST}
CUCM_USERNAME=${CUCM_USER_CRED}
CUCM_PASSWORD=${CUCM_PASS}
CUCM_AXL_VERSION=${CUCM_VERSION}

# Unity Connection
UNITY_HOST=${UNITY_HOST}
UNITY_USERNAME=${UNITY_USER_CRED}
UNITY_PASSWORD=${UNITY_PASS}

# IM & Presence
IMP_HOST=${IMP_HOST}
IMP_USERNAME=${IMP_USER_CRED}
IMP_PASSWORD=${IMP_PASS}

# Expressway
EXPRESSWAY_HOST=${EXPY_HOST}
EXPRESSWAY_USERNAME=${EXPY_USER_CRED}
EXPRESSWAY_PASSWORD=${EXPY_PASS}
ENVEOF
            ;;
    esac

    chmod 600 "${MOD_DST}/.env"
    success ".env configuration written."

    # Run database migrations
    info "Running database migrations..."
    cd "${MOD_DST}"
    export FLASK_ENV=production
    export FLASK_APP="app:create_app()"

    # Source .env for migrations
    set -a; source "${MOD_DST}/.env"; set +a

    "${MOD_VENV}/bin/flask" db migrate -m "initial" 2>/dev/null || true
    "${MOD_VENV}/bin/flask" db upgrade 2>/dev/null \
        || warn "Migration may need manual attention for ${MOD_LABEL}."
    success "Database migrated."

    # Create admin user
    info "Creating admin user..."
    "${MOD_VENV}/bin/flask" admin create-admin \
        --username "${ADMIN_USER}" \
        --email "${ADMIN_EMAIL}" \
        --password "${ADMIN_PASS}" 2>/dev/null \
        || warn "Admin user creation needs manual attention for ${MOD_LABEL}."
    success "Admin user '${ADMIN_USER}' created."

    # Set ownership
    chown -R "${ORBIT_USER}:${ORBIT_GROUP}" "${MOD_DST}"
    chmod 750 "${MOD_DST}"

    # Create systemd service — Gunicorn
    local SVC_NAME="orbit-${MOD_NAME}"
    cat > "/etc/systemd/system/${SVC_NAME}.service" <<SVCEOF
[Unit]
Description=Orbit ${MOD_LABEL} — Gunicorn
After=network.target postgresql.service redis-server.service
Requires=postgresql.service

[Service]
Type=notify
User=${ORBIT_USER}
Group=${ORBIT_GROUP}
WorkingDirectory=${MOD_DST}
EnvironmentFile=${MOD_DST}/.env
ExecStart=${MOD_VENV}/bin/gunicorn wsgi:application \\
    --bind 127.0.0.1:${MOD_PORT} \\
    --workers ${GUNICORN_WORKERS} \\
    --worker-class gevent \\
    --timeout 120 \\
    --access-logfile ${ORBIT_LOG}/${MOD_NAME}-access.log \\
    --error-logfile ${ORBIT_LOG}/${MOD_NAME}-error.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

    # Create systemd service — Celery Worker
    cat > "/etc/systemd/system/${SVC_NAME}-celery.service" <<SVCEOF
[Unit]
Description=Orbit ${MOD_LABEL} — Celery Worker
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=forking
User=${ORBIT_USER}
Group=${ORBIT_GROUP}
WorkingDirectory=${MOD_DST}
EnvironmentFile=${MOD_DST}/.env
ExecStart=${MOD_VENV}/bin/celery -A celery_worker.celery multi start worker1 \\
    --concurrency=${CELERY_CONCURRENCY} \\
    --loglevel=info \\
    --logfile=${ORBIT_LOG}/${MOD_NAME}-celery-%%n.log \\
    --pidfile=/tmp/${SVC_NAME}-celery-%%n.pid
ExecStop=${MOD_VENV}/bin/celery -A celery_worker.celery multi stopwait worker1 \\
    --pidfile=/tmp/${SVC_NAME}-celery-%%n.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF

    # Create systemd service — Celery Beat
    cat > "/etc/systemd/system/${SVC_NAME}-beat.service" <<SVCEOF
[Unit]
Description=Orbit ${MOD_LABEL} — Celery Beat Scheduler
After=network.target redis-server.service ${SVC_NAME}-celery.service

[Service]
Type=simple
User=${ORBIT_USER}
Group=${ORBIT_GROUP}
WorkingDirectory=${MOD_DST}
EnvironmentFile=${MOD_DST}/.env
ExecStart=${MOD_VENV}/bin/celery -A celery_worker.celery beat \\
    --loglevel=info \\
    --logfile=${ORBIT_LOG}/${MOD_NAME}-beat.log \\
    --schedule=/tmp/${SVC_NAME}-celerybeat-schedule
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF

    success "${MOD_LABEL} services created."

    # Enable and start services
    systemctl daemon-reload
    systemctl enable "${SVC_NAME}" "${SVC_NAME}-celery" "${SVC_NAME}-beat" --now 2>/dev/null || true
    success "${MOD_LABEL} services started."
}

# =============================================================================
# INSTALL SELECTED MODULES
# =============================================================================

PROGRESS=0
TOTAL=0
${INSTALL_WEBEX} && TOTAL=$((TOTAL + 1))
${INSTALL_TEAMS} && TOTAL=$((TOTAL + 1))
${INSTALL_CISCO} && TOTAL=$((TOTAL + 1))

if ${INSTALL_WEBEX}; then
    PROGRESS=$((PROGRESS + 1))
    info "[${PROGRESS}/${TOTAL}] Installing Webex Calling module..."
    install_module "webex-calling" "Webex Calling" "${PORT_WEBEX}" \
        "orbit_webex" "orbit_webex" "${DB_PASS_WEBEX}" "${SECRET_KEY_WEBEX}"
fi

if ${INSTALL_TEAMS}; then
    PROGRESS=$((PROGRESS + 1))
    info "[${PROGRESS}/${TOTAL}] Installing Microsoft Teams module..."
    install_module "teams-hub" "Microsoft Teams" "${PORT_TEAMS}" \
        "orbit_teams" "orbit_teams" "${DB_PASS_TEAMS}" "${SECRET_KEY_TEAMS}"
fi

if ${INSTALL_CISCO}; then
    PROGRESS=$((PROGRESS + 1))
    info "[${PROGRESS}/${TOTAL}] Installing Cisco UC module..."
    install_module "cisco-uc" "Cisco UC" "${PORT_CISCO}" \
        "orbit_cisco" "orbit_cisco" "${DB_PASS_CISCO}" "${SECRET_KEY_CISCO}"
fi

# =============================================================================
# NGINX REVERSE PROXY
# =============================================================================
echo ""
echo -e "${BOLD}${BLUE}━━━ Configuring Nginx Reverse Proxy ━━━${NC}"

# Landing page
mkdir -p "${ORBIT_BASE}/landing"
cat > "${ORBIT_BASE}/landing/index.html" <<'HTMLEOF'
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Orbit Platform</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<style>
:root { --bg:#0f1117; --card:#1a1d27; --text:#e4e7ef; --muted:#9ca3b4; --accent:#3b82f6; --border:#2d3348; }
[data-theme="light"] { --bg:#f5f7fa; --card:#ffffff; --text:#1a1d27; --muted:#6b7280; --accent:#2563eb; --border:#e5e7eb; }
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px}
.header{text-align:center;margin-bottom:48px}
.header i{font-size:56px;color:var(--accent);margin-bottom:16px}
.header h1{font-size:32px;margin-bottom:8px}
.header p{color:var(--muted);font-size:15px}
.modules{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px;max-width:960px;width:100%}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:32px;text-align:center;transition:transform 0.2s,box-shadow 0.2s;text-decoration:none;color:var(--text)}
.card:hover{transform:translateY(-4px);box-shadow:0 8px 32px rgba(0,0,0,0.3)}
.card i{font-size:40px;color:var(--accent);margin-bottom:16px}
.card h2{font-size:18px;margin-bottom:8px}
.card p{color:var(--muted);font-size:13px;line-height:1.5}
.card .status{display:inline-block;margin-top:12px;padding:4px 12px;border-radius:12px;font-size:11px;font-weight:600}
.card .active{background:rgba(16,185,129,0.15);color:#10b981}
.card .inactive{background:rgba(107,114,128,0.15);color:#6b7280}
.theme-toggle{position:fixed;top:20px;right:20px;background:var(--card);border:1px solid var(--border);border-radius:50%;width:44px;height:44px;cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--text);font-size:18px}
.footer{margin-top:48px;color:var(--muted);font-size:12px}
</style>
</head>
<body>
<button class="theme-toggle" onclick="toggleTheme()" title="Toggle theme"><i class="fas fa-sun" id="theme-icon"></i></button>
<div class="header">
  <i class="fas fa-satellite-dish"></i>
  <h1>Orbit Platform</h1>
  <p>Unified Communications Management</p>
</div>
<div class="modules" id="modules"></div>
<div class="footer">Orbit Platform &copy; 2024</div>
<script>
const modules = [
HTMLEOF

# Dynamically add module cards based on what was installed
if ${INSTALL_WEBEX}; then
    cat >> "${ORBIT_BASE}/landing/index.html" <<HTMLEOF
  {name:"Webex Calling",icon:"fa-phone",desc:"Cisco Webex Calling provisioning & management",url:"/webex/",active:true},
HTMLEOF
fi
if ${INSTALL_TEAMS}; then
    cat >> "${ORBIT_BASE}/landing/index.html" <<HTMLEOF
  {name:"Microsoft Teams",icon:"fa-users",desc:"Microsoft Teams administration via Graph API",url:"/teams/",active:true},
HTMLEOF
fi
if ${INSTALL_CISCO}; then
    cat >> "${ORBIT_BASE}/landing/index.html" <<HTMLEOF
  {name:"Cisco UC",icon:"fa-server",desc:"CUCM, Unity Connection, IM&P, Expressway",url:"/cisco-uc/",active:true},
HTMLEOF
fi

cat >> "${ORBIT_BASE}/landing/index.html" <<'HTMLEOF'
];
const container=document.getElementById('modules');
modules.forEach(m=>{
  const a=document.createElement('a');a.className='card';a.href=m.url;
  a.innerHTML=`<i class="fas ${m.icon}"></i><h2>${m.name}</h2><p>${m.desc}</p><span class="status ${m.active?'active':'inactive'}">${m.active?'Active':'Not Installed'}</span>`;
  container.appendChild(a);
});
function toggleTheme(){
  const t=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
  document.documentElement.setAttribute('data-theme',t);
  document.getElementById('theme-icon').className=t==='dark'?'fas fa-sun':'fas fa-moon';
  localStorage.setItem('orbit-theme',t);
}
(function(){const t=localStorage.getItem('orbit-theme')||'dark';document.documentElement.setAttribute('data-theme',t);document.getElementById('theme-icon').className=t==='dark'?'fas fa-sun':'fas fa-moon';})();
</script>
</body>
</html>
HTMLEOF

chown -R "${ORBIT_USER}:${ORBIT_GROUP}" "${ORBIT_BASE}/landing"

# Nginx configuration
cat > "/etc/nginx/sites-available/orbit" <<NGXEOF
# Orbit Platform — Nginx Reverse Proxy
# Generated by installer on $(date -Iseconds)

server {
    listen 80;
    server_name ${SERVER_FQDN};
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${SERVER_FQDN};

    ssl_certificate     ${ORBIT_BASE}/certs/orbit.crt;
    ssl_certificate_key ${ORBIT_BASE}/certs/orbit.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    client_max_body_size 50M;

    # Landing page
    location = / {
        root ${ORBIT_BASE}/landing;
        index index.html;
    }
    location = /index.html {
        root ${ORBIT_BASE}/landing;
    }

NGXEOF

if ${INSTALL_WEBEX}; then
    cat >> "/etc/nginx/sites-available/orbit" <<NGXEOF
    # Webex Calling module
    location /webex/ {
        proxy_pass http://127.0.0.1:${PORT_WEBEX}/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Script-Name /webex;
        proxy_read_timeout 300;
    }

NGXEOF
fi

if ${INSTALL_TEAMS}; then
    cat >> "/etc/nginx/sites-available/orbit" <<NGXEOF
    # Microsoft Teams module
    location /teams/ {
        proxy_pass http://127.0.0.1:${PORT_TEAMS}/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Script-Name /teams;
        proxy_read_timeout 300;
    }

NGXEOF
fi

if ${INSTALL_CISCO}; then
    cat >> "/etc/nginx/sites-available/orbit" <<NGXEOF
    # Cisco UC module
    location /cisco-uc/ {
        proxy_pass http://127.0.0.1:${PORT_CISCO}/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Script-Name /cisco-uc;
        proxy_read_timeout 300;
    }

NGXEOF
fi

echo "}" >> "/etc/nginx/sites-available/orbit"

# Enable the site
ln -sf /etc/nginx/sites-available/orbit /etc/nginx/sites-enabled/orbit
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

nginx -t 2>/dev/null && systemctl restart nginx && success "Nginx configured and restarted." \
    || warn "Nginx configuration test failed — check /etc/nginx/sites-available/orbit"

systemctl enable nginx --now 2>/dev/null || true

# =============================================================================
# LOG ROTATION
# =============================================================================
cat > "/etc/logrotate.d/orbit" <<LOGEOF
${ORBIT_LOG}/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
LOGEOF

# Set ownership on log directory
chown -R "${ORBIT_USER}:${ORBIT_GROUP}" "${ORBIT_LOG}"

# =============================================================================
# FIREWALL
# =============================================================================
if command -v ufw &>/dev/null; then
    ufw allow 80/tcp  >/dev/null 2>&1 || true
    ufw allow 443/tcp >/dev/null 2>&1 || true
    ufw allow 22/tcp  >/dev/null 2>&1 || true
    success "UFW rules added (22, 80, 443)."
elif command -v firewall-cmd &>/dev/null; then
    firewall-cmd --permanent --add-service=http  >/dev/null 2>&1 || true
    firewall-cmd --permanent --add-service=https >/dev/null 2>&1 || true
    firewall-cmd --permanent --add-service=ssh   >/dev/null 2>&1 || true
    firewall-cmd --reload >/dev/null 2>&1 || true
    success "Firewalld rules added (ssh, http, https)."
fi

# =============================================================================
# COMPLETION SCREEN
# =============================================================================
echo ""
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${GREEN}  Orbit Platform — Installation Complete!              ${NC}"
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

SUMMARY="Installation complete!\n\n"
SUMMARY+="Landing Page:\n  https://${SERVER_FQDN}/\n\n"
SUMMARY+="Installed Modules:\n"

if ${INSTALL_WEBEX}; then
    SUMMARY+="  Webex Calling:    https://${SERVER_FQDN}/webex/\n"
    SUMMARY+="    Service:  systemctl status orbit-webex-calling\n"
    SUMMARY+="    Logs:     ${ORBIT_LOG}/webex-calling-*.log\n\n"
    echo -e "  ${GREEN}Webex Calling${NC}:   https://${SERVER_FQDN}/webex/"
fi

if ${INSTALL_TEAMS}; then
    SUMMARY+="  Microsoft Teams:  https://${SERVER_FQDN}/teams/\n"
    SUMMARY+="    Service:  systemctl status orbit-teams-hub\n"
    SUMMARY+="    Logs:     ${ORBIT_LOG}/teams-hub-*.log\n\n"
    echo -e "  ${GREEN}Microsoft Teams${NC}: https://${SERVER_FQDN}/teams/"
fi

if ${INSTALL_CISCO}; then
    SUMMARY+="  Cisco UC:         https://${SERVER_FQDN}/cisco-uc/\n"
    SUMMARY+="    Service:  systemctl status orbit-cisco-uc\n"
    SUMMARY+="    Logs:     ${ORBIT_LOG}/cisco-uc-*.log\n\n"
    echo -e "  ${GREEN}Cisco UC${NC}:        https://${SERVER_FQDN}/cisco-uc/"
fi

SUMMARY+="Credentials:\n"
SUMMARY+="  Web Admin:  ${ADMIN_USER} / ${ADMIN_EMAIL}\n"
SUMMARY+="  CLI Admin:  ${CLI_ADMIN_USER} (SSH access)\n\n"
SUMMARY+="Service Management:\n"
SUMMARY+="  sudo systemctl {start|stop|restart|status} orbit-<module>\n\n"
SUMMARY+="Logs:\n  ${ORBIT_LOG}/\n\n"
SUMMARY+="Install log: ${INSTALL_LOG}\n"

echo ""
echo -e "  ${CYAN}Web Admin${NC}:   ${ADMIN_USER} / ${ADMIN_EMAIL}"
echo -e "  ${CYAN}CLI Admin${NC}:   ${CLI_ADMIN_USER}"
echo -e "  ${CYAN}Landing Page${NC}: https://${SERVER_FQDN}/"
echo ""

# Show final whiptail summary
${DIALOG} --title "  Installation Complete!  " --msgbox "${SUMMARY}" $DLG_H $DLG_W 2>/dev/null || true

echo -e "${GREEN}Done! Access the Orbit landing page at: https://${SERVER_FQDN}/${NC}"
echo ""
