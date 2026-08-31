#!/bin/sh

echo "================================================="
echo " Installing: Cord Cutter IPTV Portal"
echo "================================================="

DIR="/etc/enigma2/xstreamity"
FILE="$DIR/playlists.txt"
SERVER_URL="http://cord-cutter.net:8080/get.php?username=59452816&password=59452816&type=m3u"

mkdir -p "$DIR"
touch "$FILE"

# ÝÍÕ ÅÐÇ ßÇä ÇáÑÇÈØ ãæÌæÏÇð ãÓÈÞÇð áãäÚ ÇáÊßÑÇÑ
if ! grep -q "cord-cutter.net" "$FILE" 2>/dev/null; then
    echo "$SERVER_URL" >> "$FILE"
fi

chmod 755 "$FILE"
rm -f "$DIR/xstreamity.db" "$DIR/playlists.json" 2>/dev/null
sync

echo "================================================="
echo " [OK] Cord Cutter Portal Added Successfully!"
echo " Open Xstreamity to play channels."
echo "================================================="
exit 0