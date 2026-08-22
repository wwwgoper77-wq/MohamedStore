#!/bin/sh
echo "1. Updating feeds list..."
opkg update >/dev/null 2>&1

echo "2. Scanning connected hardware..."
# Scan and install drivers for Realtek, Ralink, and Bluetooth devices
for DRV in rtl8812au rtl8192eu rt2800-usb kernel-module-btusb; do
    echo "Checking driver: $DRV"
    opkg install enigma2-plugin-drivers-network-usb-$DRV >/dev/null 2>&1
    opkg install $DRV >/dev/null 2>&1
done

echo "3. Refreshing system kernel..."
depmod -a 2>/dev/null

echo "======================================="
echo " SUCCESS: USB Drivers process done! "
echo "======================================="
exit 0
