#!/bin/sh

PLUGIN_DIR="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore"

echo "Installing Mohamed Store..."

mkdir -p "$PLUGIN_DIR"

wget -O "$PLUGIN_DIR/plugin.py" https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/plugin.py
wget -O "$PLUGIN_DIR/plugin.png" https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/plugin.png

mkdir -p "$PLUGIN_DIR/images"

wget -O "$PLUGIN_DIR/images/logo.png" https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/images/logo.png
wget -O "$PLUGIN_DIR/images/plugins.png" https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/images/plugins.png
wget -O "$PLUGIN_DIR/images/skins.png" https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/images/skins.png
wget -O "$PLUGIN_DIR/images/system_images.png" https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/images/system_images.png
wget -O "$PLUGIN_DIR/images/tools.png" https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/images/tools.png
wget -O "$PLUGIN_DIR/images/ipaudiopro.png" https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/images/ipaudiopro.png
wget -O "$PLUGIN_DIR/images/timeshiftdelay.png" https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/images/timeshiftdelay.png

sync
killall -9 enigma2

exit 0
