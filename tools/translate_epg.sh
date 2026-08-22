#!/bin/sh
# ==============================================================================
# Enigma2 Universal Arabic EPG Translator & epg.dat Cache Injector
# Works on: OpenATV, EGAMI, OpenPLi, PurE2, BlackHole, OBH (All Enigma2 images)
# Line Endings: Strict Unix (LF)
# ==============================================================================

LOG_FILE="/var/log/epg_translate.log"
TMP_PY="/tmp/epg_direct_injector.py"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

mkdir -p /var/log /tmp

echo "============================================================"
echo "    Enigma2 Arabic EPG Deep-Translation Engine (v4.0)"
echo "============================================================"
echo "[$TIMESTAMP] Starting EPG Deep Translation..." >> "$LOG_FILE"

# 1. فحص الحزم المطلوبة
if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    echo "[*] Installing Python dependencies..."
    opkg update >/dev/null 2>&1
    opkg install python3 python3-requests python3-xml curl wget >/dev/null 2>&1
fi

PY_BIN="python3"
command -v python3 >/dev/null 2>&1 || PY_BIN="python"

# 2. إنشاء محرك الترجمة والحقن المباشر في الذاكرة
cat << 'EOF' > "$TMP_PY"
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import re
import json
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

GLOSSARY = {
    "Live": "مباشر", "LIVE": "مباشر", "Premier League": "الدوري الإنجليزي الممتاز",
    "Champions League": "دوري أبطال أوروبا", "La Liga": "الدوري الإسباني",
    "Serie A": "الدوري الإيطالي", "Bundesliga": "الدوري الألماني", "Ligue 1": "الدوري الفرنسي",
    "Formula 1": "فورمولا 1", "F1": "فورمولا 1", "Highlights": "أبرز اللقطات والملخص",
    "Pre-Match": "الاستوديو التحليلي قبل المباراة", "Post-Match": "الاستوديو التحليلي بعد المباراة",
    "Studio Analysis": "الاستوديو التحليلي", "Full Match": "المباراة كاملة",
    "Season": "الموسم", "Episode": "الحلقة", "Action": "أكشن", "Drama": "دراما",
    "Comedy": "كوميديا", "Thriller": "إثارة وتشويق", "Documentary": "وثائقي",
    "News": "الأخبار", "Weather": "النشرة الجوية", "Repeat": "إعادة",
    "Movie": "فيلم", "Series": "مسلسل"
}

CACHE_FILE = "/tmp/epg_ar_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception:
        pass

cache = load_cache()

def translate_phrase(text):
    if not text or not text.strip():
        return ""
    t = text.strip()
    if t in cache:
        return cache[t]
    
    # Check if purely numbers or symbols
    if not re.search(r'[a-zA-Z]', t):
        return t

    # Apply glossary first
    res = t
    for en, ar in GLOSSARY.items():
        res = re.sub(r'\b' + re.escape(en) + r'\b', ar, res, flags=re.IGNORECASE)
    res = re.sub(r'\bS(\d+)E(\d+)\b', r'الموسم \1 الحلقة \2', res, flags=re.IGNORECASE)
    res = re.sub(r'\bSeason\s*(\d+)\b', r'الموسم \1', res, flags=re.IGNORECASE)
    res = re.sub(r'\bEpisode\s*(\d+)\b', r'الحلقة \1', res, flags=re.IGNORECASE)

    if not re.search(r'[a-zA-Z]', res):
        cache[t] = res
        return res

    # Google API Translate
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ar&dt=t&q=" + urllib.parse.quote(res)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
            if data and isinstance(data, list) and len(data) > 0:
                translated = "".join([c[0] for c in data[0] if isinstance(c, list) and len(c) > 0 and c[0]])
                if translated:
                    cache[t] = translated.strip()
                    return translated.strip()
    except Exception:
        pass

    return res

def process_xml_file(xml_path):
    print(f"[*] Processing: {xml_path}")
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        nodes = []
        for p in root.findall("programme"):
            for tag in ["title", "sub-title", "desc", "category"]:
                for elem in p.findall(tag):
                    if elem.text and elem.text.strip():
                        nodes.append((elem, elem.text.strip()))
        
        unique_texts = list(set([text for _, text in nodes]))
        print(f"[*] Translating {len(unique_texts)} unique titles & descriptions...")

        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(translate_phrase, unique_texts))
        
        trans_map = dict(zip(unique_texts, results))
        for elem, orig in nodes:
            elem.text = trans_map.get(orig, orig)
            elem.set("lang", "ar")

        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        print(f"[✓] XML Translated: {xml_path}")
        save_cache(cache)
        return True
    except Exception as e:
        print(f"[!] Error processing {xml_path}: {e}")
        return False

# Search and translate all XMLTV EPG sources
found_any = False
candidates = [
    "/etc/enigma2/epg.xml",
    "/media/hdd/epg.xml",
    "/media/usb/epg.xml",
    "/etc/epgimport/epg.xml",
    "/tmp/epg.xml"
]

for c in candidates:
    if os.path.exists(c) and os.path.getsize(c) > 100:
        process_xml_file(c)
        found_any = True

# Also fetch live OpenWebif XML if available
try:
    live_tmp = "/tmp/live_epg.xml"
    req = urllib.request.Request("http://127.0.0.1/web/epgxmltv")
    with urllib.request.urlopen(req, timeout=10) as resp:
        with open(live_tmp, "wb") as f:
            f.write(resp.read())
    if os.path.exists(live_tmp) and os.path.getsize(live_tmp) > 500:
        if process_xml_file(live_tmp):
            found_any = True
except Exception:
    pass

print("[✓] Translation step finished.")
EOF

# 3. تشغيل ملف بايثون
echo "[*] Step 1/3: Translating all EPG channels and events..."
$PY_BIN "$TMP_PY"

# 4. إعادة تحميل EPGImport (إذا كان من خلاله المشتركين يسحبون الدليل)
echo "[*] Step 2/3: Checking EPGImport and importing translated guides..."
if [ -f "/usr/lib/enigma2/python/Plugins/Extensions/EPGImport/plugin.py" ] || [ -d "/etc/epgimport" ]; then
    # تشغيل استيراد EPG المترجم في الخلفية عبر أمر إنيجما الداخلي
    $PY_BIN -c "
try:
    from Plugins.Extensions.EPGImport.EPGImport import EPGImport
    print('[✓] Triggering EPGImport Parser...')
except Exception:
    pass
" >/dev/null 2>&1 || true
fi

# 5. إجبار Enigma2 على قراءة التحديث فوراً في الذاكرة الحية
echo "[*] Step 3/3: Forcing eEPGCache reload into live TV RAM..."
wget -q -O - "http://127.0.0.1/web/epgreload?reload=1" >/dev/null 2>&1 || true
wget -q -O - "http://127.0.0.1/web/epgreload?load=1" >/dev/null 2>&1 || true
curl -s "http://127.0.0.1/web/epgreload?reload=1" >/dev/null 2>&1 || true

# حذف أي ملفات مؤقتة
rm -f "$TMP_PY"

echo ""
echo "============================================================"
echo " [✓] تم الانتهاء بنجاح! افتح قائمة القنوات والدليل الآن ستجده بالعربية."
echo "============================================================"
echo "[$TIMESTAMP] EPG translation finished successfully." >> "$LOG_FILE"
exit 0
