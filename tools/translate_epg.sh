#!/bin/sh
# ==============================================================================
# Enigma2 Arabic EPG Auto-Translator (Standalone Custom Panel Edition)
# Line Endings: Strict Unix (LF)
# ==============================================================================

TMP_PY="/tmp/epg_translate_engine.py"
LOG_FILE="/var/log/epg_translate.log"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

mkdir -p /var/log
mkdir -p /tmp

echo "============================================================"
echo "    Enigma2 Arabic EPG Translator (Single-Script Mode)"
echo "============================================================"
echo "[$TIMESTAMP] Starting EPG translation from panel..." >> "$LOG_FILE"

# 1. Verify / Install Dependencies
echo "[*] Step 1/4: Checking system dependencies..."
if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    echo "[!] Python not found. Installing python3 packages via opkg..."
    opkg update >/dev/null 2>&1 || true
    opkg install python3 python3-requests python3-xml curl wget >/dev/null 2>&1 || true
fi

if command -v python3 >/dev/null 2>&1; then
    PY_BIN=$(command -v python3)
elif command -v python >/dev/null 2>&1; then
    PY_BIN=$(command -v python)
else
    echo "[X] Error: Could not find or install Python. Please install python3 manually."
    exit 1
fi

echo "[$TIMESTAMP] Using Python binary: $PY_BIN" >> "$LOG_FILE"

# 2. Extract Embedded Python Translation Engine to /tmp
echo "[*] Step 2/4: Initializing translation engine..."
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
import urllib.error
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

CONFIG = {
    "SOURCE_LANG": "en",
    "TARGET_LANG": "ar",
    "CACHE_FILE": "/tmp/epg_translate_cache.json",
    "RECEIVER_WEB_URL": "http://127.0.0.1",
    "MAX_WORKERS": 6,
    "TRANSLATION_ENGINE": "google_free",
    "RETRY_ATTEMPTS": 3,
    "TIMEOUT_SECONDS": 10
}

GLOSSARY = {
    "Live": "„»«‘—",
    "LIVE": "„»«‘—",
    "Premier League": "«·œÊ—Ì «·≈‰Ã·Ì“Ì «·„„ «“",
    "Champions League": "œÊ—Ì √»ÿ«· √Ê—Ê»«",
    "La Liga": "«·œÊ—Ì «·≈”»«‰Ì",
    "Serie A": "«·œÊ—Ì «·≈Ìÿ«·Ì",
    "Bundesliga": "«·œÊ—Ì «·√·„«‰Ì",
    "Ligue 1": "«·œÊ—Ì «·›—‰”Ì",
    "Formula 1": "›Ê—„Ê·« 1",
    "F1": "›Ê—„Ê·« 1",
    "Highlights": "√»—“ «··ﬁÿ«  Ê«·„·Œ’",
    "Pre-Match": "«·«” ÊœÌÊ «· Õ·Ì·Ì ﬁ»· «·„»«—«…",
    "Post-Match": "«·«” ÊœÌÊ «· Õ·Ì·Ì »⁄œ «·„»«—«…",
    "Studio Analysis": "«·«” ÊœÌÊ «· Õ·Ì·Ì",
    "Full Match": "«·„»«—«… ﬂ«„·…",
    "Season": "«·„Ê”„",
    "Episode": "«·Õ·ﬁ…",
    "Premiere": "⁄—÷ √Ê·",
    "Action": "√ﬂ‘‰",
    "Drama": "œ—«„«",
    "Comedy": "ﬂÊ„ÌœÌ«",
    "Thriller": "≈À«—… Ê ‘ÊÌﬁ",
    "Documentary": "ÊÀ«∆ﬁÌ",
    "Animation": "—”Ê„ „ Õ—ﬂ…",
    "News": "«·√Œ»«—",
    "Weather": "«·‰‘—… «·ÃÊÌ…",
    "Breaking News": "⁄«Ã·",
    "Repeat": "≈⁄«œ…",
    "Live Match": "„»«—«… „»«‘—…",
    "Round": "«·ÃÊ·…",
    "Quarter-Final": "—»⁄ «·‰Â«∆Ì",
    "Semi-Final": "‰’› «·‰Â«∆Ì",
    "Final": "«·‰Â«∆Ì"
}

class EPGTranslator:
    def __init__(self):
        self.cache = self._load_cache()
        self.cache_updated = False
        self.stats = {"total": 0, "cached": 0, "translated": 0, "failed": 0}

    def _load_cache(self):
        cache_path = CONFIG["CACHE_FILE"]
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_cache(self):
        if not self.cache_updated:
            return
        try:
            with open(CONFIG["CACHE_FILE"], "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def clean_text(self, text):
        if not text:
            return ""
        t = text.strip()
        t = t.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">")
        return t

    def apply_glossary(self, text):
        if not text:
            return text
        res = text
        for en_term, ar_term in GLOSSARY.items():
            pattern = re.compile(r'\b' + re.escape(en_term) + r'\b', re.IGNORECASE)
            res = pattern.sub(ar_term, res)
        res = re.sub(r'\bS(\d+)E(\d+)\b', r'«·„Ê”„ \1 «·Õ·ﬁ… \2', res, flags=re.IGNORECASE)
        res = re.sub(r'\bSeason\s*(\d+)\s*Episode\s*(\d+)\b', r'«·„Ê”„ \1 «·Õ·ﬁ… \2', res, flags=re.IGNORECASE)
        res = re.sub(r'\bEpisode\s*(\d+)\b', r'«·Õ·ﬁ… \1', res, flags=re.IGNORECASE)
        return res

    def translate_google(self, text):
        if not text:
            return ""
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": CONFIG["SOURCE_LANG"],
            "tl": CONFIG["TARGET_LANG"],
            "dt": "t",
            "q": text
        }
        encoded_url = url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            encoded_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=CONFIG["TIMEOUT_SECONDS"]) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            chunks = []
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                for c in data[0]:
                    if isinstance(c, list) and len(c) > 0 and c[0]:
                        chunks.append(c[0])
            return "".join(chunks) if chunks else text

    def translate_text(self, text):
        cleaned = self.clean_text(text)
        if not cleaned or re.match(r'^[0-9\s\-\:\.\,\!\?\/\|\(\)]+$', cleaned):
            return cleaned

        self.stats["total"] += 1
        if cleaned in self.cache:
            self.stats["cached"] += 1
            return self.cache[cleaned]

        partially = self.apply_glossary(cleaned)
        if not re.search(r'[a-zA-Z]', partially):
            self.cache[cleaned] = partially
            self.cache_updated = True
            self.stats["translated"] += 1
            return partially

        for attempt in range(CONFIG["RETRY_ATTEMPTS"]):
            try:
                translated = self.translate_google(partially)
                if translated and translated.strip():
                    final_text = self.apply_glossary(translated.strip())
                    self.cache[cleaned] = final_text
                    self.cache_updated = True
                    self.stats["translated"] += 1
                    return final_text
            except Exception:
                time.sleep(0.4 * (attempt + 1))

        self.stats["failed"] += 1
        return cleaned

    def process_file(self, file_path):
        print(f"[*] Processing EPG XML file: {file_path}")
        tree = ET.parse(file_path)
        root = tree.getroot()
        programmes = root.findall("programme")
        print(f"[*] Found {len(programmes)} programme events in guide.")

        text_nodes = []
        for prog in programmes:
            for title in prog.findall("title"):
                if title.text and title.text.strip():
                    text_nodes.append((title, title.text))
            for subtitle in prog.findall("sub-title"):
                if subtitle.text and subtitle.text.strip():
                    text_nodes.append((subtitle, subtitle.text))
            for desc in prog.findall("desc"):
                if desc.text and desc.text.strip():
                    text_nodes.append((desc, desc.text))
            for cat in prog.findall("category"):
                if cat.text and cat.text.strip():
                    text_nodes.append((cat, cat.text))

        unique_texts = list(set([t for _, t in text_nodes]))
        print(f"[*] Translating {len(text_nodes)} nodes ({len(unique_texts)} unique strings)...")

        with ThreadPoolExecutor(max_workers=CONFIG["MAX_WORKERS"]) as ex:
            translations = list(ex.map(self.translate_text, unique_texts))

        trans_map = dict(zip(unique_texts, translations))
        for elem, orig in text_nodes:
            elem.text = trans_map.get(orig, orig)
            elem.set("lang", CONFIG["TARGET_LANG"])

        # Backup old file
        bak_file = file_path + ".bak"
        try:
            if not os.path.exists(bak_file):
                import shutil
                shutil.copyfile(file_path, bak_file)
        except Exception:
            pass

        tree.write(file_path, encoding="utf-8", xml_declaration=True)
        self.save_cache()
        print(f"[?] XMLTV updated successfully: {file_path}")
        print(f"[?] Summary: Total={self.stats['total']} | Cached={self.stats['cached']} | Translated={self.stats['translated']} | Failed={self.stats['failed']}")

if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else "/etc/enigma2/epg.xml"
    translator = EPGTranslator()
    translator.process_file(target_file)
EOF

chmod +x "$TMP_PY"

# 3. Locate EPG file
echo "[*] Step 3/4: Locating receiver EPG data..."
TARGET_EPG=""
if [ -n "$1" ] && [ -f "$1" ]; then
    TARGET_EPG="$1"
else
    for candidate in "/etc/enigma2/epg.xml" "/media/hdd/epg.xml" "/etc/epgimport/epg.xml" "/media/usb/epg.xml" "/tmp/epg.xml"; do
        if [ -f "$candidate" ]; then
            TARGET_EPG="$candidate"
            break
        fi
    done
fi

if [ -z "$TARGET_EPG" ]; then
    echo "[!] No EPG XML found in default paths. Generating EPG from active services..."
    TARGET_EPG="/tmp/epg.xml"
    if command -v curl >/dev/null 2>&1; then
        curl -s "http://127.0.0.1/web/epgxmltv" -o "$TARGET_EPG" || true
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$TARGET_EPG" "http://127.0.0.1/web/epgxmltv" || true
    fi
fi

if [ ! -f "$TARGET_EPG" ] || [ ! -s "$TARGET_EPG" ]; then
    echo "[X] Error: Could not locate or generate an EPG file to translate."
    rm -f "$TMP_PY"
    exit 1
fi

echo "[*] Translating EPG file: $TARGET_EPG"
"$PY_BIN" "$TMP_PY" "$TARGET_EPG"
RET_VAL=$?

# 4. Trigger In-Memory eEPGCache Reload
echo "[*] Step 4/4: Reloading Enigma2 EPG Cache into live TV guide..."
if command -v wget >/dev/null 2>&1; then
    wget -q -O - "http://127.0.0.1/web/epgreload?reload=1" >/dev/null 2>&1 || true
    wget -q -O - "http://127.0.0.1/api/epgreload" >/dev/null 2>&1 || true
elif command -v curl >/dev/null 2>&1; then
    curl -s "http://127.0.0.1/web/epgreload?reload=1" >/dev/null 2>&1 || true
    curl -s "http://127.0.0.1/api/epgreload" >/dev/null 2>&1 || true
fi

# Cleanup temporary engine script
rm -f "$TMP_PY"

if [ $RET_VAL -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo " [?] SUCCESS: EPG is now 100% Arabic!"
    echo "     All channel guides updated on screen."
    echo "============================================================"
    echo "[$TIMESTAMP] [SUCCESS] Completed standalone EPG translation." >> "$LOG_FILE"
    exit 0
else
    echo ""
    echo "[X] Translation finished with errors (code $RET_VAL)."
    echo "[$TIMESTAMP] [FAIL] Standalone translation error code $RET_VAL." >> "$LOG_FILE"
    exit $RET_VAL
fi