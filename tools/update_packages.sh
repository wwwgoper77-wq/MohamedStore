#!/bin/sh
opkg update && opkg upgrade
echo "System packages updated successfully!"
exit 0