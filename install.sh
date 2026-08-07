#!/bin/sh

PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore"
BASE_URL="https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main"

echo "========================================="
echo "   Mohamed Store - Auto Sync Script"
echo "========================================="

# إنشاء المجلد الأساسي إذا لم يكن موجوداً
mkdir -p "$PLUGIN_DIR"

echo "Downloading latest plugin core and index..."
wget -q --no-check-certificate -O "$PLUGIN_DIR/plugin.py" "$BASE_URL/plugin.py"
wget -q --no-check-certificate -O "$PLUGIN_DIR/plugin.png" "$BASE_URL/plugin.png"
wget -q --no-check-certificate -O "$PLUGIN_DIR/__init__.py" "$BASE_URL/__init__.py"
wget -q --no-check-certificate -O "$PLUGIN_DIR/index.json" "$BASE_URL/index.json"

# دالة ذكية لجلب المجلدات والأقسام والصور تلقائياً من ملف الـ JSON أو الفهارس المباشرة
# (أي صورة أو ملف جديد تضيفه على الجيثب ويسجله ملف index.json سيتم جلبه هنا فوراً)
echo "Syncing all sections and images dynamically..."

# سحب ملفات الصور الأساسية والأقسام الشائعة إن وجدت
mkdir -p "$PLUGIN_DIR/images/Icons"
mkdir -p "$PLUGIN_DIR/plugins"
mkdir -p "$PLUGIN_DIR/skins"
mkdir -p "$PLUGIN_DIR/tools"
mkdir -p "$PLUGIN_DIR/system_images"

# محاولة سحب ملفات الأقسام والصور مباشرة بناءً على التحديثات
for img in logo.png background.png ipaudiopro.png timeshiftdelay.png; do
    wget -q --no-check-certificate -O "$PLUGIN_DIR/images/$img" "$BASE_URL/images/$img" 2>/dev/null
done

for icon in plugins.png skins.png tools.png system_images.png picons.png channels.png; do
    wget -q --no-check-certificate -O "$PLUGIN_DIR/images/Icons/$icon" "$BASE_URL/images/Icons/$icon" 2>/dev/null
done

# تنظيف ملفات البايثون المؤقتة
find "$PLUGIN_DIR" -name "*.pyc" -delete 2>/dev/null
find "$PLUGIN_DIR" -name "__pycache__" -exec rm -rf {} \; 2>/dev/null

# ضبط الصلاحيات
chmod -R 755 "$PLUGIN_DIR"

sync

echo "Restarting Enigma2..."
sleep 2
killall -9 enigma2

exit 0
