#!/bin/sh

echo "================================================="
echo " Installing: FastOpen Sports Portal"
echo "================================================="

DIR="/etc/enigma2/xstreamity"
FILE="$DIR/playlists.txt"
SERVER_URL="http://fastopen.live:8080/get.php?username=pcsline07&password=MN6FuAliGD&type=m3u_plus"

mkdir -p "$DIR"
touch "$FILE"

# ÝÍÕ ÅÐÇ ßÇä ÇáÑÇÈØ ãæÌæÏÇð ãÓÈÞÇð áãäÚ ÇáÊßÑÇÑ
if ! grep -q "fastopen.live" "$FILE" 2>/dev/null; then
    echo "$SERVER_URL" >> "$FILE"
fi

chmod 755 "$FILE"
rm -f "$DIR/xstreamity.db" "$DIR/playlists.json" 2>/dev/null
sync

echo "================================================="
echo " [OK] FastOpen Portal Added Successfully!"
echo " Open Xstreamity to play channels."
echo "================================================="
exit 0