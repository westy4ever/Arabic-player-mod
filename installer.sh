#!/bin/sh

# ArabicPlayer Enigma2 Plugin Installer
# Professional Script for Novaler 4K Pro and other E2 devices

PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/ArabicPlayer"
GITHUB_USER="asdrere123-alt"
REPO_NAME="ArabicPlayer"
TMP_DIR="/tmp/arabicplayer_install"

echo "========================================================="
echo "   ArabicPlayer Installer - Modern Premium UI Version    "
echo "========================================================="

# 1. Cleanup old version
if [ -d "$PLUGIN_PATH" ]; then
    echo "> Removing existing installation..."
    rm -rf "$PLUGIN_PATH"
fi

# 2. Dependency Check (Optional but helpful)
echo "> Checking dependencies..."
# Add any specific opkg packages if needed, e.g., python3-requests
# opkg update > /dev/null 2>&1
# opkg install python3-requests > /dev/null 2>&1

# 3. Download and Extract
echo "> Downloading latest version from GitHub..."
mkdir -p "$TMP_DIR"
cd "$TMP_DIR"

wget -q "--no-check-certificate" "https://github.com/$GITHUB_USER/$REPO_NAME/archive/refs/heads/main.tar.gz" -O main.tar.gz
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to download from GitHub!"
    exit 1
fi

echo "> Extracting files..."
tar -xzf main.tar.gz
CP_DIR=$(ls -d */ | grep "$REPO_NAME")
mv "$CP_DIR" "/usr/lib/enigma2/python/Plugins/Extensions/ArabicPlayer"

# 4. Final Cleanup
echo "> Cleaning up temporary files..."
rm -rf "$TMP_DIR"

# 5. Success and Restart
echo "========================================================="
echo "   ArabicPlayer INSTALLED SUCCESSFULLY!                  "
echo "   Restarting Enigma2 to load the new Premium UI...      "
echo "========================================================="

# Auto-restart Enigma2 (Ultra-robust approach)
echo "> Sending restart command..."
# Try Web Interface first (Most reliable across all images)
wget -qO - http://127.0.0.1/web/powerstate?newstate=3 > /dev/null 2>&1

# Fallbacks
if [ -f /usr/bin/systemctl ]; then
    systemctl restart enigma2
elif [ -f /sbin/init ]; then
    killall -9 enigma2 > /dev/null 2>&1
    init 4 && sleep 1 && init 3
else
    killall -9 enigma2
fi

exit 0

exit 0
