#!/bin/sh

echo "================================================="
echo " Installing: TVMate Portal (Server 2 - Xc8SjG)"
echo "================================================="

DIR="/etc/enigma2/xstreamity"
FILE="$DIR/playlists.txt"
SERVER_URL="http://tvmate.icu:8080/get.php?username=Xc8SjG&password=508039&type=m3u"

mkdir -p "$DIR"
touch "$FILE"

# ÝÍÕ ÅÐÇ ßÇä ÇáÑÇÈØ ãæÌæÏÇð ãÓÈÞÇð áãäÚ ÇáÊßÑÇÑ
if ! grep -q "username=Xc8SjG" "$FILE" 2>/dev/null; then
    echo "$SERVER_URL" >> "$FILE"
fi

chmod 755 "$FILE"
rm -f "$DIR/xstreamity.db" "$DIR/playlists.json" 2>/dev/null
sync

echo "================================================="
echo " [OK] TVMate Portal (Xc8SjG) Added Successfully!"
echo " Open Xstreamity to play channels."
echo "================================================="
exit 0