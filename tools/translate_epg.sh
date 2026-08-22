#!/bin/sh
# ==============================================================================
# Arabic EPG Free Translator (No Key Required)
# ==============================================================================

PY_SCRIPT="/tmp/run_free_epg.py"

echo "============================================================"
echo "      Starting Free Arabic EPG Translation Process"
echo "============================================================"

# إنشاء كود البايثون الداخلي لعمل الترجمة المجانية
cat << 'EOF' > "$PY_SCRIPT"
import sys, os, urllib.request, urllib.parse, json, re
import xml.etree.ElementTree as ET

def translate_google_free(text):
    if not text or not text.strip(): return text
    if re.match(r'^[0-9\s\-\:\.\,\!\?\/\|\(\)]+$', text): return text
    
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ar&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode("utf-8"))
            translated_parts = []
            if data and data[0]:
                for part in data[0]:
                    if part and part[0]:
                        translated_parts.append(part[0])
            return "".join(translated_parts).strip()
    except Exception:
        pass
    return text

epg_paths = ["/etc/enigma2/epg.dat", "/media/hdd/epg.dat", "/media/usb/epg.dat", "/tmp/epg.xml"]
xml_file = None

for path in epg_paths:
    if os.path.exists(path) and path.endswith(".xml"):
        xml_file = path
        break

if not xml_file:
    xml_file = "/tmp/live_epg.xml"
    os.system('wget -q -O /tmp/live_epg.xml "http://127.0.0.1/web/epgxmltv" 2>/dev/null')

if os.path.exists(xml_file) and os.path.getsize(xml_file) > 0:
    print("[*] Processing EPG XML with Free Google Engine...")
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        count = 0
        for elem in root.findall(".//title") + root.findall(".//desc"):
            if elem.text:
                elem.text = translate_google_free(elem.text)
                count += 1
                if count % 15 == 0:
                    print(f"[*] Translated {count} items...")
        tree.write(xml_file, encoding="utf-8", xml_declaration=True)
        print("[✓] EPG Translation Finished Successfully.")
    except Exception as e:
        print(f"[X] XML Error: {e}")
else:
    print("[!] No active EPG XML found.")

EOF

# إيقاف واجهة Enigma2 لتطبيق الترجمة على الذاكرة
echo "[*] Stopping Enigma2 GUI..."
init 4
sleep 3

# تنفيذ الترجمة
echo "[*] Translating EPG..."
python3 "$PY_SCRIPT" || python "$PY_SCRIPT"

rm -f "$PY_SCRIPT"

# إعادة تشغيل الواجهة
echo "[*] Restarting Enigma2 GUI..."
init 3

echo "============================================================"
echo "          Process Completed Successfully!"
echo "============================================================"
exit 0
