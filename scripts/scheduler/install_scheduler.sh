#!/bin/bash
# install_scheduler.sh — Install WACH Insight ETL Scheduler as LaunchAgent
#
# This script creates the LaunchAgent plist file and loads it.
# The scheduler runs automatically on login and restarts if it crashes.
#
# Usage:
#   bash scripts/install_scheduler.sh [--uninstall]
#
# Options:
#   --uninstall    Remove the LaunchAgent
#   -h, --help     Show this help message

set -e  # Exit on error

# Project directory
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_PYTHON="${PROJECT_DIR}/venv/bin/python"
SCRIPTS_DIR="${PROJECT_DIR}/scripts/scheduler"

# Path for LaunchAgent
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="${LAUNCH_AGENTS_DIR}/com.wach.insight.scheduler.plist"

# Function to show help
show_help() {
    echo "WACH Insight Scheduler Installation"
    echo ""
    echo "Usage: bash scripts/install_scheduler.sh [--uninstall]"
    echo ""
    echo "Options:"
    echo "  --uninstall    Remove the LaunchAgent"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "Description:"
    echo "  This script installs the ETL scheduler as a macOS LaunchAgent."
    echo "  The scheduler runs every 30 minutes to:"
    echo "    1. Fetch energy data from InfluxDB"
    echo "    2. Compute predictions and health scores"
    echo "    3. Update CSV files for the dashboard"
    echo ""
    echo "After installation, the scheduler:"
    echo "  - Runs automatically on login"
    echo "  - Runs every 30 minutes"
    echo "  - Automatically restarts if it crashes"
    echo ""
}

# Check if Python exists
if [[ ! -f "${VENV_PYTHON}" ]]; then
    echo "[ERROR] Python venv not found at ${PROJECT_DIR}/venv/bin/python"
    echo "Please create the virtual environment first:"
    echo "  python -m venv venv"
    exit 1
fi

# Check if scheduler.sh exists
if [[ ! -f "${SCRIPTS_DIR}/scheduler.sh" ]]; then
    echo "[ERROR] scheduler.sh not found at ${SCRIPTS_DIR}/scheduler.sh"
    exit 1
fi

# Parse arguments
UNINSTALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Ensure LaunchAgents directory exists
mkdir -p "${LAUNCH_AGENTS_DIR}"

# Check if already installed
if [[ -f "${PLIST_FILE}" ]]; then
    echo "[INFO] LaunchAgent already installed at:"
    echo "  ${PLIST_FILE}"
    
    if [[ "${UNINSTALL}" == "true" ]]; then
        echo ""
        echo "[INFO] Uninstalling LaunchAgent..."
        
        # Stop the agent if running
        if launchctl list | grep -q "com.wach.insight.scheduler"; then
            echo "[INFO] Stopping scheduler..."
            launchctl stop com.wach.insight.scheduler 2>/dev/null || true
        fi
        
        # Unload the agent
        echo "[INFO] Unloading LaunchAgent..."
        launchctl unload "${PLIST_FILE}" 2>/dev/null || true
        
        # Remove the file
        rm -f "${PLIST_FILE}"
        
        echo "[OK] LaunchAgent uninstalled successfully"
        exit 0
    else
        echo ""
        echo "[INFO] To reinstall, first uninstall:"
        echo "  bash scripts/install_scheduler.sh --uninstall"
        exit 0
    fi
fi

# Check if already loaded (for reinstallation without remove)
if launchctl list | grep -q "com.wach.insight.scheduler"; then
    echo "[WARN] LaunchAgent is already loaded!"
    echo "Use --uninstall to remove it first."
    exit 1
fi

# Create the LaunchAgent plist
echo "[INFO] Creating LaunchAgent..."
cat > "${PLIST_FILE}" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>

  <!-- Unique identifier for this agent -->
  <key>Label</key>
  <string>com.wach.insight.scheduler</string>

  <!-- Command to run -->
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${SCRIPTS_DIR}/scheduler.sh</string>
  </array>

  <!-- Working directory (project root) -->
  <key>WorkingDirectory</key>
  <string>${PROJECT_DIR}</string>

  <!-- Environment variables -->
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>${PROJECT_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>

  <!-- Log files -->
  <key>StandardOutPath</key>
  <string>${PROJECT_DIR}/logs/scheduler.log</string>
  <key>StandardErrorPath</key>
  <string>${PROJECT_DIR}/logs/scheduler-error.log</string>

  <!-- Auto-restart if it crashes -->
  <key>KeepAlive</key>
  <true/>

  <!-- Start on login -->
  <key>RunAtLoad</key>
  <true/>

  <!-- Throttle interval (seconds between restarts) -->
  <key>ThrottleInterval</key>
  <integer>10</integer>

  <!-- Start_INTERVAL (seconds between runs) -->
  <!-- Note: Set to 1800 for every 30 minutes -->
  <key>StartInterval</key>
  <integer>1800</integer>

</dict>
</plist>
PLIST_EOF

# Get current username
CURRENT_USER=$(whoami)
PLIST_OWNER=$(stat -f "%Su" "${PLIST_FILE}" 2>/dev/null || echo "")

echo "[INFO] LaunchAgent created at:"
echo "  ${PLIST_FILE}"
echo ""
echo "[INFO] Configured:"
echo "  User: ${CURRENT_USER}"
echo "  Interval: Every 30 minutes (StartInterval: 1800)"
echo ""

# Set proper permissions
chmod 644 "${PLIST_FILE}"
chown "${CURRENT_USER}" "${PLIST_FILE}"

echo "[OK] Permissions set correctly"
echo ""

# Load the agent
echo "[INFO] Loading LaunchAgent..."
launchctl load "${PLIST_FILE}"

# Verify it loaded
if launchctl list | grep -q "com.wach.insight.scheduler"; then
    echo "[OK] LaunchAgent loaded successfully"
else
    echo "[ERROR] Failed to load LaunchAgent"
    exit 1
fi

# Display status
echo ""
echo "========================================="
echo "  Installation Complete!"
echo "========================================="
echo ""
echo "The scheduler is now running automatically."
echo ""
echo "View logs:"
echo "  tail -f ${PROJECT_DIR}/logs/scheduler.log"
echo ""
echo "Check status:"
echo "  launchctl list | grep wach.insight"
echo ""
echo "To uninstall:"
echo "  bash scripts/install_scheduler.sh --uninstall"
echo ""
echo "Manual control:"
echo "  launchctl start com.wach.insight.scheduler   # Start"
echo "  launchctl stop com.wach.insight.scheduler    # Stop"
echo "  launchctl restart com.wach.insight.scheduler # Restart"
