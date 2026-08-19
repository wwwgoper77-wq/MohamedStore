#!/bin/sh
# تنزيل الملف وحفظه في المسار الرئيسي
wget -q --no-check-certificate "https://raw.githubusercontent.com/oe-alliance/oe-alliance-plugins/master/xml/satellites.xml" -O /etc/tuxbox/satellites.xml

# إنشاء رابط مباشر أو نسخ الملف إلى مسار enigma2 أيضاً
cp /etc/tuxbox/satellites.xml /etc/enigma2/satellites.xml

# أعطاء صلاحيات القراءة للرسيفر
chmod 644 /etc/tuxbox/satellites.xml
chmod 644 /etc/enigma2/satellites.xml

echo "Satellites.xml Updated Successfully!"
exit 0
