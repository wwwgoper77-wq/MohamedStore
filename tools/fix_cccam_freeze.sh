#!/bin/sh
CCCAM_CFG="/etc/CCcam.cfg"

echo "1. Cleaning RAM and Cache memory..."
sync
echo 3 > /proc/sys/vm/drop_caches

echo "2. Optimizing CCcam configuration..."
if [ -f "$CCCAM_CFG" ]; then
    # ãäÚ ÇÓÊÞÈÇá ÑÓÇÆá ÊÍÏíË ÇáßÑæÊ ÇáÒÇÆÏÉ áãäÚ ÇáÊÌãíÏ
    grep -q "DISABLE EMM : yes" $CCCAM_CFG || echo "DISABLE EMM : yes" >> $CCCAM_CFG
    grep -q "MINI EMM ADDR : 10" $CCCAM_CFG || echo "MINI EMM ADDR : 10" >> $CCCAM_CFG
    echo "CCcam.cfg optimized successfully!"
else
    echo "CCcam.cfg not found in /etc/"
fi

echo "3. Restarting Softcam service..."
/etc/init.d/softcam restart 2>/dev/null || /etc/init.d/cardserver restart 2>/dev/null

echo "======================================="
echo " SUCCESS: CCcam Network Optimized! "
echo "======================================="
exit 0