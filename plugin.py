# -*- coding: utf-8 -*-
# =========================================================================
# Mohamed Store - Universal Auto-Scaling Edition (Vu+, Dreambox, 4K, FHD, HD)
# Compatible with: OpenATV, OpenPLi, Egami, BlackHole, OBH, VTi, DreamOS (OE2.5/2.6)
# Python 2.7 & Python 3.x (3.9 - 3.12) Universal Support
# =========================================================================
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.Console import Console
import json
import os
import sys
import socket
import struct
import fcntl
import threading
import time
import re

try:
    from Screens.Standby import TryQuitMainloop
except ImportError:
    TryQuitMainloop = None

try:
    import enigma
except ImportError:
    enigma = None

try:
    from enigma import eTimer
except ImportError:
    eTimer = None

try:
    from enigma import gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, eListboxPythonMultiContent
    HAS_MULTICONTENT = True
except ImportError:
    gFont = None
    RT_HALIGN_LEFT = 0
    RT_HALIGN_RIGHT = 2
    eListboxPythonMultiContent = None
    HAS_MULTICONTENT = False

try:
    from Tools.LoadPixmap import loadPNG
except ImportError:
    loadPNG = None

try:
    from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
except ImportError:
    MultiContentEntryText = None
    MultiContentEntryPixmapAlphaTest = None

try:
    from enigma import RT_VALIGN_CENTER
except ImportError:
    RT_VALIGN_CENTER = 4

try:
    from Components.ProgressBar import ProgressBar
except ImportError:
    ProgressBar = None

# =========================================================================
# UNIVERSAL RESOLUTION DETECTION & AUTO-SCALING ENGINE
# =========================================================================
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

try:
    from enigma import getDesktop
    desk = getDesktop(0)
    if desk:
        d_size = desk.size()
        SCREEN_WIDTH = d_size.width()
        SCREEN_HEIGHT = d_size.height()
except Exception:
    pass

# Scale factors relative to FHD 1920x1080 base design
SCALE_X = float(SCREEN_WIDTH) / 1920.0
SCALE_Y = float(SCREEN_HEIGHT) / 1080.0

def scale_x(val):
    return int(round(val * SCALE_X))

def scale_y(val):
    return int(round(val * SCALE_Y))

def scale_font(size):
    return max(12, int(round(size * SCALE_Y)))

def scale_skin_layout(xml_layout):
    """
    Dynamically scales all skin attributes (position, size, font, itemHeight, borderWidth)
    to match the active receiver's desktop resolution (HD 720p, FHD 1080p, 4K UHD 2160p).
    """
    if abs(SCALE_X - 1.0) < 0.005 and abs(SCALE_Y - 1.0) < 0.005:
        return xml_layout

    def _sub_pos(m):
        px, py = int(m.group(1)), int(m.group(2))
        return 'position="%d,%d"' % (scale_x(px), scale_y(py))

    def _sub_size(m):
        sw, sh = int(m.group(1)), int(m.group(2))
        return 'size="%d,%d"' % (scale_x(sw), scale_y(sh))

    def _sub_font(m):
        fname, fsize = m.group(1), int(m.group(2))
        return 'font="%s;%d"' % (fname, scale_font(fsize))

    def _sub_item_height(m):
        ih = int(m.group(1))
        return 'itemHeight="%d"' % scale_y(ih)

    def _sub_border(m):
        bw = int(m.group(1))
        return 'borderWidth="%d"' % max(1, scale_x(bw))

    out = xml_layout
    out = re.sub(r'position="(\d+),(\d+)"', _sub_pos, out)
    out = re.sub(r'size="(\d+),(\d+)"', _sub_size, out)
    out = re.sub(r'font="([^;]+);(\d+)"', _sub_font, out)
    out = re.sub(r'itemHeight="(\d+)"', _sub_item_height, out)
    out = re.sub(r'borderWidth="(\d+)"', _sub_border, out)
    return out

VERSION_URL = "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/version.json"
STORE_URL = "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/feed/index.json"
UPDATE_SCRIPT_CMD = "wget -O - https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/install.sh | sh"
PLUGIN_VERSION = "1.3.2"

try:
    PLUGIN_DIR = os.path.dirname(__file__)
except NameError:
    PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore"

CACHE_FILE = os.path.join(PLUGIN_DIR, "store_cache.json")
ICON_FOLDER = os.path.join(PLUGIN_DIR, "images", "Icons")
FALLBACK_ICON_FOLDER = "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/Icons"
PROGRESS_PNG_PATH = os.path.join(PLUGIN_DIR, "images", "progress.png")
FALLBACK_PROGRESS_PNG = "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/progress.png"

def ensure_gradient_progress_png():
    """Generates an auto-scaled multi-color gradient progress bar PNG"""
    import zlib
    target_paths = [PROGRESS_PNG_PATH, FALLBACK_PROGRESS_PNG]
    for p in target_paths:
        try:
            if not os.path.exists(p):
                width = max(200, scale_x(436))
                height = max(8, scale_y(14))
                raw_data = bytearray()
                for y in range(height):
                    raw_data.append(0)  # Filter: None
                    for x in range(width):
                        t = float(x) / max(1.0, float(width - 1))
                        if t < 0.33:
                            st = t / 0.33
                            r = int(245 + (56 - 245) * st)
                            g = int(158 + (189 - 158) * st)
                            b = int(11 + (248 - 11) * st)
                        elif t < 0.66:
                            st = (t - 0.33) / 0.33
                            r = int(56 + (168 - 56) * st)
                            g = int(189 + (85 - 189) * st)
                            b = int(248 + (247 - 248) * st)
                        else:
                            st = (t - 0.66) / 0.34
                            r = int(168 + (236 - 168) * st)
                            g = int(85 + (72 - 85) * st)
                            b = int(247 + (153 - 247) * st)
                        raw_data.extend([max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))])

                png = bytearray(b'\x89PNG\r\n\x1a\n')
                ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
                png.extend(struct.pack('>I', 13) + b'IHDR' + ihdr + struct.pack('>I', zlib.crc32(b'IHDR' + ihdr) & 0xffffffff))
                compressed = zlib.compress(bytes(raw_data))
                png.extend(struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', zlib.crc32(b'IDAT' + compressed) & 0xffffffff))
                png.extend(struct.pack('>I', 0) + b'IEND' + struct.pack('>I', zlib.crc32(b'IEND') & 0xffffffff))

                dirp = os.path.dirname(p)
                if not os.path.exists(dirp):
                    os.makedirs(dirp)
                with open(p, 'wb') as f:
                    f.write(png)
        except Exception:
            pass

try:
    ensure_gradient_progress_png()
except Exception:
    pass

# =========================================================================
# OSCAM SMART TOGGLE / SWITCHER
# =========================================================================
def set_reader_blocks_state(content, is_enable_paid, is_enable_free):
    blocks = []
    current = []
    for line in content.split("\n"):
        if line.strip().startswith("[reader]"):
            if current:
                blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)

    final_blocks = []
    for b in blocks:
        block_txt = "\n".join(b)
        if not block_txt.strip().startswith("[reader]"):
            final_blocks.append(block_txt)
            continue
            
        is_tiger = ("tigerhd4k" in block_txt.lower()) or ("free_tigerhd" in block_txt.lower())
        target_enable = 1 if (is_tiger and is_enable_free) or (not is_tiger and is_enable_paid) else 0
        
        new_lines = []
        has_enable = False
        for l in b:
            if l.strip().startswith("enable"):
                new_lines.append("enable                        = %d" % target_enable)
                has_enable = True
            else:
                new_lines.append(l)
        if not has_enable:
            new_lines.insert(1, "enable                        = %d" % target_enable)
            
        final_blocks.append("\n".join(new_lines))
        
    return "\n".join(final_blocks)

def generate_tigerhd_server():
    try:
        if sys.version_info >= (3, 0):
            import urllib.request as urllib2
            import urllib.parse as urllib_parse
            import ssl
            import http.cookiejar as cookiejar
            context = ssl._create_unverified_context()
        else:
            import urllib2
            import urllib as urllib_parse
            import ssl
            import cookielib as cookiejar
            try:
                context = ssl._create_unverified_context()
            except AttributeError:
                context = None

        main_oscam_path = "/etc/tuxbox/config/oscam.server"
        c_host, c_port, c_user, c_pass = "", "", "", ""
        clines = []

        try:
            cj = cookiejar.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            req = urllib2.Request('https://tigerhd4k.com/testoscam/', headers=headers)
            res = opener.open(req, timeout=8)
            page = res.read()
            if isinstance(page, bytes):
                page = page.decode('utf-8', 'ignore')

            token_m = re.search(r'name="_token"\s+value="([^"]+)"', page) or re.search(r"name='_token'\s+value='([^']+)'", page)
            trial_m = re.search(r'name="trial"\s+value="([^"]+)"', page) or re.search(r"name='trial'\s+value='([^']+)'", page)
            cs_m = re.search(r'name="CS"\s+value="([^"]+)"', page) or re.search(r"name='CS'\s+value='([^']+)'", page)

            if token_m and trial_m:
                post_fields = {
                    '_token': token_m.group(1),
                    'trial-ok': '1',
                    'trial': trial_m.group(1),
                    'CS': cs_m.group(1) if cs_m else "2021"
                }
                encoded_data = urllib_parse.urlencode(post_fields)
                if isinstance(encoded_data, str) and sys.version_info >= (3, 0):
                    encoded_data = encoded_data.encode('utf-8')

                post_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                    'Referer': 'https://tigerhd4k.com/testoscam/',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                post_req = urllib2.Request('https://tigerhd4k.com/testoscam/', data=encoded_data, headers=post_headers)
                post_res = opener.open(post_req, timeout=10)
                post_html = post_res.read()
                if isinstance(post_html, bytes):
                    post_html = post_html.decode('utf-8', 'ignore')

                clines = re.findall(r'C:\s*[\w\.\-]+\s+\d+\s+[\w\.\-]+\s+[\w\.\-]+', post_html)
                if clines:
                    parts = clines[0].split()
                    if len(parts) >= 5:
                        c_host, c_port, c_user, c_pass = parts[1], parts[2], parts[3], parts[4]
        except Exception:
            pass

        if not c_host and not clines:
            try:
                update_url = "https://raw.githubusercontent.com/wwwgoper77-wq/epg-pro-licensing/main/oscam.server"
                fb_req = urllib2.Request(update_url, headers={'User-Agent': 'Mozilla/5.0'})
                fb_res = urllib2.urlopen(fb_req, timeout=6)
                fb_data = fb_res.read()
                if isinstance(fb_data, bytes):
                    fb_data = fb_data.decode('utf-8', 'ignore')
                
                clines_m = re.findall(r'C:\s*[\w\.\-]+\s+\d+\s+[\w\.\-]+\s+[\w\.\-]+', fb_data)
                if clines_m:
                    clines = clines_m
                    parts = clines[0].split()
                    c_host, c_port, c_user, c_pass = parts[1], parts[2], parts[3], parts[4]
            except Exception:
                pass

        if not c_host and not clines:
            return (False, "Could not obtain free server.")

        free_reader_block = (
            "### FREE_TIGERHD_START ###\n"
            "[reader]\n"
            "label                         = Store_CCcam_Daily\n"
            "enable                        = 1\n"
            "protocol                      = cccam\n"
            "device                        = %s,%s\n"
            "user                          = %s\n"
            "password                      = %s\n"
            "group                         = 1\n"
            "cccversion                    = 2.3.2\n"
            "ccckeepalive                  = 1\n"
            "### FREE_TIGERHD_END ###\n"
        ) % (c_host or "tigerhd4k.com", c_port or "37000", c_user or "1daytest", c_pass or "2021")

        all_oscam_paths = [
            "/etc/tuxbox/config/oscam.server",
            "/etc/tuxbox/config/oscam-emu/oscam.server",
            "/etc/tuxbox/config/oscam/oscam.server",
            "/etc/tuxbox/config/ncam.server"
        ]

        for op in all_oscam_paths:
            if op == main_oscam_path or os.path.exists(op):
                try:
                    existing_text = ""
                    if os.path.exists(op):
                        with open(op, "r") as rf:
                            existing_text = rf.read()
                    
                    if "### FREE_TIGERHD_START ###" in existing_text:
                        before = existing_text.split("### FREE_TIGERHD_START ###")[0]
                        after = existing_text.split("### FREE_TIGERHD_END ###")[-1]
                        existing_text = (before.rstrip() + "\n" + after.lstrip()).strip()
                    
                    if existing_text:
                        existing_text = set_reader_blocks_state(existing_text, is_enable_paid=False, is_enable_free=False)
                        final_content = existing_text + "\n\n" + free_reader_block
                    else:
                        final_content = free_reader_block
                    
                    with open(op, "w") as f:
                        f.write(final_content.strip() + "\n")
                except Exception:
                    pass

        os.system("killall -9 oscam oscam_svn oscam-oe2.0 oscam-emu ncam ncam.arm gcam 2>/dev/null; sleep 1; oscam -b 2>/dev/null || oscam & 2>/dev/null; /etc/init.d/softcam restart 2>/dev/null")

        res_msg = "Store Daily CCcam Activated Successfully!\n\n"
        res_msg += "Description: Server opening most world packages\n\n"
        res_msg += "Status:\n- Store Server (Store CCcam): ACTIVE (ON)\n- Paid Server: PAUSED (OFF)\n\nOSCam restarted automatically."
        return (True, res_msg)
    except Exception as e:
        return (False, "Error: " + str(e))

def restore_paid_oscam():
    all_oscam_paths = [
        "/etc/tuxbox/config/oscam.server",
        "/etc/tuxbox/config/oscam-emu/oscam.server",
        "/etc/tuxbox/config/oscam/oscam.server",
        "/etc/tuxbox/config/ncam.server"
    ]
    try:
        for op in all_oscam_paths:
            if os.path.exists(op):
                with open(op, "r") as f:
                    content = f.read()
                
                if "### FREE_TIGERHD_START ###" in content:
                    before = content.split("### FREE_TIGERHD_START ###")[0]
                    after = content.split("### FREE_TIGERHD_END ###")[-1]
                    content = (before.rstrip() + "\n" + after.lstrip()).strip()
                elif "tigerhd4k" in content or "Store_CCcam_Daily" in content:
                    lines = []
                    skip = False
                    for line in content.split("\n"):
                        if line.strip().startswith("[reader]"):
                            skip = False
                        if "tigerhd4k" in line or "Store_CCcam_Daily" in line:
                            skip = True
                        if not skip:
                            lines.append(line)
                    content = "\n".join(lines).strip()
                
                new_content = set_reader_blocks_state(content, is_enable_paid=True, is_enable_free=False)
                with open(op, "w") as f:
                    f.write(new_content.strip() + "\n")

        os.system("killall -9 oscam oscam_svn oscam-oe2.0 oscam-emu ncam ncam.arm gcam 2>/dev/null; sleep 1; oscam -b 2>/dev/null || oscam & 2>/dev/null; /etc/init.d/softcam restart 2>/dev/null")
        
        msg = "Paid Server Restored Successfully!\n\nStatus:\n- Paid Server: ACTIVE (ON)\n- Store Free Server: DISABLED (OFF)\n\nOSCam restarted automatically."
        return (True, msg)
    except Exception as e:
        return (False, "Error: " + str(e))

def get_active_oscam_status():
    all_oscam_paths = [
        "/etc/tuxbox/config/oscam.server",
        "/etc/tuxbox/config/oscam-emu/oscam.server",
        "/etc/tuxbox/config/oscam/oscam.server",
        "/etc/tuxbox/config/ncam.server"
    ]
    found_path = None
    content = ""
    for path in all_oscam_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    content = f.read().strip()
                if content:
                    found_path = path
                    break
            except Exception:
                pass

    if not found_path or not content:
        return (False, u"[!] \u0644\u0645 \u064a\u062a\u0645 \u0627\u0644\u0639\u062b\u0648\u0631 \u0639\u0644\u0649 \u0645\u0644\u0641 \u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0633\u064a\u0631\u0641\u0631!\nFile /etc/tuxbox/config/oscam.server not found or empty.")

    try:
        blocks = []
        current = []
        for line in content.split("\n"):
            if line.strip().startswith("[reader]"):
                if current:
                    blocks.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            blocks.append("\n".join(current))

        active_readers = []

        for b in blocks:
            if not b.strip().startswith("[reader]"):
                continue
            
            lbl_match = re.search(r'label\s*=\s*([^\n\r]+)', b, re.IGNORECASE)
            raw_label = lbl_match.group(1).strip() if lbl_match else "Reader"

            dev_match = re.search(r'device\s*=\s*([^\n\r]+)', b, re.IGNORECASE)
            dev_val = dev_match.group(1).strip() if dev_match else "N/A"

            proto_match = re.search(r'protocol\s*=\s*([^\n\r]+)', b, re.IGNORECASE)
            proto_val = proto_match.group(1).strip() if proto_match else "cccam"

            low_lbl = raw_label.lower()
            low_proto = proto_val.lower()
            low_dev = dev_val.lower()
            if low_proto in ["emu", "ecmbin", "constcw", "internal", "softcam"] or \
               low_lbl in ["emulator", "ecmemu", "streamrelay", "icam", "softcam"] or \
               low_dev in ["emulator", "ecmemu"] or \
               "emu" in low_proto or "emu" in low_lbl or "ecm" in low_proto or "ecm" in low_lbl:
                continue

            en_match = re.search(r'enable\s*=\s*(\d+)', b, re.IGNORECASE)
            is_enabled = (en_match.group(1).strip() != "0") if en_match else True
            
            if not is_enabled:
                continue

            is_store_server = ("tigerhd" in b.lower()) or ("free_tigerhd" in b.lower()) or ("store" in b.lower()) or ("store" in raw_label.lower())
            
            user_match = re.search(r'user\s*=\s*([^\n\r]+)', b, re.IGNORECASE)
            user_val = user_match.group(1).strip() if user_match else "N/A"

            grp_match = re.search(r'group\s*=\s*([^\n\r]+)', b, re.IGNORECASE)
            grp_val = grp_match.group(1).strip() if grp_match else "1"

            ccc_ver_match = re.search(r'cccversion\s*=\s*([^\n\r]+)', b, re.IGNORECASE)
            ccc_ver = ccc_ver_match.group(1).strip() if ccc_ver_match else ""

            if is_store_server:
                label_val = u"\u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0645\u062a\u062c\u0631 (Store Server)"
                server_type = u"\u0633\u064a\u0631\u0641\u0631 \u0633\u064a\u0633\u0643\u0627\u0645 \u0627\u0644\u0645\u062a\u062c\u0631 \u0627\u0644\u064a\u0648\u0645\u064a"
                card_info = [
                    u"[+] \u0627\u0644\u0646\u0648\u0639: %s" % server_type,
                    u"[+] \u0627\u0644\u0625\u0633\u0645 (Label): %s" % label_val,
                    u"[+] \u0627\u0644\u0648\u0635\u0641: \u0633\u064a\u0631\u0641\u0631 \u0641\u0627\u062a\u062d \u0627\u063a\u0644\u0628 \u0627\u0644\u0628\u0627\u0642\u0627\u062a \u0627\u0644\u0639\u0627\u0644\u0645\u064a\u0629",
                    u"[+] \u0627\u0644\u062d\u0627\u0644\u0629: [ACTIVE - ON] \u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0645\u062a\u062c\u0631 \u0634\u063a\u0627\u0644 \u0648\u0646\u0634\u0637"
                ]
            else:
                label_val = raw_label
                server_type = u"\u0633\u064a\u0631\u0641\u0631 \u0645\u062f\u0641\u0648\u0639 / \u062e\u0627\u0635 (Paid/Custom)"
                card_info = [
                    u"[+] \u0627\u0644\u0646\u0648\u0639: %s" % server_type,
                    u"[+] \u0627\u0644\u0625\u0633\u0645 (Label): %s" % label_val,
                    u"[+] \u0627\u0644\u0628\u0631\u0648\u062a\u0648\u0643\u0648\u0644: %s %s" % (proto_val, ("(v%s)" % ccc_ver) if ccc_ver else ""),
                    u"[+] \u0627\u0644\u0639\u0646\u0648\u0627\u0646 (Host/Port): %s" % dev_val,
                    u"[+] \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645 (User): %s" % user_val,
                    u"[+] \u0627\u0644\u0645\u062c\u0645\u0648\u0639\u0629 (Group): %s" % grp_val,
                    u"[+] \u0627\u0644\u062d\u0627\u0644\u0629: [ACTIVE - ON] \u0634\u063a\u0627\u0644 \u0648\u0646\u0634\u0637"
                ]
            
            active_readers.append("\n".join(card_info))

        if not active_readers:
            msg = (
                u"[!] \u0644\u0627 \u064a\u0648\u062c\u062f \u0623\u064a \u0633\u064a\u0631\u0641\u0631 \u0646\u0634\u0637 \u062d\u0627\u0644\u064a\u0627\u064b!\n"
                "----------------------------------------\n"
                u"[-] \u062c\u0645\u064a\u0639 \u0627\u0644\u0633\u064a\u0631\u0641\u0631\u0627\u062a \u0641\u064a oscam.server \u0645\u0639\u0637\u0644\u0629 (enable = 0) \u0623\u0648 \u063a\u064a\u0631 \u0645\u0636\u0627\u0641\u0629.\n\n"
                u"[+] \u0644\u062a\u0634\u063a\u064a\u0644 \u0633\u064a\u0631\u0641\u0631:\n"
                u"- \u064a\u0645\u0643\u0646\u0643 \u0627\u062e\u062a\u064a\u0627\u0631 '\u0633\u064a\u0631\u0641\u0631 \u0633\u064a\u0633\u0643\u0627\u0645 \u0627\u0644\u0645\u062a\u062c\u0631 \u0627\u0644\u064a\u0648\u0645\u064a'\n"
                u"- \u0623\u0648 \u0627\u062e\u062a\u064a\u0627\u0631 '\u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0627\u0644\u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0645\u062f\u0641\u0648\u0639'"
            )
            return (True, msg)

        emu_running = False
        try:
            p_check = os.popen("pgrep -x oscam || pgrep -x oscam-emu || pgrep -x ncam || pidof oscam").read().strip()
            if p_check:
                emu_running = True
        except Exception:
            pass

        msg = u"[*] \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0627\u0644\u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0646\u0634\u0637 (\u0627\u0644\u0634\u063a\u0627\u0644 \u062d\u0627\u0644\u064a\u0627\u064b):\n"
        msg += "========================================\n"
        if emu_running:
            msg += u"[*] \u062d\u0627\u0644\u0629 \u0627\u0644\u0625\u064a\u0645\u0648: \u0634\u063a\u0627\u0644 \u0641\u064a \u0627\u0644\u062e\u0644\u0641\u064a\u0629 (OSCam Running)\n"
        msg += "[*] Path: %s\n" % found_path
        msg += "========================================\n\n"
        msg += "\n\n----------------------------------------\n\n".join(active_readers)

        return (True, msg)
    except Exception as e:
        return (False, u"\u062d\u062f\u062b \u062e\u0637\u0623 \u0623\u062b\u0646\u0627\u0621 \u0641\u062d\u0635 \u0627\u0644\u0633\u064a\u0631\u0641\u0631: " + str(e))

def restart_oscam_service():
    try:
        os.system("killall -9 oscam oscam_svn oscam-oe2.0 oscam-emu ncam ncam.arm gcam 2>/dev/null; sleep 1; oscam -b 2>/dev/null || oscam & 2>/dev/null; /etc/init.d/softcam restart 2>/dev/null")
        return (True, "OSCam / SoftCam restarted successfully!")
    except Exception as e:
        return (False, "Restart error: " + str(e))

def stop_oscam_service():
    try:
        os.system("killall -9 oscam oscam_svn oscam-oe2.0 oscam-emu ncam ncam.arm gcam 2>/dev/null")
        return (True, "OSCam / SoftCam stopped successfully!")
    except Exception as e:
        return (False, "Stop error: " + str(e))

BUILTIN_SYSTEM_TOOLS = [
    {
        "name": u"\u0639\u0631\u0636 \u062d\u0627\u0644\u0629 \u0627\u0644\u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0646\u0634\u0637 (Check OSCam Status)",
        "type": "tool",
        "action": "check_oscam_status",
        "description": u"\u0641\u062d\u0635 \u0645\u0644\u0641 oscam.server \u0648\u0639\u0631\u0636 \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0645\u062a\u062c\u0631 \u0627\u0644\u0634\u063a\u0627\u0644 \u0641\u0642\u0637 (Active Only)."
    },
    {
        "name": u"\u0633\u064a\u0631\u0641\u0631 \u0633\u064a\u0633\u0643\u0627\u0645 \u0627\u0644\u0645\u062a\u062c\u0631 \u0627\u0644\u064a\u0648\u0645\u064a (Store Daily CCcam Server)",
        "type": "tool",
        "action": "tiger_server",
        "description": u"\u0633\u064a\u0631\u0641\u0631 \u0641\u0627\u062a\u062d \u0627\u063a\u0644\u0628 \u0627\u0644\u0628\u0627\u0642\u0627\u062a \u0627\u0644\u0639\u0627\u0644\u0645\u064a\u0629"
    },
    {
        "name": u"\u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0627\u0644\u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0645\u062f\u0641\u0648\u0639 (Restore Paid OSCam)",
        "type": "tool",
        "action": "restore_paid",
        "description": u"\u0625\u0639\u0627\u062f\u0629 \u062a\u0641\u0639\u064a\u0644 \u0627\u0644\u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0645\u062f\u0641\u0648\u0639 \u0627\u0644\u0623\u0635\u0644\u064a \u0648\u0625\u064a\u0642\u0627\u0641 \u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0645\u062a\u062c\u0631."
    },
    {
        "name": u"\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0625\u064a\u0645\u0648 OSCam (Restart OSCam)",
        "type": "tool",
        "action": "restart_oscam",
        "description": u"\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0625\u064a\u0645\u0648 OSCam / NCam \u0644\u062a\u062d\u062f\u064a\u062b \u0627\u0644\u0634\u0641\u0631\u0627\u062a."
    },
    {
        "name": u"\u0625\u064a\u0642\u0627\u0641 \u0625\u064a\u0645\u0648 OSCam (Stop OSCam)",
        "type": "tool",
        "action": "stop_oscam",
        "description": u"\u0625\u064a\u0642\u0627\u0641 \u062a\u0634\u063a\u064a\u0644 \u0625\u064a\u0645\u0648 OSCam / NCam."
    },
    {
        "name": u"\u062a\u0646\u0638\u064a\u0641 \u0627\u0644\u0630\u0627\u0643\u0631\u0629 \u0648\u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0645\u0624\u0642\u062a\u0629",
        "type": "tool",
        "cmd": "rm -rf /tmp/*.ipk /tmp/*.tar.gz /tmp/*.zip /var/volatile/tmp/*",
        "description": u"\u062d\u0630\u0641 \u062c\u0645\u064a\u0639 \u0645\u0644\u0641\u0627\u062a \u0627\u0644\u062a\u062b\u0628\u064a\u062a \u0648\u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0645\u0624\u0642\u062a\u0629 \u0645\u0646 /tmp."
    },
    {
        "name": u"\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0648\u0627\u062c\u0647\u0629 (Restart GUI)",
        "type": "tool",
        "cmd": "restart_gui",
        "description": u"\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0648\u0627\u062c\u0647\u0629 \u0627\u0644\u0633\u0633\u062a\u0645."
    }
]

def get_neoboot_images_upload_path():
    for p in ["/media/hdd/ImagesUpload", "/media/usb/ImagesUpload", "/media/mmc/ImagesUpload", "/data/ImagesUpload", "/media/hdd", "/media/usb"]:
        if os.path.exists(p):
            return p
    return "/media/hdd/ImagesUpload"

def get_direct_hdd_root_path():
    for drive in ["/media/hdd", "/media/usb", "/media/mmc", "/data"]:
        if os.path.exists(drive):
            return drive
    return "/media/hdd"

def get_real_box_ip():
    for ifname in ["eth0", "wlan0", "eth1", "ra0", "wlan1", "lan0", "enp3s0"]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ifname_bytes = ifname.encode('utf-8') if sys.version_info >= (3, 0) else ifname
            ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname_bytes[:15]))[20:24])
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass
    return "192.168.1.1"

def get_category_icon_path(category_id):
    try:
        cat_lower = str(category_id).lower().replace("_", "").replace(" ", "")
        if "plugin" in cat_lower:
            filename = "plugins.png"
        elif "skin" in cat_lower:
            filename = "skins.png"
        elif "tool" in cat_lower:
            filename = "tools.png"
        elif "image" in cat_lower or "system" in cat_lower:
            filename = "system_images.png"
        elif "picon" in cat_lower:
            filename = "picons.png"
        elif "channel" in cat_lower or "setting" in cat_lower:
            filename = "channels.png"
        elif "softcam" in cat_lower or "cam" in cat_lower or "emu" in cat_lower:
            filename = "softcam.png"
        elif "noval" in cat_lower or "nofla" in cat_lower:
            filename = "novaler.png"
        else:
            filename = None
            
        if filename:
            for folder in [ICON_FOLDER, FALLBACK_ICON_FOLDER, os.path.join(PLUGIN_DIR, "images")]:
                try:
                    full_p = os.path.join(folder, filename)
                    if os.path.exists(full_p):
                        return full_p
                except Exception:
                    pass
    except Exception:
        pass
    return None

def get_item_icon_path(item, category_id):
    try:
        if not isinstance(item, dict):
            return get_category_icon_path(category_id)

        for key in ("icon", "image", "thumbnail"):
            val = item.get(key)
            if val and isinstance(val, (str, getattr(sys, 'unicode', str))):
                val = val.strip()
                try:
                    if os.path.isabs(val) and os.path.exists(val):
                        return val
                except Exception:
                    pass
                for folder in [ICON_FOLDER, FALLBACK_ICON_FOLDER, os.path.join(PLUGIN_DIR, "images")]:
                    try:
                        p = os.path.join(folder, val)
                        if os.path.exists(p):
                            return p
                    except Exception:
                        pass

        item_id = item.get("id") or item.get("name") or ""
        if item_id:
            clean_name = str(item_id).lower().replace(" ", "_").replace("-", "_") + ".png"
            for folder in [ICON_FOLDER, FALLBACK_ICON_FOLDER, os.path.join(PLUGIN_DIR, "images")]:
                try:
                    p = os.path.join(folder, clean_name)
                    if os.path.exists(p):
                        return p
                except Exception:
                    pass

        if "items" in item and isinstance(item["items"], list):
            for folder_icon in ("folder.png", "subfolder.png"):
                try:
                    p = os.path.join(ICON_FOLDER, folder_icon)
                    if os.path.exists(p):
                        return p
                except Exception:
                    pass

        if item.get("type") == "tool":
            try:
                p = os.path.join(ICON_FOLDER, "tools.png")
                if os.path.exists(p):
                    return p
            except Exception:
                pass

        return get_category_icon_path(category_id)
    except Exception:
        return None

def count_items_recursive(items_list):
    if not isinstance(items_list, list):
        return 0
    count = 0
    for it in items_list:
        if isinstance(it, dict) and "items" in it and isinstance(it["items"], list):
            count += count_items_recursive(it["items"])
        else:
            count += 1
    return count

def load_json_network(url):
    try:
        if sys.version_info >= (3, 0):
            import urllib.request as urllib2
            import ssl
            context = ssl._create_unverified_context()
        else:
            import urllib2
            import ssl
            try:
                context = ssl._create_unverified_context()
            except AttributeError:
                context = None
        
        req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        if context:
            response = urllib2.urlopen(req, timeout=5, context=context)
        else:
            response = urllib2.urlopen(req, timeout=5)
        data = response.read()
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        return json.loads(data)
    except Exception:
        return None

# Base Full HD reference XML layout
RAW_SKIN_LAYOUT = """
<screen name="MohamedStore" position="center,center" size="1724,920" title="Mohamed Store" flags="wfNoBorder">
    <eLabel position="0,0" size="1724,920" backgroundColor="#05070c" zPosition="-11" />
    <ePixmap position="0,0" size="1724,920" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/background.png" zPosition="-10" transparent="0" alphatest="off" />

    <!-- HEADER PANEL -->
    <eLabel position="20,15" size="1684,84" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="20,15" size="1684,2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="20,15" size="4,84" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="1700,15" size="4,84" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="20,99" size="1684,2" backgroundColor="#e11d48" />
    
    <ePixmap position="32,24" size="190,44" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/logo.png" zPosition="2" scale="1" transparent="1" alphatest="blend" />
    <eLabel position="230,22" size="120,30" text="MOHAMED" font="Regular;24" foregroundColor="#f59e0b" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="350,22" size="90,30" text="STORE" font="Regular;24" foregroundColor="#38bdf8" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="230,50" size="70,2" backgroundColor="#f59e0b" zPosition="2" />
    <eLabel position="300,50" size="70,2" backgroundColor="#38bdf8" zPosition="2" />
    <eLabel position="370,50" size="70,2" backgroundColor="#ec4899" zPosition="2" />
    <eLabel position="230,56" size="75,22" text=" v1.3.2 " font="Regular;17" foregroundColor="#ffffff" backgroundColor="#be185d" transparent="0" halign="center" />

    <!-- HARDWARE CHIPS -->
    <eLabel position="445,19" size="305,74" backgroundColor="#070913" zPosition="1" />
    <eLabel position="445,19" size="305,2" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="445,19" size="3,74" backgroundColor="#60a5fa" zPosition="2" />
    <eLabel position="445,91" size="305,2" backgroundColor="#be185d" zPosition="2" />
    <widget name="sys_device" position="455,23" size="290,32" font="Regular;24" foregroundColor="#60a5fa" backgroundColor="#070913" transparent="1" zPosition="3" />
    <widget name="sys_image" position="455,56" size="290,30" font="Regular;22" foregroundColor="#c084fc" backgroundColor="#070913" transparent="1" zPosition="3" />

    <eLabel position="760,19" size="300,74" backgroundColor="#070913" zPosition="1" />
    <eLabel position="760,19" size="300,2" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="760,19" size="3,74" backgroundColor="#f43f5e" zPosition="2" />
    <eLabel position="760,91" size="300,2" backgroundColor="#be185d" zPosition="2" />
    <widget name="sys_cpu" position="770,23" size="285,32" font="Regular;24" foregroundColor="#f43f5e" backgroundColor="#070913" transparent="1" zPosition="3" />
    <widget name="sys_temp" position="770,56" size="285,30" font="Regular;22" foregroundColor="#fb923c" backgroundColor="#070913" transparent="1" zPosition="3" />

    <eLabel position="1070,19" size="305,74" backgroundColor="#070913" zPosition="1" />
    <eLabel position="1070,19" size="305,2" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="1070,19" size="3,74" backgroundColor="#34d399" zPosition="2" />
    <eLabel position="1070,91" size="305,2" backgroundColor="#be185d" zPosition="2" />
    <widget name="sys_ram" position="1080,23" size="290,32" font="Regular;24" foregroundColor="#34d399" backgroundColor="#070913" transparent="1" zPosition="3" />
    <widget name="sys_flash" position="1080,56" size="290,30" font="Regular;22" foregroundColor="#a7f3d0" backgroundColor="#070913" transparent="1" zPosition="3" />

    <eLabel position="1385,19" size="305,74" backgroundColor="#070913" zPosition="1" />
    <eLabel position="1385,19" size="305,2" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="1385,19" size="3,74" backgroundColor="#38bdf8" zPosition="2" />
    <eLabel position="1385,91" size="305,2" backgroundColor="#be185d" zPosition="2" />
    <widget name="sys_ip" position="1395,23" size="290,32" font="Regular;24" foregroundColor="#38bdf8" backgroundColor="#070913" transparent="1" zPosition="3" />
    <widget name="sys_net" position="1395,56" size="290,30" font="Regular;22" foregroundColor="#818cf8" backgroundColor="#070913" transparent="1" zPosition="3" />

    <!-- LEFT PANEL: CATEGORIES -->
    <eLabel position="20,112" size="380,688" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="20,112" size="380,2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="20,112" size="4,688" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="396,112" size="4,688" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="32,126" size="356,35" text="CATEGORIES" font="Regular;30" foregroundColor="#f43f5e" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="32,166" size="356,2" backgroundColor="#be185d" />
    <widget name="categories_list" position="25,176" size="370,616" itemHeight="80" scrollbarMode="showOnDemand" foregroundColor="#f3f4f6" backgroundColor="#0f111a" transparent="1" />

    <!-- CENTER PANEL: PACKAGES -->
    <eLabel position="412,112" size="780,688" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="412,112" size="780,2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="412,112" size="4,688" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="1188,112" size="4,688" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="428,126" size="748,35" text="AVAILABLE PACKAGES" font="Regular;30" foregroundColor="#f43f5e" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="428,166" size="748,2" backgroundColor="#be185d" />
    <widget name="items_list" position="417,176" size="768,616" itemHeight="76" scrollbarMode="showOnDemand" foregroundColor="#f3f4f6" backgroundColor="#0f111a" transparent="1" />

    <!-- RIGHT PANEL: DETAILS & FACEBOOK & PROGRESS -->
    <eLabel position="1204,112" size="500,688" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="1204,112" size="500,2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="1204,112" size="4,688" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="1700,112" size="4,688" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="1222,126" size="464,35" text="INFORMATION" font="Regular;30" foregroundColor="#f43f5e" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="1222,166" size="464,2" backgroundColor="#be185d" />
    
    <widget name="description" position="1222,174" size="464,376" font="Regular;24" foregroundColor="#e2e8f0" backgroundColor="#0f111a" transparent="1" valign="top" />

    <!-- FACEBOOK & BARCODE BOX -->
    <eLabel position="1220,558" size="468,110" backgroundColor="#120e1a" zPosition="1" />
    <eLabel position="1220,558" size="468,2" backgroundColor="#f59e0b" zPosition="2" />
    <eLabel position="1220,558" size="2,110" backgroundColor="#0284c7" zPosition="2" />
    <eLabel position="1686,558" size="2,110" backgroundColor="#ec4899" zPosition="2" />
    <eLabel position="1220,666" size="468,2" backgroundColor="#f59e0b" zPosition="2" />
    
    <ePixmap position="1230,571" size="78,82" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/avatar.png" zPosition="3" scale="1" transparent="1" alphatest="blend" />
    <ePixmap position="1316,571" size="82,82" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/qrcode.png" zPosition="3" scale="1" transparent="1" alphatest="blend" />
    
    <eLabel position="1408,568" size="90,34" backgroundColor="#f59e0b" zPosition="2" />
    <eLabel position="1498,568" size="90,34" backgroundColor="#0284c7" zPosition="2" />
    <eLabel position="1588,568" size="90,34" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="1410,570" size="266,30" backgroundColor="#1a1426" zPosition="3" />
    <widget name="facebook_title" position="1408,568" size="260,34" font="Regular;24" foregroundColor="#fde047" backgroundColor="#1a1426" transparent="1" zPosition="4" halign="right" />
    <widget name="facebook_label" position="1408,608" size="270,46" text="https://www.facebook.com/share/1G8inRhUib/" font="Regular;18" foregroundColor="#38bdf8" backgroundColor="#120e1a" transparent="1" zPosition="3" halign="right" />

    <!-- PROGRESS BOX WITH MULTI-COLOR ACCENTS -->
    <eLabel position="1220,676" size="468,114" backgroundColor="#0c0714" zPosition="1" />
    <eLabel position="1220,676" size="117,2" backgroundColor="#f59e0b" zPosition="2" />
    <eLabel position="1337,676" size="117,2" backgroundColor="#0284c7" zPosition="2" />
    <eLabel position="1454,676" size="117,2" backgroundColor="#a855f7" zPosition="2" />
    <eLabel position="1571,676" size="117,2" backgroundColor="#ec4899" zPosition="2" />
    <eLabel position="1220,676" size="2,114" backgroundColor="#f59e0b" zPosition="2" />
    <eLabel position="1686,676" size="2,114" backgroundColor="#ec4899" zPosition="2" />
    <eLabel position="1220,788" size="117,2" backgroundColor="#f59e0b" zPosition="2" />
    <eLabel position="1337,788" size="117,2" backgroundColor="#0284c7" zPosition="2" />
    <eLabel position="1454,788" size="117,2" backgroundColor="#a855f7" zPosition="2" />
    <eLabel position="1571,788" size="117,2" backgroundColor="#ec4899" zPosition="2" />
    
    <widget name="progress" position="1236,686" size="436,14" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/progress.png" borderWidth="2" borderColor="#0284c7" backgroundColor="#1e1035" foregroundColor="#38bdf8" zPosition="3" />
    <widget name="percentage" position="1236,705" size="120,22" font="Regular;22" foregroundColor="#fde047" backgroundColor="#0c0714" transparent="1" zPosition="3" halign="left" />
    <widget name="speed" position="1366,705" size="306,22" font="Regular;22" foregroundColor="#38bdf8" backgroundColor="#0c0714" transparent="1" zPosition="3" halign="right" />
    <widget name="size" position="1236,730" size="436,22" font="Regular;20" foregroundColor="#fbbf24" backgroundColor="#0c0714" transparent="1" zPosition="3" halign="center" />
    <widget name="status" position="1236,754" size="436,28" font="Regular;20" foregroundColor="#f472b6" backgroundColor="#0c0714" transparent="1" zPosition="3" halign="center" />

    <!-- FOOTER BUTTONS -->
    <eLabel position="20,812" size="1684,93" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="20,812" size="1684,2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="20,812" size="4,93" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="1700,812" size="4,93" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="20,903" size="1684,2" backgroundColor="#be185d" zPosition="1" />

    <eLabel position="40,824" size="395,68" backgroundColor="#1e111d" zPosition="1" />
    <eLabel position="40,824" size="395,2" backgroundColor="#e11d48" zPosition="2" />
    <eLabel position="40,824" size="3,68" backgroundColor="#e11d48" zPosition="2" />
    <eLabel position="432,824" size="3,68" backgroundColor="#e11d48" zPosition="2" />
    <eLabel position="40,890" size="395,2" backgroundColor="#e11d48" zPosition="2" />
    <ePixmap position="56,836" size="44,44" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/key_red.png" scale="1" transparent="1" alphatest="blend" zPosition="3" />
    <widget name="key_red" position="114,824" size="311,68" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#1e111d" transparent="1" zPosition="3" halign="left" valign="center" />

    <eLabel position="451,824" size="395,68" backgroundColor="#0d1f19" zPosition="1" />
    <eLabel position="451,824" size="395,2" backgroundColor="#059669" zPosition="2" />
    <eLabel position="451,824" size="3,68" backgroundColor="#059669" zPosition="2" />
    <eLabel position="843,824" size="3,68" backgroundColor="#059669" zPosition="2" />
    <eLabel position="451,890" size="395,2" backgroundColor="#059669" zPosition="2" />
    <ePixmap position="467,836" size="44,44" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/key_green.png" scale="1" transparent="1" alphatest="blend" zPosition="3" />
    <widget name="key_green" position="525,824" size="311,68" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#0d1f19" transparent="1" zPosition="3" halign="left" valign="center" />

    <eLabel position="862,824" size="395,68" backgroundColor="#1f180c" zPosition="1" />
    <eLabel position="862,824" size="395,2" backgroundColor="#d97706" zPosition="2" />
    <eLabel position="862,824" size="3,68" backgroundColor="#d97706" zPosition="2" />
    <eLabel position="1254,824" size="3,68" backgroundColor="#d97706" zPosition="2" />
    <eLabel position="862,890" size="395,2" backgroundColor="#d97706" zPosition="2" />
    <ePixmap position="878,836" size="44,44" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/key_yellow.png" scale="1" transparent="1" alphatest="blend" zPosition="3" />
    <widget name="key_yellow" position="936,824" size="311,68" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#1f180c" transparent="1" zPosition="3" halign="left" valign="center" />

    <eLabel position="1273,824" size="395,68" backgroundColor="#0f152b" zPosition="1" />
    <eLabel position="1273,824" size="395,2" backgroundColor="#4f46e5" zPosition="2" />
    <eLabel position="1273,824" size="3,68" backgroundColor="#4f46e5" zPosition="2" />
    <eLabel position="1665,824" size="3,68" backgroundColor="#4f46e5" zPosition="2" />
    <eLabel position="1273,890" size="395,2" backgroundColor="#4f46e5" zPosition="2" />
    <ePixmap position="1289,836" size="44,44" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/key_blue.png" scale="1" transparent="1" alphatest="blend" zPosition="3" />
    <widget name="key_blue" position="1347,824" size="311,68" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#0f152b" transparent="1" zPosition="3" halign="left" valign="center" />
</screen>
"""

# Apply Auto-Scaling to Skin Layout dynamically
SKIN_LAYOUT = scale_skin_layout(RAW_SKIN_LAYOUT)

class MohamedStore(Screen):
    skin = SKIN_LAYOUT

    def __init__(self, session):
        Screen.__init__(self, session)
        
        self.categories_list_has_multicontent = False
        if HAS_MULTICONTENT and eListboxPythonMultiContent:
            try:
                try:
                    self["categories_list"] = MenuList([], content=eListboxPythonMultiContent)
                except TypeError:
                    self["categories_list"] = MenuList([])
                    self["categories_list"].l = eListboxPythonMultiContent()
                
                if gFont:
                    try:
                        self["categories_list"].l.setFont(0, gFont("Regular", scale_font(30)))
                        self["categories_list"].l.setFont(1, gFont("Regular", scale_font(22)))
                    except Exception:
                        pass
                self["categories_list"].l.setBuildFunc(self.build_category_entry)
                self.categories_list_has_multicontent = True
            except Exception:
                self["categories_list"] = MenuList([])
        else:
            self["categories_list"] = MenuList([])

        self.items_list_has_multicontent = False
        if HAS_MULTICONTENT and eListboxPythonMultiContent:
            try:
                try:
                    self["items_list"] = MenuList([], content=eListboxPythonMultiContent)
                except TypeError:
                    self["items_list"] = MenuList([])
                    self["items_list"].l = eListboxPythonMultiContent()
                
                if gFont:
                    try:
                        self["items_list"].l.setFont(0, gFont("Regular", scale_font(32)))
                    except Exception:
                        pass
                self["items_list"].l.setBuildFunc(self.build_item_entry)
                self.items_list_has_multicontent = True
            except Exception:
                self["items_list"] = MenuList([])
        else:
            self["items_list"] = MenuList([])

        self["description"] = Label("Loading...")
        
        telemetry = self.get_system_telemetry_info()
        self["sys_device"] = Label(telemetry.get("device", "Box: Enigma2"))
        self["sys_image"] = Label(telemetry.get("image", "OS: EGAMI"))
        self["sys_cpu"] = Label(telemetry.get("cpu", "CPU: Active"))
        self["sys_temp"] = Label(telemetry.get("temp", "Temp: N/A"))
        self["sys_ram"] = Label(telemetry.get("ram", "RAM: OK"))
        self["sys_flash"] = Label(telemetry.get("flash", "Flash: OK"))
        
        real_ip = get_real_box_ip()
        self["sys_ip"] = Label("IP: %s" % real_ip)
        self["sys_net"] = Label("Net: Online")
        
        self["facebook_title"] = Label(u"\u062a\u0627\u0628\u0639\u0646\u0627 \u0639\u0644\u0649 \u0641\u064a\u0633\u0628\u0648\u0643")
        self["facebook_label"] = Label("https://www.facebook.com/share/1G8inRhUib/")
        
        self["key_red"] = Label("Exit")
        self["key_green"] = Label("Install")
        self["key_yellow"] = Label("Refresh Store")
        self["key_blue"] = Label("Update Store")
        
        if ProgressBar:
            self["progress"] = ProgressBar()
        else:
            self["progress"] = Label("")
        self["percentage"] = Label("")
        self["speed"] = Label("")
        self["size"] = Label("")
        self["status"] = Label("")

        try:
            self["progress"].hide()
            self["percentage"].hide()
            self["speed"].hide()
            self["size"].hide()
            self["status"].hide()
        except Exception:
            pass

        self.download_in_progress = False
        self.download_is_update_script = False
        self.download_is_system_image = False
        self.download_is_picon = False
        self.download_url = ""
        self.download_dest_path = ""
        self.download_aborted = False
        self.download_completed = False
        self.download_error_msg = ""
        self.download_total_bytes = 0
        self.downloaded_bytes = 0
        self.download_start_time = 0
        self.download_last_update_bytes = 0
        self.download_last_update_time = 0
        self.download_current_speed = 0.0

        self.download_timer = eTimer()
        if self.download_timer:
            try:
                self.download_timer_conn = self.download_timer.timeout.connect(self.update_download_ui)
            except AttributeError:
                try:
                    self.download_timer.callback.append(self.update_download_ui)
                except Exception:
                    pass
        
        self.store_data = {}
        self.categories = []
        self.visible_items = []
        self.current_path = []
        self.active_focus = "categories"
        self.my_console = Console()
        
        self.install_cmd = ""
        self.install_item_name = ""
        
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
            "cancel": self.go_back,
            "red": self.red_key_pressed,
            "green": self.download,
            "yellow": self.load_store,
            "blue": self.manual_update,
            "ok": self.press_ok,
            "up": self.go_up,
            "down": self.go_down,
            "left": self.switch_to_categories,
            "right": self.switch_to_items,
        }, -1)
        
        self["categories_list"].onSelectionChanged.append(self.category_changed)
        self["items_list"].onSelectionChanged.append(self.item_changed)
        
        self.load_local_cache()

        self.bg_sync_timer = eTimer()
        try:
            self.bg_sync_timer_conn = self.bg_sync_timer.timeout.connect(self.start_background_sync)
        except AttributeError:
            try:
                self.bg_sync_timer.callback.append(self.start_background_sync)
            except Exception:
                pass
        self.onLayoutFinish.append(self.schedule_bg_sync)

    def load_local_cache(self):
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r") as f:
                    cached_data = json.load(f)
                    if cached_data and "categories" in cached_data:
                        self.apply_store_data(cached_data)
                        return True
        except Exception:
            pass
        return False

    def schedule_bg_sync(self):
        if self.bg_sync_timer:
            self.bg_sync_timer.start(100, True)

    def start_background_sync(self):
        t = threading.Thread(target=self.async_network_fetch)
        t.daemon = True
        t.start()

    def async_network_fetch(self):
        try:
            current_ip = get_real_box_ip()
            self["sys_ip"].setText("IP: %s" % current_ip)
        except Exception:
            pass

        try:
            data = load_json_network(STORE_URL)
            if data and "categories" in data:
                self.apply_store_data(data)
                try:
                    with open(CACHE_FILE, "w") as f:
                        json.dump(data, f)
                except Exception:
                    pass
            elif not self.categories:
                self["description"].setText("Failed to connect to GitHub feed.")
        except Exception:
            pass

    def apply_store_data(self, data):
        try:
            store_title = "%s v%s" % (data.get("store_name", "M Store"), data.get("version", "1.3.2"))
            self.setTitle(store_title)
            
            self.store_data = data["categories"]
            if isinstance(self.store_data, dict):
                self.categories = list(self.store_data.keys())
            else:
                self.categories = []
            
            if "tools" not in self.categories:
                self.categories.append("tools")
            
            if self.categories:
                display_cats = []
                for cat in self.categories:
                    cat_clean_name = str(cat).replace("_", " ").capitalize()
                    
                    if cat == "tools":
                        remote_tools = self.store_data.get("tools", [])
                        count = len(BUILTIN_SYSTEM_TOOLS) + (len(remote_tools) if isinstance(remote_tools, list) else 0)
                    else:
                        cat_content = self.store_data.get(cat, [])
                        count = count_items_recursive(cat_content)
                    
                    if self.categories_list_has_multicontent:
                        display_cats.append((cat, cat_clean_name, count))
                    else:
                        display_cats.append("%s (%d)" % (cat_clean_name, count))
                        
                self["categories_list"].setList(display_cats)
                self.current_path = []
                self.category_changed()
        except Exception:
            pass

    def get_system_telemetry_info(self):
        info = {
            "device": "Box: Enigma2",
            "image": "OS: EGAMI",
            "cpu": "CPU: Normal",
            "temp": "Temp: --",
            "ram": "RAM: --",
            "flash": "Flash: --",
            "ip": "IP: --",
            "net": "Net: Online"
        }
        try:
            device_name = "Enigma2"
            image_name = "EGAMI"
            if os.path.exists("/proc/stb/info/model"):
                with open("/proc/stb/info/model", "r") as f:
                    device_name = f.read().strip().upper()
            elif os.path.exists("/proc/stb/info/boxtype"):
                with open("/proc/stb/info/boxtype", "r") as f:
                    device_name = f.read().strip().upper()

            if os.path.exists("/etc/image-version"):
                with open("/etc/image-version", "r") as f:
                    for line in f:
                        if "imagename" in line or "creator" in line or "name" in line:
                            val = line.split("=")[-1].strip().upper()
                            if val:
                                image_name = val
                                break
                                
            info["device"] = "Box: %s" % device_name
            info["image"] = "OS: %s" % image_name
        except Exception:
            pass

        try:
            temp_val = None
            for temp_path in ("/proc/stb/sensors/temp0/value", "/proc/stb/fp/temp_sensor", "/sys/class/thermal/thermal_zone0/temp"):
                if os.path.exists(temp_path):
                    with open(temp_path, "r") as f:
                        t_str = f.read().strip()
                        if t_str.isdigit():
                            t_num = int(t_str)
                            if t_num > 1000:
                                t_num = int(t_num / 1000)
                            temp_val = t_num
                            break
            info["temp"] = ("Temp: %d C" % temp_val) if temp_val is not None else "Temp: 42 C"

            if os.path.exists("/proc/loadavg"):
                with open("/proc/loadavg", "r") as f:
                    info["cpu"] = "CPU Load: %s" % f.read().split()[0]
            else:
                info["cpu"] = "CPU: Ready"
        except Exception:
            pass

        try:
            if os.path.exists("/proc/meminfo"):
                mem_total = 0
                mem_free = 0
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            k = parts[0].strip()
                            v = parts[1].strip().split()[0]
                            if k == "MemTotal":
                                mem_total = int(v)
                            elif k in ["MemFree", "MemAvailable"]:
                                mem_free = int(v)
                if mem_total > 0:
                    pct = int((float(mem_total - mem_free) / float(mem_total)) * 100)
                    info["ram"] = "RAM: %d%% (%dM Free)" % (pct, int(mem_free / 1024))

            stat = os.statvfs('/')
            free_gb = float(stat.f_bavail * stat.f_frsize) / (1024.0 * 1024.0 * 1024.0)
            info["flash"] = "Flash: %.1f GB Free" % free_gb
        except Exception:
            pass

        return info

    def build_category_entry(self, *args):
        try:
            category_id = "unknown"
            display_name = "Unknown"
            count = 0

            if len(args) == 1:
                arg0 = args[0]
                if isinstance(arg0, (list, tuple)):
                    if len(arg0) >= 1:
                        category_id = arg0[0]
                    if len(arg0) >= 2:
                        display_name = str(arg0[1])
                    if len(arg0) >= 3:
                        try:
                            count = int(arg0[2])
                        except Exception:
                            count = 0
                else:
                    category_id = str(arg0)
                    display_name = str(arg0)
            elif len(args) >= 2:
                category_id = args[0]
                display_name = str(args[1])
                if len(args) >= 3:
                    try:
                        count = int(args[2])
                    except Exception:
                        count = 0

            icon_path = get_category_icon_path(category_id)
            pixmap = None
            if icon_path and loadPNG:
                try:
                    pixmap = loadPNG(icon_path)
                except Exception:
                    pixmap = None

            res = [category_id]
            # Scaled sizes and coordinates for MultiContent
            icon_w = scale_x(70)
            icon_h = scale_y(70)
            icon_pos_x = scale_x(8)
            icon_pos_y = scale_y(5)
            row_h = scale_y(80)

            if pixmap and HAS_MULTICONTENT and MultiContentEntryPixmapAlphaTest:
                res.append(MultiContentEntryPixmapAlphaTest(pos=(icon_pos_x, icon_pos_y), size=(icon_w, icon_h), png=pixmap))
                text_x = scale_x(86)
                text_w = scale_x(200)
            else:
                text_x = scale_x(15)
                text_w = scale_x(270)

            if HAS_MULTICONTENT and MultiContentEntryText:
                res.append(MultiContentEntryText(pos=(text_x, 0), size=(text_w, row_h), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(display_name)))
                count_str = "[%d]" % int(count)
                res.append(MultiContentEntryText(pos=(scale_x(286), 0), size=(scale_x(74), row_h), font=0, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=count_str))
                
            return res
        except Exception:
            return [str(args[0]) if args else "Category"]

    def build_item_entry(self, *args):
        try:
            item = {}
            display_text = "Unknown"
            category_id = "unknown"

            if len(args) == 1:
                arg0 = args[0]
                if isinstance(arg0, (list, tuple)):
                    if len(arg0) >= 1:
                        item = arg0[0]
                    if len(arg0) >= 2:
                        display_text = str(arg0[1])
                    if len(arg0) >= 3:
                        category_id = str(arg0[2])
                else:
                    item = {"name": str(arg0)}
                    display_text = str(arg0)
            elif len(args) >= 2:
                item = args[0]
                display_text = str(args[1])
                if len(args) >= 3:
                    category_id = str(args[2])

            icon_path = get_item_icon_path(item, category_id)
            pixmap = None
            if icon_path and loadPNG:
                try:
                    pixmap = loadPNG(icon_path)
                except Exception:
                    pixmap = None

            res = [item]
            # Scaled sizes and coordinates for Item MultiContent
            icon_w = scale_x(56)
            icon_h = scale_y(56)
            icon_pos_x = scale_x(10)
            icon_pos_y = scale_y(10)
            row_h = scale_y(76)

            if pixmap and HAS_MULTICONTENT and MultiContentEntryPixmapAlphaTest:
                res.append(MultiContentEntryPixmapAlphaTest(pos=(icon_pos_x, icon_pos_y), size=(icon_w, icon_h), png=pixmap))
                text_x = scale_x(78)
                text_w = scale_x(670)
            else:
                text_x = scale_x(15)
                text_w = scale_x(740)

            if HAS_MULTICONTENT and MultiContentEntryText:
                res.append(MultiContentEntryText(pos=(text_x, 0), size=(text_w, row_h), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=str(display_text)))
                
            return res
        except Exception:
            return [str(args[0]) if args else "Item"]

    def load_store(self):
        self["description"].setText("Refreshing feed from GitHub...")
        t = threading.Thread(target=self.async_network_fetch)
        t.daemon = True
        t.start()

    def manual_update(self):
        self.session.openWithCallback(
            self.run_install_script,
            MessageBox,
            "Do you want to update Mohamed Store using online script?",
            MessageBox.TYPE_YESNO
        )

    def run_install_script(self, answer):
        if answer:
            self.start_script_update()
        else:
            self.load_store()

    def start_script_update(self):
        self.install_cmd = "chmod +x /tmp/install.sh && /tmp/install.sh && rm -f /tmp/install.sh"
        self.install_item_name = "Mohamed Store Update Script"
        self.download_url = "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/install.sh"
        self.download_dest_path = "/tmp/install.sh"
        self.download_is_update_script = True
        self.download_is_system_image = False
        self.download_is_picon = False
        self.download_aborted = False
        self.download_completed = False
        self.download_error_msg = ""
        self.download_total_bytes = 0
        self.downloaded_bytes = 0
        self.download_start_time = time.time()
        self.download_last_update_bytes = 0
        self.download_last_update_time = self.download_start_time
        self.download_current_speed = 0.0

        self["description"].setText("Downloading update script...\nPress RED or BACK to cancel.")
        self["key_red"].setText("Cancel")

        try:
            self["progress"].show()
            self["percentage"].show()
            self["speed"].show()
            self["size"].show()
            self["status"].show()

            self["progress"].setValue(0)
            self["percentage"].setText("0%")
            self["speed"].setText("0 KB/s")
            self["size"].setText("Downloading script...")
            self["status"].setText("Updating plugin...")
        except Exception:
            pass

        self.download_in_progress = True

        if self.download_timer:
            self.download_timer.start(100, False)

        self.download_thread_obj = threading.Thread(target=self.start_download_thread)
        self.download_thread_obj.daemon = True
        self.download_thread_obj.start()

    def update_finished(self, result, retval, extra_args=None):
        try:
            self["progress"].hide()
            self["percentage"].hide()
            self["speed"].hide()
            self["size"].hide()
            self["status"].hide()
        except Exception:
            pass
        self["key_red"].setText("Exit")

        if retval == 0:
            self.session.openWithCallback(
                self.restartGUICallback,
                MessageBox,
                "Mohamed Store updated successfully via script!\n\nRestart GUI now?",
                MessageBox.TYPE_YESNO
            )
        else:
            self["description"].setText("Self-Update Failed! Exit Code: " + str(retval))

    def restartGUICallback(self, answer):
        if answer:
            try:
                if TryQuitMainloop:
                    self.session.open(TryQuitMainloop, 3)
                else:
                    enigma.quitMainloop(3)
            except Exception:
                try:
                    enigma.quitMainloop(3)
                except Exception:
                    pass
        else:
            self.load_store()

    def category_changed(self):
        try:
            if self.active_focus == "categories":
                self.current_path = []
            
            idx = self["categories_list"].getSelectionIndex()
            if idx < 0 or idx >= len(self.categories):
                return
            
            selected_cat = self.categories[idx]
            if selected_cat == "tools":
                remote_tools = self.store_data.get("tools", [])
                self.visible_items = BUILTIN_SYSTEM_TOOLS + remote_tools
            else:
                category_data = self.store_data.get(selected_cat, [])
                if len(self.current_path) == 0:
                    self.visible_items = category_data
                else:
                    self.rebuild_visible_items()
            
            self.update_items_list()
        except Exception as e:
            self["description"].setText("Category Change Error: " + str(e))

    def rebuild_visible_items(self):
        try:
            idx = self["categories_list"].getSelectionIndex()
            if idx < 0 or idx >= len(self.categories):
                self.visible_items = []
                return
            
            selected_cat = self.categories[idx]
            if selected_cat == "tools":
                items = BUILTIN_SYSTEM_TOOLS + self.store_data.get("tools", [])
            else:
                items = self.store_data.get(selected_cat, [])
                
            for folder in self.current_path:
                items = folder.get("items", [])
            self.visible_items = items
        except Exception:
            self.visible_items = []

    def update_items_list(self):
        try:
            if not isinstance(self.visible_items, list):
                self["items_list"].setList([])
                self["description"].setText("No items found in this section.")
                return
            
            cat_idx = self["categories_list"].getSelectionIndex()
            category_id = self.categories[cat_idx] if (cat_idx >= 0 and cat_idx < len(self.categories)) else "unknown"

            display_items = []
            for item in self.visible_items:
                if "items" in item and isinstance(item["items"], list):
                    folder_count = count_items_recursive(item["items"])
                    display_text = "> %s  (%d)" % (str(item.get("name", "Unknown Folder")), folder_count)
                elif item.get("type") == "tool":
                    display_text = str(item.get("name", "Unknown Tool"))
                else:
                    ver = item.get("version")
                    if ver:
                        display_text = "%s  (v%s)" % (str(item.get("name", "Unknown")), str(ver))
                    else:
                        display_text = str(item.get("name", "Unknown"))

                if self.items_list_has_multicontent:
                    display_items.append((item, display_text, category_id))
                else:
                    display_items.append(display_text)
            
            self["items_list"].setList(display_items)
            self.item_changed()
        except Exception as e:
            self["description"].setText("Update Items List Error: " + str(e))

    def item_changed(self):
        try:
            idx = self["items_list"].getSelectionIndex()
            if idx < 0 or not self.visible_items or idx >= len(self.visible_items):
                return
            
            item = self.visible_items[idx]
            cat_idx = self["categories_list"].getSelectionIndex()
            cat_id = str(self.categories[cat_idx]).lower() if cat_idx >= 0 else ""
            cat_name = str(self.categories[cat_idx]).replace("_", " ").capitalize() if cat_idx >= 0 else "Unknown"
            
            path_parts = [cat_name]
            for folder in self.current_path:
                path_parts.append(str(folder.get("name", "")))
            path_str = " > ".join(path_parts)
            
            is_sys_img = ("image" in cat_id or "system" in cat_id or "neoboot" in cat_id or item.get("type") in ["image", "system_image", "system"])
            is_picon = ("picon" in cat_id or item.get("type") in ["picon", "picons"])
            
            if item.get("type") == "tool":
                self["key_green"].setText("Execute")
                info_text = "Section: %s\nTool Name: %s\n\nDescription:\n%s" % (
                    path_str,
                    str(item.get("name", "")),
                    str(item.get("description", "System tool execution."))
                )
            elif "items" in item and isinstance(item["items"], list):
                self["key_green"].setText("Install")
                sub_count = count_items_recursive(item["items"])
                info_text = "Section: %s\nFolder: %s (Packages: %d)\n\nPress OK to view packages inside this folder." % (
                    path_str,
                    str(item.get("name", "")),
                    sub_count
                )
            elif is_sys_img:
                self["key_green"].setText("Download")
                info_text = "Section: %s (NeoBoot Safe)\nImage: %s\nVersion: %s\n\nDescription:\n%s\n\n* Note: Downloaded directly as ZIP into NeoBoot ImagesUpload." % (
                    path_str,
                    str(item.get("name", "")),
                    str(item.get("version", "-")),
                    str(item.get("description", "Enigma2 System Image for NeoBoot."))
                )
            elif is_picon:
                self["key_green"].setText("Download")
                info_text = "Section: %s (Direct HDD ZIP)\nName: %s\nVersion: %s\n\nDescription:\n%s\n\n* Note: Downloaded directly into /media/hdd/." % (
                    path_str,
                    str(item.get("name", "")),
                    str(item.get("version", "-")),
                    str(item.get("description", "Channel Picons Package."))
                )
            else:
                self["key_green"].setText("Install")
                info_text = "Section: %s\nName: %s\nVersion: %s\n\nDescription:\n%s" % (
                    path_str,
                    str(item.get("name", "")),
                    str(item.get("version", "-")),
                    str(item.get("description", "No description available."))
                )
            self["description"].setText(info_text)
        except Exception as e:
            self["description"].setText("Item Change Error: " + str(e))

    def red_key_pressed(self):
        if self.download_in_progress:
            self.cancel_active_download()
        else:
            self.close()

    def switch_to_items(self):
        if self.download_in_progress:
            return
        if self.visible_items:
            self.active_focus = "items"
            self["description"].setText("Navigating: Items List\n\nPress OK or Green to Install / Execute.")

    def switch_to_categories(self):
        if self.download_in_progress:
            return
        if self.active_focus == "items" and len(self.current_path) > 0:
            self.current_path.pop()
            self.rebuild_visible_items()
            self.update_items_list()
        else:
            self.active_focus = "categories"
            self.current_path = []
            self.category_changed()

    def go_up(self):
        if self.download_in_progress:
            return
        try:
            if self.active_focus == "categories":
                self["categories_list"].up()
            else:
                self["items_list"].up()
        except Exception:
            pass

    def go_down(self):
        if self.download_in_progress:
            return
        try:
            if self.active_focus == "categories":
                self["categories_list"].down()
            else:
                self["items_list"].down()
        except Exception:
            pass

    def press_ok(self):
        if self.download_in_progress:
            return
        if self.active_focus == "categories":
            self.switch_to_items()
        else:
            idx = self["items_list"].getSelectionIndex()
            if idx >= 0 and idx < len(self.visible_items):
                item = self.visible_items[idx]
                if "items" in item and isinstance(item["items"], list):
                    self.current_path.append(item)
                    self.rebuild_visible_items()
                    self.update_items_list()
                else:
                    self.download()

    def go_back(self):
        if self.download_in_progress:
            self.cancel_active_download()
            return
        if self.active_focus == "items" and len(self.current_path) > 0:
            self.current_path.pop()
            self.rebuild_visible_items()
            self.update_items_list()
        elif self.active_focus == "items" and len(self.current_path) == 0:
            self.switch_to_categories()
        else:
            self.close()

    def download(self):
        if self.download_in_progress:
            return
        try:
            idx = self["items_list"].getSelectionIndex()
            if idx >= 0 and idx < len(self.visible_items) and self.visible_items:
                item = self.visible_items[idx]
                
                if item.get("type") == "tool":
                    action = item.get("action", "")
                    if action == "check_oscam_status":
                        success, msg = get_active_oscam_status()
                        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
                        self.item_changed()
                        return

                    elif action == "tiger_server":
                        self["description"].setText("Activating Free 24h Server...\nDisabling Paid Server...\nPlease wait...")
                        def _run_tiger():
                            success, msg = generate_tigerhd_server()
                            def _show_res():
                                if success:
                                    self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
                                else:
                                    self.session.open(MessageBox, "Failed to activate server:\n" + msg, MessageBox.TYPE_ERROR)
                                self.item_changed()
                            if sys.version_info >= (3, 0):
                                try:
                                    from twisted.internet import reactor
                                    reactor.callFromThread(_show_res)
                                except Exception:
                                    _show_res()
                            else:
                                _show_res()
                        
                        t = threading.Thread(target=_run_tiger)
                        t.daemon = True
                        t.start()
                        return

                    elif action == "restore_paid":
                        success, msg = restore_paid_oscam()
                        if success:
                            self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
                        else:
                            self.session.open(MessageBox, msg, MessageBox.TYPE_WARNING)
                        self.item_changed()
                        return

                    elif action == "restart_oscam":
                        success, msg = restart_oscam_service()
                        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
                        self.item_changed()
                        return

                    elif action == "stop_oscam":
                        success, msg = stop_oscam_service()
                        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
                        self.item_changed()
                        return

                    cmd = item.get("cmd", "")
                    if cmd == "restart_gui":
                        if TryQuitMainloop:
                            self.session.open(TryQuitMainloop, 3)
                        else:
                            enigma.quitMainloop(3)
                    elif cmd:
                        self["description"].setText("Executing tool: %s\nPlease wait..." % item.get("name", ""))
                        self.my_console.ePopen(cmd + " 2>&1", self.tool_execution_finished)
                    return

                if "items" in item and isinstance(item["items"], list):
                    self.current_path.append(item)
                    self.rebuild_visible_items()
                    self.update_items_list()
                    return
                
                url = item.get("file", "").strip()
                if not url:
                    self["description"].setText("Error: Download URL is missing in JSON.")
                    return
                
                pure_url = url.split('?')[0]
                ext = ""
                if pure_url.endswith(".tar.gz"):
                    ext = ".tar.gz"
                else:
                    _, ext_part = os.path.splitext(pure_url)
                    ext = ext_part.lower()

                filename = pure_url.split('/')[-1]
                if not filename:
                    filename = "addon" + ext

                cat_idx = self["categories_list"].getSelectionIndex()
                cat_id = str(self.categories[cat_idx]).lower() if cat_idx >= 0 else ""
                item_type = str(item.get("type", "")).lower()
                
                is_system_image = ("system" in cat_id or "image" in cat_id or "neoboot" in cat_id or item_type in ["image", "system", "system_image"])
                is_picon = ("picon" in cat_id or item_type in ["picon", "picons"])

                dest_path = ""
                cmd = ""

                if is_system_image:
                    target_dir = get_neoboot_images_upload_path()
                    safe_filename = filename if filename.lower().endswith(".zip") else (filename + ".zip")
                    dest_path = os.path.join(target_dir, safe_filename)
                    cmd = "sync"
                    self.download_is_system_image = True
                    self.download_is_picon = False

                elif is_picon:
                    target_dir = get_direct_hdd_root_path()
                    safe_filename = filename if filename.lower().endswith(".zip") else (filename + ".zip")
                    dest_path = os.path.join(target_dir, safe_filename)
                    cmd = "sync"
                    self.download_is_system_image = False
                    self.download_is_picon = True

                else:
                    self.download_is_system_image = False
                    self.download_is_picon = False
                    if ext == ".deb":
                        dest_path = "/tmp/addon.deb"
                        cmd = "dpkg -i /tmp/addon.deb && rm -f /tmp/addon.deb"
                    elif ext == ".ipk":
                        dest_path = "/tmp/addon.ipk"
                        cmd = "opkg install --force-overwrite /tmp/addon.ipk && rm -f /tmp/addon.ipk"
                    elif ext == ".sh":
                        dest_path = "/tmp/addon.sh"
                        cmd = "chmod +x /tmp/addon.sh && /tmp/addon.sh && rm -f /tmp/addon.sh"
                    elif ext == ".zip":
                        dest_path = "/tmp/addon.zip"
                        cmd = "unzip -o /tmp/addon.zip -d / && rm -f /tmp/addon.zip"
                    elif ext in [".tar.gz", ".tgz"]:
                        dest_path = "/tmp/addon.tar.gz"
                        cmd = "tar -xzf /tmp/addon.tar.gz -C / && rm -f /tmp/addon.tar.gz"
                    elif ext == ".tar":
                        dest_path = "/tmp/addon.tar"
                        cmd = "tar -xf /tmp/addon.tar -C / && rm -f /tmp/addon.tar"
                    elif ext == ".tv":
                        dest_path = os.path.join("/etc/enigma2", filename)
                        cmd = (
                            "if ! grep -q '" + filename + "' /etc/enigma2/bouquets.tv; then "
                            "echo '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"" + filename + "\" ORDER BY bouquet' >> /etc/enigma2/bouquets.tv; "
                            "fi && "
                            "(wget -qO - http://127.0.0.1/web/servicelistreload?mode=0 || "
                            "curl -s http://127.0.0.1/web/servicelistreload?mode=0 || true)"
                        )
                    elif ext == ".py":
                        dest_path = "/tmp/addon.py"
                        cmd = "(python /tmp/addon.py || python3 /tmp/addon.py) && rm -f /tmp/addon.py"
                    else:
                        dest_path = "/tmp/addon.ipk"
                        cmd = "opkg install --force-overwrite /tmp/addon.ipk && rm -f /tmp/addon.ipk"

                self.install_cmd = cmd
                self.install_item_name = str(item.get("name", ""))
                self.download_url = url
                self.download_dest_path = dest_path
                self.download_is_update_script = False
                self.download_aborted = False
                self.download_completed = False
                self.download_error_msg = ""
                self.download_total_bytes = 0
                self.downloaded_bytes = 0
                self.download_start_time = time.time()
                self.download_last_update_bytes = 0
                self.download_last_update_time = self.download_start_time
                self.download_current_speed = 0.0
                
                self["description"].setText("Downloading: %s\n\nPress RED or BACK to cancel." % self.install_item_name)
                self["key_red"].setText("Cancel")
                
                try:
                    self["progress"].show()
                    self["percentage"].show()
                    self["speed"].show()
                    self["size"].show()
                    self["status"].show()
                    
                    self["progress"].setValue(0)
                    self["percentage"].setText("0%")
                    self["speed"].setText("0 KB/s")
                    self["size"].setText("0 MB / 0 MB")
                    self["status"].setText(os.path.basename(dest_path))
                except Exception:
                    pass
                
                self.download_in_progress = True
                if self.download_timer:
                    self.download_timer.start(100, False)
                    
                self.download_thread_obj = threading.Thread(target=self.start_download_thread)
                self.download_thread_obj.daemon = True
                self.download_thread_obj.start()
                
        except Exception:
            self["description"].setText("Execution error, check system log.")

    def tool_execution_finished(self, result, retval, extra_args=None):
        if retval == 0:
            self.session.open(MessageBox, "Tool executed successfully!", MessageBox.TYPE_INFO)
        else:
            self.session.open(MessageBox, "Tool execution failed!", MessageBox.TYPE_ERROR)
        self.item_changed()

    def start_download_thread(self):
        try:
            if sys.version_info >= (3, 0):
                import urllib.request as urllib2
                import ssl
                context = ssl._create_unverified_context()
            else:
                import urllib2
                import ssl
                try:
                    context = ssl._create_unverified_context()
                except AttributeError:
                    context = None
                    
            url = self.download_url
            try:
                if sys.version_info >= (3, 0):
                    from urllib.parse import quote as urllib_quote
                    url = str(url)
                else:
                    from urllib import quote as urllib_quote
                    if isinstance(url, unicode):
                        url = url.encode('utf-8')
                url = urllib_quote(url, safe='/:?=&%')
            except Exception:
                url = url.replace(" ", "%20")
                
            req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            opener = urllib2.build_opener(urllib2.HTTPSHandler(context=context)) if context else urllib2.build_opener()
            response = opener.open(req, timeout=12)
                
            try:
                self.download_total_bytes = int(response.info().get('Content-Length', 0))
            except Exception:
                self.download_total_bytes = 0
                
            dir_name = os.path.dirname(self.download_dest_path)
            if dir_name and not os.path.exists(dir_name):
                try:
                    os.makedirs(dir_name)
                except Exception:
                    pass
                
            self.download_start_time = time.time()
            self.download_last_update_time = self.download_start_time
            self.download_last_update_bytes = 0
            
            with open(self.download_dest_path, 'wb') as f:
                while not self.download_aborted:
                    chunk = response.read(16384)
                    if not chunk:
                        break
                    f.write(chunk)
                    self.downloaded_bytes += len(chunk)
                    
            if self.download_aborted:
                if os.path.exists(self.download_dest_path):
                    try:
                        os.remove(self.download_dest_path)
                    except Exception:
                        pass
            else:
                self.download_completed = True
        except Exception as e:
            self.download_error_msg = str(e)
            if os.path.exists(self.download_dest_path):
                try:
                    os.remove(self.download_dest_path)
                except Exception:
                    pass

    def update_download_ui(self):
        if not self.download_in_progress:
            return
            
        now = time.time()
        elapsed = now - self.download_last_update_time
        if elapsed >= 0.5:
            diff_bytes = self.downloaded_bytes - self.download_last_update_bytes
            self.download_current_speed = float(diff_bytes) / elapsed
            self.download_last_update_bytes = self.downloaded_bytes
            self.download_last_update_time = now
            
        if self.download_total_bytes > 0:
            pct = int(float(self.downloaded_bytes) / self.download_total_bytes * 100)
            pct = min(100, max(0, pct))
            if ProgressBar:
                try:
                    self["progress"].setValue(pct)
                except Exception:
                    pass
            self["percentage"].setText("%d%%" % pct)
            
            dl_mb = float(self.downloaded_bytes) / (1024 * 1024)
            tot_mb = float(self.download_total_bytes) / (1024 * 1024)
            self["size"].setText("%.2f MB / %.2f MB" % (dl_mb, tot_mb))
        else:
            if ProgressBar:
                try:
                    self["progress"].setValue(0)
                except Exception:
                    pass
            self["percentage"].setText("---")
            dl_kb = float(self.downloaded_bytes) / 1024
            self["size"].setText("%.1f KB / Unknown" % dl_kb)
            
        if self.download_current_speed > 1024 * 1024:
            speed_str = "%.2f MB/s" % (self.download_current_speed / (1024 * 1024))
        else:
            speed_str = "%.1f KB/s" % (self.download_current_speed / 1024)
        self["speed"].setText(speed_str)
        
        if self.download_completed:
            self.download_in_progress = False
            if self.download_timer:
                self.download_timer.stop()
            
            if self.download_is_update_script:
                self.download_is_update_script = False
                self["description"].setText("Executing Mohamed Store Update Script...\nPlease wait...")
                try:
                    self["progress"].setValue(100)
                    self["percentage"].setText("100%")
                    self["status"].setText("Executing install.sh...")
                except Exception:
                    pass
                self.my_console.ePopen(self.install_cmd + " 2>&1", self.update_finished)

            elif self.download_is_system_image:
                self.download_is_system_image = False
                try:
                    self["progress"].hide()
                    self["percentage"].hide()
                    self["speed"].hide()
                    self["size"].hide()
                    self["status"].hide()
                except Exception:
                    pass
                    
                self["key_red"].setText("Exit")
                file_size_mb = float(self.downloaded_bytes) / (1024.0 * 1024.0)
                success_msg = u"Image downloaded successfully as a ZIP file!\n\nSize: %.1f MB\nPath: %s\n\nYou can now open NeoBoot and install it." % (file_size_mb, str(self.download_dest_path))
                self["description"].setText(success_msg)
                self.session.open(MessageBox, success_msg, MessageBox.TYPE_INFO)
                self.item_changed()

            elif self.download_is_picon:
                self.download_is_picon = False
                try:
                    self["progress"].hide()
                    self["percentage"].hide()
                    self["speed"].hide()
                    self["size"].hide()
                    self["status"].hide()
                except Exception:
                    pass
                    
                self["key_red"].setText("Exit")
                file_size_mb = float(self.downloaded_bytes) / (1024.0 * 1024.0)
                success_msg = u"Picons ZIP package downloaded directly to HDD!\n\nSize: %.1f MB\nPath: %s" % (file_size_mb, str(self.download_dest_path))
                self["description"].setText(success_msg)
                self.session.open(MessageBox, success_msg, MessageBox.TYPE_INFO)
                self.item_changed()

            else:
                try:
                    self["progress"].hide()
                    self["percentage"].hide()
                    self["speed"].hide()
                    self["size"].hide()
                    self["status"].hide()
                except Exception:
                    pass
                    
                self["key_red"].setText("Exit")
                self["description"].setText("Download completed successfully!")
                
                self.session.openWithCallback(
                    self.install_confirmation_callback,
                    MessageBox,
                    "Download completed successfully.\n\nDo you want to install it now?",
                    MessageBox.TYPE_YESNO
                )
            
        elif self.download_error_msg:
            self.download_in_progress = False
            if self.download_timer:
                self.download_timer.stop()
                
            try:
                self["progress"].hide()
                self["percentage"].hide()
                self["speed"].hide()
                self["size"].hide()
                self["status"].hide()
            except Exception:
                pass
                
            self["key_red"].setText("Exit")
            self["description"].setText("Download failed: " + self.download_error_msg)

    def cancel_active_download(self):
        self.download_aborted = True
        self.download_in_progress = False
        if self.download_timer:
            self.download_timer.stop()
        
        try:
            self["progress"].hide()
            self["percentage"].hide()
            self["speed"].hide()
            self["size"].hide()
            self["status"].hide()
        except Exception:
            pass
            
        self["key_red"].setText("Exit")
        self["description"].setText("Download cancelled by user.")
        
        if self.download_dest_path and os.path.exists(self.download_dest_path):
            try:
                os.remove(self.download_dest_path)
            except Exception:
                pass

    def install_confirmation_callback(self, answer):
        if answer:
            self["description"].setText("Installing %s...\nPlease wait..." % self.install_item_name)
            self.my_console.ePopen(self.install_cmd + " 2>&1", self.download_finished)
        else:
            self["description"].setText("Installation skipped.")
            self.item_changed()

    def download_finished(self, result, retval, extra_args=None):
        if retval == 0:
            self.session.openWithCallback(self.restartCallback, MessageBox, "Installation completed successfully!\n\nRestart GUI now?", MessageBox.TYPE_YESNO)
        else:
            error = result.strip() if result else "Unknown error"
            self["description"].setText("Installation Failed!\n\nExit Code: " + str(retval) + "\n\n" + str(error))

    def restartCallback(self, answer):
        if answer:
            try:
                if TryQuitMainloop:
                    self.session.open(TryQuitMainloop, 3)
                else:
                    enigma.quitMainloop(3)
            except Exception:
                try:
                    enigma.quitMainloop(3)
                except Exception:
                    pass
        else:
            self["description"].setText("Installation completed successfully. Restart skipped.")

def main(session, **kwargs):
    session.open(MohamedStore)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="Mohamed Store",
            description="Download and install addons, plugins, and softcams",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main
        )
    ]
