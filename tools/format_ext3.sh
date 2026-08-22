#!/bin/sh

echo "1. Installing required formatting tools..."
opkg update >/dev/null 2>&1
opkg install e2fsprogs parted >/dev/null 2>&1

echo "2. Searching for USB device..."
DEV=""
for disk in /dev/sdb1 /dev/sda1 /dev/sdc1 /dev/sdb /dev/sda ; do
    if [ -b "$disk" ]; then
        DEV="$disk"
        break
    fi
done

if [ -z "$DEV" ]; then
    echo "ERROR: USB drive not detected! Please insert USB."
    exit 1
fi

echo "Found USB at: $DEV"

echo "3. Stopping Enigma2 and unmounting USB..."
init 4
sleep 2
fuser -k -9 /media/usb 2>/dev/null
fuser -k -9 /media/hdd 2>/dev/null
umount -f -l /media/usb 2>/dev/null
umount -f -l /media/hdd 2>/dev/null
umount -f -l $DEV 2>/dev/null

echo "4. Formatting USB to ext3 (Force)..."
mkfs.ext3 -F -L "neo_usb" $DEV

if [ $? -eq 0 ]; then
    echo "======================================="
    echo " SUCCESS: USB formatted to ext3!"
    echo " Label set to: neo_usb"
    echo "======================================="
    
    mkdir -p /media/usb
    mount $DEV /media/usb
    
    init 3
    exit 0
else
    echo "ERROR: Formatting failed!"
    init 3
    exit 1
fi
