#!/bin/sh

echo "================================================="
echo " Installing: TVMate Portal (Server 1 - JvVev6)"
echo "================================================="

DIR="/etc/enigma2/xstreamity"
FILE="$DIR/playlists.txt"
SERVER_URL="http://tvmate.icu:8080/get.php?username=JvVev6&password=097466&type=m3u"

mkdir -p "$DIR"
touch "$FILE"

# ÝÍÕ ÅÐÇ ßÇä ÇáÑÇÈØ ãæÌæÏÇð ãÓÈÞÇð áãäÚ ÇáÊßÑÇÑ
if ! grep -q "username=JvVev6" "$FILE" 2>/dev/null; then
    echo "$SERVER_URL" >> "$FILE"
fi

chmod 755 "$FILE"
rm -f "$DIR/xstreamity.db" "$DIR/playlists.json" 2>/dev/null
sync

echo "================================================="
echo " [OK] TVMate Portal (JvVev6) Added Successfully!"
echo " Open Xstreamity to play channels."
echo "================================================="
exit 0