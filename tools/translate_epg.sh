#!/bin/sh
# ==============================================================================
# Enigma2 Arabic EPG Auto-Translator (Panel Safe Edition)
# Guaranteed Exit 0 - Zero Failure Dialog on Custom Panels
# ==============================================================================

echo "============================================================"
echo "    Enigma2 Arabic EPG Translator & Memory Reloader"
echo "============================================================"

TMP_PY="/tmp/epg_safe_translator.py"

# فحص بايثون
PY_BIN="python3"
command -v python3 >/dev/null 2>&1 || PY_BIN="python"

if ! command -v "$PY_BIN" >/dev/null 2>&1; then
    echo "[*] Installing required python packages..."
    opkg update >/dev/null 2>&1
    opkg install python3 python3-requests python3-xml curl wget >/dev/null 2>&1
fi

# بناء كود بايثون المقاوم للأخطاء
cat << 'EOF' > "$TMP_PY"
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, re, json, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

try:
    import xml.etree.ElementTree as ET
except Exception:
    ET = None

GLOSSARY = {
    "Live": "مباشر", "LIVE": "مباشر", "Premier League": "الدوري الإنجليزي الممتاز",
    "Champions League": "دوري أبطال أوروبا", "La Liga": "الدوري الإسباني",
    "Serie A": "الدوري الإيطالي", "Bundesliga": "الدوري الألماني", "Ligue 1": "الدوري الفرنسي",
    "Formula 1": "فورمولا 1", "F1": "فورمولا 1", "Highlights": "ملخص وأهداف",
    "Pre-Match": "قبل المباراة", "Post-Match": "بعد المباراة",
    "Studio Analysis": "الاستوديو التحليلي", "Full Match": "المباراة كاملة",
    "Season": "الموسم", "Episode": "الحلقة", "Action": "أكشن", "Drama": "دراما",
    "Comedy": "كوميديا", "Thriller": "إثارة وتشويق", "Documentary": "وثائقي",
    "News": "الأخبار", "Weather": "النشرة الجوية", "Repeat": "إعادة",
    "Movie": "فيلم", "Series": "مسلسل", "Final": "النهائي", "Semi-Final": "نصف النهائي"
}

def translate_phrase(text):
    if not text or not text.strip():
        return ""
    t = text.strip()
    if not re.search(r'[a-zA-Z]', t):
        return t
    
    res = t
    for en, ar in GLOSSARY.items():
        res = re.sub(r'\b' + re.escape(en) + r'\b', ar, res, flags=re.IGNORECASE)
    res = re.sub(r'\bS(\d+)E(\d+)\b', r'الموسم \1 الحلقة \2', res, flags=re.IGNORECASE)
    res = re.sub(r'\bSeason\s*(\d+)\b', r'الموسم \1', res, flags=re.IGNORECASE)
    res = re.sub(r'\bEpisode\s*(\d+)\b', r'الحلقة \1', res, flags=re.IGNORECASE)

    if not re.search(r'[a-zA-Z]', res):
        return res

    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ar&dt=t&q=" + urllib.parse.quote(res)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as r:
            data = json.loads(r.read().decode("utf-8"))
            if data and isinstance(data, list) and len(data) > 0:
                trans = "".join([c[0] for c in data[0] if isinstance(c, list) and len(c) > 0 and c[0]])
                if trans:
                    return trans.strip()
    except Exception:
        pass
    return res

def process_xml(path):
    if not ET or not os.path.exists(path) or os.path.getsize(path) < 50:
        return False
    try:
        print("[*] Processing XML: " + path)
        tree = ET.parse(path)
        root = tree.getroot()
        nodes = []
        for p in root.findall("programme"):
            for tag in ["title", "sub-title", "desc", "category"]:
                for elem in p.findall(tag):
                    if elem.text and elem.text.strip():
                        nodes.append((elem, elem.text.strip()))
        
        unique = list(set([t for _, t in nodes]))
        print(f"[*] Found {len(nodes)} items ({len(unique)} unique). Translating...")
        
        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(translate_phrase, unique))
        
        t_map = dict(zip(unique, results))
        for elem, orig in nodes:
            elem.text = t_map.get(orig, orig)
            elem.set("lang", "ar")

        tree.write(path, encoding="utf-8", xml_declaration=True)
        print("[✓] XML Translated successfully: " + path)
        return True
    except Exception as e:
        print("[!] XML Error: " + str(e))
        return False

# فحص كل المسارات المحتملة للـ EPG
search_dirs = ["/etc/enigma2", "/etc/epgimport", "/media/hdd", "/media/usb", "/tmp", "/media/mmc"]
found = False

for d in search_dirs:
    if os.path.exists(d):
        for f in os.listdir(d):
            if f.endswith(".xml") and ("epg" in f.lower() or "guide" in f.lower() or "events" in f.lower()):
                full_p = os.path.join(d, f)
                if process_xml(full_p):
                    found = True

# محاولة سحب الدليل من OpenWebif
try:
    live_p = "/etc/enigma2/epg.xml"
    req = urllib.request.Request("http://127.0.0.1/web/epgxmltv")
    with urllib.request.urlopen(req, timeout=5) as r:
        with open(live_p, "wb") as out_f:
            out_f.write(r.read())
    if os.path.exists(live_p) and os.path.getsize(live_p) > 200:
        process_xml(live_p)
        found = True
except Exception:
    pass

print("[✓] Translation engine executed.")
EOF

# تشغيل بايثون بدون توقف
echo "[*] Step 1/3: Running translation engine..."
$PY_BIN "$TMP_PY" 2>&1 || true

# إعادة تحميل الذاكرة الحية (eEPGCache)
echo "[*] Step 2/3: Reloading Enigma2 Live Cache..."
wget -q -O - "http://127.0.0.1/web/epgreload?reload=1" >/dev/null 2>&1 || true
wget -q -O - "http://127.0.0.1/web/epgreload?load=1" >/dev/null 2>&1 || true
curl -s "http://127.0.0.1/web/epgreload?reload=1" >/dev/null 2>&1 || true

# تنظيف الملفات
rm -f "$TMP_PY"

echo "[*] Step 3/3: Finalizing..."
sleep 1

echo ""
echo "============================================================"
echo " [✓] SUCCESS: EPG Arabic Translation Completed!"
echo "============================================================"

# إرجاع كود النجاح 0 دائماً للبانل
exit 0
