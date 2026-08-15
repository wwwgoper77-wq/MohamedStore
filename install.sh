#!/bin/sh

PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore"
BASE_URL="https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main"

echo "========================================="
echo "    Installing Mohamed Store..."
echo "========================================="

# حذف المجلد القديم لضمان نظافة التثبيت
rm -rf "$PLUGIN_DIR"

# إنشاء كافة المجلدات والهيكلية الأساسية والفرعية للصور والأقسام
mkdir -p "$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR/images"
mkdir -p "$PLUGIN_DIR/images/Icons"
mkdir -p "$PLUGIN_DIR/plugins"
mkdir -p "$PLUGIN_DIR/skins"
mkdir -p "$PLUGIN_DIR/tools"
mkdir -p "$PLUGIN_DIR/system_images"
mkdir -p "$PLUGIN_DIR/novaler"

echo "Downloading plugin core files..."
wget -O "$PLUGIN_DIR/plugin.py" "$BASE_URL/plugin.py"
wget -O "$PLUGIN_DIR/plugin.png" "$BASE_URL/plugin.png"
wget -O "$PLUGIN_DIR/__init__.py" "$BASE_URL/__init__.py"

echo "Downloading main images and logos..."
wget -O "$PLUGIN_DIR/images/logo.png" "$BASE_URL/images/logo.png"
wget -O "$PLUGIN_DIR/images/background.png" "$BASE_URL/images/background.png"
wget -O "$PLUGIN_DIR/images/ipaudiopro.png" "$BASE_URL/images/ipaudiopro.png"
wget -O "$PLUGIN_DIR/images/timeshiftdelay.png" "$BASE_URL/images/timeshiftdelay.png"
wget -O "$PLUGIN_DIR/images/avatar.png" "$BASE_URL/images/avatar.png"
wget -O "$PLUGIN_DIR/images/qrcode.png" "$BASE_URL/images/qrcode.png"
wget -O "$PLUGIN_DIR/images/novaler.png" "$BASE_URL/images/novaler.png"

echo "Downloading section icons..."
wget -O "$PLUGIN_DIR/images/Icons/plugins.png" "$BASE_URL/images/Icons/plugins.png"
wget -O "$PLUGIN_DIR/images/Icons/skins.png" "$BASE_URL/images/Icons/skins.png"
wget -O "$PLUGIN_DIR/images/Icons/tools.png" "$BASE_URL/images/Icons/tools.png"
wget -O "$PLUGIN_DIR/images/Icons/system_images.png" "$BASE_URL/images/Icons/system_images.png"
wget -O "$PLUGIN_DIR/images/Icons/picons.png" "$BASE_URL/images/Icons/picons.png"
wget -O "$PLUGIN_DIR/images/Icons/channels.png" "$BASE_URL/images/Icons/channels.png"
wget -O "$PLUGIN_DIR/images/Icons/novaler.png" "$BASE_URL/images/Icons/novaler.png"

# تنظيف ملفات البايثون المؤقتة
find "$PLUGIN_DIR" -name "*.pyc" -delete 2>/dev/null
find "$PLUGIN_DIR" -name "__pycache__" -exec rm -rf {} \; 2>/dev/null

# منح الصلاحيات الكاملة
chmod -R 755 "$PLUGIN_DIR"

sync

echo "Restarting Enigma2..."
sleep 2
killall -9 enigma2

exit 0
