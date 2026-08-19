#!/bin/sh
# 1. إزالة كافة الملفات والروابط القديمة من جميع المسارات المحتملة
rm -rf /etc/tuxbox/satellites.xml
rm -rf /etc/enigma2/satellites.xml
rm -rf /usr/share/enigma2/satellites.xml

DEST="/etc/tuxbox/satellites.xml"
URL1="https://raw.githubusercontent.com/oe-alliance/oe-alliance-plugins/master/xml/satellites.xml"
URL2="http://www.satellites-xml.org/satellites.xml"

# 2. التنزيل المباشر وضمان جلب الملف
if command -v curl >/dev/null 2>&1; then
    curl -s -k -L --user-agent "Mozilla/5.0" "$URL1" -o "$DEST"
fi

if [ ! -s "$DEST" ]; then
    wget -q --no-check-certificate --user-agent="Mozilla/5.0" "$URL1" -O "$DEST"
fi

if [ ! -s "$DEST" ]; then
    wget -q "$URL2" -O "$DEST"
fi

# 3. النسخ المباشر إلى كافة المسارات (بدلاً من الرابط الشعبي لمنع أي تعارض)
if [ -s "$DEST" ]; then
    cp -f "$DEST" /etc/enigma2/satellites.xml
    cp -f "$DEST" /usr/share/enigma2/satellites.xml
    
    chmod 644 /etc/tuxbox/satellites.xml
    chmod 644 /etc/enigma2/satellites.xml
    chmod 644 /usr/share/enigma2/satellites.xml
    
    echo "Satellites.xml Updated Successfully!"
    exit 0
else
    echo "Update Failed!"
    exit 1
fi
