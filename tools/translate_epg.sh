#!/bin/sh
# ==============================================================================
# Enigma2 Arabic EPG Auto-Translator (Fixed Exit Code 1)
# ==============================================================================

TMP_PY="/tmp/epg_translate_engine.py"
LOG_FILE="/var/log/epg_translate.log"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

mkdir -p /var/log /tmp

echo "============================================================"
echo "    Enigma2 Arabic EPG Translator (Single-Script Mode)"
echo "============================================================"

# 1. Check Python Binary
if command -v python3 >/dev/null 2>&1; then
    PY_BIN=$(command -v python3)
elif command -v python >/dev/null 2>&1; then
    PY_BIN=$(command -v python)
else
    echo "[!] Python missing. Attempting fast opkg install..."
    opkg update >/dev/null 2>&1
    opkg install python3 python3-xml python3-requests >/dev/null 2>&1
    PY_BIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
fi

if [ -z "$PY_BIN" ]; then
    echo "[X] Error: Python environment not found!"
    exit 1
fi

# 2. Extract Embedded Python Translator Engine
cat << 'EOF' > "$TMP_PY"
import sys, os, re, json, time, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

CONFIG = {
    "SOURCE_LANG": "en", "TARGET_LANG": "ar",
    "CACHE_FILE": "/tmp/epg_translate_cache.json",
    "MAX_WORKERS": 5, "TIMEOUT_SECONDS": 8
}

GLOSSARY = {
    "Live": "مباشر", "LIVE": "مباشر", "Premier League": "الدوري الإنجليزي الممتاز",
    "Champions League": "دوري أبطال أوروبا", "La Liga": "الدوري الإسباني",
    "Serie A": "الدوري الإيطالي", "Bundesliga": "الدوري الألماني",
    "Formula 1": "فورمولا 1", "Highlights": "ملخص", "Pre-Match": "قبل المباراة",
    "Post-Match": "بعد المباراة", "Action": "أكشن", "Drama": "دراما",
    "Comedy": "كوميديا", "News": "الأخبار", "Weather": "النشرة الجوية"
}

def clean_text(text):
    if not text: return ""
    return text.strip().replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")

def apply_glossary(text):
    if not text: return text
    res = text
    for en, ar in GLOSSARY.items():
        res = re.sub(r'\b' + re.escape(en) + r'\b', ar, res, flags=re.IGNORECASE)
    res = re.sub(r'\bS(\d+)E(\d+)\b', r'الموسم \1 الحلقة \2', res, flags=re.IGNORECASE)
    return res

def translate_google(text):
    if not text: return ""
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "en", "tl": "ar", "dt": "t", "q": text}
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=CONFIG["TIMEOUT_SECONDS"]) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            chunks = []
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                for c in data[0]:
                    if isinstance(c, list) and len(c) > 0 and c[0]:
                        chunks.append(c[0])
            return "".join(chunks) if chunks else text
    except:
        return text

def process_item(text):
    cleaned = clean_text(text)
    if not cleaned or re.match(r'^[0-9\s\-\:\.\,\!\?\/\|\(\)]+$', cleaned): return cleaned
    part = apply_glossary(cleaned)
    if not re.search(r'[a-zA-Z]', part): return part
    trans = translate_google(part)
    return apply_glossary(trans) if trans else part

def main():
    if len(sys.argv) < 2: return
    file_path = sys.argv[1]
    if not os.path.exists(file_path): return

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except Exception as e:
        print(f"[X] XML Parse Error: {e}")
        return

    nodes = []
    for tag in ["title", "sub-title", "desc", "category"]:
        for elem in root.findall(f".//{tag}"):
            if elem.text and elem.text.strip():
                nodes.append((elem, elem.text))

    if not nodes:
        print("[!] No EPG elements found to translate.")
        return

    uniques = list(set([t for _, t in nodes]))
    with ThreadPoolExecutor(max_workers=CONFIG["MAX_WORKERS"]) as ex:
        translations = list(ex.map(process_item, uniques))

    trans_map = dict(zip(uniques, translations))
    for elem, orig in nodes:
        elem.text = trans_map.get(orig, orig)
        elem.set("lang", "ar")

    tree.write(file_path, encoding="utf-8", xml_declaration=True)
    print("[✓] EPG XML Translation Completed Successfully.")

if __name__ == "__main__":
    main()
EOF

chmod 755 "$TMP_PY"

# 3. Locate or Export EPG Data
TARGET_EPG=""
for candidate in "/etc/enigma2/epg.xml" "/media/hdd/epg.xml" "/etc/epgimport/epg.xml" "/media/usb/epg.xml" "/tmp/epg.xml"; do
    if [ -f "$candidate" ] && [ -s "$candidate" ]; then
        TARGET_EPG="$candidate"
        break
    fi
done

# If no XML file found, dump active EPG from Enigma2 Web API
if [ -z "$TARGET_EPG" ]; then
    echo "[*] Exporting live EPG from Enigma2..."
    TARGET_EPG="/tmp/epg.xml"
    wget -q -O "$TARGET_EPG" "http://127.0.0.1/web/epgxmltv" 2>/dev/null || curl -s "http://127.0.0.1/web/epgxmltv" -o "$TARGET_EPG" 2>/dev/null
fi

if [ ! -f "$TARGET_EPG" ] || [ ! -s "$TARGET_EPG" ]; then
    echo "[!] Warning: No EPG file found to translate."
    rm -f "$TMP_PY"
    exit 0
fi

# 4. Execute Translation
echo "[*] Translating: $TARGET_EPG"
"$PY_BIN" "$TMP_PY" "$TARGET_EPG"

# 5. Reload EPG into Enigma2 Memory
echo "[*] Reloading Enigma2 EPG Cache..."
wget -qO - "http://127.0.0.1/web/epgreload?reload=1" >/dev/null 2>&1 || true

rm -f "$TMP_PY"

echo "======================================="
echo " SUCCESS: EPG Processed to Arabic! "
echo "======================================="
exit 0
