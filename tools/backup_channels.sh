#!/bin/sh
mkdir -p /media/hdd/Channels_Backup
tar -czvf /media/hdd/Channels_Backup/channels_backup.tar.gz /etc/enigma2/lamedb /etc/enigma2/*.tv /etc/enigma2/*.radio
echo "Backup Saved to /media/hdd/Channels_Backup"
exit 0