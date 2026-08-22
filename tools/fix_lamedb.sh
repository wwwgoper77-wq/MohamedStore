#!/bin/sh
echo "Stopping Enigma2..."
init 4
sleep 2

echo "Cleaning lamedb backup files..."
rm -f /etc/enigma2/lamedb5 /etc/enigma2/lamedb.bak /etc/enigma2/*.sc

init 3
echo "Lamedb database cleaned and reloaded!"
exit 0