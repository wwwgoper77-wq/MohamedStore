#!/bin/sh
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

echo "Formatting $DEV to ext3..."
mkfs.ext3 -F -L "neo_usb" $DEV

if [ $? -eq 0 ]; then
    echo "Formatting Completed Successfully to ext3!"
    mkdir -p /media/usb
    mount $DEV /media/usb
else
    echo "Error: Formatting Failed."
fi

exit 0