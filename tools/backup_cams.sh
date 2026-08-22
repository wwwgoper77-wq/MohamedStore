#!/bin/sh
BACKUP_DIR="/media/hdd/Cam_Configs_Backup"
[ -d /media/usb ] && BACKUP_DIR="/media/usb/Cam_Configs_Backup"
mkdir -p $BACKUP_DIR

# äÓÎ ãáÝÇÊ ÇáÅÚÏÇÏÇÊ
cp -r /etc/tuxbox/config/ $BACKUP_DIR/tuxbox_config/ 2>/dev/null
cp /etc/cccam.cfg $BACKUP_DIR/ 2>/dev/null

echo "Cam Configs Backed Up Successfully to $BACKUP_DIR!"
exit 0