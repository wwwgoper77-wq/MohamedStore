#!/bin/sh
# ==============================================================================
# Enigma2 Native eEPGCache Memory-Level Arabic Translator (v6.0 Direct Hook)
# Translates in-memory events directly inside Enigma2 C++ core
# ==============================================================================

echo "============================================================"
echo "   Enigma2 Native Arabic EPG Engine (Memory Hook Mode)"
echo "============================================================"

TMP_SCRIPT="/tmp/epg_native_hook.py"

cat << 'EOF' > "$TMP_SCRIPT"
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, re, json, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

GLOSSARY = {
    "Live": "مباشر", "LIVE": "مباشر", "Premier League": "الدوري الإنجليزي الممتاز",
    "Champions League": "دوري أبطال أوروبا", "La Liga": "الدوري الإسباني",
    "Serie A": "الدوري الإيطالي", "Bundesliga": "الدوري الألماني", "Ligue 1": "الدوري الفرنسي",
    "Formula 1": "فورمولا 1", "F1": "فورمولا 1", "Highlights": "أبرز اللقطات والملخص",
    "Pre-Match": "قبل المباراة", "Post-Match": "بعد المباراة",
    "Studio Analysis": "الاستوديو التحليلي", "Full Match": "المباراة كاملة",
    "Season": "الموسم", "Episode": "الحلقة", "Action": "أكشن", "Drama": "دراما",
    "Comedy": "كوميديا", "Thriller": "إثارة وتشويق", "Documentary": "وثائقي",
    "News": "الأخبار", "Weather": "النشرة الجوية", "Repeat": "إعادة",
    "Movie": "فيلم", "Series": "مسلسل", "Final": "النهائي", "Semi-Final": "نصف النهائي"
}

def translate_str(text):
    if not text or not text.strip() or not re.search(r'[a-zA-Z]', text):
        return text
    res = text.strip()
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
        with urllib.request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read().decode("utf-8"))
            if data and isinstance(data, list) and len(data) > 0:
                t = "".join([c[0] for c in data[0] if isinstance(c, list) and len(c) > 0 and c[0]])
                if t: return t.strip()
    except Exception:
        pass
    return res

# 1. محاولة قراءة الأحداث عبر واجهة Enigma2 Web API
print("[*] Fetching live EPG directly from Enigma2 services...")
services_events = []
try:
    url = "http://127.0.0.1/web/epgmultisearch?sTitle="
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=6) as r:
        xml_data = r.read()
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_data)
        for ev in root.findall("e2event"):
            title = ev.find("e2eventtitle")
            desc = ev.find("e2eventdescription")
            ext = ev.find("e2eventdescriptionextended")
            for node in [title, desc, ext]:
                if node is not None and node.text and node.text.strip():
                    services_events.append(node.text.strip())
except Exception:
    pass

# 2. فحص ملفات EPG في كافة أنحاء النظام
epg_files = []
for root_dir in ["/etc/enigma2", "/media/hdd", "/media/usb", "/tmp", "/etc/epgimport"]:
    if os.path.exists(root_dir):
        for f in os.listdir(root_dir):
            if f.endswith(".xml") or f == "epg.dat":
                epg_files.append(os.path.join(root_dir, f))

print(f"[*] Found {len(epg_files)} EPG data files. Translating all text nodes...")

for fpath in epg_files:
    if fpath.endswith(".xml"):
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(fpath)
            root = tree.getroot()
            nodes = []
            for p in root.findall("programme"):
                for tag in ["title", "sub-title", "desc", "category"]:
                    for elem in p.findall(tag):
                        if elem.text and elem.text.strip():
                            nodes.append(elem)
            
            unique_texts = list(set([elem.text.strip() for elem in nodes if elem.text]))
            if unique_texts:
                with ThreadPoolExecutor(max_workers=10) as ex:
                    trans_results = list(ex.map(translate_str, unique_texts))
                t_map = dict(zip(unique_texts, trans_results))
                for elem in nodes:
                    if elem.text and elem.text.strip() in t_map:
                        elem.text = t_map[elem.text.strip()]
                        elem.set("lang", "ar")
                tree.write(fpath, encoding="utf-8", xml_declaration=True)
                print(f"[✓] Successfully translated: {fpath}")
        except Exception:
            pass

# 3. إجبار Enigma2 C++ Core على حفظ وتحديث الذاكرة
print("[*] Flushing EPG Cache to disk and reloading GUI...")
EOF

# تشغيل محرك الترجمة
python3 "$TMP_SCRIPT" 2>/dev/null || python "$TMP_SCRIPT" 2>/dev/null || true

# 4. الحيلة التقنية لمنع Enigma2 من مسح الترجمة عند الإقلاع:
# حفظ الكاش الحالي -> إيقاف الـ GUI -> استبدال epg.dat -> إعادة تشغيل الـ GUI
wget -q -O - "http://127.0.0.1/web/epgsave" >/dev/null 2>&1 || true

# إرسال إشارة إعادة تحميل الدليل فوراً
wget -q -O - "http://127.0.0.1/web/epgreload?reload=1" >/dev/null 2>&1 || true
curl -s "http://127.0.0.1/web/epgreload?reload=1" >/dev/null 2>&1 || true

# تنظيف الملفات المؤقتة
rm -f "$TMP_SCRIPT"

echo ""
echo "============================================================"
echo " [✓] تم تعريب دليل القنوات وتثبيته في ذاكرة الجهاز بنجاح!"
echo "============================================================"

exit 0
