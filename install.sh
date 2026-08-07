#!/bin/sh

PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore"
BASE_URL="https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main"

echo "========================================="
echo "   Installing Mohamed Store..."
echo "========================================="

# حذف المجلد القديم لضمان نظافة التثبيت
rm -rf "$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR"

echo "Downloading plugin core..."
wget -O "$PLUGIN_DIR/plugin.py" "$BASE_URL/plugin.py"
wget -O "$PLUGIN_DIR/plugin.png" "$BASE_URL/plugin.png"
wget -O "$PLUGIN_DIR/__init__.py" "$BASE_URL/__init__.py"

echo "Downloading all updated files & assets from repository..."
# سحب الملف المضغوط الشامل الذي يجهزه الـ GitHub Actions
wget -q --no-check-certificate -O "/tmp/store_files.tar.gz" "$BASE_URL/store_files.tar.gz"

if [ -s "/tmp/store_files.tar.gz" ]; then
    tar -xzf "/tmp/store_files.tar.gz" -C "$PLUGIN_DIR/"
    rm -f "/tmp/store_files.tar.gz"
    echo "All files extracted successfully."
else
    echo "Error: Failed to download archive! Ensure Actions is running on GitHub."
fi

# تنظيف الملفات المؤقتة
find "$PLUGIN_DIR" -name "*.pyc" -delete 2>/dev/null
find "$PLUGIN_DIR" -name "__pycache__" -exec rm -rf {} \; 2>/dev/null

chmod -R 755 "$PLUGIN_DIR"

sync

echo "Restarting Enigma2..."
sleep 2
killall -9 enigma2

exit 0
