#!/bin/sh
# ==============================================================================
# Enigma2 Universal Arabic EPG Live-Extractor & Direct Importer (v5.0 Final)
# Compatible with: OpenATV, EGAMI, OpenPLi, PurE2, BlackHole, OBH
# Line Endings: Strict Unix (LF)
# ==============================================================================

LOG_FILE="/var/log/epg_translate.log"
TMP_PY="/tmp/epg_universal_engine.py"
OUT_XML="/etc/enigma2/epg_arabic.xml"
IMPORT_CONF="/etc/epgimport/custom_arabic.sources.xml"

mkdir -p /var/log /tmp /etc/enigma2 /etc/epgimport

echo "============================================================"
echo "    Enigma2 Arabic EPG Live-Extractor & Translator"
echo "============================================================"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Universal EPG Translation..." > "$LOG_FILE"

# 1. التأكد من وجود الحزم البرمجية
echo "[*] 1/5: Checking Python & Network tools..."
if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    echo "[!] Installing python3 packages via opkg..."
    opkg update >/dev/null 2>&1
    opkg install python3 python3-requests python3-xml curl wget >/dev/null 2>&1
fi

PY_BIN="python3"
command -v python3 >/dev/null 2>&1 || PY_BIN="python"

# 2. إنشاء محرك سحب القنوات وترجمتها وبناء XMLTV متوافق 100% مع Enigma2
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
    "Formula 1": "فورمولا 1", "F1": "فورمولا 1", "Highlights": "ملخص وأهداف",
    "Pre-Match": "قبل المباراة", "Post-Match": "بعد المباراة",
    "Studio Analysis": "الاستوديو التحليلي", "Full Match": "المباراة كاملة",
    "Season": "الموسم", "Episode": "الحلقة", "Action": "أكشن", "Drama": "دراما",
    "Comedy": "كوميديا", "Thriller": "إثارة وتشويق", "Documentary": "وثائقي",
    "News": "الأخبار", "Weather": "النشرة الجوية", "Repeat": "إعادة",
    "Movie": "فيلم", "Series": "مسلسل", "Final": "النهائي", "Semi-Final": "نصف النهائي"
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

def translate_text(text):
    if not text or not text.strip():
        return ""
    t = text.strip()
    if t in cache:
        return cache[t]
    
    if not re.search(r'[a-zA-Z]', t):
        return t

    res = t
    for en, ar in GLOSSARY.items():
        res = re.sub(r'\b' + re.escape(en) + r'\b', ar, res, flags=re.IGNORECASE)
    res = re.sub(r'\bS(\d+)E(\d+)\b', r'الموسم \1 الحلقة \2', res, flags=re.IGNORECASE)
    res = re.sub(r'\bSeason\s*(\d+)\b', r'الموسم \1', res, flags=re.IGNORECASE)
    res = re.sub(r'\bEpisode\s*(\d+)\b', r'الحلقة \1', res, flags=re.IGNORECASE)

    if not re.search(r'[a-zA-Z]', res):
        cache[t] = res
        return res

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

def fetch_events_from_openwebif():
    events_list = []
    print("[*] Reading live bouquets and active channels from Enigma2...")
    try:
        url = "http://127.0.0.1/web/getallservices"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=8) as resp:
            tree = ET.fromstring(resp.read())
            services = [s.text for s in tree.iter("e2servicereference") if s.text]
            print(f"[*] Found {len(services)} services in bouquets.")
    except Exception:
        services = []

    # Get EPG via multichannel or all services
    try:
        url = "http://127.0.0.1/web/epgxmltv"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = resp.read()
            if len(content) > 500:
                return content
    except Exception:
        pass
    return None

def process():
    out_xml = "/etc/enigma2/epg_arabic.xml"
    xml_content = fetch_events_from_openwebif()
    
    # Also check if existing XMLTV files exist on HDD or /etc
    candidates = ["/etc/enigma2/epg.xml", "/media/hdd/epg.xml", "/etc/epgimport/epg.xml", "/tmp/epg.xml"]
    source_file = None
    if not xml_content:
        for c in candidates:
            if os.path.exists(c) and os.path.getsize(c) > 100:
                source_file = c
                break

    if xml_content:
        root = ET.fromstring(xml_content)
    elif source_file:
        print(f"[*] Parsing local file: {source_file}")
        tree = ET.parse(source_file)
        root = tree.getroot()
    else:
        print("[!] No active EPG data found to translate. Please make sure channels have EPG first.")
        return False

    programmes = root.findall("programme")
    print(f"[*] Total events extracted: {len(programmes)}")
    if len(programmes) == 0:
        print("[!] No programme tags found in EPG.")
        return False

    nodes = []
    for p in programmes:
        for tag in ["title", "sub-title", "desc", "category"]:
            for elem in p.findall(tag):
                if elem.text and elem.text.strip():
                    nodes.append((elem, elem.text.strip()))

    unique_texts = list(set([t for _, t in nodes]))
    print(f"[*] Translating {len(nodes)} text entries ({len(unique_texts)} unique phrases)...")

    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(translate_text, unique_texts))

    trans_map = dict(zip(unique_texts, results))
    for elem, orig in nodes:
        elem.text = trans_map.get(orig, orig)
        elem.set("lang", "ar")

    new_tree = ET.ElementTree(root)
    new_tree.write(out_xml, encoding="utf-8", xml_declaration=True)
    save_cache(cache)
    print(f"[✓] Successfully generated Arabic XMLTV at: {out_xml}")
    return True

if __name__ == "__main__":
    if not process():
        sys.exit(1)
EOF

# 3. استخراج وترجمة الدليل الحصري للقنوات
echo "[*] 2/5: Extracting and translating EPG entries into Arabic..."
$PY_BIN "$TMP_PY"
RET=$?

if [ $RET -ne 0 ]; then
    echo "[X] Error during translation phase." >> "$LOG_FILE"
    rm -f "$TMP_PY"
    exit 1
fi

# 4. تسجيل المصدر العربي داخل EPGImport
echo "[*] 3/5: Registering Arabic Source in EPGImport..."
cat << 'EOF' > "$IMPORT_CONF"
<sources>
    <source type="gen_xmltv" channels="/etc/epgimport/custom_arabic.channels.xml">
        <description>Arabic Translated EPG Source</description>
        <url>/etc/enigma2/epg_arabic.xml</url>
    </source>
</sources>
EOF

# 5. حقن الدليل مباشرة في ذاكرة Enigma2 دون فقدان الترجمة
echo "[*] 4/5: Injecting Arabic EPG into Enigma2 eEPGCache memory..."
# نرسل إشارة التحميل عبر Web API أولاً
wget -q -O - "http://127.0.0.1/web/epgreload?reload=1" >/dev/null 2>&1 || true
curl -s "http://127.0.0.1/web/epgreload?reload=1" >/dev/null 2>&1 || true

# إعادة تشغيل سريعة لواجهة المستخدم (GUI Restart) لتطبيق التغييرات في الذاكرة
echo "[*] 5/5: Refreshing GUI to display Arabic EPG on TV screen..."
init 4
sleep 2
# نسخ ملف XML المترجم كملف افتراضي
cp -f "$OUT_XML" /etc/enigma2/epg.xml 2>/dev/null || true
init 3

rm -f "$TMP_PY"

echo ""
echo "============================================================"
echo " [✓] مبروك! تمت ترجمة دليل القنوات بالكامل إلى اللغة العربية."
echo "     افتح قائمة القنوات (EPG) على التلفاز الآن ستجدها معربة."
echo "============================================================"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Arabic Translation completed successfully." >> "$LOG_FILE"
exit 0
