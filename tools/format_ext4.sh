#!/bin/sh
# ÊÍÏíÏ ãÓÇÑ ÇáÝáÇÔÉ (ÛÇáÈÇð sda1 Ãæ sdb1)
DEV=""
if [ -b /dev/sdb1 ]; then
    DEV="/dev/sdb1"
elif [ -b /dev/sda1 ]; then
    DEV="/dev/sda1"
fi

if [ -z "$DEV" ]; then
    echo "Error: USB drive not found!"
    exit 1
fi

echo "Unmounting $DEV..."
umount -f $DEV 2>/dev/null

echo "Formatting $DEV to ext4..."
mkfs.ext4 -F -L "neo_usb" $DEV

if [ $? -eq 0 ]; then
    echo "Formatting Completed Successfully! Label set to neo_usb"
    mkdir -p /media/usb
    mount $DEV /media/usb
else
    echo "Error: Formatting Failed. Make sure e2fsprogs package is installed."
fi

exit 0