#!/bin/sh

echo "================================================="
echo " Installing: Remorize VIP (SoltanAlaaelden)"
echo "================================================="

DIR="/etc/enigma2/xstreamity"
FILE="$DIR/playlists.txt"
SERVER_URL="http://live.remorize.live:2082/get.php?username=SoltanAlaaelden&password=pVdJkd3qQJrT&type=m3u_plus"

# ÅäÔÇÁ ÇáãÌáÏ æÇáãáÝ Åä áã íßæäÇ ãæÌæÏíä
mkdir -p "$DIR"
touch "$FILE"

# ÝÍÕ ÅÐÇ ßÇä ÇáÑÇÈØ ãæÌæÏÇð ãÓÈÞÇð áãäÚ ÇáÊßÑÇÑ
if ! grep -q "username=SoltanAlaaelden" "$FILE" 2>/dev/null; then
    echo "$SERVER_URL" >> "$FILE"
    echo " [+] Playlist added successfully."
else
    echo " [!] Server already exists in playlist."
fi

# ÖÈØ ÇáÕáÇÍíÇÊ æÊäÙíÝ ÇáßÇÔ áÊÍÏíË ÇáÞæÇÆã ÝæÑÇð
chmod 755 "$FILE"
rm -f "$DIR/xstreamity.db" "$DIR/playlists.json" 2>/dev/null
sync

echo "================================================="
echo " [OK] Remorize VIP Portal Added Successfully!"
echo " Open Xstreamity plugin to start watching."
echo "================================================="
exit 0