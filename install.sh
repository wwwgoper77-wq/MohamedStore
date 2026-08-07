#!/bin/sh

# مسار تثبيت البلجن
PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore"
# رابط تحميل كامل المستودع كملف مضغوط من GitHub
REPO_URL="https://github.com/wwwgoper77-wq/MohamedStore/archive/refs/heads/main.tar.gz"

echo "========================================="
echo "   Installing Full Project..."
echo "========================================="

# 1. حذف المجلد القديم بالكامل
rm -rf "$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR"

# 2. تحميل كامل المشروع من GitHub
echo "Downloading repository archive..."
wget -q --no-check-certificate -O "/tmp/repo.tar.gz" "$REPO_URL"

# 3. فك الضغط (استخدام strip-components=1 لإزالة المجلد الرئيسي المزعج للمستودع)
if [ -f "/tmp/repo.tar.gz" ]; then
    tar -xzf "/tmp/repo.tar.gz" -C "$PLUGIN_DIR" --strip-components=1
    rm -f "/tmp/repo.tar.gz"
    echo "Project installed successfully!"
else
    echo "Error: Download failed!"
fi

# 4. تنظيف الملفات غير الضرورية
find "$PLUGIN_DIR" -name "*.pyc" -delete 2>/dev/null
find "$PLUGIN_DIR" -name "__pycache__" -exec rm -rf {} \; 2>/dev/null

# 5. ضبط الصلاحيات
chmod -R 755 "$PLUGIN_DIR"

sync
echo "Restarting Enigma2..."
sleep 2
killall -9 enigma2

exit 0
