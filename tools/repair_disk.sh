#!/bin/sh
umount /media/usb 2>/dev/null
umount /media/hdd 2>/dev/null
e2fsck -y /dev/sda1 2>/dev/null || e2fsck -y /dev/sdb1 2>/dev/null
echo "Disk Check & Repair Completed!"
exit 0