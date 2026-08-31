#!/bin/sh

echo "================================================="
echo " Installing: NoCable VIP Portal"
echo "================================================="

DIR="/etc/enigma2/xstreamity"
FILE="$DIR/playlists.txt"
SERVER_URL="http://nocable.cc:8080/get.php?username=foyers1@rogers.com&password=9jguFdUq3Y&type=m3u"

mkdir -p "$DIR"
touch "$FILE"

# ÝÍÕ ÅÐÇ ßÇä ÇáÑÇÈØ ãæÌæÏÇð ãÓÈÞÇð áãäÚ ÇáÊßÑÇÑ
if ! grep -q "nocable.cc" "$FILE" 2>/dev/null; then
    echo "$SERVER_URL" >> "$FILE"
fi

chmod 755 "$FILE"
rm -f "$DIR/xstreamity.db" "$DIR/playlists.json" 2>/dev/null
sync

echo "================================================="
echo " [OK] NoCable Portal Added Successfully!"
echo " Open Xstreamity to play channels."
echo "================================================="
exit 0