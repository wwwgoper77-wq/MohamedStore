#!/bin/sh
# 1. تنظيف المسارات والروابط القديمة
rm -f /etc/tuxbox/satellites.xml /etc/enigma2/satellites.xml

URL1="https://raw.githubusercontent.com/oe-alliance/oe-alliance-plugins/master/xml/satellites.xml"
URL2="http://www.satellites-xml.org/satellites.xml"
DEST="/etc/tuxbox/satellites.xml"

# 2. محاولة التنزيل باستخدام curl إن وجد، أو wget كخيار ثاني
if command -v curl >/dev/null 2>&1; then
    curl -s -k -L --user-agent "Mozilla/5.0" "$URL1" -o "$DEST"
fi

# إذا فشل curl أو لم يكن مثبتاً، يتم استخدام wget
if [ ! -s "$DEST" ]; then
    wget -q --no-check-certificate --user-agent="Mozilla/5.0" "$URL1" -O "$DEST"
fi

# خطة احتياطية أجهزة بدون HTTPS: التنزيل من سيرفر HTTP مباشر
if [ ! -s "$DEST" ]; then
    wget -q "$URL2" -O "$DEST"
fi

# 3. الربط وتطبيق الصلاحيات عند نجاح التنزيل
if [ -s "$DEST" ]; then
    ln -s /etc/tuxbox/satellites.xml /etc/enigma2/satellites.xml
    chmod 644 /etc/tuxbox/satellites.xml
    echo "Satellites.xml Updated Successfully!"
    exit 0
else
    echo "Update Failed! Check Internet Connection or SSL support."
    exit 1
fi
