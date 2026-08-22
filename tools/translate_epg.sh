#!/bin/sh
# ==============================================================================
# EPG Translator via Gemini API
# ==============================================================================

PY_SCRIPT="/tmp/run_gemini_epg.py"

echo "============================================================"
echo "      Starting Gemini API EPG Translation Process"
echo "============================================================"

# إنشاء كود البايثون الداخلي
cat << 'EOF' > "$PY_SCRIPT"
import sys, os, urllib.request, json, re
import xml.etree.ElementTree as ET

# --- ضع مفتاح Gemini الخاص بك هنا ---
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

def translate_gemini(text):
    if not text or not text.strip(): return text
    if re.match(r'^[0-9\s\-\:\.\,\!\?\/\|\(\)]+$', text): return text
    
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + GEMINI_API_KEY
        payload = {
            "contents": [{
                "parts": [{
                    "text": "Translate the following TV EPG text to natural, high-quality Arabic. Return ONLY the translated Arabic text with absolutely no explanations, codeblocks, formatting, or extra words:\n\n" + text
                }]
            }]
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if "candidates" in res_data:
                translated = res_data["candidates"][0]["content"]["parts"][0]["text"]
                return translated.strip()
    except Exception as e:
        print(f"Gemini Error: {e}")
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
    print("[*] Processing EPG XML with Gemini AI...")
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        count = 0
        for elem in root.findall(".//title") + root.findall(".//desc"):
            if elem.text:
                elem.text = translate_gemini(elem.text)
                count += 1
                if count % 10 == 0:
                    print(f"[*] Translated {count} items...")
        tree.write(xml_file, encoding="utf-8", xml_declaration=True)
        print("[✓] Translation Finished Successfully.")
    except Exception as e:
        print(f"[X] XML Error: {e}")
else:
    print("[!] No EPG data found.")
EOF

echo "[*] Stopping Enigma2 GUI..."
init 4
sleep 3

echo "[*] Running Translation via Gemini..."
python3 "$PY_SCRIPT" || python "$PY_SCRIPT"

rm -f "$PY_SCRIPT"

echo "[*] Restarting Enigma2 GUI..."
init 3

echo "============================================================"
echo "          Completed!"
echo "============================================================"
exit 0
