#!/bin/sh
# 1. تنظيف المسارات القديمة
rm -f /etc/tuxbox/satellites.xml /etc/enigma2/satellites.xml

# 2. التنزيل مع إضافة User-Agent لضمان عدم رفض الطلب من GitHub
wget -q --no-check-certificate --user-agent="Mozilla/5.0" "https://raw.githubusercontent.com/oe-alliance/oe-alliance-plugins/master/xml/satellites.xml" -O /etc/tuxbox/satellites.xml

# 3. خطة احتياطية: إذا كان الملف فارغاً ينزل من سيرفر بديل مباشر
if [ ! -s /etc/tuxbox/satellites.xml ]; then
    wget -q --no-check-certificate "http://www.satellites-xml.org/satellites.xml" -O /etc/tuxbox/satellites.xml
fi

# 4. الربط وإعطاء الصلاحيات
if [ -s /etc/tuxbox/satellites.xml ]; then
    ln -s /etc/tuxbox/satellites.xml /etc/enigma2/satellites.xml
    chmod 644 /etc/tuxbox/satellites.xml
    echo "Satellites.xml Updated Successfully!"
else
    echo "Update Failed!"
    exit 1
fi

exit 0
