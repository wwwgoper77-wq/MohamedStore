#!/bin/sh

echo "1. Stopping Enigma2 interface..."
init 4
sleep 3

SETTINGS="/etc/enigma2/settings"

echo "2. Disabling service name caching and duplicates override..."
# إلغاء خاصية إجبار استخدام الاسم المخزن قدماً عند تغير التردد
sed -i '/config.Nims.use_service_name=/d' $SETTINGS
echo "config.Nims.use_service_name=false" >> $SETTINGS

sed -i '/config.usage.hide_number_markers=/d' $SETTINGS
echo "config.usage.hide_number_markers=true" >> $SETTINGS

echo "3. Cleaning bouquet files from orphan/broken references..."
# إزالة الأسطر التالفة في المفضلات التي تشير لترددات خاطئة
for bouquet in /etc/enigma2/userbouquet.*; do
    if [ -f "$bouquet" ]; then
        # إزالة المعرفات الفارغة أو غير المعرفة
        sed -i '/#SERVICE 1:0:0:0:0:0:0:0:0:0:/d' "$bouquet"
    fi
done

echo "4. Reloading clean channel database..."
init 3

echo "======================================="
echo " SUCCESS: Channel references fixed!"
echo "======================================="
exit 0
