#!/bin/sh
# ==============================================================================
#           MOHAMED STORE - SMART ONE-TIME TELNET INSTALLER
# ==============================================================================
# Repository: wwwgoper77-wq/MohamedStore (main)
# Note: You only need to run this command ONCE via Telnet/SSH.
# All future items, plugins, skins, and tools added to GitHub will automatically 
# appear inside Mohamed Store on your Enigma2 box without re-running this script.
# ==============================================================================

PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore"
BASE_URL="https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main"

echo ""
echo "=========================================================="
echo "          Installing Mohamed Store Enigma2 Plugin         "
echo "=========================================================="
echo ""

# 1. Check & Install required packages (curl, wget, python-json/python3-json)
echo "Checking receiver dependencies..."
if command -v opkg >/dev/null 2>&1; then
    opkg update >/dev/null 2>&1
    opkg install wget curl >/dev/null 2>&1
    # Check Python version
    if python --version 2>&1 | grep -q "Python 3"; then
        opkg install python3-json python3-urllib >/dev/null 2>&1
    else
        opkg install python-json python-urllib2 >/dev/null 2>&1
    fi
fi

# 2. Prepare Plugin Directory Structure
echo "Preparing plugin directories..."
rm -rf "$PLUGIN_DIR" 2>/dev/null
mkdir -p "$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR/images"
mkdir -p "$PLUGIN_DIR/images/Icons"

# 3. Download Core Plugin Files from GitHub
echo "Downloading core plugin files from GitHub..."
wget --no-check-certificate -q -O "$PLUGIN_DIR/plugin.py" "$BASE_URL/plugin.py"
wget --no-check-certificate -q -O "$PLUGIN_DIR/__init__.py" "$BASE_URL/__init__.py"
wget --no-check-certificate -q -O "$PLUGIN_DIR/plugin.png" "$BASE_URL/plugin.png" 2>/dev/null || true

# 4. Download Section Icons
echo "Downloading section icons..."
wget --no-check-certificate -q -O "$PLUGIN_DIR/images/logo.png" "$BASE_URL/images/logo.png" 2>/dev/null || true
wget --no-check-certificate -q -O "$PLUGIN_DIR/images/background.png" "$BASE_URL/images/background.png" 2>/dev/null || true

wget --no-check-certificate -q -O "$PLUGIN_DIR/images/Icons/plugins.png" "$BASE_URL/images/Icons/plugins.png" 2>/dev/null || true
wget --no-check-certificate -q -O "$PLUGIN_DIR/images/Icons/skins.png" "$BASE_URL/images/Icons/skins.png" 2>/dev/null || true
wget --no-check-certificate -q -O "$PLUGIN_DIR/images/Icons/tools.png" "$BASE_URL/images/Icons/tools.png" 2>/dev/null || true
wget --no-check-certificate -q -O "$PLUGIN_DIR/images/Icons/system_images.png" "$BASE_URL/images/Icons/system_images.png" 2>/dev/null || true
wget --no-check-certificate -q -O "$PLUGIN_DIR/images/Icons/picons.png" "$BASE_URL/images/Icons/picons.png" 2>/dev/null || true
wget --no-check-certificate -q -O "$PLUGIN_DIR/images/Icons/channels.png" "$BASE_URL/images/Icons/channels.png" 2>/dev/null || true

# 5. Pre-fetch initial index.json
echo "Fetching latest store index catalog..."
wget --no-check-certificate -q -O "$PLUGIN_DIR/index.json" "$BASE_URL/index.json" 2>/dev/null || true

# 6. Cleanup stale python bytecodes
echo "Cleaning up temporary files..."
find "$PLUGIN_DIR" -name "*.pyc" -delete 2>/dev/null
find "$PLUGIN_DIR" -name "__pycache__" -exec rm -rf {} ; 2>/dev/null

# 7. Set execution permissions
chmod -R 755 "$PLUGIN_DIR"

sync

echo ""
echo "=========================================================="
echo "   SUCCESS: Mohamed Store installed successfully!        "
echo "   Restarting Enigma2 UI in 3 seconds...                  "
echo "=========================================================="
echo ""

sleep 3

# Restart Enigma2 safely
if command -v systemctl >/dev/null 2>&1; then
    systemctl restart enigma2 2>/dev/null || killall -9 enigma2
else
    killall -9 enigma2
fi

exit 0
