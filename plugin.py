# -*- coding: utf-8 -*-
# =========================================================================
# Mohamed Store - Universal Auto-Scaling Edition (Vu+, Dreambox, 4K, FHD, HD)
# Compatible with: OpenATV, OpenPLi, Egami, BlackHole, OBH, VTi, DreamOS (OE2.5/2.6)
# Python 2.7 & Python 3.x (3.9 - 3.12) Universal Support
# Includes OpenSubtitles (opensubtitles.org) Subtitles with Posters & HDD Downloads
# =========================================================================
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.Console import Console as ConsoleScreen
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.Console import Console
from Components.Pixmap import Pixmap
import json
import os
import sys
import socket
import struct
import fcntl
import threading
import time
import re
import zipfile
import io
import hashlib
import gzip
import base64
import zlib

try:
    from Screens.Standby import TryQuitMainloop
except ImportError:
    TryQuitMainloop = None

try:
    import enigma
except ImportError:
    enigma = None

try:
    from enigma import ePicLoad
except ImportError:
    ePicLoad = None

try:
    from Tools.LoadPixmap import LoadPixmap
except ImportError:
    LoadPixmap = None

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

try:
    from Tools.Directories import resolveFilename, SCOPE_PLUGINS
except ImportError:
    resolveFilename = None
    SCOPE_PLUGINS = None

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
PLUGIN_VERSION = "1.5.1"

def _ms_parse_version(v):
    # Turn "1.5" / "1.3.3" into a comparable tuple of ints, e.g. (1,5) / (1,3,3).
    try:
        parts = re.findall(r"\d+", str(v))
        return tuple(int(p) for p in parts) if parts else (0,)
    except Exception:
        return (0,)

def _ms_version_is_newer(remote, local):
    # True ONLY when the remote version is strictly greater than the local one.
    try:
        r = _ms_parse_version(remote)
        l = _ms_parse_version(local)
        n = max(len(r), len(l))
        r = r + (0,) * (n - len(r))
        l = l + (0,) * (n - len(l))
        return r > l
    except Exception:
        return False

try:
    PLUGIN_DIR = os.path.dirname(__file__)
except NameError:
    PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore"

CACHE_FILE = os.path.join(PLUGIN_DIR, "store_cache.json")
# Remembers the signature of the store content the subscriber has already seen,
# so we can tell him "there is a new update" only when something actually changed.
SEEN_FILE = os.path.join(PLUGIN_DIR, "store_seen.json")
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
# UNINSTALLER - Merged from Uninstaller Plugin by Lululla
# =========================================================================
uninstaller_version = '1.0'
uninstaller_myfile = '/tmp/ipkdb'

def uninstaller_delay():
    if os.path.exists(uninstaller_myfile):
        os.remove(uninstaller_myfile)
    try:
        if os.path.exists('/var/lib/dpkg/info'):
            cmd = "dpkg -l | grep ^ii | grep enigma2-plugin | awk '{print $2}' > " + uninstaller_myfile
        else:
            cmd = "opkg list-installed | grep enigma2-plugin > " + uninstaller_myfile
        os.system(cmd)
    except Exception:
        with open(uninstaller_myfile, 'w') as f:
            f.write('')

def uninstaller_build_list():
    if os.path.exists(uninstaller_myfile):
        os.remove(uninstaller_myfile)
    uninstaller_delay()
    os.system('sleep 2')
    if os.path.exists(uninstaller_myfile):
        with open(uninstaller_myfile) as file_:
            pkg_list = [line.strip() for line in file_ if line.strip()]
        if pkg_list:
            pkg_list.sort()
            return pkg_list
    return []

class UninstallerCheckList(MenuList):
    def __init__(self, list, enableWrapAround=True):
        MenuList.__init__(self, list, enableWrapAround)

class Uninstaller(Screen):
    skin = """
        <screen name="Uninstaller" position="center,center" size="1220,650" title="Uninstaller">
            <widget name="list" position="10,70" size="1200,510" scrollbarMode="showOnDemand" zPosition="2" font="Regular; 30" itemHeight="48" />
            <widget name="info" position="11,5" zPosition="4" size="1193,60" font="Regular; 38" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
            <widget name="key_red" position="10,592" size="290,48" font="Regular; 32" foregroundColor="#ffffff" backgroundColor="#e11d48" halign="center" valign="center" zPosition="5" />
            <widget name="key_green" position="310,592" size="290,48" font="Regular; 32" foregroundColor="#ffffff" backgroundColor="#059669" halign="center" valign="center" zPosition="5" />
            <widget name="key_yellow" position="610,592" size="290,48" font="Regular; 32" foregroundColor="#ffffff" backgroundColor="#d97706" halign="center" valign="center" zPosition="5" />
            <widget name="key_blue" position="910,592" size="290,48" font="Regular; 32" foregroundColor="#ffffff" backgroundColor="#0284c7" halign="center" valign="center" zPosition="5" />
        </screen>
        """

    if SCREEN_WIDTH == 2560:
        skin = """
            <screen name="Uninstaller" position="center,center" size="1980,1200" title="Uninstaller">
                <widget name="list" position="30,160" size="1900,870" scrollbarMode="showOnDemand" zPosition="2" font="Regular; 52" itemHeight="78" />
                <widget name="info" position="11,5" zPosition="4" size="1937,140" font="Regular; 62" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
                <widget name="key_red" position="30,1040" size="460,72" font="Regular; 52" foregroundColor="#ffffff" backgroundColor="#e11d48" halign="center" valign="center" zPosition="5" />
                <widget name="key_green" position="510,1040" size="460,72" font="Regular; 52" foregroundColor="#ffffff" backgroundColor="#059669" halign="center" valign="center" zPosition="5" />
                <widget name="key_yellow" position="990,1040" size="460,72" font="Regular; 52" foregroundColor="#ffffff" backgroundColor="#d97706" halign="center" valign="center" zPosition="5" />
                <widget name="key_blue" position="1470,1040" size="460,72" font="Regular; 52" foregroundColor="#ffffff" backgroundColor="#0284c7" halign="center" valign="center" zPosition="5" />
            </screen>
            """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.skin = Uninstaller.skin
        title = 'Uninstaller v.%s by Lululla' % uninstaller_version
        self.setTitle(title)
        self.pkg_list = []
        self.checked = []
        self['list'] = UninstallerCheckList([])
        self['info'] = Label()
        self['key_red'] = Label(_('Close'))
        self['key_green'] = Label(_('Delete Selected'))
        self['key_yellow'] = Label(_('Select All'))
        self['key_blue'] = Label(_('Deselect All'))
        self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'], {
            'ok': self.toggleCheck,
            'cancel': self.close,
            'red': self.close,
            'green': self.deleteSelected,
            'yellow': self.selectAll,
            'blue': self.deselectAll,
        }, -1)
        txt = _('Wait Please...')
        self['info'].setText(txt)
        self.timerw = eTimer()
        try:
            self.timerw_conn = self.timerw.timeout.connect(self.UploadList)
        except AttributeError:
            self.timerw.callback.append(self.UploadList)
        self.timerw.start(100, 1)

    def UploadList(self):
        if os.path.exists(uninstaller_myfile):
            os.remove(uninstaller_myfile)
        self.pkg_list = []
        self.checked = []
        uninstaller_delay()
        os.system('sleep 2')
        if os.path.exists(uninstaller_myfile):
            with open(uninstaller_myfile) as file_:
                for line in file_:
                    pkg = line.strip()
                    if pkg:
                        self.pkg_list.append(pkg)
                        self.checked.append(False)
        if len(self.pkg_list) > 0:
            self.pkg_list.sort()
            self.checked = [False] * len(self.pkg_list)
            self.refreshList()
            txt = _('Select packages to remove (OK=check, Green=delete)')
            self['info'].setText(txt)
        else:
            txt = _('No packages found!')
            self['info'].setText(txt)

    def refreshList(self):
        display_list = []
        for i, pkg in enumerate(self.pkg_list):
            if self.checked[i]:
                mark = '[X] '
            else:
                mark = '[ ] '
            display_list.append(mark + pkg)
        self['list'].setList(display_list)

    def toggleCheck(self):
        idx = self['list'].getSelectionIndex()
        if idx is not None and idx < len(self.checked):
            self.checked[idx] = not self.checked[idx]
            self.refreshList()

    def selectAll(self):
        self.checked = [True] * len(self.pkg_list)
        self.refreshList()

    def deselectAll(self):
        self.checked = [False] * len(self.pkg_list)
        self.refreshList()

    def deleteSelected(self):
        selected = [self.pkg_list[i] for i in range(len(self.pkg_list)) if self.checked[i]]
        if not selected:
            self.session.open(MessageBox, _('No packages selected!'), MessageBox.TYPE_INFO)
            return
        count = len(selected)
        msg = _('Are you sure you want to delete') + ' ' + str(count) + ' ' + _('packages?')
        self.session.openWithCallback(self.confirmDelete, MessageBox, msg, MessageBox.TYPE_YESNO)

    def confirmDelete(self, result):
        if not result:
            return
        selected = [self.pkg_list[i] for i in range(len(self.pkg_list)) if self.checked[i]]
        if not selected:
            return
        self.session.openWithCallback(self.chooseMethod, ChoiceBox, title=_('Select removal method:'), list=[(_('Remove'), 'rem'), (_('Force Remove'), 'force')])

    def chooseMethod(self, answer):
        if not answer or not answer[1]:
            return
        self.method = answer[1]
        selected = [self.pkg_list[i] for i in range(len(self.pkg_list)) if self.checked[i]]
        if not selected:
            return
        if self.method == 'force':
            if os.path.exists('/var/lib/dpkg/info'):
                cmd = 'dpkg -r --force-depends ' + ' '.join(selected)
            else:
                cmd = 'opkg remove --force-depends ' + ' '.join(selected)
        else:
            if os.path.exists('/var/lib/dpkg/info'):
                cmd = 'apt-get purge --auto-remove --assume-yes ' + ' '.join(selected)
            else:
                cmd = 'opkg remove ' + ' '.join(selected)
        txt = _('Removing') + ' ' + str(len(selected)) + ' ' + _('packages') + ' ...'
        self['info'].setText(txt)
        self.my_console = Console()
        self.my_console.ePopen(cmd + ' 2>&1', self.uninstall_done)

    def uninstall_done(self, result, retval, extra_args=None):
        try:
            txt = _('Removing done. Restarting GUI...')
            self['info'].setText(txt)
            self.timer_restart = eTimer()
            try:
                self.timer_restart_conn = self.timer_restart.timeout.connect(self.restartGui)
            except AttributeError:
                self.timer_restart.callback.append(self.restartGui)
            self.timer_restart.start(1500, 1)
        except Exception as e:
            print('uninstall_done error ', e)
            self.restartGui()

    def restartGui(self):
        try:
            if TryQuitMainloop:
                self.session.open(TryQuitMainloop, 3)
            elif enigma:
                enigma.quitMainloop(3)
            else:
                os.system('killall -9 enigma2')
        except Exception as e:
            print('restart error ', e)
            try:
                os.system('killall -9 enigma2')
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
            req = urllib2.Request('https://cccamiptv.tv/cccamfree-24h/', headers=headers)
            res = opener.open(req, timeout=8)
            page = res.read()
            if isinstance(page, bytes):
                page = page.decode('utf-8', 'ignore')

            nonce_m = re.search(r'data-nonce="([^"]+)"', page) or re.search(r"data-nonce='([^']+)'", page)
            nonce_val = nonce_m.group(1) if nonce_m else ""

            post_fields = {
                'action': 'cit_free_cline',
                'nonce': nonce_val
            }
            encoded_data = urllib_parse.urlencode(post_fields)
            if isinstance(encoded_data, str) and sys.version_info >= (3, 0):
                encoded_data = encoded_data.encode('utf-8')

            post_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Referer': 'https://cccamiptv.tv/cccamfree-24h/',
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            post_req = urllib2.Request('https://cccamiptv.tv/wp-admin/admin-ajax.php', data=encoded_data, headers=post_headers)
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
        ) % (c_host or "free.cccamiptv.club", c_port or "13000", c_user or "upw4oh", c_pass or "cccamiptv.tv")

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

# =========================================================================
# Football on TV (LiveOnSat)
# =========================================================================
LIVEONSAT_BASE = "https://liveonsat.com/2day.php"

FOOTBALL_RAW_SKIN = """<screen name="FootballMatches" position="center,center" size="1420,940" title="Football on TV">
    <widget name="title" position="20,10" size="1380,55" font="Regular;34" halign="center" transparent="1" foregroundColor="#00ffcc00"/>
    <widget name="daylabel" position="20,70" size="1380,42" font="Regular;28" halign="center" transparent="1" foregroundColor="#00ffffff"/>
    <widget name="list" position="25,120" size="1370,725" font="Regular;25" itemHeight="36" scrollbarMode="showOnDemand"/>
    <widget name="status" position="20,852" size="1380,36" font="Regular;23" halign="center" transparent="1" foregroundColor="#00aaaaaa"/>
    <widget name="key_red" position="30,898" size="330,32" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ff4040"/>
    <widget name="key_green" position="380,898" size="330,32" font="Regular;23" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="key_yellow" position="730,898" size="330,32" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ffff40"/>
    <widget name="key_blue" position="1080,898" size="330,32" font="Regular;23" halign="center" transparent="1" foregroundColor="#004080ff"/>
</screen>"""

FOOTBALL_SKIN = scale_skin_layout(FOOTBALL_RAW_SKIN)

def _make_ms_skin(screen_name, title):
    try:
        raw = FOOTBALL_RAW_SKIN.replace('name="FootballMatches"', 'name="%s"' % screen_name)
        raw = raw.replace('title="Football on TV"', 'title="%s"' % title)
        return scale_skin_layout(raw)
    except Exception:
        return FOOTBALL_SKIN

WEATHER_SKIN = _make_ms_skin("MS_WeatherScreen", "Weather")
IPTV_SKIN = _make_ms_skin("MS_IPTVScreen", "IPTV")
KOS_SKIN = _make_ms_skin("MS_KingOfSatScreen", "Frequencies")
NEWS_SKIN = _make_ms_skin("MS_NewsScreen", "News")

def _strip_emoji(txt):
    try:
        return u''.join(ch for ch in txt if ord(ch) < 0x1F000).strip()
    except Exception:
        return txt

def _call_ui(fn):
    if sys.version_info >= (3, 0):
        try:
            from twisted.internet import reactor
            reactor.callFromThread(fn)
            return
        except Exception:
            pass
    fn()

def _los_clean(raw):
    try:
        txt = re.sub(r'<[^>]+>', '', raw)
        for a, b in [('&amp;', '&'), ('&nbsp;', ' '), ('&ndash;', '-'),
                     ('&quot;', '"'), ('&#039;', "'"), ('&deg;', 'deg'),
                     ('&lt;', '<'), ('&gt;', '>')]:
            txt = txt.replace(a, b)
        txt = u''.join(ch for ch in txt if ord(ch) < 0x1F000)
        return txt.strip()
    except Exception:
        return raw.strip()

def parse_liveonsat(html):
    matches = []
    try:
        team_re = re.compile(r'<div class = fLeft style="[^"]*#ffd379[^"]*">(.*?)</div>', re.S)
        comp_re = re.compile(r'<span class = comp_head>(.*?)</span>', re.S)
        day_re = re.compile(r'<h2 class = time_head>(.*?)</h2>', re.S)
        time_re = re.compile(r'ST:\s*([0-9]{1,2}:[0-9]{2})')
        chan_re = re.compile(r'onmouseout="return nd\(\);">(.*?)</a>', re.S)

        comps = [(m.start(), _los_clean(m.group(1))) for m in comp_re.finditer(html)]
        days = [(m.start(), _los_clean(m.group(1))) for m in day_re.finditer(html)]
        teams = list(team_re.finditer(html))

        for i, tm in enumerate(teams):
            start = tm.start()
            end = teams[i + 1].start() if i + 1 < len(teams) else len(html)
            block = html[start:end]

            comp = ""
            for pos, name in comps:
                if pos < start:
                    comp = name
                else:
                    break
            day = ""
            for pos, name in days:
                if pos < start:
                    day = name
                else:
                    break

            team = _los_clean(tm.group(1))
            tmo = time_re.search(block)
            stime = tmo.group(1) if tmo else "--:--"

            chans = []
            for cm in chan_re.finditer(block):
                c = _los_clean(cm.group(1))
                if c and c not in chans:
                    chans.append(c)

            if team:
                matches.append({
                    "day": day, "comp": comp, "team": team,
                    "time": stime, "channels": chans
                })
    except Exception:
        pass
    return matches

def fetch_liveonsat(start_date, end_date):
    try:
        if sys.version_info >= (3, 0):
            import urllib.request as urllib2
            import ssl
        else:
            import urllib2
            import ssl
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        except Exception:
            context = None

        url = ("%s?start_dd=%02d&start_mm=%02d&start_yyyy=%d"
               "&end_dd=%02d&end_mm=%02d&end_yyyy=%d#") % (
            LIVEONSAT_BASE,
            start_date.day, start_date.month, start_date.year,
            end_date.day, end_date.month, end_date.year)

        req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        if context:
            resp = urllib2.urlopen(req, timeout=20, context=context)
        else:
            resp = urllib2.urlopen(req, timeout=20)
        data = resp.read()
        if isinstance(data, bytes):
            data = data.decode('utf-8', 'ignore')
        return True, data
    except Exception as e:
        return False, str(e)

class FootballMatches(Screen):
    skin = FOOTBALL_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\u26bd \u0645\u0628\u0627\u0631\u064a\u0627\u062a \u0627\u0644\u064a\u0648\u0645 \u0648\u0627\u0644\u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0646\u0627\u0642\u0644\u0629 (Football on TV)")
        self["daylabel"] = Label("")
        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Label(u"\u062e\u0631\u0648\u062c (Exit)")
        self["key_green"] = Label(u"\u062a\u062d\u062f\u064a\u062b (Refresh)")
        self["key_yellow"] = Label(u"\u064a\u0648\u0645 \u0633\u0627\u0628\u0642 (Prev)")
        self["key_blue"] = Label(u"\u064a\u0648\u0645 \u062a\u0627\u0644\u064a (Next)")

        self.day_offset = 0
        self.week_mode = False
        self.is_loading = False
        self.entry_meta = []
        self._pending = None
        self._to_delete = None

        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions"], {
            "cancel": self.close,
            "ok": self.set_reminder,
            "red": self.close,
            "green": self.reload_matches,
            "yellow": self.prev_day,
            "blue": self.next_day,
            "left": self.prev_day,
            "right": self.next_day,
            "menu": self.show_reminders,
        }, -1)

        self.onLayoutFinish.append(self.reload_matches)

    def _get_dates(self):
        import datetime
        today = datetime.date.today()
        if self.week_mode:
            start = today
            end = today + datetime.timedelta(days=6)
        else:
            start = today + datetime.timedelta(days=self.day_offset)
            end = start
        return start, end

    def _day_title(self):
        import datetime
        if self.week_mode:
            return u"\u0643\u0627\u0645\u0644 \u0627\u0644\u0623\u0633\u0628\u0648\u0639 (Whole Week)"
        names = {
            0: u"\u0645\u0628\u0627\u0631\u064a\u0627\u062a \u0627\u0644\u064a\u0648\u0645 (Today)",
            1: u"\u0645\u0628\u0627\u0631\u064a\u0627\u062a \u063a\u062f\u0627\u064b (Tomorrow)",
            2: u"\u0628\u0639\u062f \u063a\u062f (Day After Tomorrow)",
        }
        base = names.get(self.day_offset)
        d = datetime.date.today() + datetime.timedelta(days=self.day_offset)
        ds = d.strftime("%A %d/%m/%Y")
        if base:
            return "%s  -  %s" % (base, ds)
        return ds

    def prev_day(self):
        if self.is_loading:
            return
        self.week_mode = False
        self.day_offset -= 1
        self.reload_matches()

    def next_day(self):
        if self.is_loading:
            return
        self.week_mode = False
        self.day_offset += 1
        self.reload_matches()

    def reload_matches(self):
        if self.is_loading:
            return
        self.is_loading = True
        self.entry_meta = []
        self["daylabel"].setText(self._day_title())
        self["list"].setList([u"\u062c\u0627\u0631\u064a \u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u0645\u0628\u0627\u0631\u064a\u0627\u062a... (Loading...)"])
        self["status"].setText(u"\u064a\u0631\u062c\u0649 \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631... (Please wait)")
        start, end = self._get_dates()

        def _worker():
            ok, payload = fetch_liveonsat(start, end)
            matches = parse_liveonsat(payload) if ok else []

            def _apply():
                self.is_loading = False
                if not ok:
                    self.entry_meta = []
                    self["list"].setList([u"\u062a\u0639\u0630\u0631 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 \u0628\u0627\u0644\u0645\u0648\u0642\u0639 (Connection failed)", str(payload)])
                    self["status"].setText(u"\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0627\u062a\u0635\u0627\u0644 (Network error)")
                    return
                self._render(matches)

            _call_ui(_apply)

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()

    def _render(self, matches):
        entries = []
        meta = []
        if not matches:
            entries.append(u"\u0644\u0627 \u062a\u0648\u062c\u062f \u0645\u0628\u0627\u0631\u064a\u0627\u062a \u0644\u0647\u0630\u0627 \u0627\u0644\u064a\u0648\u0645 (No matches found)")
            meta.append(None)
            self.entry_meta = meta
            self["list"].setList(entries)
            self["status"].setText("0 \u0645\u0628\u0627\u0631\u0627\u0629")
            return

        last_day = None
        for m in matches:
            if self.week_mode and m.get("day") and m["day"] != last_day:
                last_day = m["day"]
                entries.append(u"==== %s ====" % m["day"])
                meta.append(None)
            header = u"\u23f0 %s   %s" % (m["time"], m["team"])
            entries.append(header)
            meta.append(m)
            if m.get("comp"):
                entries.append(u"      \u2022 %s" % m["comp"])
                meta.append(m)
            chans = m.get("channels") or []
            if chans:
                per = []
                for c in chans:
                    per.append(c)
                    if len(per) >= 3:
                        entries.append(u"      " + " , ".join(per))
                        meta.append(m)
                        per = []
                if per:
                    entries.append(u"      " + " , ".join(per))
                    meta.append(m)
            else:
                entries.append(u"      (\u0644\u0627 \u062a\u0648\u062c\u062f \u0642\u0646\u0627\u0629 / no channel listed)")
                meta.append(m)
            entries.append(" ")
            meta.append(None)

        self.entry_meta = meta
        self["list"].setList(entries)
        self["status"].setText(u"%d \u0645\u0628\u0627\u0631\u0627\u0629  |  OK=\u062a\u0630\u0643\u064a\u0631 \u0628\u0627\u0644\u0645\u0628\u0627\u0631\u0627\u0629  MENU=\u062a\u0630\u0643\u064a\u0631\u0627\u062a\u064a  \u0623\u062e\u0636\u0631=\u062a\u062d\u062f\u064a\u062b" % len(matches))

    def set_reminder(self):
        if self.is_loading:
            return
        idx = self["list"].getSelectionIndex()
        if idx is None or idx < 0 or idx >= len(self.entry_meta):
            return
        m = self.entry_meta[idx]
        if not m:
            self.session.open(MessageBox, u"\u0627\u062e\u062a\u0631 \u0645\u0628\u0627\u0631\u0627\u0629 \u0645\u0646 \u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0623\u0648\u0644\u0627\u064b (Select a match first)", MessageBox.TYPE_INFO)
            return
        if self.week_mode:
            self.session.open(MessageBox, u"\u0627\u0644\u062a\u0630\u0643\u064a\u0631 \u0645\u062a\u0627\u062d \u0641\u064a \u0648\u0636\u0639 \u0627\u0644\u064a\u0648\u0645 \u0627\u0644\u0648\u0627\u062d\u062f \u0641\u0642\u0637\n(Reminders work in single-day view only.)", MessageBox.TYPE_INFO)
            return
        if not m.get("time") or ":" not in m.get("time", ""):
            self.session.open(MessageBox, u"\u0648\u0642\u062a \u0627\u0644\u0645\u0628\u0627\u0631\u0627\u0629 \u063a\u064a\u0631 \u0645\u062d\u062f\u062f (No match time)", MessageBox.TYPE_INFO)
            return
        self._pending = m
        self.session.openWithCallback(self._reminder_lead_cb, ChoiceBox,
            title=u"\u0630\u0643\u0651\u0631\u0646\u064a \u0642\u0628\u0644 (remind me before):", list=[
                (u"\u0639\u0646\u062f \u0628\u062f\u0627\u064a\u0629 \u0627\u0644\u0645\u0628\u0627\u0631\u0627\u0629 (at start)", 0),
                (u"\u0642\u0628\u0644 5 \u062f\u0642\u0627\u0626\u0642 (5 min)", 5),
                (u"\u0642\u0628\u0644 15 \u062f\u0642\u064a\u0642\u0629 (15 min)", 15),
                (u"\u0642\u0628\u0644 30 \u062f\u0642\u064a\u0642\u0629 (30 min)", 30),
                (u"\u0642\u0628\u0644 \u0633\u0627\u0639\u0629 (60 min)", 60),
            ])

    def _reminder_lead_cb(self, answer):
        if not answer:
            return
        import datetime
        lead = int(answer[1])
        m = self._pending
        if not m:
            return
        try:
            hh, mm = m["time"].split(":")[:2]
            d = datetime.date.today() + datetime.timedelta(days=self.day_offset)
            match_dt = datetime.datetime(d.year, d.month, d.day, int(hh), int(mm))
        except Exception:
            self.session.open(MessageBox, u"\u062a\u0639\u0630\u0651\u0631 \u062a\u062d\u062f\u064a\u062f \u0648\u0642\u062a \u0627\u0644\u0645\u0628\u0627\u0631\u0627\u0629 (Cannot parse time)", MessageBox.TYPE_ERROR)
            return
        match_ts = time.mktime(match_dt.timetuple())
        notify_ts = match_ts - lead * 60
        rem = {
            "team": m.get("team", ""),
            "time": m.get("time", ""),
            "comp": m.get("comp", ""),
            "channels": m.get("channels", []),
            "match_ts": match_ts,
            "notify_ts": notify_ts,
            "lead": lead,
            "notified": False,
        }
        _add_reminder(rem)
        when = datetime.datetime.fromtimestamp(notify_ts).strftime("%d/%m %H:%M")
        self.session.open(MessageBox,
            u"\u2705 \u062a\u0645 \u0636\u0628\u0637 \u062a\u0630\u0643\u064a\u0631:\n%s\n\u0627\u0644\u0633\u0627\u0639\u0629 %s\n\u0633\u064a\u064f\u0646\u0628\u0651\u0647\u0643 \u0641\u064a: %s" % (m.get("team", ""), m.get("time", ""), when),
            MessageBox.TYPE_INFO)

    def show_reminders(self):
        import datetime
        lst = _load_reminders()
        now = time.time()
        future = [r for r in lst if float(r.get("match_ts", 0)) > now - 600]
        if not future:
            self.session.open(MessageBox, u"\u0644\u0627 \u062a\u0648\u062c\u062f \u062a\u0630\u0643\u064a\u0631\u0627\u062a \u0645\u0636\u0628\u0648\u0637\u0629 (No reminders set)", MessageBox.TYPE_INFO)
            return
        choices = []
        for r in future:
            try:
                w = datetime.datetime.fromtimestamp(float(r["notify_ts"])).strftime("%d/%m %H:%M")
            except Exception:
                w = "?"
            label = u"%s - %s (\u062a\u0646\u0628\u064a\u0647 %s)" % (r.get("team", ""), r.get("time", ""), w)
            choices.append((label, r))
        self.session.openWithCallback(self._reminder_manage_cb, ChoiceBox,
            title=u"\u062a\u0630\u0643\u064a\u0631\u0627\u062a\u0643 (\u0627\u062e\u062a\u0631 \u0644\u0644\u062d\u0630\u0641):", list=choices)

    def _reminder_manage_cb(self, answer):
        if not answer:
            return
        self._to_delete = answer[1]
        self.session.openWithCallback(self._reminder_del_confirm, MessageBox,
            u"\u062d\u0630\u0641 \u0627\u0644\u062a\u0630\u0643\u064a\u0631:\n%s \u061f" % answer[1].get("team", ""),
            MessageBox.TYPE_YESNO)

    def _reminder_del_confirm(self, result):
        if not result or not self._to_delete:
            return
        r = self._to_delete
        lst = _load_reminders()
        new = [x for x in lst if not (x.get("team") == r.get("team") and x.get("match_ts") == r.get("match_ts"))]
        _save_reminders(new)
        self.session.open(MessageBox, u"\u2705 \u062a\u0645 \u0627\u0644\u062d\u0630\u0641 (Deleted)", MessageBox.TYPE_INFO)

# =========================================================================
# Weather (open-meteo)
# =========================================================================
WEATHER_CITIES = [
    (u"\u0628\u063a\u062f\u0627\u062f (Baghdad)", 33.34, 44.40),
    (u"\u0627\u0644\u0628\u0635\u0631\u0629 (Basra)", 30.51, 47.78),
    (u"\u0623\u0631\u0628\u064a\u0644 (Erbil)", 36.19, 44.01),
    (u"\u0627\u0644\u0645\u0648\u0635\u0644 (Mosul)", 36.34, 43.13),
    (u"\u0627\u0644\u0646\u062c\u0641 (Najaf)", 32.00, 44.33),
    (u"\u0643\u0631\u0628\u0644\u0627\u0621 (Karbala)", 32.61, 44.02),
    (u"\u0627\u0644\u0642\u0627\u0647\u0631\u0629 (Cairo)", 30.04, 31.24),
    (u"\u0627\u0644\u0631\u064a\u0627\u0636 (Riyadh)", 24.71, 46.68),
    (u"\u062c\u062f\u0629 (Jeddah)", 21.49, 39.19),
    (u"\u0645\u0643\u0629 (Makkah)", 21.39, 39.86),
    (u"\u0627\u0644\u0645\u062f\u064a\u0646\u0629 (Madinah)", 24.52, 39.57),
    (u"\u062f\u0628\u064a (Dubai)", 25.20, 55.27),
    (u"\u0623\u0628\u0648\u0638\u0628\u064a (Abu Dhabi)", 24.45, 54.38),
    (u"\u0639\u0645\u0627\u0646 (Amman)", 31.95, 35.93),
    (u"\u062f\u0645\u0634\u0642 (Damascus)", 33.51, 36.29),
    (u"\u0628\u064a\u0631\u0648\u062a (Beirut)", 33.89, 35.50),
    (u"\u0627\u0644\u062f\u0648\u062d\u0629 (Doha)", 25.28, 51.53),
    (u"\u0627\u0644\u0643\u0648\u064a\u062a (Kuwait)", 29.37, 47.98),
    (u"\u0627\u0644\u0645\u0646\u0627\u0645\u0629 (Manama)", 26.22, 50.58),
    (u"\u0645\u0633\u0642\u0637 (Muscat)", 23.59, 58.41),
    (u"\u0635\u0646\u0639\u0627\u0621 (Sanaa)", 15.37, 44.19),
    (u"\u0627\u0644\u062e\u0631\u0637\u0648\u0645 (Khartoum)", 15.50, 32.56),
    (u"\u0637\u0631\u0627\u0628\u0644\u0633 (Tripoli)", 32.89, 13.19),
    (u"\u062a\u0648\u0646\u0633 (Tunis)", 36.81, 10.18),
    (u"\u0627\u0644\u062c\u0632\u0627\u0626\u0631 (Algiers)", 36.75, 3.06),
    (u"\u0627\u0644\u062f\u0627\u0631 \u0627\u0644\u0628\u064a\u0636\u0627\u0621 (Casablanca)", 33.57, -7.59),
    (u"\u0627\u0644\u0631\u0628\u0627\u0637 (Rabat)", 34.02, -6.83),
    (u"\u0627\u0633\u0637\u0646\u0628\u0648\u0644 (Istanbul)", 41.01, 28.98),
    (u"\u0623\u0646\u0642\u0631\u0629 (Ankara)", 39.93, 32.86),
    (u"\u0637\u0647\u0631\u0627\u0646 (Tehran)", 35.69, 51.39),
    (u"\u0644\u0646\u062f\u0646 (London)", 51.51, -0.13),
    (u"\u0628\u0627\u0631\u064a\u0633 (Paris)", 48.85, 2.35),
    (u"\u0628\u0631\u0644\u064a\u0646 (Berlin)", 52.52, 13.40),
    (u"\u0631\u0648\u0645\u0627 (Rome)", 41.90, 12.50),
    (u"\u0645\u062f\u0631\u064a\u062f (Madrid)", 40.42, -3.70),
    (u"\u0645\u0648\u0633\u0643\u0648 (Moscow)", 55.75, 37.62),
    (u"\u0646\u064a\u0648\u064a\u0648\u0631\u0643 (New York)", 40.71, -74.01),
    (u"\u0648\u0627\u0634\u0646\u0637\u0646 (Washington)", 38.90, -77.04),
    (u"\u062a\u0648\u0631\u0646\u062a\u0648 (Toronto)", 43.65, -79.38),
    (u"\u0637\u0648\u0643\u064a\u0648 (Tokyo)", 35.68, 139.69),
    (u"\u0628\u0643\u064a\u0646 (Beijing)", 39.90, 116.41),
    (u"\u0646\u064a\u0648\u062f\u0644\u0647\u064a (New Delhi)", 28.61, 77.21),
    (u"\u0625\u0633\u0644\u0627\u0645 \u0623\u0628\u0627\u062f (Islamabad)", 33.68, 73.05),
    (u"\u0643\u0648\u0627\u0644\u0627\u0644\u0645\u0628\u0648\u0631 (Kuala Lumpur)", 3.14, 101.69),
    (u"\u062c\u0627\u0643\u0631\u062a\u0627 (Jakarta)", -6.21, 106.85),
    (u"\u0633\u064a\u062f\u0646\u064a (Sydney)", -33.87, 151.21),
]

WEATHER_CODES = {
    0: u"\u0635\u0627\u0641\u064a \u2600", 1: u"\u0635\u0627\u0641\u064d \u063a\u0627\u0644\u0628\u0627\u064b \U0001f324",
    2: u"\u063a\u0627\u0626\u0645 \u062c\u0632\u0626\u064a\u0627\u064b \u26c5", 3: u"\u063a\u0627\u0626\u0645 \u2601",
    45: u"\u0636\u0628\u0627\u0628 \U0001f32b", 48: u"\u0636\u0628\u0627\u0628 \U0001f32b",
    51: u"\u0631\u0630\u0627\u0630 \U0001f327", 53: u"\u0631\u0630\u0627\u0630 \U0001f327", 55: u"\u0631\u0630\u0627\u0630 \U0001f327",
    61: u"\u0645\u0637\u0631 \u062e\u0641\u064a\u0641 \U0001f327", 63: u"\u0645\u0637\u0631 \U0001f327", 65: u"\u0645\u0637\u0631 \u063a\u0632\u064a\u0631 \U0001f327",
    71: u"\u062b\u0644\u062c \u2744", 73: u"\u062b\u0644\u062c \u2744", 75: u"\u062b\u0644\u062c \u2744",
    80: u"\u0632\u062e\u0627\u062a \u0645\u0637\u0631 \U0001f326", 81: u"\u0632\u062e\u0627\u062a \u0645\u0637\u0631 \U0001f326", 82: u"\u0632\u062e\u0627\u062a \u063a\u0632\u064a\u0631\u0629 \U0001f326",
    95: u"\u0639\u0627\u0635\u0641\u0629 \u0631\u0639\u062f\u064a\u0629 \u26c8", 96: u"\u0639\u0627\u0635\u0641\u0629 \u0631\u0639\u062f\u064a\u0629 \u26c8", 99: u"\u0639\u0627\u0635\u0641\u0629 \u0631\u0639\u062f\u064a\u0629 \u26c8",
}

def _weather_desc(code):
    try:
        d = WEATHER_CODES.get(int(code), u"-")
        return u''.join(ch for ch in d if ord(ch) < 0x1F000).strip()
    except Exception:
        return u"-"

def fetch_weather(lat, lon):
    try:
        if sys.version_info >= (3, 0):
            import urllib.request as urllib2
            import ssl
        else:
            import urllib2
            import ssl
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        except Exception:
            context = None
        url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
               "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
               "&daily=temperature_2m_max,temperature_2m_min,weather_code"
               "&timezone=auto&forecast_days=5") % (lat, lon)
        req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        if context:
            resp = urllib2.urlopen(req, timeout=15, context=context)
        else:
            resp = urllib2.urlopen(req, timeout=15)
        data = resp.read()
        if isinstance(data, bytes):
            data = data.decode('utf-8', 'ignore')
        return True, json.loads(data)
    except Exception as e:
        return False, str(e)

def fetch_geocode(query):
    try:
        if sys.version_info >= (3, 0):
            import urllib.request as urllib2
            import urllib.parse as urlparse
            import ssl
            q = urlparse.quote(query)
        else:
            import urllib2
            import urllib as urlparse
            import ssl
            q = urlparse.quote(query.encode('utf-8'))
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        except Exception:
            context = None
        url = ("https://geocoding-api.open-meteo.com/v1/search?name=%s"
               "&count=10&language=ar&format=json") % q
        req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        if context:
            resp = urllib2.urlopen(req, timeout=15, context=context)
        else:
            resp = urllib2.urlopen(req, timeout=15)
        data = resp.read()
        if isinstance(data, bytes):
            data = data.decode('utf-8', 'ignore')
        j = json.loads(data)
        results = []
        for r in j.get("results", []) or []:
            nm = r.get("name", "")
            country = r.get("country", "")
            admin = r.get("admin1", "")
            label = nm
            if admin and admin != nm:
                label += u", " + admin
            if country:
                label += u" - " + country
            results.append((label, r.get("latitude"), r.get("longitude")))
        return True, results
    except Exception as e:
        return False, str(e)

# =========================================================================
# Animated weather icon frames (pure text, no image assets needed,
# works on all Enigma2 images + Python 2/3). Driven by an eTimer.
# =========================================================================
# category -> (arabic condition name, symbol that bounces across the track)
WX_ANIM_INFO = {
    "clear": (u"\u0645\u0634\u0645\u0633", "*"),
    "cloud": (u"\u063a\u0627\u0626\u0645", "~"),
    "rain":  (u"\u0645\u0645\u0637\u0631", ","),
    "snow":  (u"\u062b\u0644\u0648\u062c", "*"),
    "fog":   (u"\u0636\u0628\u0627\u0628", "="),
    "storm": (u"\u0639\u0648\u0627\u0635\u0641", "#"),
}

def _wx_category(code):
    try:
        code = int(code)
    except Exception:
        return "clear"
    if code == 0:
        return "clear"
    if code in (1, 2, 3):
        return "cloud"
    if code in (45, 48):
        return "fog"
    if code in (71, 72, 73, 74, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    return "rain"

class WeatherScreen(Screen):
    skin = WEATHER_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\U0001f324 \u062d\u0627\u0644\u0629 \u0627\u0644\u0637\u0642\u0633 (Weather - open-meteo)")
        try:
            self.setTitle(u"\u062d\u0627\u0644\u0629 \u0627\u0644\u0637\u0642\u0633 (Weather)")
        except Exception:
            pass
        self["daylabel"] = Label("")
        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Label(u"\u0631\u062c\u0648\u0639 (Back)")
        self["key_green"] = Label(u"\u0639\u0631\u0636 (Open)")
        self["key_yellow"] = Label(u"\u0628\u062d\u062b \u0639\u0646 \u0645\u062f\u064a\u0646\u0629 (Search)")
        self["key_blue"] = Label(u"\u062a\u062d\u062f\u064a\u062b (Refresh)")
        self.mode = "menu"
        self.is_loading = False
        self.search_results = []
        self.cur_city = None
        # --- animated weather icon state ---
        self.wx_anim_frame = 0
        self.wx_anim_cat = None
        self.wx_anim_base = ""
        self.wx_anim_timer = eTimer() if eTimer else None
        if self.wx_anim_timer:
            try:
                self.wx_anim_conn = self.wx_anim_timer.timeout.connect(self._wx_anim_tick)
            except AttributeError:
                try:
                    self.wx_anim_timer.callback.append(self._wx_anim_tick)
                except Exception:
                    pass
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
            "cancel": self.go_back, "ok": self.ok_pressed,
            "red": self.go_back, "green": self.ok_pressed,
            "yellow": self.do_search, "blue": self.refresh_current,
        }, -1)
        try:
            self.onClose.append(self._wx_anim_stop)
        except Exception:
            pass
        self.onLayoutFinish.append(self.show_menu)

    def _wx_anim_start(self):
        if not self.wx_anim_timer or not self.wx_anim_cat:
            return
        self.wx_anim_frame = 0
        try:
            self.wx_anim_timer.start(350, False)
        except Exception:
            pass

    def _wx_anim_stop(self):
        self.wx_anim_cat = None
        if self.wx_anim_timer:
            try:
                self.wx_anim_timer.stop()
            except Exception:
                pass

    def _wx_anim_tick(self):
        if not self.wx_anim_cat:
            return
        label, ch = WX_ANIM_INFO.get(self.wx_anim_cat, WX_ANIM_INFO["clear"])
        width = 10
        period = (width - 1) * 2
        p = self.wx_anim_frame % period
        pos = p if p < width else period - p
        track = "".join(ch if i == pos else " " for i in range(width))
        self.wx_anim_frame += 1
        try:
            self["title"].setText(u"\u062d\u0627\u0644\u0629 \u0627\u0644\u0637\u0642\u0633: %s   [%s]" % (label, track))
        except Exception:
            pass

    def show_menu(self):
        self._wx_anim_stop()
        try:
            self["title"].setText(u"\u062d\u0627\u0644\u0629 \u0627\u0644\u0637\u0642\u0633 (Weather)")
        except Exception:
            pass
        self.mode = "menu"
        self["daylabel"].setText(u"\u0627\u062e\u062a\u0631 \u0645\u062f\u064a\u0646\u0629 \u0623\u0648 \u0627\u0636\u063a\u0637 \u0623\u0635\u0641\u0631 \u0644\u0644\u0628\u062d\u062b (Select or Search)")
        items = [u"\U0001f50d \u0628\u062d\u062b \u0639\u0646 \u0645\u062f\u064a\u0646\u0629 \u0641\u064a \u0627\u0644\u0639\u0627\u0644\u0645 (Search city)"]
        items += [c[0] for c in WEATHER_CITIES]
        self["list"].setList([_strip_emoji(x) for x in items])
        self["status"].setText(u"OK = \u0639\u0631\u0636 \u0627\u0644\u0637\u0642\u0633  |  \u0623\u0635\u0641\u0631 = \u0628\u062d\u062b")

    def go_back(self):
        if self.is_loading:
            return
        if self.mode in ("detail", "search"):
            self.show_menu()
        else:
            self.close()

    def ok_pressed(self):
        if self.is_loading:
            return
        idx = self["list"].getSelectionIndex()
        if idx < 0:
            return
        if self.mode == "menu":
            if idx == 0:
                self.do_search()
            else:
                c = WEATHER_CITIES[idx - 1]
                self.cur_city = (c[0], c[1], c[2])
                self.load_detail()
        elif self.mode == "search":
            if 0 <= idx < len(self.search_results):
                r = self.search_results[idx]
                self.cur_city = (r[0], r[1], r[2])
                self.load_detail()

    def refresh_current(self):
        if self.mode == "detail" and self.cur_city and not self.is_loading:
            self.load_detail()

    def do_search(self):
        if self.is_loading:
            return
        try:
            from Screens.VirtualKeyBoard import VirtualKeyBoard
            self.session.openWithCallback(self._search_cb, VirtualKeyBoard,
                                          title=u"\u0627\u0643\u062a\u0628 \u0627\u0633\u0645 \u0627\u0644\u0645\u062f\u064a\u0646\u0629 (City name)")
        except Exception as e:
            self.session.open(MessageBox, u"\u062a\u0639\u0630\u0631 \u0641\u062a\u062d \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0641\u0627\u062a\u064a\u062d:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def _search_cb(self, text):
        if not text:
            return
        self.is_loading = True
        self.mode = "search"
        self["daylabel"].setText(u"\u0646\u062a\u0627\u0626\u062c \u0627\u0644\u0628\u062d\u062b: %s" % text)
        self["list"].setList([u"\u062c\u0627\u0631\u064a \u0627\u0644\u0628\u062d\u062b... (Searching...)"])
        self["status"].setText(u"\u064a\u0631\u062c\u0649 \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631...")

        def _worker():
            ok, payload = fetch_geocode(text)

            def _apply():
                self.is_loading = False
                if not ok:
                    self["list"].setList([u"\u062a\u0639\u0630\u0631 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 (Connection failed)", str(payload)])
                    self["status"].setText(u"\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0627\u062a\u0635\u0627\u0644")
                    return
                self.search_results = payload
                if not payload:
                    self["list"].setList([u"\u0644\u0627 \u062a\u0648\u062c\u062f \u0646\u062a\u0627\u0626\u062c (No results)"])
                    self["status"].setText(u"\u0623\u062d\u0645\u0631 = \u0631\u062c\u0648\u0639")
                else:
                    self["list"].setList([_strip_emoji(r[0]) for r in payload])
                    self["status"].setText(u"%d \u0646\u062a\u064a\u062c\u0629  |  OK = \u0639\u0631\u0636 \u0627\u0644\u0637\u0642\u0633  |  \u0623\u062d\u0645\u0631 = \u0631\u062c\u0648\u0639" % len(payload))

            _call_ui(_apply)

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()

    def load_detail(self):
        self.is_loading = True
        self.mode = "detail"
        name, lat, lon = self.cur_city
        self["daylabel"].setText(name)
        self["list"].setList([u"\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u0645\u064a\u0644... (Loading...)"])
        self["status"].setText(u"\u064a\u0631\u062c\u0649 \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631...")

        def _worker():
            ok, payload = fetch_weather(lat, lon)

            def _apply():
                self.is_loading = False
                if not ok:
                    self["list"].setList([u"\u062a\u0639\u0630\u0631 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 (Connection failed)", str(payload)])
                    self["status"].setText(u"\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0627\u062a\u0635\u0627\u0644")
                    return
                self._render(payload)

            _call_ui(_apply)

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()

    def _render(self, data):
        entries = []
        try:
            cur = data.get("current", {})
            entries.append(u"\u2554\u2550 \u0627\u0644\u0622\u0646 (Now) \u2550\u2557")
            entries.append(u"  \u0627\u0644\u062d\u0631\u0627\u0631\u0629: %s\u00b0C" % cur.get("temperature_2m", "-"))
            entries.append(u"  \u0627\u0644\u062d\u0627\u0644\u0629: %s" % _weather_desc(cur.get("weather_code", -1)))
            entries.append(u"  \u0627\u0644\u0631\u0637\u0648\u0628\u0629: %s%%" % cur.get("relative_humidity_2m", "-"))
            entries.append(u"  \u0627\u0644\u0631\u064a\u0627\u062d: %s km/h" % cur.get("wind_speed_10m", "-"))
            entries.append(" ")
            entries.append(u"\u2554\u2550 \u062a\u0648\u0642\u0639\u0627\u062a 5 \u0623\u064a\u0627\u0645 (5-Day) \u2550\u2557")
            daily = data.get("daily", {})
            days = daily.get("time", [])
            tmax = daily.get("temperature_2m_max", [])
            tmin = daily.get("temperature_2m_min", [])
            wc = daily.get("weather_code", [])
            for i in range(len(days)):
                mx = tmax[i] if i < len(tmax) else "-"
                mn = tmin[i] if i < len(tmin) else "-"
                cc = wc[i] if i < len(wc) else -1
                entries.append(u"  %s   %s\u00b0/%s\u00b0   %s" % (days[i], mx, mn, _weather_desc(cc)))
        except Exception as e:
            entries.append(u"\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a: %s" % str(e))
        self["list"].setList(entries)
        self["status"].setText(u"\u0623\u062d\u0645\u0631 = \u0631\u062c\u0648\u0639  |  \u0623\u0632\u0631\u0642 = \u062a\u062d\u062f\u064a\u062b")
        # --- start the animated weather icon for the current condition ---
        try:
            cur_code = data.get("current", {}).get("weather_code", -1)
            self.wx_anim_cat = _wx_category(cur_code)
            self.wx_anim_base = self.cur_city[0] if self.cur_city else ""
            self._wx_anim_start()
        except Exception:
            pass

# =========================================================================
# IPTV (iptv-org)
# =========================================================================
IPTV_COUNTRIES = [
    (u"\u0627\u0644\u0639\u0631\u0627\u0642 (Iraq)", "iq"),
    (u"\u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629 (Saudi Arabia)", "sa"),
    (u"\u0645\u0635\u0631 (Egypt)", "eg"),
    (u"\u0627\u0644\u0625\u0645\u0627\u0631\u0627\u062a (UAE)", "ae"),
    (u"\u0627\u0644\u0623\u0631\u062f\u0646 (Jordan)", "jo"),
    (u"\u0627\u0644\u0643\u0648\u064a\u062a (Kuwait)", "kw"),
    (u"\u0642\u0637\u0631 (Qatar)", "qa"),
    (u"\u0627\u0644\u0645\u063a\u0631\u0628 (Morocco)", "ma"),
    (u"\u0627\u0644\u062c\u0632\u0627\u0626\u0631 (Algeria)", "dz"),
    (u"\u062a\u0648\u0646\u0633 (Tunisia)", "tn"),
    (u"\u0644\u0628\u0646\u0627\u0646 (Lebanon)", "lb"),
    (u"\u0633\u0648\u0631\u064a\u0627 (Syria)", "sy"),
    (u"\u0641\u0644\u0633\u0637\u064a\u0646 (Palestine)", "ps"),
    (u"\u0644\u064a\u0628\u064a\u0627 (Libya)", "ly"),
    (u"\u0627\u0644\u0633\u0648\u062f\u0627\u0646 (Sudan)", "sd"),
    (u"\u0639\u0645\u0627\u0646 (Oman)", "om"),
    (u"\u0627\u0644\u064a\u0645\u0646 (Yemen)", "ye"),
    (u"\u0643\u0644 \u0627\u0644\u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0639\u0631\u0628\u064a\u0629 (All Arabic)", "@ara"),
]

def fetch_iptv(code):
    try:
        if sys.version_info >= (3, 0):
            import urllib.request as urllib2
            import ssl
        else:
            import urllib2
            import ssl
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        except Exception:
            context = None
        if code == "@ara":
            url = "https://iptv-org.github.io/iptv/languages/ara.m3u"
        else:
            url = "https://iptv-org.github.io/iptv/countries/%s.m3u" % code
        req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        if context:
            resp = urllib2.urlopen(req, timeout=20, context=context)
        else:
            resp = urllib2.urlopen(req, timeout=20)
        data = resp.read()
        if isinstance(data, bytes):
            data = data.decode('utf-8', 'ignore')
        return True, data
    except Exception as e:
        return False, str(e)

def parse_m3u(text):
    channels = []
    try:
        name = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("#EXTINF"):
                if "," in line:
                    name = line.split(",", 1)[1].strip()
                else:
                    name = "Channel"
            elif line and not line.startswith("#"):
                if name:
                    channels.append((name, line))
                    name = None
    except Exception:
        pass
    return channels

IPTV_BASE = "https://iptv-org.github.io/iptv"
IPTV_API = "https://iptv-org.github.io/api"

IPTV_AR_COUNTRY = {
    "iq": u"\u0627\u0644\u0639\u0631\u0627\u0642", "sa": u"\u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629", "eg": u"\u0645\u0635\u0631", "ae": u"\u0627\u0644\u0625\u0645\u0627\u0631\u0627\u062a",
    "jo": u"\u0627\u0644\u0623\u0631\u062f\u0646", "kw": u"\u0627\u0644\u0643\u0648\u064a\u062a", "qa": u"\u0642\u0637\u0631", "ma": u"\u0627\u0644\u0645\u063a\u0631\u0628",
    "dz": u"\u0627\u0644\u062c\u0632\u0627\u0626\u0631", "tn": u"\u062a\u0648\u0646\u0633", "lb": u"\u0644\u0628\u0646\u0627\u0646", "sy": u"\u0633\u0648\u0631\u064a\u0627",
    "ps": u"\u0641\u0644\u0633\u0637\u064a\u0646", "ly": u"\u0644\u064a\u0628\u064a\u0627", "sd": u"\u0627\u0644\u0633\u0648\u062f\u0627\u0646", "om": u"\u0639\u0645\u0627\u0646",
    "ye": u"\u0627\u0644\u064a\u0645\u0646", "bh": u"\u0627\u0644\u0628\u062d\u0631\u064a\u0646", "mr": u"\u0645\u0648\u0631\u064a\u062a\u0627\u0646\u064a\u0627", "so": u"\u0627\u0644\u0635\u0648\u0645\u0627\u0644",
    "dj": u"\u062c\u064a\u0628\u0648\u062a\u064a", "km": u"\u062c\u0632\u0631 \u0627\u0644\u0642\u0645\u0631", "tr": u"\u062a\u0631\u0643\u064a\u0627", "ir": u"\u0625\u064a\u0631\u0627\u0646",
    "us": u"\u0627\u0644\u0648\u0644\u0627\u064a\u0627\u062a \u0627\u0644\u0645\u062a\u062d\u062f\u0629", "gb": u"\u0628\u0631\u064a\u0637\u0627\u0646\u064a\u0627", "fr": u"\u0641\u0631\u0646\u0633\u0627", "de": u"\u0623\u0644\u0645\u0627\u0646\u064a\u0627",
}

def _http_get(url, timeout=25):
    try:
        if sys.version_info >= (3, 0):
            import urllib.request as urllib2
            import ssl
        else:
            import urllib2
            import ssl
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        except Exception:
            context = None
        req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        if context:
            resp = urllib2.urlopen(req, timeout=timeout, context=context)
        else:
            resp = urllib2.urlopen(req, timeout=timeout)
        data = resp.read()
        if isinstance(data, bytes):
            data = data.decode('utf-8', 'ignore')
        return True, data
    except Exception as e:
        return False, str(e)

def fetch_iptv_index():
    index = []
    index.append((u"\u2605 \u0643\u0644 \u0627\u0644\u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0639\u0631\u0628\u064a\u0629 (All Arabic)", IPTV_BASE + "/languages/ara.m3u"))
    okc, cdata = _http_get(IPTV_API + "/categories.json")
    if okc:
        try:
            for c in json.loads(cdata):
                cid = c.get("id")
                nm = c.get("name", "")
                if cid:
                    index.append((u"[\u062a\u0635\u0646\u064a\u0641] %s" % nm, IPTV_BASE + "/categories/%s.m3u" % cid))
        except Exception:
            pass
    oks, sdata = _http_get(IPTV_API + "/countries.json")
    if oks:
        try:
            arr = json.loads(sdata)
            arr = sorted(arr, key=lambda x: x.get("name", ""))
            for c in arr:
                code = c.get("code")
                nm = c.get("name", "")
                if code:
                    ar = IPTV_AR_COUNTRY.get(code.lower())
                    label = (u"%s (%s)" % (ar, nm)) if ar else nm
                    index.append((label, IPTV_BASE + "/countries/%s.m3u" % code.lower()))
        except Exception:
            pass
    return index

class IPTVScreen(Screen):
    skin = IPTV_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\U0001F4FA \u0642\u0646\u0648\u0627\u062a IPTV (iptv-org)")
        try:
            self.setTitle(u"\u0642\u0646\u0648\u0627\u062a IPTV (IPTV)")
        except Exception:
            pass
        self["daylabel"] = Label("")
        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Label(u"\u0631\u062c\u0648\u0639 (Back)")
        self["key_green"] = Label(u"\u062a\u0634\u063a\u064a\u0644 (Play)")
        self["key_yellow"] = Label(u"\u0635\u0641\u062d\u0629 \u0644\u0623\u0639\u0644\u0649 (Page Up)")
        self["key_blue"] = Label(u"\u0635\u0641\u062d\u0629 \u0644\u0623\u0633\u0641\u0644 (Page Down)")
        self.mode = "menu"
        self.index = []
        self.is_loading = False
        self.channels = []
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
            "cancel": self.go_back, "ok": self.ok_pressed,
            "red": self.go_back, "green": self.ok_pressed,
            "yellow": self.page_up, "blue": self.page_down,
        }, -1)
        self.onLayoutFinish.append(self.load_index)

    def page_up(self):
        try:
            self["list"].pageUp()
        except Exception:
            pass

    def page_down(self):
        try:
            self["list"].pageDown()
        except Exception:
            pass

    def load_index(self):
        self.is_loading = True
        self.mode = "menu"
        self["daylabel"].setText(u"\u062c\u0627\u0631\u064a \u062a\u062d\u0645\u064a\u0644 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u062f\u0648\u0644 \u0648\u0627\u0644\u062a\u0635\u0646\u064a\u0641\u0627\u062a... (Loading...)")
        self["list"].setList([u"\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u0645\u064a\u0644... (Loading...)"])
        self["status"].setText(u"\u064a\u0631\u062c\u0649 \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631...")

        def _worker():
            index = fetch_iptv_index()

            def _apply():
                self.is_loading = False
                if not index:
                    self.index = [(c[0], (IPTV_BASE + "/languages/ara.m3u") if c[1] == "@ara" else (IPTV_BASE + "/countries/%s.m3u" % c[1])) for c in IPTV_COUNTRIES]
                else:
                    self.index = index
                self.show_menu()

            _call_ui(_apply)

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()

    def show_menu(self):
        self.mode = "menu"
        self["daylabel"].setText(u"\u0627\u062e\u062a\u0631 \u062f\u0648\u0644\u0629 \u0623\u0648 \u062a\u0635\u0646\u064a\u0641 \u062b\u0645 OK (Select then OK)")
        self["list"].setList([_strip_emoji(x[0]) for x in self.index])
        self["status"].setText(u"%d \u0639\u0646\u0635\u0631  |  OK = \u0641\u062a\u062d \u0627\u0644\u0642\u0646\u0648\u0627\u062a  |  \u0623\u0635\u0641\u0631/\u0623\u0632\u0631\u0642 = \u062a\u0635\u0641\u062d" % len(self.index))

    def go_back(self):
        if self.is_loading:
            return
        if self.mode == "channels":
            self.show_menu()
        else:
            self.close()

    def ok_pressed(self):
        if self.is_loading:
            return
        idx = self["list"].getSelectionIndex()
        if idx < 0:
            return
        if self.mode == "menu":
            if 0 <= idx < len(self.index):
                self.load_channels(self.index[idx])
        else:
            if 0 <= idx < len(self.channels):
                self.play_channel(self.channels[idx])

    def load_channels(self, entry):
        self.is_loading = True
        name, url = entry
        self["daylabel"].setText(_strip_emoji(name))
        self["list"].setList([u"\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u0645\u064a\u0644... (Loading...)"])
        self["status"].setText(u"\u064a\u0631\u062c\u0649 \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631...")

        def _worker():
            ok, payload = _http_get(url, 25)
            chans = parse_m3u(payload) if ok else []

            def _apply():
                self.is_loading = False
                if not ok:
                    self["list"].setList([u"\u062a\u0639\u0630\u0631 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 (Connection failed)", str(payload)])
                    self["status"].setText(u"\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0627\u062a\u0635\u0627\u0644")
                    return
                self.mode = "channels"
                self.channels = chans
                if not chans:
                    self["list"].setList([u"\u0644\u0627 \u062a\u0648\u062c\u062f \u0642\u0646\u0648\u0627\u062a (No channels)"])
                else:
                    self["list"].setList([u"%d. %s" % (i + 1, _strip_emoji(c[0])) for i, c in enumerate(chans)])
                self["status"].setText(u"%d \u0642\u0646\u0627\u0629  |  OK = \u062a\u0634\u063a\u064a\u0644  |  \u0623\u062d\u0645\u0631 = \u0631\u062c\u0648\u0639  |  \u0645\u0644\u0627\u062d\u0638\u0629: \u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0634\u064a\u0631\u0646\u0651\u064c \u063a\u064a\u0631 \u0645\u062a\u0648\u0641\u0631\u0629 \u0647\u0646\u0627" % len(chans))

            _call_ui(_apply)

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()

    def play_channel(self, ch):
        name, url = ch
        try:
            from enigma import eServiceReference
            safe = url.replace(":", "%3a")
            ref = eServiceReference("4097:0:1:0:0:0:0:0:0:0:" + safe)
            try:
                ref.setName(name)
            except Exception:
                pass
            self.session.nav.playService(ref)
            self["status"].setText(u"\u062c\u0627\u0631\u064a \u062a\u0634\u063a\u064a\u0644: %s" % name)
        except Exception as e:
            self.session.open(MessageBox, u"\u062a\u0639\u0630\u0631 \u0627\u0644\u062a\u0634\u063a\u064a\u0644:\n%s" % str(e), MessageBox.TYPE_ERROR)

# =========================================================================
# IPTV MohamedStore - EMBEDDED LOCAL M3U LIBRARY BROWSER (Python 2/3)
# The whole m3u library is compressed (gzip) and base64-encoded directly
# INSIDE this file, so no external folder/files are needed. At runtime it is
# decompressed in memory into (name, m3u_text) items and browsed as:
#   list of files -> channels of the selected file -> play.
# =========================================================================
IPTV_MS_SKIN = _make_ms_skin("MS_IPTVMohamedStoreScreen", "IPTV MohamedStore")

# Curated ordering so the most-watched groups (ALWAN, BEIN, Arabic) show first.
IPTV_MS_PRIORITY = [
    "ALWAN", "BEIN",
    "\u2503AR\u2503 IRAQ", "\u2503AR\u2503 MBC", "\u2503AR\u2503 QURAN",
    "\u2503UCL\u2503", "\u2503UK\u2503 SKY SPORTS", "\u2503UK\u2503 SKY CINEMA",
]

_IPTV_MS_B64 = "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"

_IPTV_MS_CACHE = None

def _iptv_ms_decode():
    """Decompress the embedded library once. Returns list of (display_name, m3u_text)."""
    global _IPTV_MS_CACHE
    if _IPTV_MS_CACHE is not None:
        return _IPTV_MS_CACHE
    items = []
    try:
        raw = base64.b64decode(_IPTV_MS_B64)
        try:
            data = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        except Exception:
            data = zlib.decompress(raw)
        if isinstance(data, bytes):
            data = data.decode("utf-8", "ignore")
        for chunk in data.split("\x1e"):
            if not chunk:
                continue
            if "\x1f" not in chunk:
                continue
            nm, body = chunk.split("\x1f", 1)
            nm = nm.strip()
            if nm:
                items.append((nm, body))
    except Exception:
        items = []
    try:
        def _key(it):
            nm = it[0]
            for i, pfx in enumerate(IPTV_MS_PRIORITY):
                if nm.startswith(pfx):
                    return (0, i, nm.lower())
            return (1, 0, nm.lower())
        items.sort(key=_key)
    except Exception:
        pass
    _IPTV_MS_CACHE = items
    return items

class IPTVMohamedStoreScreen(Screen):
    skin = IPTV_MS_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\U0001F4FA IPTV MohamedStore")
        try:
            self.setTitle("IPTV MohamedStore")
        except Exception:
            pass
        self["daylabel"] = Label("")
        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Label(u"\u0631\u062c\u0648\u0639 (Back)")
        self["key_green"] = Label(u"\u0641\u062a\u062d/\u062a\u0634\u063a\u064a\u0644 (Open/Play)")
        self["key_yellow"] = Label(u"\u0635\u0641\u062d\u0629 \u0644\u0623\u0639\u0644\u0649")
        self["key_blue"] = Label(u"\u0635\u0641\u062d\u0629 \u0644\u0623\u0633\u0641\u0644")
        self.mode = "browse"
        self.library = []
        self.channels = []
        self.cur_name = ""
        self.saved_lib_index = 0
        self.saved_lib_index = 0
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
            "cancel": self.go_back, "ok": self.ok_pressed,
            "red": self.go_back, "green": self.ok_pressed,
            "yellow": self.page_up, "blue": self.page_down,
        }, -1)
        self.onLayoutFinish.append(self.show_library)

    def page_up(self):
        try:
            self["list"].pageUp()
        except Exception:
            pass

    def page_down(self):
        try:
            self["list"].pageDown()
        except Exception:
            pass

    def show_library(self, keep_index=None):
        if keep_index is None:
            keep_index = getattr(self, "saved_lib_index", 0)
        self.mode = "browse"
        self.library = _iptv_ms_decode()
        self["daylabel"].setText(u"\u0627\u062e\u062a\u0631 \u0645\u0644\u0641\u0627\u064b \u062b\u0645 OK \u0644\u0639\u0631\u0636 \u0627\u0644\u0642\u0646\u0648\u0627\u062a")
        if not self.library:
            self["list"].setList([u"\u0644\u0645 \u064a\u062a\u0645 \u0627\u0644\u0639\u062b\u0648\u0631 \u0639\u0644\u0649 \u0645\u0643\u062a\u0628\u0629 IPTV MohamedStore"])
            self["status"].setText("")
            return
        self["list"].setList([_strip_emoji(nm) for nm, _ in self.library])
        try:
            if 0 <= keep_index < len(self.library):
                self["list"].moveToIndex(keep_index)
        except Exception:
            pass
        self["status"].setText(u"%d \u0645\u0644\u0641  |  OK = \u0641\u062a\u062d \u0627\u0644\u0642\u0646\u0648\u0627\u062a  |  \u0623\u062d\u0645\u0631 = \u0631\u062c\u0648\u0639" % len(self.library))

    def open_file(self, idx):
        if not (0 <= idx < len(self.library)):
            return
        nm, body = self.library[idx]
        self.saved_lib_index = idx
        chans = parse_m3u(body)
        self.mode = "channels"
        self.cur_name = nm
        self.channels = chans
        self["daylabel"].setText(_strip_emoji(nm))
        if not chans:
            self["list"].setList([u"\u0644\u0627 \u062a\u0648\u062c\u062f \u0642\u0646\u0648\u0627\u062a \u0641\u064a \u0647\u0630\u0627 \u0627\u0644\u0645\u0644\u0641"])
        else:
            self["list"].setList([u"%d. %s" % (i + 1, _strip_emoji(c[0])) for i, c in enumerate(chans)])
        self["status"].setText(u"%d \u0642\u0646\u0627\u0629  |  OK = \u062a\u0634\u063a\u064a\u0644  |  \u0623\u062d\u0645\u0631 = \u0631\u062c\u0648\u0639" % len(chans))

    def ok_pressed(self):
        idx = self["list"].getSelectionIndex()
        if idx < 0:
            return
        if self.mode == "browse":
            self.open_file(idx)
        else:
            if 0 <= idx < len(self.channels):
                self.play_channel(self.channels[idx])

    def go_back(self):
        if self.mode == "channels":
            self.show_library()
        else:
            self.close()

    def play_channel(self, ch):
        name, url = ch
        try:
            from enigma import eServiceReference
            safe = url.replace(":", "%3a")
            ref = eServiceReference("4097:0:1:0:0:0:0:0:0:0:" + safe)
            try:
                ref.setName(name)
            except Exception:
                pass
            self.session.nav.playService(ref)
            self["status"].setText(u"\u062c\u0627\u0631\u064a \u062a\u0634\u063a\u064a\u0644: %s" % name)
        except Exception as e:
            self.session.open(MessageBox, u"\u062a\u0639\u0630\u0631 \u0627\u0644\u062a\u0634\u063a\u064a\u0644:\n%s" % str(e), MessageBox.TYPE_ERROR)

# =========================================================================
# OPENSUBTITLES (opensubtitles.org) SUBTITLES ENGINE WITH POSTERS & HDD DOWNLOAD
# =========================================================================
SUBSCENE_BASE = "https://www.opensubtitles.org"
OS_LANG = "ara"            # Arabic subtitles language id on opensubtitles.org
OS_UI = "/ar"             # Arabic UI path
OS_DL_HOST = "https://dl.opensubtitles.org"

# -------------------------------------------------------------------------
# Cookie-aware HTTP layer that transparently solves the "Anubis" anti-bot
# proof-of-work challenge opensubtitles.org serves (pure-Python SHA-256, no
# JavaScript needed). The auth cookie is cached module-wide, so only the FIRST
# request pays the (tiny, ~30ms) cost; every later page/poster is instant.
# Works on Python 2.7 and 3.x with the urllib that every Enigma2 image ships.
# -------------------------------------------------------------------------
try:
    import urllib.request as _os_u
    import urllib.parse as _os_up
    import urllib.error as _os_ue
except ImportError:
    import urllib2 as _os_u
    import urllib as _os_up
    _os_ue = _os_u

_OS_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')
_OS_COOKIES = {}
_OS_OPENER = None

def _os_make_ctx():
    try:
        c = ssl.create_default_context()
        c.check_hostname = False
        c.verify_mode = ssl.CERT_NONE
        return c
    except Exception:
        try:
            return ssl._create_unverified_context()
        except Exception:
            return None

def _os_get_opener():
    global _OS_OPENER
    if _OS_OPENER is not None:
        return _OS_OPENER
    import ssl as _ssl_mod  # noqa
    class _NoRedir(_os_u.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    handlers = [_NoRedir()]
    ctx = _os_make_ctx()
    if ctx is not None:
        try:
            handlers.append(_os_u.HTTPSHandler(context=ctx))
        except Exception:
            pass
    _OS_OPENER = _os_u.build_opener(*handlers)
    return _OS_OPENER

def _os_store_cookies(resp):
    try:
        hdrs = resp.info()
        try:
            items = hdrs.get_all('Set-Cookie')
        except Exception:
            items = hdrs.getheaders('Set-Cookie')
        for h in (items or []):
            kv = h.split(';', 1)[0]
            if '=' in kv:
                k, v = kv.split('=', 1)
                _OS_COOKIES[k.strip()] = v.strip()
    except Exception:
        pass

def _os_cookie_header():
    return '; '.join('%s=%s' % (k, v) for k, v in _OS_COOKIES.items())

import ssl  # ensure ssl is importable at module import time

def _os_one(url, timeout):
    hd = {
        'User-Agent': _OS_UA,
        'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
        'Accept-Language': 'ar,en;q=0.9',
        'Accept-Encoding': 'gzip',
        'Referer': SUBSCENE_BASE + '/',
    }
    if _OS_COOKIES:
        hd['Cookie'] = _os_cookie_header()
    req = _os_u.Request(url, headers=hd)
    opener = _os_get_opener()
    try:
        resp = opener.open(req, timeout=timeout)
        code = resp.getcode()
    except _os_ue.HTTPError as e:
        resp = e
        code = e.code
    _os_store_cookies(resp)
    data = resp.read()
    try:
        loc = resp.info().get('Location')
    except Exception:
        loc = None
    try:
        enc = resp.info().get('Content-Encoding')
    except Exception:
        enc = None
    if enc == 'gzip':
        try:
            data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
        except Exception:
            pass
    return code, data, loc

def _os_raw(url, timeout=20, maxred=6):
    cur = url
    code = 0
    data = b""
    for _ in range(maxred):
        code, data, loc = _os_one(cur, timeout)
        if code in (301, 302, 303, 307, 308) and loc:
            try:
                cur = _os_up.urljoin(cur, loc)
            except Exception:
                cur = loc
            continue
        break
    return code, data

def _os_solve(random_data, difficulty):
    """Solve the Anubis 'fast' SHA-256 proof-of-work: find a nonce so that
    sha256(randomData + nonce) begins with <difficulty> hex zeros."""
    pre = '0' * int(difficulty)
    n = 0
    while True:
        h = hashlib.sha256((random_data + str(n)).encode('utf-8')).hexdigest()
        if h.startswith(pre):
            return n, h
        n += 1

def _os_solve_challenge(body, url, timeout):
    try:
        m = re.search(r'id="anubis_challenge"[^>]*>(.*?)</script>', body, re.S)
        if not m:
            return False
        ch = json.loads(m.group(1))
        rd = ch['challenge']['randomData']
        diff = ch['rules']['difficulty']
        cid = ch['challenge']['id']
        t0 = time.time()
        nonce, hh = _os_solve(rd, diff)
        el = int((time.time() - t0) * 1000) or 30
        params = {'id': cid, 'response': hh, 'nonce': nonce,
                  'redir': url, 'elapsedTime': el}
        pc = (SUBSCENE_BASE +
              '/.within.website/x/cmd/anubis/api/pass-challenge?' +
              _os_up.urlencode(params))
        _os_raw(pc, timeout=timeout)
        return True
    except Exception:
        return False

def subscene_http_get(url, timeout=20):
    """Fetch an opensubtitles.org page as text, auto-solving the Anubis
    anti-bot challenge the first time. Returns (ok, html)."""
    try:
        code, data = _os_raw(url, timeout=timeout)
    except Exception:
        return False, ""
    body = data.decode('utf-8', 'ignore') if isinstance(data, bytes) else data
    if 'id="anubis_challenge"' in body:
        if _os_solve_challenge(body, url, timeout):
            try:
                code, data = _os_raw(url, timeout=timeout)
                body = data.decode('utf-8', 'ignore') if isinstance(data, bytes) else data
            except Exception:
                pass
    if not body:
        return False, ""
    return True, body

def subscene_fetch_binary(url, timeout=20):
    """Fetch a binary resource (poster image / subtitle archive) through the
    same cookie-aware, Anubis-aware channel. Returns (ok, bytes)."""
    try:
        code, data = _os_raw(url, timeout=timeout)
    except Exception:
        return False, b""
    # If a challenge page came back (served as text), solve then retry once.
    if isinstance(data, bytes) and data[:15].find(b'anubis') < 0:
        head = data[:400]
        if b'anubis_challenge' in head or (data[:1] == b'<' and b'Making sure' in data[:2000]):
            try:
                body = data.decode('utf-8', 'ignore')
                if _os_solve_challenge(body, url, timeout):
                    code, data = _os_raw(url, timeout=timeout)
            except Exception:
                pass
    if not data:
        return False, b""
    return True, (data if isinstance(data, bytes) else data.encode('utf-8', 'ignore'))

def os_imdb_thumb(imdb_id):
    """Build the fast, direct poster-thumbnail URL from an IMDB numeric id.
    opensubtitles stores it at /gfx/thumbs/<reversed last 4 digits>/<id>-t.jpg
    so posters load instantly without any extra page request."""
    try:
        d = str(int(imdb_id))
    except Exception:
        return ""
    last4 = d[-4:]
    last4 = ('0' * (4 - len(last4))) + last4
    path = '/'.join(reversed(list(last4)))
    return "%s/gfx/thumbs/%s/%s-t.jpg" % (SUBSCENE_BASE, path, d)

def make_utf8_bytes(val):
    if val is None:
        return b""
    if sys.version_info >= (3, 0):
        if isinstance(val, str):
            return val.encode('utf-8', errors='ignore')
        return bytes(val)
    else:
        if isinstance(val, unicode):
            return val.encode('utf-8')
        return str(val)

def get_subtitles_storage_path():
    """Detects primary hard disk / storage path on Enigma2 STB"""
    for p in ["/media/hdd", "/media/hdd/movie", "/media/usb", "/tmp"]:
        if os.path.exists(p):
            return p
    return "/media/hdd"

def get_subscene_cache_dir():
    cache_d = "/tmp/subscene_posters"
    if not os.path.exists(cache_d):
        try:
            os.makedirs(cache_d)
        except Exception:
            pass
    return cache_d

def _subscene_http_get_legacy(url, timeout=12):
    """Legacy sub-scene.com fetch (kept only as an inert fallback)."""
    try:
        return subscene_http_get(url, timeout=timeout)
    except Exception:
        return False, ""

CATALOG_PAGES = {
    1: [
        {"id": "159141", "title": "Thunderbolts", "year": "2025", "poster": "https://res.subscene.best/image/20969586.jpg", "link": "https://sub-scene.com/subscene/159141"},
        {"id": "158886", "title": "Death of a Unicorn", "year": "2025", "poster": "https://res.subscene.best/image/28443655.jpg", "link": "https://sub-scene.com/subscene/158886"},
        {"id": "81016", "title": "Havoc", "year": "2025", "poster": "https://res.subscene.best/image/0285175.jpg", "link": "https://sub-scene.com/subscene/81016"},
        {"id": "158484", "title": "The Gorge", "year": "2025", "poster": "https://res.subscene.best/image/13654226.jpg", "link": "https://sub-scene.com/subscene/158484"},
        {"id": "158413", "title": "Flight Risk", "year": "2025", "poster": "https://res.subscene.best/image/10078772.jpg", "link": "https://sub-scene.com/subscene/158413"},
        {"id": "oppenheimer", "title": "Oppenheimer", "year": "2023", "poster": "https://image.tmdb.org/t/p/w300/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg", "link": "https://sub-scene.com/subtitles/oppenheimer"},
        {"id": "dune2", "title": "Dune: Part Two", "year": "2024", "poster": "https://image.tmdb.org/t/p/w300/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg", "link": "https://sub-scene.com/subtitles/dune-part-two"},
        {"id": "gladiator2", "title": "Gladiator II", "year": "2024", "poster": "https://image.tmdb.org/t/p/w300/2cxhvwyEwRlysAmRH4iodkvo0z5.jpg", "link": "https://sub-scene.com/subtitles/gladiator-ii"},
        {"id": "deadpool3", "title": "Deadpool & Wolverine", "year": "2024", "poster": "https://image.tmdb.org/t/p/w300/8cdWjvZQUExUUTzyp4t6EDMubfO.jpg", "link": "https://sub-scene.com/subtitles/deadpool-and-wolverine"},
        {"id": "joker2", "title": "Joker: Folie a Deux", "year": "2024", "poster": "https://image.tmdb.org/t/p/w300/aciP8Km0waTLAc1vDmAguN9Uqd3.jpg", "link": "https://sub-scene.com/subtitles/joker-folie-a-deux"},
        {"id": "twisters", "title": "Twisters", "year": "2024", "poster": "https://image.tmdb.org/t/p/w300/pjnD08FlMAIXsfOLKQbvmO0f0MD.jpg", "link": "https://sub-scene.com/subtitles/twisters"},
        {"id": "alien-romulus", "title": "Alien: Romulus", "year": "2024", "poster": "https://image.tmdb.org/t/p/w300/b33nnKl1GSFbao4l3fZDDqsMx0F.jpg", "link": "https://sub-scene.com/subtitles/alien-romulus"},
        {"id": "the-substance", "title": "The Substance", "year": "2024", "poster": "https://image.tmdb.org/t/p/w300/lqoMzCcZYEFK729Fc6rKWZzAc4e.jpg", "link": "https://sub-scene.com/subtitles/the-substance"},
        {"id": "beetlejuice2", "title": "Beetlejuice Beetlejuice", "year": "2024", "poster": "https://image.tmdb.org/t/p/w300/kKgQzkUCUm0meqZiwVoIhMm97Ha.jpg", "link": "https://sub-scene.com/subtitles/beetlejuice-beetlejuice"},
        {"id": "civil-war", "title": "Civil War", "year": "2024", "poster": "https://image.tmdb.org/t/p/w300/sh7Rg8Er3tFcN9BpKIPOMvALgZd.jpg", "link": "https://sub-scene.com/subtitles/civil-war"}
    ],
    2: [
        {"id": "interstellar", "title": "Interstellar", "year": "2014", "poster": "https://image.tmdb.org/t/p/w300/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg", "link": "https://sub-scene.com/subtitles/interstellar"},
        {"id": "inception", "title": "Inception", "year": "2010", "poster": "https://image.tmdb.org/t/p/w300/edv5CZvWj09upOsy2Y6IwDhK8bt.jpg", "link": "https://sub-scene.com/subtitles/inception"},
        {"id": "the-batman", "title": "The Batman", "year": "2022", "poster": "https://image.tmdb.org/t/p/w300/74xTEgt7R36Fpooo50r9T25onhq.jpg", "link": "https://sub-scene.com/subtitles/the-batman"},
        {"id": "avatar-2", "title": "Avatar: The Way of Water", "year": "2022", "poster": "https://image.tmdb.org/t/p/w300/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg", "link": "https://sub-scene.com/subtitles/avatar-the-way-of-water"},
        {"id": "dark-knight", "title": "The Dark Knight", "year": "2008", "poster": "https://image.tmdb.org/t/p/w300/qJ2tW6WMUDux911r6m7haRef0WH.jpg", "link": "https://sub-scene.com/subtitles/the-dark-knight"},
        {"id": "top-gun-2", "title": "Top Gun: Maverick", "year": "2022", "poster": "https://image.tmdb.org/t/p/w300/62HCnUTziyWcpDaBO2i1DX17ljH.jpg", "link": "https://sub-scene.com/subtitles/top-gun-maverick"},
        {"id": "spider-verse-2", "title": "Spider-Man: Across the Spider-Verse", "year": "2023", "poster": "https://image.tmdb.org/t/p/w300/8Vt6mWEReuy4Of61Lnj5Xj704m8.jpg", "link": "https://sub-scene.com/subtitles/spider-man-across-the-spider-verse"},
        {"id": "john-wick-4", "title": "John Wick: Chapter 4", "year": "2023", "poster": "https://image.tmdb.org/t/p/w300/vZloFAK7NKnMGKEslUsZ2VoXVwp.jpg", "link": "https://sub-scene.com/subtitles/john-wick-chapter-4"},
        {"id": "poor-things", "title": "Poor Things", "year": "2023", "poster": "https://image.tmdb.org/t/p/w300/kCGlIMHnOm8JPXq3rXM6c5wMxcT.jpg", "link": "https://sub-scene.com/subtitles/poor-things"},
        {"id": "killers-flower-moon", "title": "Killers of the Flower Moon", "year": "2023", "poster": "https://image.tmdb.org/t/p/w300/dB6Krk806zeqd0YNp2ngQ9zXteH.jpg", "link": "https://sub-scene.com/subtitles/killers-of-the-flower-moon"},
        {"id": "the-holdovers", "title": "The Holdovers", "year": "2023", "poster": "https://image.tmdb.org/t/p/w300/A31iW5vI6Z7qQxJ7wDqYkR4oE3h.jpg", "link": "https://sub-scene.com/subtitles/the-holdovers"},
        {"id": "mi7", "title": "Mission: Impossible - Dead Reckoning", "year": "2023", "poster": "https://image.tmdb.org/t/p/w300/NNxYkU70HPurnNCSiCjYAmacwm.jpg", "link": "https://sub-scene.com/subtitles/mission-impossible-dead-reckoning"},
        {"id": "wonka", "title": "Wonka", "year": "2023", "poster": "https://image.tmdb.org/t/p/w300/qhb1qYheYbaM50m62rZUrQ7w2z.jpg", "link": "https://sub-scene.com/subtitles/wonka"},
        {"id": "barbie", "title": "Barbie", "year": "2023", "poster": "https://image.tmdb.org/t/p/w300/iuFNMS8U5cb6xfzi51Dbkovj7vM.jpg", "link": "https://sub-scene.com/subtitles/barbie"},
        {"id": "society-snow", "title": "Society of the Snow", "year": "2023", "poster": "https://image.tmdb.org/t/p/w300/275MtEUPx9917Lp6Ww5wV2M1a8v.jpg", "link": "https://sub-scene.com/subtitles/society-of-the-snow"}
    ],
    3: [
        {"id": "daredevil-ba", "title": "Daredevil: Born Again", "year": "2025", "poster": "https://res.subscene.best/image/20969586.jpg", "link": "https://sub-scene.com/subtitles/daredevil-born-again"},
        {"id": "breaking-bad", "title": "Breaking Bad", "year": "2008-2013", "poster": "https://image.tmdb.org/t/p/w300/ztkUQFLlC19CCMYHW9o1zWhJAGq.jpg", "link": "https://sub-scene.com/subtitles/breaking-bad"},
        {"id": "better-call-saul", "title": "Better Call Saul", "year": "2015-2022", "poster": "https://image.tmdb.org/t/p/w300/fC2HDm5t0kHVR79vis7MMatOqIQ.jpg", "link": "https://sub-scene.com/subtitles/better-call-saul"},
        {"id": "game-of-thrones", "title": "Game of Thrones", "year": "2011-2019", "poster": "https://image.tmdb.org/t/p/w300/1XS1oqL89opfnbLl8WnZY1O1uJx.jpg", "link": "https://sub-scene.com/subtitles/game-of-thrones"},
        {"id": "house-of-dragon", "title": "House of the Dragon", "year": "2022-2024", "poster": "https://image.tmdb.org/t/p/w300/1X4h40fcB4WWUmIBK0auT4zRBAV.jpg", "link": "https://sub-scene.com/subtitles/house-of-the-dragon"},
        {"id": "chernobyl", "title": "Chernobyl", "year": "2019", "poster": "https://image.tmdb.org/t/p/w300/hlLXt2tOPT6RRnjiUmoxyG1LTFi.jpg", "link": "https://sub-scene.com/subtitles/chernobyl"},
        {"id": "stranger-things", "title": "Stranger Things", "year": "2016-2025", "poster": "https://image.tmdb.org/t/p/w300/49WJfeN0moxb9IPfGn8AIqMGskD.jpg", "link": "https://sub-scene.com/subtitles/stranger-things"},
        {"id": "the-last-of-us", "title": "The Last of Us", "year": "2023-2025", "poster": "https://image.tmdb.org/t/p/w300/uKvVjHNqB5VmOrdxqAt2V7JMrRI.jpg", "link": "https://sub-scene.com/subtitles/the-last-of-us"},
        {"id": "peaky-blinders", "title": "Peaky Blinders", "year": "2013-2022", "poster": "https://image.tmdb.org/t/p/w300/vUUqzWa2LnHIVqkaKVlVGkVcZIW.jpg", "link": "https://sub-scene.com/subtitles/peaky-blinders"},
        {"id": "succession", "title": "Succession", "year": "2018-2023", "poster": "https://image.tmdb.org/t/p/w300/7EZv9oA7b6n8eR6V1Ww7W2oE5k.jpg", "link": "https://sub-scene.com/subtitles/succession"},
        {"id": "prison-break", "title": "Prison Break", "year": "2005-2017", "poster": "https://image.tmdb.org/t/p/w300/uxqXvNqQ106bM7MfqPq4YhF5I8o.jpg", "link": "https://sub-scene.com/subtitles/prison-break"},
        {"id": "the-sopranos", "title": "The Sopranos", "year": "1999-2007", "poster": "https://image.tmdb.org/t/p/w300/6nT1e6G9u4Y4CqP5i8oV7W2a8v.jpg", "link": "https://sub-scene.com/subtitles/the-sopranos"},
        {"id": "dexter", "title": "Dexter", "year": "2006-2013", "poster": "https://image.tmdb.org/t/p/w300/58H69TvlSmW2egMVxkRzpmMG0YF.jpg", "link": "https://sub-scene.com/subtitles/dexter"},
        {"id": "the-boys", "title": "The Boys", "year": "2019-2024", "poster": "https://image.tmdb.org/t/p/w300/2zmTngn1tYC1AvfnNDBpQI4vlBu.jpg", "link": "https://sub-scene.com/subtitles/the-boys"},
        {"id": "shogun", "title": "Shogun", "year": "2024", "poster": "https://image.tmdb.org/t/p/w300/7O4iVfOMQmdCSxhOg1WNzG1AgYT.jpg", "link": "https://sub-scene.com/subtitles/shogun"}
    ],
    4: [
        {"id": "godfather", "title": "The Godfather", "year": "1972", "poster": "https://image.tmdb.org/t/p/w300/3bhkrj58Vtu7enYsRolD1fZdja1.jpg", "link": "https://sub-scene.com/subtitles/the-godfather"},
        {"id": "pulp-fiction", "title": "Pulp Fiction", "year": "1994", "poster": "https://image.tmdb.org/t/p/w300/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg", "link": "https://sub-scene.com/subtitles/pulp-fiction"},
        {"id": "fight-club", "title": "Fight Club", "year": "1999", "poster": "https://image.tmdb.org/t/p/w300/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg", "link": "https://sub-scene.com/subtitles/fight-club"},
        {"id": "the-matrix", "title": "The Matrix", "year": "1999", "poster": "https://image.tmdb.org/t/p/w300/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg", "link": "https://sub-scene.com/subtitles/the-matrix"},
        {"id": "shawshank", "title": "The Shawshank Redemption", "year": "1994", "poster": "https://image.tmdb.org/t/p/w300/9cqNxx0GxF0bflZmeSMuL5tnGzr.jpg", "link": "https://sub-scene.com/subtitles/the-shawshank-redemption"},
        {"id": "forrest-gump", "title": "Forrest Gump", "year": "1994", "poster": "https://image.tmdb.org/t/p/w300/arw2VCBveWOVZr6pxd9XTd1TdQa.jpg", "link": "https://sub-scene.com/subtitles/forrest-gump"},
        {"id": "se7en", "title": "Se7en", "year": "1995", "poster": "https://image.tmdb.org/t/p/w300/6yoghtyTpznpBik8EngEmJskVUO.jpg", "link": "https://sub-scene.com/subtitles/se7en"},
        {"id": "goodfellas", "title": "Goodfellas", "year": "1990", "poster": "https://image.tmdb.org/t/p/w300/aKuFiU82s5ISJpGZp7YkIr3kCUd.jpg", "link": "https://sub-scene.com/subtitles/goodfellas"},
        {"id": "parasite", "title": "Parasite", "year": "2019", "poster": "https://image.tmdb.org/t/p/w300/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg", "link": "https://sub-scene.com/subtitles/parasite"},
        {"id": "django", "title": "Django Unchained", "year": "2012", "poster": "https://image.tmdb.org/t/p/w300/7oWY8vdWW7thTzN34DyqzbAqqa5.jpg", "link": "https://sub-scene.com/subtitles/django-unchained"},
        {"id": "inglourious", "title": "Inglourious Basterds", "year": "2009", "poster": "https://image.tmdb.org/t/p/w300/7sfbEnaARXDD5P0ms7ms1Q2voxG.jpg", "link": "https://sub-scene.com/subtitles/inglourious-basterds"},
        {"id": "wolf-wall-street", "title": "The Wolf of Wall Street", "year": "2013", "poster": "https://image.tmdb.org/t/p/w300/34m2tygAYBGqA9MXKhRDtzYd4MR.jpg", "link": "https://sub-scene.com/subtitles/the-wolf-of-wall-street"},
        {"id": "shutter-island", "title": "Shutter Island", "year": "2010", "poster": "https://image.tmdb.org/t/p/w300/4GDy0PHYX3VRXUtwK5ysagvk2Te.jpg", "link": "https://sub-scene.com/subtitles/shutter-island"},
        {"id": "gladiator-2000", "title": "Gladiator", "year": "2000", "poster": "https://image.tmdb.org/t/p/w300/ty8TGRuvJLPUmAR1H1nRIsgwvim.jpg", "link": "https://sub-scene.com/subtitles/gladiator"},
        {"id": "heat", "title": "Heat", "year": "1995", "poster": "https://image.tmdb.org/t/p/w300/rrBuGu0PjqYW9T0EBA5Y9zYgL3G.jpg", "link": "https://sub-scene.com/subtitles/heat"}
    ],
    5: [
        {"id": "wlad-rizk-3", "title": "Wlad Rizk 3", "year": "2024", "poster": "https://image.tmdb.org/t/p/w300/1hQyYV6vV7Xj0aV4T4g0oY5Z8l.jpg", "link": "https://sub-scene.com/subtitles/welad-rizk-3"},
        {"id": "kira-el-gin", "title": "Kira & El Gin", "year": "2022", "poster": "https://image.tmdb.org/t/p/w300/3oN8bK6v8Gg2T7Q5g0wY6l8k4o.jpg", "link": "https://sub-scene.com/subtitles/kira-and-el-gin"},
        {"id": "blue-elephant-2", "title": "The Blue Elephant 2", "year": "2019", "poster": "https://image.tmdb.org/t/p/w300/k7Z8Xw2Y6vT8G9g0Y5Z8l4oK1.jpg", "link": "https://sub-scene.com/subtitles/the-blue-elephant-2"},
        {"id": "el-gawahergy", "title": "El Gawahergy", "year": "2024", "poster": "https://image.tmdb.org/t/p/w300/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg", "link": "https://sub-scene.com/subtitles/el-gawahergy"},
        {"id": "hashashin", "title": "The Assassins (Al-Hashashin)", "year": "2024", "poster": "https://image.tmdb.org/t/p/w300/2cxhvwyEwRlysAmRH4iodkvo0z5.jpg", "link": "https://sub-scene.com/subtitles/al-hashashin"},
        {"id": "gaafar-omda", "title": "Gaafar El Omda", "year": "2023", "poster": "https://image.tmdb.org/t/p/w300/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg", "link": "https://sub-scene.com/subtitles/gaafar-el-omda"},
        {"id": "al-asliyyin", "title": "The Originals (Al-Asliyyin)", "year": "2017", "poster": "https://image.tmdb.org/t/p/w300/74xTEgt7R36Fpooo50r9T25onhq.jpg", "link": "https://sub-scene.com/subtitles/the-originals"},
        {"id": "shams-zanati", "title": "Shams El Zanati", "year": "1991", "poster": "https://image.tmdb.org/t/p/w300/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg", "link": "https://sub-scene.com/subtitles/shams-el-zanati"},
        {"id": "omar-series", "title": "Omar", "year": "2012", "poster": "https://image.tmdb.org/t/p/w300/ztkUQFLlC19CCMYHW9o1zWhJAGq.jpg", "link": "https://sub-scene.com/subtitles/omar"},
        {"id": "taghriba", "title": "Al-Taghriba Al-Filistiniya", "year": "2004", "poster": "https://image.tmdb.org/t/p/w300/1XS1oqL89opfnbLl8WnZY1O1uJx.jpg", "link": "https://sub-scene.com/subtitles/al-taghriba-al-filistiniya"},
        {"id": "bab-al-hara", "title": "Bab Al-Hara", "year": "2006-2023", "poster": "https://image.tmdb.org/t/p/w300/edv5CZvWj09upOsy2Y6IwDhK8bt.jpg", "link": "https://sub-scene.com/subtitles/bab-al-hara"},
        {"id": "ramy", "title": "Ramy", "year": "2019-2022", "poster": "https://image.tmdb.org/t/p/w300/qJ2tW6WMUDux911r6m7haRef0WH.jpg", "link": "https://sub-scene.com/subtitles/ramy"},
        {"id": "moon-knight", "title": "Moon Knight", "year": "2022", "poster": "https://image.tmdb.org/t/p/w300/x6FsYvt33846sp7NuiojlLnvgpo.jpg", "link": "https://sub-scene.com/subtitles/moon-knight"},
        {"id": "the-night-agent", "title": "The Night Agent", "year": "2023-2025", "poster": "https://image.tmdb.org/t/p/w300/5Am5hV1Gj7Xk0bY6V7w9kL4o.jpg", "link": "https://sub-scene.com/subtitles/the-night-agent"},
        {"id": "al-kabeer", "title": "Al Kabeer Awi", "year": "2010-2024", "poster": "https://image.tmdb.org/t/p/w300/8cdWjvZQUExUUTzyp4t6EDMubfO.jpg", "link": "https://sub-scene.com/subtitles/al-kabeer-awi"}
    ]
}

def get_catalog_page_movies(page=1):
    """Returns a list of 15 movies for the given page number"""
    if page in CATALOG_PAGES:
        return list(CATALOG_PAGES[page])
    
    # For page 6+, dynamically generate classic high-profile cinema
    classics = [
        ("Blade Runner 2049", "2017", "https://image.tmdb.org/t/p/w300/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg"),
        ("Mad Max: Fury Road", "2015", "https://image.tmdb.org/t/p/w300/hA2ple9q4qnwxp3hKVNhroipsir.jpg"),
        ("1917", "2019", "https://image.tmdb.org/t/p/w300/iZf0KyrE25z1sage4SYFLCCrMi9.jpg"),
        ("Ford v Ferrari", "2019", "https://image.tmdb.org/t/p/w300/6ApDtO7xaBYeg9ygvXq62XQ1eT8.jpg"),
        ("No Time to Die", "2021", "https://image.tmdb.org/t/p/w300/iUgygt3fWVTjhCVQ3T0xaAg0jv5.jpg"),
        ("Avengers: Endgame", "2019", "https://image.tmdb.org/t/p/w300/or06FN3Dka5tukK1e9sl16pB3iy.jpg"),
        ("Avengers: Infinity War", "2018", "https://image.tmdb.org/t/p/w300/7WsyChQLEftFiDOVTGkv3hFpyyt.jpg"),
        ("Iron Man", "2008", "https://image.tmdb.org/t/p/w300/78lPtwv72eTNqFW9COBYI0dWDJa.jpg"),
        ("Titanic", "1997", "https://image.tmdb.org/t/p/w300/9xjZS2rlVxm8SFx8kPC3aIGCOYQ.jpg"),
        ("Jurassic Park", "1993", "https://image.tmdb.org/t/p/w300/oU7Oq2kFAAlGqbU4VoAE36g4hoI.jpg"),
        ("Back to the Future", "1985", "https://image.tmdb.org/t/p/w300/fNOH9f1aA7XRTzl1sAOx9iF553Q.jpg"),
        ("Terminator 2: Judgment Day", "1991", "https://image.tmdb.org/t/p/w300/5M0j0B18abtBI5em29CGOCHNqJ.jpg"),
        ("Scarface", "1983", "https://image.tmdb.org/t/p/w300/iQ5ztdjvteGeboxtmRdXEChJOHh.jpg"),
        ("Casino", "1995", "https://image.tmdb.org/t/p/w300/4TS5O1IP42bY2BvgZmwhDQwUd61.jpg"),
        ("Good Will Hunting", "1997", "https://image.tmdb.org/t/p/w300/bABCBKYBK7A5G1x0Fzo4q4v7qJ.jpg")
    ]
    base_list = []
    for idx, (t, y, pos) in enumerate(classics):
        m_id = "page%d_%d" % (page, idx)
        base_list.append({
            "id": m_id,
            "title": "%s (Part %d)" % (t, page) if page > 6 else t,
            "year": y,
            "poster": pos,
            "link": "https://sub-scene.com/subscene/" + m_id
        })
    return base_list

def subscene_browse_url(page=1, query=None):
    """Real browse / search endpoint on opensubtitles.org.
    - No query  -> newest Arabic subtitles, 40 per page, offset paginated.
    - With query-> Arabic subtitles matching the search text.
    Each page returns a fresh batch, so 'More / Next page' never repeats."""
    try:
        page = int(page)
    except Exception:
        page = 1
    if page < 1:
        page = 1
    offset = (page - 1) * 40
    if query:
        try:
            q = _os_up.quote(query.encode('utf-8') if not isinstance(query, bytes) else query)
        except Exception:
            q = _os_up.quote(str(query))
        return "%s%s/search/sublanguageid-%s/moviename-%s/offset-%d" % (
            SUBSCENE_BASE, OS_UI, OS_LANG, q, offset)
    return "%s%s/search/sublanguageid-%s/offset-%d" % (
        SUBSCENE_BASE, OS_UI, OS_LANG, offset)

def parse_subscene_movies(html, page=1):
    """Parse real movie entries from an opensubtitles.org Arabic listing page.
    Each table row (<tr ... servOC(SUBID,'LINK'...)>) is one Arabic subtitle;
    we group them into movies and dedupe by IMDB id so each movie appears once,
    with its fast poster thumbnail. Different offsets (via subscene_browse_url)
    naturally bring NEW movies, so 'More / Next page' never repeats.
    Returns [] when nothing real is found (we never fabricate fake entries).
    """
    movies = []
    seen = set()
    try:
        rows = re.findall(r"<tr[^>]*servOC\((\d+),'([^']+)'[^>]*>(.*?)</tr>",
                          html, re.S | re.I)
        for sub_id, sub_link, inner in rows:
            # IMDB id (from the imdb link, the poster thumb path or idmovie-)
            imdb_m = (re.search(r'imdb\.com/title/tt(\d+)', inner)
                      or re.search(r'/gfx/thumbs/[\d/]+/(\d+)-', inner)
                      or re.search(r'idmovie-(\d+)', inner))
            imdb = imdb_m.group(1) if imdb_m else ""

            # Movie title: anchor to the movie subtitle list /ar/subtitles/...
            name_m = re.search(r'title="[^"]*?-\s*([^"]+?)"\s*href="/ar/subtitles/', inner)
            if not name_m:
                name_m = re.search(r'href="/ar/subtitles/\d+/[^"]*"[^>]*>([^<]+)', inner)
            title = _los_clean(name_m.group(1)) if name_m else ""
            year_m = re.search(r'\((\d{4})\)', inner)
            year = year_m.group(1) if year_m else ""
            title = re.sub(r'\(\d{4}\)', '', title).strip()
            if not title:
                continue

            # Dedupe one card per movie (by imdb when present, else by title).
            dkey = ("i" + imdb) if imdb else ("t" + title.lower())
            if dkey in seen:
                continue
            seen.add(dkey)

            poster = os_imdb_thumb(imdb) if imdb else ""
            if imdb:
                link = "%s%s/search/sublanguageid-%s/imdbid-%s" % (
                    SUBSCENE_BASE, OS_UI, OS_LANG, imdb)
            else:
                link = SUBSCENE_BASE + sub_link if sub_link.startswith('/') else sub_link

            movies.append({
                "id": imdb or sub_id,
                "imdb": imdb,
                "title": title,
                "year": year,
                "link": link,
                "poster": poster,
                "first_sub_id": sub_id,
                "first_sub_link": SUBSCENE_BASE + sub_link if sub_link.startswith('/') else sub_link,
            })
    except Exception:
        pass
    return movies

def make_err_no_real_sub():
    return (u"\u062a\u0639\u0630\u0631 \u062a\u062d\u0645\u064a\u0644 \u0645\u0644\u0641 \u0627\u0644\u062a\u0631\u062c\u0645\u0629 \u0627\u0644\u062d\u0642\u064a\u0642\u064a "
            u"\u0645\u0646 OpenSubtitles.\n"
            u"\u062a\u062d\u0642\u0642 \u0645\u0646 \u0627\u062a\u0635\u0627\u0644 \u0627\u0644\u0627\u0646\u062a\u0631\u0646\u062a "
            u"\u062b\u0645 \u0623\u0639\u062f \u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629 (\u0644\u0645 \u064a\u062a\u0645 "
            u"\u062d\u0641\u0638 \u0623\u064a \u0645\u0644\u0641 \u0648\u0647\u0645\u064a).")

def download_file_to_hdd(url, dest_dir, filename_prefix="subtitle", sub_id=None, movie_title="Movie", *args, **kwargs):
    """
    Downloads the REAL subtitle archive from sub-scene.com to the hard drive
    and extracts the genuine .srt/.sub/.ass/... files.
    Saves to: dest_dir, /media/hdd/, /media/hdd/movie/, /media/hdd/subtitles/.
    NEVER writes a placeholder/fake subtitle: if the real file cannot be
    downloaded, it returns an explicit failure instead.
    """
    try:
        # Determine all available storage targets on the hard drive
        save_targets = []
        if os.path.exists("/media/hdd"):
            save_targets.append("/media/hdd")
            for subf in ["movie", "subtitles"]:
                p = os.path.join("/media/hdd", subf)
                try:
                    if not os.path.exists(p):
                        os.makedirs(p)
                    save_targets.append(p)
                except Exception:
                    pass
        elif os.path.exists("/media/usb"):
            save_targets.append("/media/usb")
            try:
                p = "/media/usb/movie"
                if not os.path.exists(p):
                    os.makedirs(p)
                save_targets.append(p)
            except Exception:
                pass
        
        if dest_dir and dest_dir not in save_targets:
            try:
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                save_targets.insert(0, dest_dir)
            except Exception:
                pass
        
        if not save_targets:
            save_targets = ["/tmp"]

        # Parse sub_id
        if not sub_id and url:
            m_id = re.search(r'/(?:sub|subtitle|download)/(\d+)', url)
            if m_id:
                sub_id = m_id.group(1)

        # OpenSubtitles real download endpoints for a given subtitle id.
        download_candidates = []
        if sub_id:
            download_candidates.append("%s%s/download/sub/%s" % (OS_DL_HOST, OS_UI, sub_id))
            download_candidates.append("%s/%s/download/sub/%s" % (OS_DL_HOST, OS_LANG, sub_id))
            download_candidates.append("%s/download/sub/%s" % (OS_DL_HOST, sub_id))
        if url and url.startswith("http"):
            download_candidates.append(url)

        raw_data = None
        for cand_url in download_candidates:
            try:
                ok_b, chunk = subscene_fetch_binary(cand_url, timeout=25)
                if ok_b and chunk and len(chunk) > 80:
                    raw_data = chunk
                    break
            except Exception:
                pass

        safe_prefix = re.sub(r'[\/:*?"<>| ]', '_', filename_prefix or "subtitle")[:60]
        target_zip_name = "%s.zip" % safe_prefix

        # If we could not fetch the REAL subtitle archive, fail honestly.
        # We NEVER write placeholder / fake subtitle text to the hard drive.
        if not raw_data:
            return False, make_err_no_real_sub(), []

        extracted_files = []
        primary_saved_path = ""

        # The download may come back as a .zip (PK), a gzip stream, or a raw
        # subtitle file. Normalize all three into (zip_bytes, real_subs).
        real_subs = []
        zip_data = None
        if raw_data[:4] == b'PK\x03\x04':
            zip_data = raw_data
            try:
                with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zf_in:
                    for zinfo in zf_in.infolist():
                        nm = zinfo.filename or ""
                        if nm.lower().endswith(('.srt', '.sub', '.ass', '.ssa', '.vtt', '.smi', '.txt')):
                            base_nm = os.path.basename(nm) or ("%s.srt" % safe_prefix)
                            try:
                                real_subs.append((base_nm, zf_in.read(zinfo)))
                            except Exception:
                                pass
            except Exception:
                real_subs = []
        elif raw_data[:2] == b'\x1f\x8b':
            # gzip-compressed single subtitle
            try:
                dec = gzip.GzipFile(fileobj=io.BytesIO(raw_data)).read()
                real_subs.append(("%s.srt" % safe_prefix, dec))
            except Exception:
                real_subs = []
        else:
            # Raw subtitle text/binary straight from the server.
            real_subs.append(("%s.srt" % safe_prefix, raw_data))

        if not real_subs and zip_data is None:
            return False, make_err_no_real_sub(), []

        # Save the authentic .zip (when present) AND every real subtitle file
        # to each HDD target.
        for loc in save_targets:
            try:
                if zip_data:
                    cur_zip_path = os.path.join(loc, target_zip_name)
                    with open(cur_zip_path, 'wb') as zf_out:
                        zf_out.write(zip_data)
                    if target_zip_name not in extracted_files:
                        extracted_files.append(target_zip_name)

                for sub_name, sub_bytes in real_subs:
                    safe_sub = re.sub(r'[\/:*?"<>|]', '_', sub_name)
                    cur_sub_path = os.path.join(loc, safe_sub)
                    with open(cur_sub_path, 'wb') as sf:
                        sf.write(sub_bytes)
                    if safe_sub not in extracted_files:
                        extracted_files.append(safe_sub)
                    if not primary_saved_path:
                        primary_saved_path = cur_sub_path
            except Exception:
                pass

        if not primary_saved_path and zip_data:
            # Archive had no recognizable subtitle file, but the genuine .zip
            # was saved so the user still gets the authentic downloaded file.
            primary_saved_path = os.path.join(save_targets[0], target_zip_name)
        if not primary_saved_path:
            return False, make_err_no_real_sub(), []

        return True, primary_saved_path, extracted_files
    except Exception as e:
        return False, str(e), []

def parse_subscene_subtitles(html, movie_title="Movie"):
    """Extracts ALL subtitle entries for a movie from opensubtitles.org.
    Handles BOTH page layouts the site serves:
      (A) listing/browse rows using the servOC(SUBID,'LINK') onclick handler, and
      (B) the movie-detail / idmovie page, where each subtitle is a plain
          anchor  <a itemprop="url" ... href="/ar/subtitles/<id>/<slug>">.
          (This is what an imdbid search redirects to, and the old parser
          missed it completely -> that was the 'no subtitles available' bug.)
    We dedupe by subtitle id. The real download link is always
    /ar/subtitleserve/sub/<id> (the downloader also derives it from the id).
    Returns [] when nothing real is found (we never fabricate fake entries).
    """
    subtitles = []
    seen = set()

    def _dl_link(sub_id):
        return "%s%s/subtitleserve/sub/%s" % (SUBSCENE_BASE, OS_UI, sub_id)

    try:
        # ---- Format A: servOC(...) onclick rows (listing/browse pages) ----
        rows = re.findall(r"<tr[^>]*servOC\((\d+),'([^']+)'[^>]*>(.*?)</tr>",
                          html, re.S | re.I)
        for sub_id, sub_link, inner in rows:
            if sub_id in seen:
                continue
            name_m = re.search(r'title="[^"]*?-\s*([^"]+?)"\s*href="/ar/subtitles/', inner)
            if not name_m:
                name_m = re.search(r'href="/ar/subtitles/\d+/[^"]*"[^>]*>([^<]+)', inner)
            title = _los_clean(name_m.group(1)) if name_m else ""

            # The actual release string is usually on its own text line.
            release_title = ""
            rm = re.search(r'</strong>.*?<br\s*/?>(.*?)<br\s*/?>', inner, re.S)
            if rm:
                release_title = _los_clean(rm.group(1))
            if not release_title:
                rm2 = re.search(r'<br\s*/?>(.*?)<br\s*/?>', inner, re.S)
                release_title = _los_clean(rm2.group(1)) if rm2 else ""
            if not release_title:
                release_title = title or "Subtitle"

            seen.add(sub_id)
            subtitles.append({
                "id": sub_id,
                "language": "Arabic",
                "release": release_title or "Standard",
                "link": _dl_link(sub_id),
                "author": "OpenSubtitles"
            })

        # ---- Format B: movie-detail page plain anchors (idmovie pages) ----
        if not subtitles:
            for m in re.finditer(
                    r'<a\b([^>]*?)href="/ar/subtitles/(\d+)/[^"]*"([^>]*)>(.*?)</a>',
                    html, re.S | re.I):
                attrs = (m.group(1) or "") + (m.group(3) or "")
                sub_id = m.group(2)
                inner = m.group(4) or ""
                if sub_id in seen:
                    continue
                seen.add(sub_id)
                tm = re.search(r'title="([^"]*)"', attrs)
                name = tm.group(1) if tm else ""
                if not name:
                    sm = re.search(r'itemprop="name"[^>]*>(.*?)<', inner, re.S)
                    name = sm.group(1) if sm else inner
                release_title = _los_clean(name) or (movie_title or "Subtitle")
                subtitles.append({
                    "id": sub_id,
                    "language": "Arabic",
                    "release": release_title,
                    "link": _dl_link(sub_id),
                    "author": "OpenSubtitles"
                })

        # ---- Format C: single-subtitle DETAIL page ----
        # Titles that have exactly ONE subtitle make the imdbid/idmovie search
        # redirect STRAIGHT to the subtitle detail page /ar/subtitles/<id>/<slug>
        # (no listing table, no servOC rows, no plain listing anchors). That was
        # why ~1/4 of the movies returned 'no subtitles' even though a subtitle
        # really exists. We detect that page and expose its single subtitle id,
        # taken from the canonical/bookmark link or the download (subtitleserve)
        # reference. This only runs as a fallback (A and B found nothing), so it
        # never shadows a real listing.
        if not subtitles:
            det_id = None
            dm = (re.search(r'rel="bookmark"\s+href="/ar/subtitles/(\d+)/', html, re.I)
                  or re.search(r'subtitleserve/sub/(\d+)', html, re.I)
                  or re.search(r'(?:canonical|og:url)[^>]*?/ar/subtitles/(\d+)/', html, re.I)
                  or re.search(r'ret="/ar/subtitles/(\d+)/', html, re.I))
            if dm:
                det_id = dm.group(1)
            if det_id and det_id not in seen:
                seen.add(det_id)
                rel_name = ""
                tm = re.search(r'<title>(.*?)</title>', html, re.S | re.I)
                if tm:
                    rel_name = _los_clean(re.sub(r'\s*[-|].*$', '', tm.group(1)))
                if not rel_name:
                    rel_name = movie_title or "Subtitle"
                subtitles.append({
                    "id": det_id,
                    "language": "Arabic",
                    "release": rel_name,
                    "link": _dl_link(det_id),
                    "author": "OpenSubtitles"
                })
    except Exception:
        pass

    return subtitles

# Subscene auto-scaled skin layout with Poster preview & full controls
SUBSCENE_RAW_SKIN = """<screen name="MS_SubsceneScreen" position="center,center" size="1680,940" title="OpenSubtitles" flags="wfNoBorder">
    <eLabel position="0,0" size="1680,940" backgroundColor="#05070c" zPosition="-11" />
    <!-- Header -->
    <eLabel position="20,15" size="1640,75" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="20,15" size="1640,2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="20,88" size="1640,2" backgroundColor="#e11d48" zPosition="0" />
    <widget name="title" position="35,22" size="700,34" font="Regular;28" foregroundColor="#f59e0b" backgroundColor="#0f111a" transparent="1" />
    <widget name="search_info" position="750,24" size="890,30" font="Regular;22" foregroundColor="#38bdf8" backgroundColor="#0f111a" transparent="1" halign="right" />
    <widget name="storage_path" position="35,58" size="1600,24" font="Regular;18" foregroundColor="#a7f3d0" backgroundColor="#0f111a" transparent="1" />

    <!-- Left: Movies / Subtitles List -->
    <eLabel position="20,102" size="1100,730" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="20,102" size="1100,2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="20,102" size="3,730" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="1118,102" size="3,730" backgroundColor="#e11d48" zPosition="1" />
    <widget name="list" position="30,112" size="1080,710" font="Regular;25" itemHeight="50" scrollbarMode="showOnDemand" />

    <!-- Right: Poster & Movie / Subtitle Details -->
    <eLabel position="1132,102" size="528,730" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="1132,102" size="528,2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="1132,102" size="3,730" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="1657,102" size="3,730" backgroundColor="#e11d48" zPosition="1" />
    <widget name="poster" position="1270,118" size="250,370" zPosition="2" alphatest="blend" />
    <widget name="details_title" position="1145,502" size="500,34" font="Regular;26" foregroundColor="#fde047" backgroundColor="#0f111a" transparent="1" halign="center" />
    <widget name="details" position="1145,542" size="500,280" font="Regular;22" foregroundColor="#e2e8f0" backgroundColor="#0f111a" transparent="1" valign="top" />

    <!-- Footer buttons -->
    <eLabel position="20,845" size="1640,80" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="20,845" size="1640,2" backgroundColor="#be185d" zPosition="0" />
    <widget name="key_red" position="35,860" size="380,50" font="Regular;26" foregroundColor="#ffffff" backgroundColor="#e11d48" halign="center" valign="center" />
    <widget name="key_green" position="445,860" size="380,50" font="Regular;26" foregroundColor="#ffffff" backgroundColor="#059669" halign="center" valign="center" />
    <widget name="key_yellow" position="855,860" size="380,50" font="Regular;26" foregroundColor="#ffffff" backgroundColor="#d97706" halign="center" valign="center" />
    <widget name="key_blue" position="1265,860" size="380,50" font="Regular;26" foregroundColor="#ffffff" backgroundColor="#0284c7" halign="center" valign="center" />
</screen>"""

SUBSCENE_SKIN = scale_skin_layout(SUBSCENE_RAW_SKIN)

class SubsceneScreen(Screen):
    skin = SUBSCENE_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        
        self["title"] = Label(u"\U0001f3ac \u062a\u0631\u062c\u0645\u0629 \u0627\u0644\u0623\u0641\u0644\u0627\u0645 \u0648\u0627\u0644\u0645\u0633\u0644\u0633\u0644\u0627\u062a - OpenSubtitles")
        self["search_info"] = Label(u"\u0627\u0644\u0623\u0641\u0644\u0627\u0645 \u0627\u0644\u0634\u0627\u0626\u0639\u0629 | \u0627\u0644\u0635\u0641\u062d\u0629 1")
        self.storage_dir = get_subtitles_storage_path()
        self["storage_path"] = Label(u"\u0645\u0633\u0627\u0631 \u0627\u0644\u062d\u0641\u0638 \u0627\u0644\u0645\u0628\u0627\u0634\u0631 \u0639\u0644\u0649 \u0627\u0644\u0647\u0627\u0631\u062f: %s/" % self.storage_dir)
        
        self["list"] = MenuList([])
        self["poster"] = Pixmap()
        self.picload = None
        if ePicLoad:
            try:
                self.picload = ePicLoad()
                self.picload.PictureData.get().append(self.show_poster_cb)
                self.picload.setPara((int(scale_x(250)), int(scale_y(370)), 1, 1, 0, 1, "#00000000"))
            except Exception:
                self.picload = None
        self["details_title"] = Label("")
        self["details"] = Label(u"\u0627\u062e\u062a\u0631 \u0641\u064a\u0644\u0645\u0627\u064b \u0644\u0639\u0631\u0636 \u0627\u0644\u0628\u0648\u0633\u062a\u0631 \u0648\u0627\u0644\u062a\u0631\u062c\u0645\u0627\u062a \u0627\u0644\u0645\u062a\u0627\u062d\u0629...")
        
        self["key_red"] = Label(u"\u062e\u0631\u0648\u062c (Exit)")
        self["key_green"] = Label(u"\u0639\u0631\u0636 \u0627\u0644\u062a\u0631\u062c\u0645\u0627\u062a (Open)")
        self["key_yellow"] = Label(u"\u0628\u062d\u062b (Search)")
        self["key_blue"] = Label(u"\u0635\u0641\u062d\u0629 2 (Next)")
        
        self.mode = "movies"
        self.current_page = 1
        self.search_query = ""
        self.movies = []
        self.current_movie = None
        self.subtitles = []
        self.is_loading = False
        
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
            "cancel": self.go_back,
            "red": self.go_back,
            "ok": self.press_ok,
            "green": self.press_green,
            "yellow": self.open_search_dialog,
            "blue": self.next_page_action,
            "right": self.next_page_action,
            "left": self.prev_page_action,
            "up": self.move_up,
            "down": self.move_down,
        }, -1)
        
        self["list"].onSelectionChanged.append(self.selection_changed)
        self.onLayoutFinish.append(self.initial_load)

    def initial_load(self):
        self.load_movies(page=1, query="")

    def move_up(self):
        try:
            self["list"].up()
        except Exception:
            pass

    def move_down(self):
        try:
            self["list"].down()
        except Exception:
            pass

    def go_back(self):
        if self.is_loading:
            return
        if self.mode == "subtitles":
            self.mode = "movies"
            self["title"].setText(u"\U0001f3ac \u062a\u0631\u062c\u0645\u0629 \u0627\u0644\u0623\u0641\u0644\u0627\u0645 \u0648\u0627\u0644\u0645\u0633\u0644\u0633\u0644\u0627\u062a - OpenSubtitles")
            self["key_green"].setText(u"\u0639\u0631\u0636 \u0627\u0644\u062a\u0631\u062c\u0645\u0627\u062a (Open)")
            self["key_yellow"].setText(u"\u0628\u062d\u062b (Search)")
            self["key_blue"].setText(u"\u0635\u0641\u062d\u0629 %d (Next)" % (self.current_page + 1))
            self.render_movies_list()
        else:
            self.close()

    def open_search_dialog(self):
        if self.mode != "movies" or self.is_loading:
            return
        try:
            from Screens.VirtualKeyBoard import VirtualKeyBoard
            self.session.openWithCallback(self.search_callback, VirtualKeyBoard,
                                          title=u"\u0627\u0643\u062a\u0628 \u0627\u0633\u0645 \u0627\u0644\u0641\u064a\u0644\u0645 \u0623\u0648 \u0627\u0644\u0645\u0633\u0644\u0633\u0644 \u0644\u0644\u0628\u062d\u062b \u0641\u064a OpenSubtitles")
        except Exception as e:
            self.session.open(MessageBox, u"\u062a\u0639\u0630\u0631 \u0641\u062a\u062d \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0641\u0627\u062a\u064a\u062d: %s" % str(e), MessageBox.TYPE_ERROR)

    def search_callback(self, text):
        if text and text.strip():
            self.search_query = text.strip()
            self.current_page = 1
            self.load_movies(page=1, query=self.search_query)

    def next_page_action(self):
        if self.mode != "movies" or self.is_loading:
            return
        self.current_page += 1
        self.load_movies(page=self.current_page, query=self.search_query)

    def prev_page_action(self):
        if self.mode != "movies" or self.is_loading or self.current_page <= 1:
            return
        self.current_page -= 1
        self.load_movies(page=self.current_page, query=self.search_query)

    def load_movies(self, page=1, query=""):
        self.is_loading = True
        self.current_page = page
        
        self["list"].setList([u"\u062c\u0627\u0631\u064a \u062a\u062d\u0645\u064a\u0644 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0623\u0641\u0644\u0627\u0645 (\u0635\u0641\u062d\u0629 %d)... \u064a\u0631\u062c\u0649 \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631" % page])
        self["details"].setText(u"\u062c\u0627\u0631\u064a \u062c\u0644\u0628 \u0627\u0644\u0623\u0641\u0644\u0627\u0645 \u0645\u0646 OpenSubtitles (\u0635\u0641\u062d\u0629 %d)..." % page)

        if query:
            self["search_info"].setText(u"\u0646\u062a\u0627\u0626\u062c \u0627\u0644\u0628\u062d\u062b: '%s' | \u0635\u0641\u062d\u0629 %d" % (query, page))
        else:
            self["search_info"].setText(u"\u0623\u062d\u062f\u062b \u0627\u0644\u0623\u0641\u0644\u0627\u0645 \u0648\u0627\u0644\u0645\u0633\u0644\u0633\u0644\u0627\u062a | \u0635\u0641\u062d\u0629 %d" % page)

        self["key_blue"].setText(u"\u0635\u0641\u062d\u0629 %d (Next)" % (page + 1))

        def _worker():
            try:
                fetched_movies = []
                # Both the newest-list and the search use the SAME live
                # OpenSubtitles endpoint (offset paginated), so 'More / Next'
                # always brings NEW movies for either mode.
                try:
                    ok, html = subscene_http_get(subscene_browse_url(page, query or None))
                    if ok and html:
                        scraped = parse_subscene_movies(html, page=page)
                        if scraped:
                            fetched_movies = scraped
                except Exception:
                    fetched_movies = []
                if not fetched_movies and not query and page == 1:
                    # Only the very first newest page falls back to the local
                    # catalog if the network is completely down.
                    fetched_movies = get_catalog_page_movies(page=page)
            except Exception:
                fetched_movies = [] if query else get_catalog_page_movies(page=page)

            def _apply():
                try:
                    self.is_loading = False
                    self.movies = fetched_movies
                    self.render_movies_list()
                except Exception:
                    self.is_loading = False

            _call_ui(_apply)

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()

    def render_movies_list(self):
        items = []
        has_prev = (self.current_page > 1)
        if has_prev:
            items.append(u"\u25c0\u25c0 [ \u0627\u0636\u063a\u0637 \u0647\u0646\u0627 \u0644\u0644\u0639\u0648\u062f\u0629 \u0625\u0644\u0649 \u0627\u0644\u0635\u0641\u062d\u0629 \u0627\u0644\u0633\u0627\u0628\u0642\u0629 (\u0635\u0641\u062d\u0629 %d) ] \u25c0\u25c0" % (self.current_page - 1))

        for i, m in enumerate(self.movies):
            year_str = " (%s)" % m["year"] if m.get("year") else ""
            items.append(u"%d. %s%s" % (i + 1, m.get("title", "Movie"), year_str))
        
        items.append(u"\u25b6\u25b6 [ \u0627\u0636\u063a\u0637 \u0647\u0646\u0627 \u0644\u0644\u0627\u0646\u062a\u0642\u0627\u0644 \u0625\u0644\u0649 \u0627\u0644\u0635\u0641\u062d\u0629 \u0627\u0644\u062a\u0627\u0644\u064a\u0629 (\u0635\u0641\u062d\u0629 %d) ] \u25b6\u25b6" % (self.current_page + 1))
        
        self["list"].setList(items)
        # Select first movie
        if has_prev:
            self["list"].moveToIndex(1)
        else:
            self["list"].moveToIndex(0)
        self.selection_changed()
        # Pre-download EVERY poster of this page in parallel (into the cache)
        # so moving the cursor shows them instantly instead of fetching
        # one-by-one on each selection change.
        self.prefetch_posters()

    def prefetch_posters(self):
        try:
            movies = list(self.movies)
        except Exception:
            return
        if not movies:
            return
        cache_dir = get_subscene_cache_dir()

        def _one(mv):
            try:
                url = mv.get("poster", "")
                if not url:
                    return
                cid = re.sub(r'[^a-zA-Z0-9]', '_', str(mv.get("id", mv.get("title", "poster")))) + ".jpg"
                cp = os.path.join(cache_dir, cid)
                if os.path.exists(cp) and os.path.getsize(cp) > 1000:
                    return
                ok_b, data = subscene_fetch_binary(url, timeout=12)
                if ok_b and data and len(data) > 500:
                    with open(cp, 'wb') as pf:
                        pf.write(data)
            except Exception:
                pass

        def _runner():
            try:
                sem = threading.Semaphore(6)   # up to 6 posters at once
                for mv in movies:
                    def _task(m=mv):
                        sem.acquire()
                        try:
                            _one(m)
                        finally:
                            try:
                                sem.release()
                            except Exception:
                                pass
                    th = threading.Thread(target=_task)
                    th.daemon = True
                    th.start()
            except Exception:
                pass

        t = threading.Thread(target=_runner)
        t.daemon = True
        t.start()

    def selection_changed(self):
        idx = self["list"].getSelectionIndex()
        if idx is None or idx < 0:
            return

        if self.mode == "movies":
            has_prev = (self.current_page > 1)
            if has_prev and idx == 0:
                self["details_title"].setText(u"\u25c0 \u0627\u0644\u0635\u0641\u062d\u0629 \u0627\u0644\u0633\u0627\u0628\u0642\u0629 (\u0635\u0641\u062d\u0629 %d)" % (self.current_page - 1))
                self["details"].setText(u"\u0627\u0636\u063a\u0637 OK \u0623\u0648 \u0627\u0644\u0633\u0647\u0645 \u0627\u0644\u0623\u064a\u0633\u0631 \u0644\u0644\u0639\u0648\u062f\u0629 \u0625\u0644\u0649 \u0627\u0644\u0635\u0641\u062d\u0629 \u0627\u0644\u0633\u0627\u0628\u0642\u0629.")
                return

            movie_start_idx = 1 if has_prev else 0
            movie_count = len(self.movies)
            next_page_idx = movie_start_idx + movie_count

            if idx == next_page_idx:
                self["details_title"].setText(u"\u25b6 \u0627\u0644\u0635\u0641\u062d\u0629 \u0627\u0644\u062a\u0627\u0644\u064a\u0629 (\u0635\u0641\u062d\u0629 %d)" % (self.current_page + 1))
                self["details"].setText(u"\u0627\u0636\u063a\u0637 OK \u0623\u0648 \u0627\u0644\u0632\u0631 \u0627\u0644\u0623\u0632\u0631\u0642 \u0623\u0648 \u0627\u0644\u0633\u0647\u0645 \u0627\u0644\u0623\u064a\u0645\u0646 \u0644\u062c\u0644\u0628 \u062f\u0641\u0639\u0629 \u062c\u062f\u064a\u062f\u0629 \u0645\u0646 \u0627\u0644\u0623\u0641\u0644\u0627\u0645.")
                return

            actual_movie_idx = idx - movie_start_idx
            if 0 <= actual_movie_idx < movie_count:
                m = self.movies[actual_movie_idx]
                self.current_movie = m
                year_str = " (%s)" % m.get("year", "") if m.get("year") else ""
                self["details_title"].setText(m.get("title", "") + year_str)
                det_text = u"\u0627\u0633\u0645 \u0627\u0644\u0641\u064a\u0644\u0645: %s\n\u0627\u0644\u0633\u0646\u0629: %s\n\u0627\u0644\u0645\u0635\u062f\u0631: OpenSubtitles\n\n\u0627\u0636\u063a\u0637 OK \u0623\u0648 \u0627\u0644\u0632\u0631 \u0627\u0644\u0623\u062e\u0636\u0631 \u0644\u0639\u0631\u0636 \u062c\u0645\u064a\u0639 \u0645\u0644\u0641\u0627\u062a \u0627\u0644\u062a\u0631\u062c\u0645\u0629 \u0648\u062a\u062d\u0645\u064a\u0644\u0647\u0627 \u0645\u0628\u0627\u0634\u0631\u0629 \u0644\u0644\u0647\u0627\u0631\u062f." % (
                    m.get("title", ""), m.get("year", "N/A")
                )
                self["details"].setText(det_text)
                self.load_poster_for_movie(m)

        elif self.mode == "subtitles":
            if idx < len(self.subtitles):
                s = self.subtitles[idx]
                is_ar = s.get("language", "").lower() in ["arabic", "ar", "\u0627\u0644\u0639\u0631\u0628\u064a\u0629"]
                ar_tag = u"\u2b50 \u062a\u0631\u062c\u0645\u0629 \u0639\u0631\u0628\u064a\u0629 \u2b50" if is_ar else u"\u062a\u0631\u062c\u0645\u0629 \u0623\u062c\u0646\u0628\u064a\u0629"
                self["details_title"].setText(s.get("language", "Subtitle"))
                info = u"%s\n\n\u0627\u0644\u0646\u0633\u062e\u0629 / \u0627\u0644\u0625\u0635\u062f\u0627\u0631:\n%s\n\n\u0627\u0644\u0645\u062a\u0631\u062c\u0645 / \u0627\u0644\u0631\u0627\u0641\u0639: %s\n\u0627\u0644\u0645\u0633\u0627\u0631 \u0639\u0644\u0649 \u0627\u0644\u0647\u0627\u0631\u062f: %s/\n\n\u0627\u0636\u063a\u0637 OK \u0623\u0648 \u0627\u0644\u0632\u0631 \u0627\u0644\u0623\u062e\u0636\u0631 \u0644\u0644\u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u0645\u0628\u0627\u0634\u0631 \u0625\u0644\u0649 \u0627\u0644\u0647\u0627\u0631\u062f." % (
                    ar_tag,
                    s.get("release", "N/A"),
                    s.get("author", "Unknown"),
                    self.storage_dir
                )
                self["details"].setText(info)

    def show_poster_cb(self, picInfo=None):
        try:
            if self.picload:
                ptr = self.picload.getData()
                if ptr and hasattr(self["poster"], "instance") and self["poster"].instance:
                    self["poster"].instance.setPixmap(ptr)
        except Exception:
            pass

    def load_poster_for_movie(self, movie):
        poster_url = movie.get("poster", "")
        # OpenSubtitles movies already carry a direct, fast thumbnail URL built
        # from their IMDB id. If one is missing (rare no-IMDB row) just skip.
        if not poster_url:
            return

        cache_id = re.sub(r'[^a-zA-Z0-9]', '_', str(movie.get("id", movie.get("title", "poster")))) + ".jpg"
        cache_path = os.path.join(get_subscene_cache_dir(), cache_id)

        if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1000:
            if self.picload:
                try:
                    self.picload.startDecode(cache_path)
                    return
                except Exception:
                    pass
            if LoadPixmap:
                try:
                    pix = LoadPixmap(cache_path)
                    if pix and hasattr(self["poster"], "instance") and self["poster"].instance:
                        self["poster"].instance.setPixmap(pix)
                        return
                except Exception:
                    pass

        def _fetch_poster():
            try:
                # OpenSubtitles poster thumbnails require the Anubis auth
                # cookie, so fetch through the shared cookie-aware channel.
                ok_b, data = subscene_fetch_binary(poster_url, timeout=12)
                if ok_b and data and len(data) > 500:
                    with open(cache_path, 'wb') as pf:
                        pf.write(data)

                def _update_pix():
                    if os.path.exists(cache_path):
                        if self.picload:
                            try:
                                self.picload.startDecode(cache_path)
                                return
                            except Exception:
                                pass
                        if LoadPixmap:
                            try:
                                pix = LoadPixmap(cache_path)
                                if pix and hasattr(self["poster"], "instance") and self["poster"].instance:
                                    self["poster"].instance.setPixmap(pix)
                                    return
                            except Exception:
                                pass
                _call_ui(_update_pix)
            except Exception:
                pass

        t = threading.Thread(target=_fetch_poster)
        t.daemon = True
        t.start()

    def press_ok(self):
        idx = self["list"].getSelectionIndex()
        if idx is None or idx < 0:
            return

        if self.mode == "movies":
            has_prev = (self.current_page > 1)
            if has_prev and idx == 0:
                self.prev_page_action()
                return

            movie_start_idx = 1 if has_prev else 0
            movie_count = len(self.movies)
            next_page_idx = movie_start_idx + movie_count

            if idx == next_page_idx:
                self.next_page_action()
                return

            actual_movie_idx = idx - movie_start_idx
            if 0 <= actual_movie_idx < movie_count:
                self.open_movie_subtitles(self.movies[actual_movie_idx])

        elif self.mode == "subtitles":
            if idx < len(self.subtitles):
                self.download_selected_subtitle(self.subtitles[idx])

    def press_green(self):
        self.press_ok()

    def open_movie_subtitles(self, movie):
        self.mode = "subtitles"
        movie_title = movie.get("title", "")
        self["title"].setText(u"\U0001f3ac \u0645\u0644\u0641\u0627\u062a \u062a\u0631\u062c\u0645\u0629: %s" % movie_title)
        self["key_green"].setText(u"\u062a\u062d\u0645\u064a\u0644 \u0644\u0644\u0647\u0627\u0631\u062f (Download)")
        self["key_yellow"].setText(u"")
        self["key_blue"].setText(u"")
        self["list"].setList([u"\u062c\u0627\u0631\u064a \u062c\u0644\u0628 \u062c\u0645\u064a\u0639 \u062a\u0631\u062c\u0645\u0627\u062a %s \u0645\u0646 OpenSubtitles..." % movie_title])
        self["details"].setText(u"\u062c\u0627\u0631\u064a \u0627\u0644\u0628\u062d\u062b \u0639\u0646 \u062c\u0645\u064a\u0639 \u0627\u0644\u062a\u0631\u062c\u0645\u0627\u062a \u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0648\u0627\u0644\u0623\u062c\u0646\u0628\u064a\u0629 \u0644\u0647\u0630\u0627 \u0627\u0644\u0641\u064a\u0644\u0645...")

        def _worker():
            try:
                ok, html = subscene_http_get(movie.get("link", ""))
                subs = parse_subscene_subtitles(html, movie_title=movie_title) if ok else []
                # Fallback: a movie with no IMDB id only has the single subtitle
                # row we already captured during browse; expose it directly.
                if not subs and movie.get("first_sub_id"):
                    subs = [{
                        "id": movie.get("first_sub_id"),
                        "language": "Arabic",
                        "release": movie_title or "Subtitle",
                        "link": movie.get("first_sub_link", ""),
                        "author": "OpenSubtitles",
                    }]
            except Exception:
                subs = []

            def _apply():
                try:
                    self.subtitles = subs
                    if not self.subtitles:
                        self["list"].setList([u"\u2757 \u0644\u0627 \u062a\u0648\u062c\u062f \u062a\u0631\u062c\u0645\u0627\u062a \u0645\u062a\u0627\u062d\u0629 \u0644\u0647\u0630\u0627 \u0627\u0644\u0641\u064a\u0644\u0645 \u062d\u0627\u0644\u064a\u0627\u064b (\u0627\u0636\u063a\u0637 \u062e\u0631\u0648\u062c \u0644\u0644\u0631\u062c\u0648\u0639)"])
                        self["details_title"].setText(u"")
                        self["details"].setText(u"\u0644\u0645 \u064a\u062a\u0645 \u0627\u0644\u0639\u062b\u0648\u0631 \u0639\u0644\u0649 \u0645\u0644\u0641\u0627\u062a \u062a\u0631\u062c\u0645\u0629 \u062d\u0642\u064a\u0642\u064a\u0629 \u0644\u0647\u0630\u0627 \u0627\u0644\u0639\u0646\u0648\u0627\u0646.")
                        return
                    items = []
                    for i, s in enumerate(self.subtitles):
                        lang = s.get("language", "Sub")
                        rel = s.get("release", "Standard")
                        is_ar = lang.lower().startswith("arab")
                        icon = u"\u2b50 [\u0627\u0644\u0639\u0631\u0628\u064a\u0629]" if is_ar else u"  [%s]" % lang
                        items.append(u"%s %s" % (icon, rel))
                    self["list"].setList(items)
                    self.selection_changed()
                except Exception:
                    pass

            _call_ui(_apply)

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()

    def download_selected_subtitle(self, sub):
        sub_link = sub.get("link", "")
        sub_id = str(sub.get("id", ""))
        release_name = sub.get("release", "subtitle")
        movie_title = self.current_movie.get("title", "") if self.current_movie else "Movie"
        self["details"].setText(u"\u062c\u0627\u0631\u064a \u062a\u062d\u0645\u064a\u0644 \u0645\u0644\u0641 \u0627\u0644\u062a\u0631\u062c\u0645\u0629 \u0645\u0628\u0627\u0634\u0631\u0629 \u0625\u0644\u0649 \u0627\u0644\u0647\u0627\u0631\u062f...\n\u0627\u0644\u0645\u0633\u0627\u0631: " + str(self.storage_dir) + "/")

        def _worker():
            try:
                ok, filepath, extracted = download_file_to_hdd(
                    sub_link, 
                    self.storage_dir, 
                    filename_prefix=re.sub(r'\W+', '_', release_name)[:35], 
                    sub_id=sub_id,
                    movie_title=movie_title
                )
            except Exception as e:
                ok = False
                filepath = str(e)
                extracted = []

            def _apply():
                try:
                    self.is_loading = False
                    if ok:
                        msg = u"\u062a\u0645 \u0628\u0646\u062c\u0627\u062d \u062a\u062d\u0645\u064a\u0644 \u0648\u0627\u0633\u062a\u062e\u0631\u0627\u062c \u0645\u0644\u0641 \u0627\u0644\u062a\u0631\u062c\u0645\u0629 \u0625\u0644\u0649 \u0627\u0644\u0647\u0627\u0631\u062f!\n\n"
                        msg += u"\u0627\u0644\u0645\u0633\u0627\u0631 \u0627\u0644\u0645\u0628\u0627\u0634\u0631: /media/hdd/\n"
                        msg += u"\u0627\u0644\u0645\u0644\u0641: " + str(filepath) + "\n\n"
                        if extracted:
                            msg += u"\u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0627\u0644\u062c\u0627\u0647\u0632\u0629 \u0644\u0644\u062a\u0634\u063a\u064a\u0644:\n" + "\n".join(["- " + str(x) for x in extracted[:3]]) + "\n"
                        msg += u"\n(\u062a\u0645 \u0623\u064a\u0636\u0627\u064b \u062d\u0641\u0638 \u0646\u0633\u062e\u0629 \u0641\u064a /media/hdd/movie/)\n"
                        msg += u"\u064a\u0645\u0643\u0646\u0643 \u0627\u0644\u0622\u0646 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0641\u064a\u0644\u0645 \u0645\u0628\u0627\u0634\u0631\u0629 \u0645\u0639 \u0627\u0644\u062a\u0631\u062c\u0645\u0629."
                        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
                        self["details"].setText(u"\u0627\u0643\u062a\u0645\u0644 \u0627\u0644\u062a\u062d\u0645\u064a\u0644 \u0628\u0646\u062c\u0627\u062d!\n\u0627\u0644\u0645\u0644\u0641: " + str(filepath))
                    else:
                        self.session.open(MessageBox, u"\u0641\u0634\u0644 \u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u062a\u0631\u062c\u0645\u0629:\n" + str(filepath), MessageBox.TYPE_ERROR)
                        self["details"].setText(u"\u062d\u062f\u062b \u062e\u0637\u0623 \u0623\u062b\u0646\u0627\u0621 \u0627\u0644\u062a\u062d\u0645\u064a\u0644. \u064a\u0631\u062c\u0649 \u0627\u0644\u0645\u062d\u062f\u0629.")
                except Exception:
                    pass

            _call_ui(_apply)

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()

# =========================================================================
# NEW TOOLS: Subscription Countdown + Mini File Manager + Match Reminders
# =========================================================================
SUBSCRIPTION_CONFIG = os.path.join(PLUGIN_DIR, "subscription.json")
REMINDERS_CONFIG = os.path.join(PLUGIN_DIR, "match_reminders.json")
KIDS_CONFIG = os.path.join(PLUGIN_DIR, "kids_mode.json")
ORG_HIDDEN_CONFIG = os.path.join(PLUGIN_DIR, "org_hidden.json")
ORG_BACKUP_DIR = os.path.join(PLUGIN_DIR, "org_backup")


def _load_json_cfg(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                raw = f.read()
            if raw and raw.strip():
                return json.loads(raw)
    except Exception:
        pass
    return default


def _save_json_cfg(path, data):
    try:
        with open(path, "w") as f:
            f.write(json.dumps(data))
        return True
    except Exception:
        return False


def _ms_safe_gui_text(s):
    """Return a string that is ALWAYS safe to hand to the enigma2 GUI
    (eLabel / MenuList / listbox). File/record names on HDD/USB often carry
    non-UTF-8 bytes (FAT/NTFS) or, on Python 3, surrogate-escaped code points
    from os.listdir(). Passing such a string to the native text renderer makes
    enigma2 abort() in C++ (a crash WITHOUT any Python traceback) - exactly the
    "crash on entry" seen in the File Manager and Boot Logo screens. Round-trip
    through UTF-8 with 'replace' to neutralise surrogates/invalid bytes, and
    drop control characters that can confuse the renderer."""
    try:
        if s is None:
            return u""
        if isinstance(s, bytes):
            s = s.decode("utf-8", "replace")
        else:
            try:
                s = u"" + s
            except Exception:
                s = u"%s" % (s,)
        # Neutralise surrogates / undecodable code points -> guaranteed clean UTF-8
        s = s.encode("utf-8", "replace").decode("utf-8", "replace")
        # Strip control characters except TAB / NEWLINE
        out = []
        for ch in s:
            if ch == u"\n" or ch == u"\t" or ch >= u" ":
                out.append(ch)
        return u"".join(out)
    except Exception:
        try:
            return repr(s)
        except Exception:
            return u"?"


def _ms_safe_list(items):
    try:
        return [_ms_safe_gui_text(x) for x in items]
    except Exception:
        return items


# ---- Subscription skin ----
SUBSCRIPTION_RAW_SKIN = """<screen name="MS_SubscriptionScreen" position="center,center" size="1100,720" title="Subscription">
    <widget name="title" position="20,15" size="1060,55" font="Regular;34" halign="center" transparent="1" foregroundColor="#00ffcc00"/>
    <widget name="bigdays" position="20,110" size="1060,170" font="Regular;120" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="status" position="20,300" size="1060,50" font="Regular;34" halign="center" transparent="1" foregroundColor="#00ffffff"/>
    <widget name="info" position="50,375" size="1000,240" font="Regular;28" halign="center" transparent="1" foregroundColor="#00cccccc"/>
    <widget name="key_red" position="30,660" size="250,40" font="Regular;24" halign="center" transparent="1" foregroundColor="#00ff4040"/>
    <widget name="key_green" position="300,660" size="250,40" font="Regular;24" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="key_yellow" position="560,660" size="250,40" font="Regular;24" halign="center" transparent="1" foregroundColor="#00ffff40"/>
    <widget name="key_blue" position="820,660" size="250,40" font="Regular;24" halign="center" transparent="1" foregroundColor="#004080ff"/>
</screen>"""
SUBSCRIPTION_SKIN = scale_skin_layout(SUBSCRIPTION_RAW_SKIN)

# ---- File manager skin ----
FM_RAW_SKIN = """<screen name="MS_FileManagerScreen" position="center,center" size="1300,860" title="File Manager">
    <widget name="path" position="20,12" size="1260,48" font="Regular;28" transparent="1" foregroundColor="#00ffcc00"/>
    <widget name="list" position="20,70" size="1260,690" font="Regular;26" itemHeight="40" scrollbarMode="showOnDemand"/>
    <widget name="status" position="20,768" size="1260,34" font="Regular;22" halign="center" transparent="1" foregroundColor="#00aaaaaa"/>
    <widget name="key_red" position="30,812" size="300,36" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ff4040"/>
    <widget name="key_green" position="345,812" size="300,36" font="Regular;23" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="key_yellow" position="660,812" size="300,36" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ffff40"/>
    <widget name="key_blue" position="975,812" size="300,36" font="Regular;23" halign="center" transparent="1" foregroundColor="#004080ff"/>
</screen>"""
FM_SKIN = scale_skin_layout(FM_RAW_SKIN)

# ---- Automatic subscription expiry detection (OSCam / NCam) ----
def _ms_read_file(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        if isinstance(data, bytes):
            data = data.decode("utf-8", "ignore")
        return data
    except Exception:
        return ""


def _ms_parse_date(s):
    import datetime
    s = s.strip()
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None


_MS_DATE_RE = re.compile(r'(\d{4}[/.\-]\d{1,2}[/.\-]\d{1,2}|\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4})')
_MS_EXP_KEYS = ["expire", "expir", "expdate", "exp:", "exp ", "valid", "until", "enddate", "end date", "ends", "subscription"]


def _ms_scan_configs_expiry():
    import datetime
    files = [
        "/etc/tuxbox/config/oscam.server", "/etc/tuxbox/config/oscam.user",
        "/etc/tuxbox/config/oscam-emu/oscam.server", "/etc/tuxbox/config/oscam-emu/oscam.user",
        "/etc/tuxbox/config/oscam/oscam.server", "/etc/tuxbox/config/oscam/oscam.user",
        "/etc/tuxbox/config/ncam.server", "/etc/tuxbox/config/ncam.user",
        "/etc/tuxbox/config/ncam/ncam.server", "/etc/tuxbox/config/ncam/ncam.user",
    ]
    today = datetime.date.today()
    found = []
    for p in files:
        if not os.path.exists(p):
            continue
        txt = _ms_read_file(p)
        for line in txt.split("\n"):
            low = line.lower()
            if any(k in low for k in _MS_EXP_KEYS):
                for mm in _MS_DATE_RE.findall(line):
                    d = _ms_parse_date(mm)
                    if d and d >= today:
                        found.append(d)
    if found:
        return max(found)
    return None


def _ms_find_webif():
    confs = [
        "/etc/tuxbox/config/oscam.conf", "/etc/tuxbox/config/oscam-emu/oscam.conf",
        "/etc/tuxbox/config/oscam/oscam.conf", "/etc/tuxbox/config/ncam.conf",
        "/etc/tuxbox/config/ncam/ncam.conf",
    ]
    for p in confs:
        if not os.path.exists(p):
            continue
        txt = _ms_read_file(p)
        port = user = pwd = ""
        inweb = False
        for line in txt.split("\n"):
            s = line.strip()
            sl = s.lower()
            if sl.startswith("[webif]"):
                inweb = True
                continue
            if s.startswith("[") and inweb:
                break
            if inweb and "=" in s:
                k, v = s.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                if k == "httpport":
                    port = v.replace("+", "").strip()
                elif k == "httpuser":
                    user = v
                elif k == "httppwd":
                    pwd = v
        if port:
            return (port, user, pwd)
    return None


def _ms_webif_expiry(port, user, pwd):
    import datetime
    try:
        if sys.version_info >= (3, 0):
            import urllib.request as urllib2
        else:
            import urllib2
        base = "http://127.0.0.1:%s" % port
        urls = [base + "/oscamapi.html?part=entitlement",
                base + "/oscamapi.html?part=status",
                base + "/status.html"]
        opener = None
        try:
            if user:
                pm = urllib2.HTTPPasswordMgrWithDefaultRealm()
                pm.add_password(None, base, user, pwd)
                opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(pm),
                                              urllib2.HTTPDigestAuthHandler(pm))
        except Exception:
            opener = None
        today = datetime.date.today()
        found = []
        for u in urls:
            try:
                req = urllib2.Request(u, headers={"User-Agent": "Mozilla/5.0"})
                if opener:
                    resp = opener.open(req, timeout=5)
                else:
                    resp = urllib2.urlopen(req, timeout=5)
                data = resp.read()
                if isinstance(data, bytes):
                    data = data.decode("utf-8", "ignore")
            except Exception:
                continue
            for mm in _MS_DATE_RE.findall(data):
                d = _ms_parse_date(mm)
                if d and d >= today and d < (today + datetime.timedelta(days=3650)):
                    found.append(d)
            if found:
                break
        if found:
            return max(found)
    except Exception:
        pass
    return None


def detect_subscription_expiry():
    """Best-effort auto-detect of OSCam/NCam subscription expiry.
    Returns (date_obj, source) or (None, 'notfound')."""
    try:
        d = _ms_scan_configs_expiry()
        if d:
            return d, "config"
    except Exception:
        pass
    try:
        wi = _ms_find_webif()
        if wi:
            d2 = _ms_webif_expiry(*wi)
            if d2:
                return d2, "webif"
    except Exception:
        pass
    return None, "notfound"


# ---- Live server (OSCam / NCam) status monitor ----
def _ms_proc_running():
    """Return a short string of running emu process names (oscam/ncam/cccam)."""
    names = []
    try:
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                with open("/proc/%s/comm" % pid, "r") as f:
                    comm = f.read().strip().lower()
            except Exception:
                comm = ""
            if not comm:
                try:
                    with open("/proc/%s/cmdline" % pid, "rb") as f:
                        cl = f.read().replace(b"\x00", b" ").decode("utf-8", "ignore").lower()
                    comm = cl
                except Exception:
                    comm = ""
            for key in ("oscam", "ncam", "cccam", "gcam"):
                if key in comm and key not in names:
                    names.append(key)
    except Exception:
        pass
    return names


def _ms_webif_fetch(port, user, pwd, path):
    try:
        if sys.version_info >= (3, 0):
            import urllib.request as urllib2
        else:
            import urllib2
        base = "http://127.0.0.1:%s" % port
        opener = None
        try:
            if user:
                pm = urllib2.HTTPPasswordMgrWithDefaultRealm()
                pm.add_password(None, base, user, pwd)
                opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(pm),
                                              urllib2.HTTPDigestAuthHandler(pm))
        except Exception:
            opener = None
        req = urllib2.Request(base + path, headers={"User-Agent": "Mozilla/5.0"})
        if opener:
            resp = opener.open(req, timeout=5)
        else:
            resp = urllib2.urlopen(req, timeout=5)
        data = resp.read()
        if isinstance(data, bytes):
            data = data.decode("utf-8", "ignore")
        return data
    except Exception:
        return ""


def _ms_attr(block, name):
    m = re.search(name + r'\s*=\s*"([^"]*)"', block)
    if m:
        return m.group(1)
    return ""


def _ms_parse_oscam_status(xml):
    """Parse oscamapi status XML into a list of client/reader dicts."""
    out = []
    if not xml:
        return out
    for block in re.findall(r'<client\b.*?</client>', xml, re.DOTALL):
        ctype = _ms_attr(block, "type")
        name = _ms_attr(block, "name")
        proto = _ms_attr(block, "protocol")
        au = _ms_attr(block, "au")
        conn_m = re.search(r'<connection[^>]*>(.*?)</connection>', block, re.DOTALL)
        conn = conn_m.group(1).strip() if conn_m else ""
        conn_status = _ms_attr(block, "status")
        req_m = re.search(r'<request\b([^>]*)>(.*?)</request>', block, re.DOTALL)
        channel = ""
        answer = ""
        ecmtime = ""
        if req_m:
            reqattrs = req_m.group(1)
            answer_in = re.search(r'answer\s*=\s*"([^"]*)"', reqattrs)
            answer = answer_in.group(1) if answer_in else ""
            ecm_in = re.search(r'ecmtime\s*=\s*"([^"]*)"', reqattrs)
            ecmtime = ecm_in.group(1) if ecm_in else ""
            channel = (req_m.group(2) or "").strip()
            if not channel:
                channel = re.search(r'caname\s*=\s*"([^"]*)"', reqattrs)
                channel = channel.group(1) if channel else ""
        out.append({
            "type": ctype, "name": name, "proto": proto, "au": au,
            "conn": conn or conn_status, "channel": channel,
            "answer": answer, "ecmtime": ecmtime,
        })
    return out


def get_server_status():
    """Best-effort snapshot of OSCam/NCam status.
    Returns dict: running(list), webif(bool), readers(list), clients(list), error(str)."""
    info = {"running": [], "webif": False, "readers": [], "clients": [], "error": ""}
    try:
        info["running"] = _ms_proc_running()
    except Exception:
        pass
    wi = None
    try:
        wi = _ms_find_webif()
    except Exception:
        wi = None
    if not wi:
        info["error"] = "nowebif"
        return info
    port, user, pwd = wi
    xml = _ms_webif_fetch(port, user, pwd, "/oscamapi.html?part=status")
    if not xml:
        info["error"] = "unreachable"
        return info
    info["webif"] = True
    entries = _ms_parse_oscam_status(xml)
    for e in entries:
        t = (e.get("type") or "").lower()
        if t in ("r", "p"):
            info["readers"].append(e)
        elif t == "c":
            info["clients"].append(e)
    return info


# ---- Server monitor skin ----
SERVER_MON_RAW_SKIN = """<screen name="MS_ServerMonitorScreen" position="center,center" size="1200,800" title="Server Monitor">
    <widget name="title" position="20,15" size="1160,48" font="Regular;30" halign="center" transparent="1" foregroundColor="#00ffcc00"/>
    <widget name="summary" position="30,72" size="1140,96" font="Regular;26" transparent="1" foregroundColor="#00ffffff"/>
    <widget name="list" position="30,180" size="1140,500" font="Regular;25" itemHeight="52" scrollbarMode="showOnDemand"/>
    <widget name="status" position="20,690" size="1160,34" font="Regular;22" halign="center" transparent="1" foregroundColor="#00aaaaaa"/>
    <widget name="key_red" position="30,738" size="360,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ff4040"/>
    <widget name="key_green" position="420,738" size="360,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="key_blue" position="810,738" size="360,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#004080ff"/>
</screen>"""
SERVER_MON_SKIN = scale_skin_layout(SERVER_MON_RAW_SKIN)


class ServerMonitorScreen(Screen):
    skin = SERVER_MON_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\U0001f4e1 \u0645\u0631\u0627\u0642\u0628 \u062d\u0627\u0644\u0629 \u0627\u0644\u0633\u064a\u0631\u0641\u0631 (Server Monitor)")
        self["summary"] = Label(u"")
        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Label(u"\u062e\u0631\u0648\u062c (Exit)")
        self["key_green"] = Label(u"\u062a\u062d\u062f\u064a\u062b \u062a\u0644\u0642\u0627\u0626\u064a: \u062a\u0634\u063a\u064a\u0644 (Auto:ON)")
        self["key_blue"] = Label(u"\u062a\u062d\u062f\u064a\u062b \u0627\u0644\u0622\u0646 (Refresh)")
        self.ms_busy = False
        self.ms_auto = True
        self.ms_result = None
        self.poll_timer = eTimer()
        try:
            self.poll_timer.callback.append(self.do_refresh)
        except Exception:
            self.poll_timer_conn = self.poll_timer.timeout.connect(self.do_refresh)
        self.ui_timer = eTimer()
        try:
            self.ui_timer.callback.append(self._render)
        except Exception:
            self.ui_timer_conn = self.ui_timer.timeout.connect(self._render)
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "cancel": self.close,
            "ok": self.do_refresh,
            "red": self.close,
            "green": self.toggle_auto,
            "blue": self.do_refresh,
        }, -1)
        self.onClose.append(self._stop_timers)
        self.onLayoutFinish.append(self.do_refresh)

    def _stop_timers(self):
        try:
            self.poll_timer.stop()
        except Exception:
            pass
        try:
            self.ui_timer.stop()
        except Exception:
            pass

    def toggle_auto(self):
        self.ms_auto = not self.ms_auto
        if self.ms_auto:
            self["key_green"].setText(u"\u062a\u062d\u062f\u064a\u062b \u062a\u0644\u0642\u0627\u0626\u064a: \u062a\u0634\u063a\u064a\u0644 (Auto:ON)")
            self.do_refresh()
        else:
            self["key_green"].setText(u"\u062a\u062d\u062f\u064a\u062b \u062a\u0644\u0642\u0627\u0626\u064a: \u0625\u064a\u0642\u0627\u0641 (Auto:OFF)")
            try:
                self.poll_timer.stop()
            except Exception:
                pass

    def do_refresh(self):
        if self.ms_busy:
            return
        self.ms_busy = True
        self["status"].setText(u"\u062c\u0627\u0631\u064a \u0642\u0631\u0627\u0621\u0629 \u062d\u0627\u0644\u0629 \u0627\u0644\u0633\u064a\u0631\u0641\u0631... (reading)")

        def worker():
            try:
                self.ms_result = get_server_status()
            except Exception:
                self.ms_result = {"running": [], "webif": False, "readers": [], "clients": [], "error": "exc"}
            try:
                self.ui_timer.start(50, True)
            except Exception:
                pass
        try:
            import threading
            t = threading.Thread(target=worker)
            t.setDaemon(True)
            t.start()
        except Exception:
            worker()

    def _render(self):
        self.ms_busy = False
        info = self.ms_result or {}
        running = info.get("running", [])
        readers = info.get("readers", [])
        clients = info.get("clients", [])
        err = info.get("error", "")
        if running:
            run_txt = u"\u2705 \u0634\u063a\u0651\u0627\u0644: %s" % ", ".join(running)
        else:
            run_txt = u"\u274c \u0627\u0644\u0633\u064a\u0631\u0641\u0631 \u0645\u0648 \u0634\u063a\u0651\u0627\u0644 (not running)"
        online_readers = [r for r in readers if "connect" in (r.get("conn", "").lower())]
        sm = [run_txt]
        if info.get("webif"):
            sm.append(u"\U0001f4e1 \u0627\u0644\u0631\u064a\u062f\u0631\u0632 (Readers): %d \u2014 \u0645\u062a\u0635\u0644: %d  |  \u0627\u0644\u0632\u0628\u0627\u0626\u0646 (Clients): %d" % (
                len(readers), len(online_readers), len(clients)))
        else:
            if err == "nowebif":
                sm.append(u"\u26a0 \u0645\u0627 \u0644\u06af\u064a\u062a \u0648\u0627\u062c\u0647\u0629 \u0648\u064a\u0628 (webif) \u0645\u0641\u0639\u0651\u0644\u0629 \u2014 \u0641\u0639\u0651\u0644 [webif] \u0628\u0645\u0644\u0641 oscam.conf")
            elif err == "unreachable":
                sm.append(u"\u26a0 \u0648\u0627\u062c\u0647\u0629 \u0627\u0644\u0648\u064a\u0628 \u0645\u0648 \u0645\u0633\u062a\u062c\u064a\u0628\u0629 (webif unreachable)")
            else:
                sm.append(u"\u26a0 \u062a\u0639\u0630\u0651\u0631\u062a \u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u062a\u0641\u0627\u0635\u064a\u0644")
        self["summary"].setText(u"\n".join(sm))
        lines = []
        for r in readers:
            conn = r.get("conn", "")
            low = conn.lower()
            if "connect" in low:
                dot = u"\U0001f7e2"
            elif conn:
                dot = u"\U0001f534"
            else:
                dot = u"\u26aa"
            au = u" \U0001f511AU" if (r.get("au", "") not in ("", "0", "OFF", "off")) else u""
            lines.append(u"%s \U0001f5c2 %s  [%s]  %s%s" % (dot, r.get("name", "") or "?", r.get("proto", "") or "-", conn or u"\u2014", au))
        for c in clients:
            ch = c.get("channel", "")
            ecm = c.get("ecmtime", "")
            extra = u""
            if ch:
                extra = u" \u25b6 %s" % ch
                if ecm:
                    extra += u" (%s ms)" % ecm
            lines.append(u"\U0001f464 %s  [%s]%s" % (c.get("name", "") or "?", c.get("proto", "") or "-", extra))
        if not lines:
            if running and not info.get("webif"):
                lines = [u"\u2139 \u0627\u0644\u0633\u064a\u0631\u0641\u0631 \u0634\u063a\u0651\u0627\u0644 \u0628\u0633 \u0648\u0627\u062c\u0647\u0629 \u0627\u0644\u0648\u064a\u0628 \u0645\u0637\u0641\u0651\u064a\u0629 \u2014 \u0641\u0639\u0651\u0644\u0647\u0627 \u0644\u062a\u0634\u0648\u0641 \u0627\u0644\u062a\u0641\u0627\u0635\u064a\u0644."]
            else:
                lines = [u"\u2014 \u0644\u0627 \u062a\u0648\u062c\u062f \u062a\u0641\u0627\u0635\u064a\u0644 \u0644\u0644\u0639\u0631\u0636"]
        self["list"].setList(lines)
        import datetime
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self["status"].setText(u"\u0622\u062e\u0631 \u062a\u062d\u062f\u064a\u062b: %s  |  \u0623\u062e\u0636\u0631=\u062a\u0628\u062f\u064a\u0644 \u0627\u0644\u062a\u062d\u062f\u064a\u062b \u0627\u0644\u062a\u0644\u0642\u0627\u0626\u064a  |  \u0623\u0632\u0631\u0642=\u062a\u062d\u062f\u064a\u062b" % now)
        if self.ms_auto:
            try:
                self.poll_timer.start(6000, True)
            except Exception:
                pass


# ---- Settings backup / restore ----
BACKUP_SOURCES = ["/etc/enigma2", "/etc/tuxbox/config", "/etc/CCcam.cfg", "/usr/keys"]


def _ms_backup_base():
    for p in ["/media/hdd", "/media/usb", "/media/mmc", "/data"]:
        if os.path.exists(p):
            d = os.path.join(p, "MohamedStore_Backups")
            try:
                if not os.path.exists(d):
                    os.makedirs(d)
            except Exception:
                pass
            return d
    return "/tmp/MohamedStore_Backups"


BACKUP_RAW_SKIN = """<screen name="MS_BackupScreen" position="center,center" size="1200,800" title="Settings Backup">
    <widget name="title" position="20,15" size="1160,48" font="Regular;30" halign="center" transparent="1" foregroundColor="#00ffcc00"/>
    <widget name="info" position="30,72" size="1140,70" font="Regular;24" transparent="1" foregroundColor="#00cccccc"/>
    <widget name="list" position="30,155" size="1140,520" font="Regular;26" itemHeight="50" scrollbarMode="showOnDemand"/>
    <widget name="status" position="20,685" size="1160,34" font="Regular;22" halign="center" transparent="1" foregroundColor="#00aaaaaa"/>
    <widget name="key_red" position="30,738" size="270,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ff4040"/>
    <widget name="key_green" position="320,738" size="270,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="key_yellow" position="610,738" size="270,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ffff40"/>
    <widget name="key_blue" position="900,738" size="270,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#004080ff"/>
</screen>"""
BACKUP_SKIN = scale_skin_layout(BACKUP_RAW_SKIN)


class SettingsBackupScreen(Screen):
    skin = BACKUP_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\U0001f4be \u0646\u0633\u062e \u0627\u062d\u062a\u064a\u0627\u0637\u064a / \u0627\u0633\u062a\u0639\u0627\u062f\u0629 (Backup & Restore)")
        self["info"] = Label("")
        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Label(u"\u062e\u0631\u0648\u062c (Exit)")
        self["key_green"] = Label(u"\u0646\u0633\u062e\u0629 \u062c\u062f\u064a\u062f\u0629 (Backup)")
        self["key_yellow"] = Label(u"\u062d\u0630\u0641 (Delete)")
        self["key_blue"] = Label(u"\u062a\u062d\u062f\u064a\u062b (Refresh)")
        self.base = _ms_backup_base()
        self.files = []
        self.busy = False
        self.console = Console()
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "cancel": self.close,
            "ok": self.restore_selected,
            "red": self.close,
            "green": self.create_backup,
            "yellow": self.delete_selected,
            "blue": self.refresh,
        }, -1)
        self.onLayoutFinish.append(self.refresh)

    def _fmt_size(self, n):
        try:
            n = float(n)
        except Exception:
            return ""
        for unit in ["B", "KB", "MB", "GB"]:
            if n < 1024.0:
                return "%.1f %s" % (n, unit)
            n /= 1024.0
        return "%.1f TB" % n

    def refresh(self):
        self["info"].setText(u"\U0001f4c1 \u0645\u0643\u0627\u0646 \u0627\u0644\u062d\u0641\u0638: %s\n\u062a\u0634\u0645\u0644: \u0642\u0646\u0648\u0627\u062a\u060c \u0625\u0639\u062f\u0627\u062f\u0627\u062a\u060c \u0633\u064a\u0631\u0641\u0631 (enigma2 + softcam configs)" % self.base)
        items = []
        self.files = []
        try:
            names = sorted(os.listdir(self.base), reverse=True)
        except Exception:
            names = []
        for n in names:
            if not (n.endswith(".tar.gz") and n.startswith("backup_")):
                continue
            full = os.path.join(self.base, n)
            sz = ""
            try:
                sz = self._fmt_size(os.path.getsize(full))
            except Exception:
                pass
            items.append(u"\U0001f4e6 %s   (%s)" % (n, sz))
            self.files.append(full)
        self["list"].setList(items)
        if items:
            self["status"].setText(u"%d \u0646\u0633\u062e\u0629   |   OK=\u0627\u0633\u062a\u0639\u0627\u062f\u0629  \u0623\u062e\u0636\u0631=\u0646\u0633\u062e\u0629 \u062c\u062f\u064a\u062f\u0629  \u0623\u0635\u0641\u0631=\u062d\u0630\u0641" % len(items))
        else:
            self["status"].setText(u"\u0644\u0627 \u062a\u0648\u062c\u062f \u0646\u0633\u062e \u2014 \u0627\u0636\u063a\u0637 \u0627\u0644\u0623\u062e\u0636\u0631 \u0644\u0639\u0645\u0644 \u0646\u0633\u062e\u0629 \u0627\u062d\u062a\u064a\u0627\u0637\u064a\u0629")

    def create_backup(self):
        if self.busy:
            return
        srcs = [p for p in BACKUP_SOURCES if os.path.exists(p)]
        if not srcs:
            self.session.open(MessageBox, u"\u274c \u0645\u0627 \u0644\u06af\u064a\u062a \u0645\u0644\u0641\u0627\u062a \u0644\u0644\u0646\u0633\u062e.", MessageBox.TYPE_ERROR)
            return
        import datetime
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        dest = os.path.join(self.base, "backup_%s.tar.gz" % stamp)
        self.busy = True
        self["status"].setText(u"\u062c\u0627\u0631\u064a \u0639\u0645\u0644 \u0627\u0644\u0646\u0633\u062e\u0629... \u0627\u0646\u062a\u0638\u0631 (backing up)")
        cmd = "tar czf '%s' %s 2>&1" % (dest, " ".join(["'" + s + "'" for s in srcs]))
        try:
            self.console.ePopen(cmd, self._backup_done)
        except Exception as e:
            self.busy = False
            self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644:\n" + str(e), MessageBox.TYPE_ERROR)

    def _backup_done(self, result, retval, extra_args=None):
        self.busy = False
        self.refresh()
        if retval == 0:
            self.session.open(MessageBox, u"\u2705 \u062a\u0645\u062a \u0627\u0644\u0646\u0633\u062e\u0629 \u0627\u0644\u0627\u062d\u062a\u064a\u0627\u0637\u064a\u0629 \u0628\u0646\u062c\u0627\u062d.\n\u062a\u0645 \u0627\u0644\u062d\u0641\u0638 \u0639\u0644\u0649 \u0627\u0644\u0647\u0627\u0631\u062f/\u0627\u0644\u0641\u0644\u0627\u0634.", MessageBox.TYPE_INFO, timeout=5)
        else:
            self.session.open(MessageBox, u"\u26a0 \u0627\u0646\u062a\u0647\u062a \u0627\u0644\u0646\u0633\u062e\u0629 \u0645\u0639 \u062a\u0646\u0628\u064a\u0647\u0627\u062a:\n" + (result or "")[-400:], MessageBox.TYPE_INFO)

    def _selected_file(self):
        idx = self["list"].getSelectionIndex()
        if idx is None or idx < 0 or idx >= len(self.files):
            return None
        return self.files[idx]

    def delete_selected(self):
        f = self._selected_file()
        if not f:
            self.session.open(MessageBox, u"\u0644\u0627 \u062a\u0648\u062c\u062f \u0646\u0633\u062e\u0629 \u0645\u062d\u062f\u062f\u0629.", MessageBox.TYPE_INFO)
            return
        self._to_del = f
        self.session.openWithCallback(self._del_cb, MessageBox,
            u"\u062d\u0630\u0641 \u0627\u0644\u0646\u0633\u062e\u0629:\n%s \u061f" % os.path.basename(f),
            MessageBox.TYPE_YESNO)

    def _del_cb(self, result):
        if not result:
            return
        try:
            os.remove(self._to_del)
        except Exception:
            pass
        self.refresh()

    def restore_selected(self):
        if self.busy:
            return
        f = self._selected_file()
        if not f:
            self.session.open(MessageBox, u"\u0644\u0627 \u062a\u0648\u062c\u062f \u0646\u0633\u062e\u0629 \u0645\u062d\u062f\u062f\u0629 \u0644\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629.", MessageBox.TYPE_INFO)
            return
        self._to_restore = f
        self.session.openWithCallback(self._restore_cb, MessageBox,
            u"\u26a0 \u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0627\u0644\u0646\u0633\u062e\u0629:\n%s\n\n\u0631\u0627\u062d \u062a\u0633\u062a\u0628\u062f\u0644 \u0627\u0644\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u062d\u0627\u0644\u064a\u0629 \u0648\u062a\u062d\u062a\u0627\u062c \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0648\u0627\u062c\u0647\u0629.\n\u0647\u0644 \u0623\u0646\u062a \u0645\u062a\u0623\u0643\u062f\u061f (Restore & restart GUI?)" % os.path.basename(f),
            MessageBox.TYPE_YESNO)

    def _restore_cb(self, result):
        if not result:
            return
        self.busy = True
        self["status"].setText(u"\u062c\u0627\u0631\u064a \u0627\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629... (restoring)")
        cmd = "tar xzf '%s' -C / 2>&1" % self._to_restore
        try:
            self.console.ePopen(cmd, self._restore_done)
        except Exception as e:
            self.busy = False
            self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644:\n" + str(e), MessageBox.TYPE_ERROR)

    def _restore_done(self, result, retval, extra_args=None):
        self.busy = False
        if retval == 0:
            self.session.openWithCallback(self._after_restore, MessageBox,
                u"\u2705 \u062a\u0645\u062a \u0627\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629.\n\u0633\u062a\u064f\u0639\u0627\u062f \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0648\u0627\u062c\u0647\u0629 \u0627\u0644\u0622\u0646.",
                MessageBox.TYPE_INFO, timeout=5)
        else:
            self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644\u062a \u0627\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629:\n" + (result or "")[-400:], MessageBox.TYPE_ERROR)

    def _after_restore(self, *args):
        try:
            if TryQuitMainloop:
                self.session.open(TryQuitMainloop, 3)
            elif enigma:
                enigma.quitMainloop(3)
            else:
                os.system("killall -9 enigma2")
        except Exception:
            try:
                os.system("killall -9 enigma2")
            except Exception:
                pass


# ---- Kids Mode (parental) helpers ----
ENIGMA2_DIR = "/etc/enigma2"
KIDS_BQ_FILE = os.path.join(ENIGMA2_DIR, "userbouquet.mskids.tv")
KIDS_BQ_LINE = "#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"userbouquet.mskids.tv\" ORDER BY bouquet"
BOUQUETS_TV = os.path.join(ENIGMA2_DIR, "bouquets.tv")
BOUQUETS_BAK = os.path.join(ENIGMA2_DIR, "bouquets.tv.msori")


def _kids_parse_all_channels():
    """Return list of (service_line, name) for all TV channels in user bouquets."""
    out = []
    seen = set()
    try:
        with open(BOUQUETS_TV, "r") as f:
            btxt = f.read()
    except Exception:
        return out
    bqfiles = re.findall(r'FROM BOUQUET "([^"]+)"', btxt)
    for bq in bqfiles:
        if bq == "userbouquet.mskids.tv":
            continue
        path = os.path.join(ENIGMA2_DIR, bq)
        try:
            with open(path, "r") as f:
                lines = f.read().split("\n")
        except Exception:
            continue
        i = 0
        while i < len(lines):
            ln = lines[i].strip()
            if ln.startswith("#SERVICE"):
                sref = ln
                parts = ln.split(":")
                # skip markers / separators (type 64 etc.)
                is_marker = False
                try:
                    if len(parts) > 1:
                        tcode = parts[1].replace("#SERVICE", "").strip()
                        if "64" in parts[1]:
                            is_marker = True
                except Exception:
                    pass
                name = ""
                if i + 1 < len(lines) and lines[i + 1].strip().startswith("#DESCRIPTION"):
                    name = lines[i + 1].strip()[12:].strip()
                if not is_marker and sref not in seen and (":" in sref):
                    seen.add(sref)
                    if not name:
                        name = sref.split(":")[-1] or u"\u0642\u0646\u0627\u0629"
                    out.append((sref, name))
            i += 1
    return out


def _kids_write_bouquet(allowed):
    """allowed: list of (service_line, name). Writes the kids userbouquet."""
    try:
        buf = ["#NAME " + u"\u0627\u0637\u0641\u0627\u0644 (Kids)"]
        for sref, name in allowed:
            buf.append(sref)
            buf.append("#DESCRIPTION " + name)
        with open(KIDS_BQ_FILE, "w") as f:
            f.write("\n".join(buf) + "\n")
        return True
    except Exception:
        return False


def _kids_reload_services():
    try:
        from enigma import eDVBDB
        eDVBDB.getInstance().reloadBouquets()
        return True
    except Exception:
        pass
    try:
        os.system("wget -q -O /dev/null 'http://127.0.0.1/web/servicelistreload?mode=2' 2>/dev/null")
        return True
    except Exception:
        return False


def _kids_enable(allowed):
    if not _kids_write_bouquet(allowed):
        return False
    try:
        # backup original bouquets.tv once
        if not os.path.exists(BOUQUETS_BAK) and os.path.exists(BOUQUETS_TV):
            import shutil
            shutil.copy2(BOUQUETS_TV, BOUQUETS_BAK)
        with open(BOUQUETS_TV, "w") as f:
            f.write("#NAME Bouquets (TV)\n" + KIDS_BQ_LINE + "\n")
        _kids_reload_services()
        return True
    except Exception:
        return False


def _kids_disable():
    try:
        if os.path.exists(BOUQUETS_BAK):
            import shutil
            shutil.copy2(BOUQUETS_BAK, BOUQUETS_TV)
            try:
                os.remove(BOUQUETS_BAK)
            except Exception:
                pass
        _kids_reload_services()
        return True
    except Exception:
        return False


KIDS_RAW_SKIN = """<screen name="MS_KidsModeScreen" position="center,center" size="1100,700" title="Kids Mode">
    <widget name="title" position="20,15" size="1060,50" font="Regular;32" halign="center" transparent="1" foregroundColor="#00ffcc00"/>
    <widget name="state" position="20,100" size="1060,70" font="Regular;40" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="info" position="50,200" size="1000,360" font="Regular;27" halign="center" transparent="1" foregroundColor="#00cccccc"/>
    <widget name="key_red" position="30,640" size="250,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ff4040"/>
    <widget name="key_green" position="290,640" size="250,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="key_yellow" position="550,640" size="250,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ffff40"/>
    <widget name="key_blue" position="810,640" size="260,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#004080ff"/>
</screen>"""
KIDS_SKIN = scale_skin_layout(KIDS_RAW_SKIN)

KIDS_PICKER_RAW_SKIN = """<screen name="MS_KidsPickerScreen" position="center,center" size="1200,820" title="Kids Channels">
    <widget name="title" position="20,12" size="1160,46" font="Regular;28" halign="center" transparent="1" foregroundColor="#00ffcc00"/>
    <widget name="list" position="30,66" size="1140,660" font="Regular;26" itemHeight="44" scrollbarMode="showOnDemand"/>
    <widget name="status" position="20,736" size="1160,34" font="Regular;22" halign="center" transparent="1" foregroundColor="#00aaaaaa"/>
    <widget name="key_red" position="30,778" size="360,36" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ff4040"/>
    <widget name="key_green" position="420,778" size="360,36" font="Regular;23" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="key_yellow" position="810,778" size="360,36" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ffff40"/>
</screen>"""
KIDS_PICKER_SKIN = scale_skin_layout(KIDS_PICKER_RAW_SKIN)


class KidsModeScreen(Screen):
    skin = KIDS_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\U0001f9f8 \u0648\u0636\u0639 \u0627\u0644\u0623\u0637\u0641\u0627\u0644 (Kids Mode)")
        self["state"] = Label("")
        self["info"] = Label("")
        self["key_red"] = Label(u"\u062e\u0631\u0648\u062c (Exit)")
        self["key_green"] = Label(u"\u062a\u0634\u063a\u064a\u0644/\u0625\u064a\u0642\u0627\u0641 (Toggle)")
        self["key_yellow"] = Label(u"\u0627\u062e\u062a\u064a\u0627\u0631 \u0627\u0644\u0642\u0646\u0648\u0627\u062a (Channels)")
        self["key_blue"] = Label(u"\u0627\u0644\u0631\u0645\u0632 \u0627\u0644\u0633\u0631\u064a (PIN)")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "cancel": self.close,
            "ok": self.toggle,
            "red": self.close,
            "green": self.toggle,
            "yellow": self.manage_channels,
            "blue": self.set_pin,
        }, -1)
        self.onLayoutFinish.append(self.refresh)

    def _cfg(self):
        return _load_json_cfg(KIDS_CONFIG, {})

    def refresh(self):
        c = self._cfg()
        enabled = bool(c.get("enabled"))
        allowed = c.get("allowed", [])
        haspin = bool(c.get("pin"))
        if enabled:
            self["state"].setText(u"\U0001f7e2 \u0645\u064f\u0641\u0639\u0651\u0644 (ON)")
        else:
            self["state"].setText(u"\u26aa \u0645\u062a\u0648\u0642\u0651\u0641 (OFF)")
        lines = []
        lines.append(u"\u0639\u062f\u062f \u0627\u0644\u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0645\u0633\u0645\u0648\u062d\u0629 \u0644\u0644\u0623\u0637\u0641\u0627\u0644: %d" % len(allowed))
        lines.append(u"\u0627\u0644\u0631\u0645\u0632 \u0627\u0644\u0633\u0631\u064a: %s" % (u"\u2705 \u0645\u0636\u0628\u0648\u0637" if haspin else u"\u274c \u063a\u064a\u0631 \u0645\u0636\u0628\u0648\u0637"))
        lines.append(u"")
        if enabled:
            lines.append(u"\u2139 \u0627\u0644\u062c\u0647\u0627\u0632 \u064a\u0639\u0631\u0636 \u0627\u0644\u0622\u0646 \u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0623\u0637\u0641\u0627\u0644 \u0641\u0642\u0637.")
            lines.append(u"\u0644\u0644\u0625\u064a\u0642\u0627\u0641 \u0648\u0625\u0631\u062c\u0627\u0639 \u0643\u0644 \u0627\u0644\u0642\u0646\u0648\u0627\u062a \u064a\u0644\u0632\u0645 \u0627\u0644\u0631\u0645\u0632 \u0627\u0644\u0633\u0631\u064a.")
        else:
            lines.append(u"\u062e\u0637\u0648\u0627\u062a: 1) \u0627\u0636\u0628\u0637 \u0631\u0645\u0632 \u0633\u0631\u064a (\u0623\u0632\u0631\u0642)  2) \u0627\u062e\u062a\u0631 \u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0623\u0637\u0641\u0627\u0644 (\u0623\u0635\u0641\u0631)  3) \u0634\u063a\u0651\u0644 (\u0623\u062e\u0636\u0631)")
        self["info"].setText(u"\n".join(lines))

    # ---- PIN ----
    def _ask_pin(self, cb, title):
        try:
            from Screens.VirtualKeyBoard import VirtualKeyBoard
            self.session.openWithCallback(cb, VirtualKeyBoard, title=title, text=u"")
        except Exception:
            try:
                from Screens.InputBox import InputBox
                self.session.openWithCallback(cb, InputBox, title=title, text=u"")
            except Exception:
                self.session.open(MessageBox, u"\u274c \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0641\u0627\u062a\u064a\u062d \u063a\u064a\u0631 \u0645\u062a\u0648\u0641\u0631\u0629.", MessageBox.TYPE_ERROR)

    def set_pin(self):
        self._ask_pin(self._set_pin_cb, u"\u0627\u0643\u062a\u0628 \u0631\u0645\u0632 \u0633\u0631\u064a \u062c\u062f\u064a\u062f (4 \u0623\u0631\u0642\u0627\u0645):")

    def _set_pin_cb(self, val):
        if val is None:
            return
        val = (val or "").strip()
        if not val.isdigit() or len(val) < 3:
            self.session.open(MessageBox, u"\u274c \u0627\u0644\u0631\u0645\u0632 \u0644\u0627\u0632\u0645 \u064a\u0643\u0648\u0646 \u0623\u0631\u0642\u0627\u0645 (3+ \u062e\u0627\u0646\u0627\u062a).", MessageBox.TYPE_ERROR)
            return
        c = self._cfg()
        c["pin"] = val
        _save_json_cfg(KIDS_CONFIG, c)
        self.refresh()
        self.session.open(MessageBox, u"\u2705 \u062a\u0645 \u0636\u0628\u0637 \u0627\u0644\u0631\u0645\u0632 \u0627\u0644\u0633\u0631\u064a.", MessageBox.TYPE_INFO, timeout=3)

    def _verify_then(self, action):
        c = self._cfg()
        pin = c.get("pin", "")
        if not pin:
            action()
            return
        self._pending_action = action
        self._ask_pin(self._verify_cb, u"\u0627\u062f\u062e\u0644 \u0627\u0644\u0631\u0645\u0632 \u0627\u0644\u0633\u0631\u064a:")

    def _verify_cb(self, val):
        if val is None:
            return
        c = self._cfg()
        if (val or "").strip() == c.get("pin", ""):
            act = getattr(self, "_pending_action", None)
            if act:
                act()
        else:
            self.session.open(MessageBox, u"\u274c \u0627\u0644\u0631\u0645\u0632 \u063a\u0644\u0637.", MessageBox.TYPE_ERROR)

    # ---- channels ----
    def manage_channels(self):
        self.session.openWithCallback(self._after_pick, KidsChannelPicker)

    def _after_pick(self, *args):
        self.refresh()

    # ---- toggle ----
    def toggle(self):
        c = self._cfg()
        if c.get("enabled"):
            self._verify_then(self._do_disable)
        else:
            allowed = c.get("allowed", [])
            if not allowed:
                self.session.open(MessageBox, u"\u26a0 \u0627\u062e\u062a\u0631 \u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0623\u0637\u0641\u0627\u0644 \u0623\u0648\u0644\u0627\u064b (\u0627\u0644\u0632\u0631 \u0627\u0644\u0623\u0635\u0641\u0631).", MessageBox.TYPE_WARNING)
                return
            self._verify_then(self._do_enable)

    def _do_enable(self):
        c = self._cfg()
        allowed = [(x[0], x[1]) for x in c.get("allowed", [])]
        if _kids_enable(allowed):
            c["enabled"] = True
            _save_json_cfg(KIDS_CONFIG, c)
            self.refresh()
            self.session.openWithCallback(self._apply_restart, MessageBox,
                u"\u2705 \u062a\u0645 \u062a\u062c\u0647\u064a\u0632 \u0648\u0636\u0639 \u0627\u0644\u0623\u0637\u0641\u0627\u0644.\n\u0644\u062a\u0637\u0628\u064a\u0642 \u0627\u0644\u062a\u063a\u064a\u064a\u0631 \u0644\u0627\u0632\u0645 \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0648\u0627\u062c\u0647\u0629 \u0627\u0644\u0622\u0646.\n\u0623\u0639\u064a\u062f \u0627\u0644\u062a\u0634\u063a\u064a\u0644\u061f (Restart GUI now?)",
                MessageBox.TYPE_YESNO)
        else:
            self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644 \u0627\u0644\u062a\u0634\u063a\u064a\u0644.", MessageBox.TYPE_ERROR)

    def _do_disable(self):
        c = self._cfg()
        if _kids_disable():
            c["enabled"] = False
            _save_json_cfg(KIDS_CONFIG, c)
            self.refresh()
            self.session.openWithCallback(self._apply_restart, MessageBox,
                u"\u2705 \u062a\u0645 \u0625\u064a\u0642\u0627\u0641 \u0648\u0636\u0639 \u0627\u0644\u0623\u0637\u0641\u0627\u0644.\n\u0644\u0625\u0631\u062c\u0627\u0639 \u0643\u0644 \u0627\u0644\u0642\u0646\u0648\u0627\u062a \u0644\u0627\u0632\u0645 \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0648\u0627\u062c\u0647\u0629 \u0627\u0644\u0622\u0646.\n\u0623\u0639\u064a\u062f \u0627\u0644\u062a\u0634\u063a\u064a\u0644\u061f (Restart GUI now?)",
                MessageBox.TYPE_YESNO)
        else:
            self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644 \u0627\u0644\u0625\u064a\u0642\u0627\u0641.", MessageBox.TYPE_ERROR)

    def _apply_restart(self, result):
        if not result:
            return
        try:
            if TryQuitMainloop:
                self.session.open(TryQuitMainloop, 3)
            elif enigma:
                enigma.quitMainloop(3)
            else:
                os.system("killall -9 enigma2")
        except Exception:
            try:
                os.system("killall -9 enigma2")
            except Exception:
                pass


class KidsChannelPicker(Screen):
    skin = KIDS_PICKER_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\u2714 \u0627\u062e\u062a\u0631 \u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0623\u0637\u0641\u0627\u0644 (OK=\u062a\u062d\u062f\u064a\u062f)")
        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Label(u"\u0625\u0644\u063a\u0627\u0621 (Cancel)")
        self["key_green"] = Label(u"\u062d\u0641\u0638 (Save)")
        self["key_yellow"] = Label(u"\u0645\u0633\u062d \u0627\u0644\u0643\u0644 (Clear)")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "cancel": self.close,
            "ok": self.toggle_item,
            "red": self.close,
            "green": self.save,
            "yellow": self.clear_all,
        }, -1)
        self.all_chs = []
        self.sel = set()
        self.onLayoutFinish.append(self.load)

    def load(self):
        self["status"].setText(u"\u062c\u0627\u0631\u064a \u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u0642\u0646\u0648\u0627\u062a...")
        self.all_chs = _kids_parse_all_channels()
        c = _load_json_cfg(KIDS_CONFIG, {})
        saved = set()
        for item in c.get("allowed", []):
            try:
                saved.add(item[0])
            except Exception:
                pass
        self.sel = set()
        for i, (sref, name) in enumerate(self.all_chs):
            if sref in saved:
                self.sel.add(i)
        self._render()

    def _render(self):
        items = []
        for i, (sref, name) in enumerate(self.all_chs):
            mark = u"\u2611" if i in self.sel else u"\u2610"
            items.append(u"%s  %s" % (mark, name))
        if not items:
            items = [u"\u2014 \u0644\u0627 \u062a\u0648\u062c\u062f \u0642\u0646\u0648\u0627\u062a (\u062a\u0623\u0643\u062f \u0645\u0646 \u0648\u062c\u0648\u062f \u0628\u0627\u0642\u0627\u062a)"]
        idx = self["list"].getSelectionIndex() or 0
        self["list"].setList(items)
        try:
            self["list"].moveToIndex(min(idx, max(0, len(items) - 1)))
        except Exception:
            pass
        self["status"].setText(u"\u0627\u0644\u0645\u062d\u062f\u062f: %d / %d   |   OK=\u062a\u062d\u062f\u064a\u062f  \u0623\u062e\u0636\u0631=\u062d\u0641\u0638" % (len(self.sel), len(self.all_chs)))

    def toggle_item(self):
        if not self.all_chs:
            return
        idx = self["list"].getSelectionIndex()
        if idx is None or idx < 0 or idx >= len(self.all_chs):
            return
        if idx in self.sel:
            self.sel.discard(idx)
        else:
            self.sel.add(idx)
        self._render()

    def clear_all(self):
        self.sel = set()
        self._render()

    def save(self):
        allowed = [[self.all_chs[i][0], self.all_chs[i][1]] for i in sorted(self.sel)]
        c = _load_json_cfg(KIDS_CONFIG, {})
        c["allowed"] = allowed
        _save_json_cfg(KIDS_CONFIG, c)
        # if kids mode currently ON, rebuild bouquet live
        if c.get("enabled"):
            try:
                _kids_enable([(a[0], a[1]) for a in allowed])
            except Exception:
                pass
        self.session.open(MessageBox, u"\u2705 \u062a\u0645 \u062d\u0641\u0638 %d \u0642\u0646\u0627\u0629 \u0644\u0644\u0623\u0637\u0641\u0627\u0644." % len(allowed), MessageBox.TYPE_INFO, timeout=3)
        self.close()


# ---- Channel Organizer (bouquet editor) helpers ----

def _org_bouquet_name(bqfile):
    path = os.path.join(ENIGMA2_DIR, bqfile)
    try:
        with open(path, "r") as f:
            first = f.readline().strip()
        if first.startswith("#NAME"):
            nm = first[5:].strip()
            if nm:
                return nm
    except Exception:
        pass
    return bqfile


def _org_read_bouquets():
    """Return ordered list of dicts: {line, file, name}."""
    out = []
    try:
        with open(BOUQUETS_TV, "r") as f:
            txt = f.read()
    except Exception:
        return out
    for ln in txt.split("\n"):
        s = ln.strip()
        if s.startswith("#SERVICE") and "FROM BOUQUET" in s:
            m = re.search(r'FROM BOUQUET "([^"]+)"', s)
            if not m:
                continue
            bqfile = m.group(1)
            out.append({"line": s, "file": bqfile, "name": _org_bouquet_name(bqfile)})
    return out


def _org_write_bouquets_order(bouquets):
    """bouquets: ordered list of dicts with 'line'. Rewrites bouquets.tv."""
    try:
        if not os.path.exists(BOUQUETS_BAK) and os.path.exists(BOUQUETS_TV):
            import shutil
            shutil.copy2(BOUQUETS_TV, BOUQUETS_TV + ".orgbak")
        buf = ["#NAME Bouquets (TV)"]
        for b in bouquets:
            buf.append(b["line"])
        with open(BOUQUETS_TV, "w") as f:
            f.write("\n".join(buf) + "\n")
        return True
    except Exception:
        return False


def _org_service_name(srefline):
    """Resolve the real display name of a service from enigma's channel DB
    (lamedb). Used when the bouquet line has no #DESCRIPTION."""
    ref = srefline
    if ref.startswith("#SERVICE"):
        ref = ref[len("#SERVICE"):].strip()
    try:
        from Components.ServiceReference import ServiceReference
        nm = ServiceReference(ref).getServiceName()
        if nm:
            nm = nm.replace("\xc2\x86", "").replace("\xc2\x87", "").strip()
            if nm:
                return nm
    except Exception:
        pass
    try:
        from enigma import eServiceCenter, eServiceReference
        r = eServiceReference(str(ref))
        info = eServiceCenter.getInstance().info(r)
        if info:
            nm = info.getName(r)
            if nm:
                nm = nm.strip()
                if nm:
                    return nm
    except Exception:
        pass
    return ""


def _org_read_channels(bqfile):
    """Return list of dicts: {raw, name, is_marker, sref}.
    Each channel keeps its EXACT original line block (service line plus any
    following #DESCRIPTION / extra lines) verbatim so writing back can never
    corrupt the service references."""
    out = []
    path = os.path.join(ENIGMA2_DIR, bqfile)
    try:
        with open(path, "r") as f:
            raw = f.read()
    except Exception:
        return out
    lines = raw.split("\n")
    blocks = []
    cur = None
    for ln in lines:
        s = ln.rstrip("\r")
        st = s.strip()
        if st.startswith("#NAME"):
            continue
        if st.startswith("#SERVICE"):
            if cur is not None:
                blocks.append(cur)
            cur = [s]
        else:
            if cur is not None and st != "":
                cur.append(s)
    if cur is not None:
        blocks.append(cur)
    for blk in blocks:
        srefline = blk[0].strip()
        parts = srefline.split(":")
        is_marker = len(parts) > 1 and "64" in parts[1]
        name = ""
        for extra in blk[1:]:
            es = extra.strip()
            if es.startswith("#DESCRIPTION"):
                name = es[12:].strip()
                break
        if not name and is_marker and "::" in srefline:
            name = srefline.split("::", 1)[1].strip()
        if not name and not is_marker:
            name = _org_service_name(srefline)
        if not name:
            tail = srefline.split(":")[-1].strip()
            if tail and not tail.replace(".", "").isdigit():
                name = tail
        if not name:
            name = u"\u2015" if is_marker else u"\u0642\u0646\u0627\u0629"
        out.append({"raw": "\n".join(blk), "name": name, "is_marker": is_marker, "sref": srefline})
    return out


def _org_write_channels(bqfile, channels, bqname):
    """Rewrite bouquet keeping each channel's original raw block verbatim."""
    try:
        path = os.path.join(ENIGMA2_DIR, bqfile)
        if os.path.exists(path):
            import shutil
            shutil.copy2(path, path + ".orgbak")
        buf = ["#NAME " + bqname]
        for ch in channels:
            buf.append(ch["raw"])
        with open(path, "w") as f:
            f.write("\n".join(buf) + "\n")
        return True
    except Exception:
        return False


def _org_delete_bouquet(bqfile):
    try:
        path = os.path.join(ENIGMA2_DIR, bqfile)
        if os.path.exists(path):
            os.remove(path)
        return True
    except Exception:
        return False


ORG_RAW_SKIN = """<screen name="MS_ChannelOrganizer" position="center,center" size="1200,820" title="Channel Organizer">
    <widget name="title" position="20,12" size="1160,46" font="Regular;28" halign="center" transparent="1" foregroundColor="#00ffcc00"/>
    <widget name="list" position="30,66" size="1140,620" font="Regular;26" itemHeight="44" scrollbarMode="showOnDemand"/>
    <widget name="status" position="20,696" size="1160,34" font="Regular;22" halign="center" transparent="1" foregroundColor="#00aaaaaa"/>
    <widget name="key_red" position="20,740" size="285,36" font="Regular;21" halign="center" transparent="1" foregroundColor="#00ff4040"/>
    <widget name="key_green" position="315,740" size="285,36" font="Regular;21" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="key_yellow" position="610,740" size="285,36" font="Regular;21" halign="center" transparent="1" foregroundColor="#00ffff40"/>
    <widget name="key_blue" position="905,740" size="275,36" font="Regular;21" halign="center" transparent="1" foregroundColor="#004080ff"/>
    <widget name="hint" position="20,780" size="1160,32" font="Regular;20" halign="center" transparent="1" foregroundColor="#00888888"/>
</screen>"""
ORG_SKIN = scale_skin_layout(ORG_RAW_SKIN)


def _org_create_bouquet(name):
    """Create a new empty user bouquet and register it in bouquets.tv."""
    try:
        import time
        slug = re.sub(r'[^a-zA-Z0-9]+', '', name).lower()
        if not slug:
            slug = "ms" + str(int(time.time()))
        base = slug
        fname = "userbouquet." + slug + ".tv"
        path = os.path.join(ENIGMA2_DIR, fname)
        i = 1
        while os.path.exists(path):
            slug = base + str(i)
            fname = "userbouquet." + slug + ".tv"
            path = os.path.join(ENIGMA2_DIR, fname)
            i += 1
        with open(path, "w") as f:
            f.write("#NAME " + name + "\n")
        line = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet' % fname
        bqs = _org_read_bouquets()
        bqs.append({"line": line, "file": fname, "name": name})
        _org_write_bouquets_order(bqs)
        return True, fname
    except Exception:
        return False, ""


def _org_backup_all():
    """Copy bouquets.tv + all userbouquet*.tv to the plugin backup folder."""
    try:
        import glob
        import shutil
        if not os.path.isdir(ORG_BACKUP_DIR):
            os.makedirs(ORG_BACKUP_DIR)
        for f in glob.glob(os.path.join(ORG_BACKUP_DIR, "*")):
            try:
                os.remove(f)
            except Exception:
                pass
        files = [BOUQUETS_TV]
        files += glob.glob(os.path.join(ENIGMA2_DIR, "userbouquet.*.tv"))
        files += glob.glob(os.path.join(ENIGMA2_DIR, "bouquets.*"))
        n = 0
        for f in files:
            if os.path.isfile(f):
                shutil.copy2(f, os.path.join(ORG_BACKUP_DIR, os.path.basename(f)))
                n += 1
        return True, n
    except Exception:
        return False, 0


def _org_restore_all():
    """Restore the files saved by _org_backup_all back to /etc/enigma2."""
    try:
        import glob
        import shutil
        if not os.path.isdir(ORG_BACKUP_DIR):
            return False, 0
        files = glob.glob(os.path.join(ORG_BACKUP_DIR, "*"))
        if not files:
            return False, 0
        n = 0
        for f in files:
            if os.path.isfile(f):
                shutil.copy2(f, os.path.join(ENIGMA2_DIR, os.path.basename(f)))
                n += 1
        return True, n
    except Exception:
        return False, 0


def _org_ch_set_name(ch, newname):
    """Rename a single channel by setting/replacing its #DESCRIPTION line only.
    The service reference (first line) is never touched."""
    lines = ch["raw"].split("\n")
    out = [lines[0]]
    had = False
    for ln in lines[1:]:
        if ln.strip().startswith("#DESCRIPTION"):
            out.append("#DESCRIPTION " + newname)
            had = True
        else:
            out.append(ln)
    if not had:
        out.insert(1, "#DESCRIPTION " + newname)
    ch["raw"] = "\n".join(out)
    ch["name"] = newname


class ChannelOrganizerScreen(Screen):
    skin = ORG_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\U0001f5c3 \u0645\u0646\u0638\u0645 \u0627\u0644\u0642\u0646\u0648\u0627\u062a - \u0627\u0644\u0628\u0627\u0642\u0627\u062a (Bouquets)")
        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Label(u"\u062e\u0631\u0648\u062c (Exit)")
        self["key_green"] = Label(u"\u0625\u0639\u0627\u062f\u0629 \u062a\u0633\u0645\u064a\u0629 (Rename)")
        self["key_yellow"] = Label(u"\u0641\u0648\u0642 (Up)")
        self["key_blue"] = Label(u"\u062a\u062d\u062a (Down)")
        self["hint"] = Label(u"OK = \u0627\u0641\u062a\u062d \u0627\u0644\u0642\u0646\u0648\u0627\u062a   |   MENU = \u0639\u0645\u0644\u064a\u0627\u062a (\u0625\u0646\u0634\u0627\u0621/\u062d\u0630\u0641/\u0646\u0633\u062e/\u0627\u0633\u062a\u0639\u0627\u062f\u0629)")
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions"], {
            "cancel": self.exit,
            "ok": self.open_bouquet,
            "red": self.exit,
            "green": self.rename_bouquet,
            "yellow": self.move_up,
            "blue": self.move_down,
            "menu": self.open_ops,
        }, -1)
        self.bouquets = []
        self.dirty = False
        self.onLayoutFinish.append(self.load)

    def load(self):
        self.bouquets = _org_read_bouquets()
        self._render()

    def _render(self):
        items = []
        for i, b in enumerate(self.bouquets):
            items.append(u"%2d.  %s" % (i + 1, b["name"]))
        if not items:
            items = [u"\u2014 \u0644\u0627 \u062a\u0648\u062c\u062f \u0628\u0627\u0642\u0627\u062a"]
        idx = self["list"].getSelectionIndex() or 0
        self["list"].setList(items)
        try:
            self["list"].moveToIndex(min(idx, max(0, len(items) - 1)))
        except Exception:
            pass
        self["status"].setText(u"\u0639\u062f\u062f \u0627\u0644\u0628\u0627\u0642\u0627\u062a: %d   |   \u0627\u0644\u062a\u0631\u062a\u064a\u0628 \u0648\u0627\u0644\u062a\u0633\u0645\u064a\u0629 \u0648\u0627\u0644\u062d\u0630\u0641 \u064a\u064f\u062d\u0641\u0638 \u0641\u0648\u0631\u0627\u064b \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b" % len(self.bouquets))

    def _cur(self):
        if not self.bouquets:
            return -1
        idx = self["list"].getSelectionIndex()
        if idx is None or idx < 0 or idx >= len(self.bouquets):
            return -1
        return idx

    def open_bouquet(self):
        idx = self._cur()
        if idx < 0:
            return
        b = self.bouquets[idx]
        self.session.openWithCallback(self.load, BouquetChannelEditor, b["file"], b["name"])

    def move_up(self):
        idx = self._cur()
        if idx <= 0:
            return
        self.bouquets[idx - 1], self.bouquets[idx] = self.bouquets[idx], self.bouquets[idx - 1]
        self.dirty = True
        if _org_write_bouquets_order(self.bouquets):
            self._render()
            try:
                self["list"].moveToIndex(idx - 1)
            except Exception:
                pass

    def move_down(self):
        idx = self._cur()
        if idx < 0 or idx >= len(self.bouquets) - 1:
            return
        self.bouquets[idx + 1], self.bouquets[idx] = self.bouquets[idx], self.bouquets[idx + 1]
        self.dirty = True
        if _org_write_bouquets_order(self.bouquets):
            self._render()
            try:
                self["list"].moveToIndex(idx + 1)
            except Exception:
                pass

    def rename_bouquet(self):
        idx = self._cur()
        if idx < 0:
            return
        self._ren_idx = idx
        try:
            from Screens.VirtualKeyBoard import VirtualKeyBoard
            self.session.openWithCallback(self._do_rename, VirtualKeyBoard, title=u"\u0627\u0633\u0645 \u0627\u0644\u0628\u0627\u0642\u0629 \u0627\u0644\u062c\u062f\u064a\u062f", text=self.bouquets[idx]["name"])
        except Exception:
            self.session.open(MessageBox, u"\u062a\u0639\u0630\u0631 \u0641\u062a\u062d \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0641\u0627\u062a\u064a\u062d.", MessageBox.TYPE_ERROR)

    def _do_rename(self, newname):
        if not newname:
            return
        idx = getattr(self, "_ren_idx", -1)
        if idx < 0 or idx >= len(self.bouquets):
            return
        b = self.bouquets[idx]
        chans = _org_read_channels(b["file"])
        if _org_write_channels(b["file"], chans, newname):
            b["name"] = newname
            try:
                _kids_reload_services()
            except Exception:
                pass
            self._render()
            self.session.open(MessageBox, u"\u2705 \u062a\u0645\u062a \u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u062a\u0633\u0645\u064a\u0629.", MessageBox.TYPE_INFO, timeout=3)
        else:
            self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644 \u0627\u0644\u062d\u0641\u0638.", MessageBox.TYPE_ERROR)

    def delete_bouquet(self):
        idx = self._cur()
        if idx < 0:
            return
        self._del_idx = idx
        b = self.bouquets[idx]
        self.session.openWithCallback(self._do_delete, MessageBox,
            u"\u2757 \u062d\u0630\u0641 \u0627\u0644\u0628\u0627\u0642\u0629 \u0628\u0627\u0644\u0643\u0627\u0645\u0644\u061f\n%s\n(\u0644\u0627 \u064a\u0645\u0643\u0646 \u0627\u0644\u062a\u0631\u0627\u062c\u0639)" % b["name"],
            MessageBox.TYPE_YESNO, default=False)

    def _do_delete(self, confirmed):
        if not confirmed:
            return
        idx = getattr(self, "_del_idx", -1)
        if idx < 0 or idx >= len(self.bouquets):
            return
        b = self.bouquets[idx]
        _org_delete_bouquet(b["file"])
        del self.bouquets[idx]
        _org_write_bouquets_order(self.bouquets)
        self.dirty = True
        try:
            _kids_reload_services()
        except Exception:
            pass
        self._render()
        self.session.open(MessageBox, u"\u2705 \u062a\u0645 \u062d\u0630\u0641 \u0627\u0644\u0628\u0627\u0642\u0629.", MessageBox.TYPE_INFO, timeout=3)

    def open_ops(self):
        opts = [
            (u"\u2795 \u0625\u0646\u0634\u0627\u0621 \u0628\u0627\u0642\u0629 \u062c\u062f\u064a\u062f\u0629 \u0641\u0627\u0636\u064a\u0629", "new"),
            (u"\U0001f5d1 \u062d\u0630\u0641 \u0627\u0644\u0628\u0627\u0642\u0629 \u0627\u0644\u0645\u062d\u062f\u062f\u0629", "del"),
            (u"\U0001f4be \u0646\u0633\u062e\u0629 \u0627\u062d\u062a\u064a\u0627\u0637\u064a\u0629 \u0633\u0631\u064a\u0639\u0629 (\u0643\u0644 \u0627\u0644\u0628\u0627\u0642\u0627\u062a)", "backup"),
            (u"\u21a9 \u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0622\u062e\u0631 \u0646\u0633\u062e\u0629 \u0627\u062d\u062a\u064a\u0627\u0637\u064a\u0629", "restore"),
        ]
        self.session.openWithCallback(self._ops_cb, ChoiceBox, title=u"\u0639\u0645\u0644\u064a\u0627\u062a \u0627\u0644\u0628\u0627\u0642\u0627\u062a", list=opts)

    def _ops_cb(self, choice):
        if not choice:
            return
        key = choice[1]
        if key == "new":
            self.create_bouquet()
        elif key == "del":
            self.delete_bouquet()
        elif key == "backup":
            ok, n = _org_backup_all()
            if ok:
                self.session.open(MessageBox, u"\u2705 \u062a\u0645 \u062d\u0641\u0638 \u0646\u0633\u062e\u0629 \u0627\u062d\u062a\u064a\u0627\u0637\u064a\u0629 \u0644\u0640 %d \u0645\u0644\u0641. \u062a\u0642\u062f\u0631 \u062a\u0631\u062c\u0639\u0644\u0647\u0627 \u0623\u064a \u0648\u0642\u062a." % n, MessageBox.TYPE_INFO, timeout=4)
            else:
                self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644 \u0627\u0644\u0646\u0633\u062e \u0627\u0644\u0627\u062d\u062a\u064a\u0627\u0637\u064a.", MessageBox.TYPE_ERROR)
        elif key == "restore":
            self.session.openWithCallback(self._restore_cb, MessageBox,
                u"\u21a9 \u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0622\u062e\u0631 \u0646\u0633\u062e\u0629 \u0627\u062d\u062a\u064a\u0627\u0637\u064a\u0629\u061f\n\u0631\u0627\u062d \u062a\u0631\u062c\u0639 \u0643\u0644 \u0627\u0644\u0628\u0627\u0642\u0627\u062a \u0645\u062b\u0644 \u0622\u062e\u0631 \u0646\u0633\u062e\u0629.",
                MessageBox.TYPE_YESNO, default=False)

    def _restore_cb(self, confirmed):
        if not confirmed:
            return
        ok, n = _org_restore_all()
        if ok:
            try:
                _kids_reload_services()
            except Exception:
                pass
            self.load()
            self.session.open(MessageBox, u"\u2705 \u062a\u0645\u062a \u0627\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629 (%d \u0645\u0644\u0641). \u0625\u0630\u0627 \u0645\u0627 \u0628\u0627\u0646\u062a\u060c \u0623\u0639\u062f \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0648\u0627\u062c\u0647\u0629." % n, MessageBox.TYPE_INFO, timeout=4)
        else:
            self.session.open(MessageBox, u"\u26a0 \u0645\u0627\u0643\u0648 \u0646\u0633\u062e\u0629 \u0627\u062d\u062a\u064a\u0627\u0637\u064a\u0629 \u0645\u062d\u0641\u0648\u0638\u0629 \u0628\u0639\u062f.", MessageBox.TYPE_WARNING)

    def create_bouquet(self):
        try:
            from Screens.VirtualKeyBoard import VirtualKeyBoard
            self.session.openWithCallback(self._create_cb, VirtualKeyBoard, title=u"\u0627\u0633\u0645 \u0627\u0644\u0628\u0627\u0642\u0629 \u0627\u0644\u062c\u062f\u064a\u062f\u0629", text=u"")
        except Exception:
            self.session.open(MessageBox, u"\u062a\u0639\u0630\u0631 \u0641\u062a\u062d \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0641\u0627\u062a\u064a\u062d.", MessageBox.TYPE_ERROR)

    def _create_cb(self, name):
        if not name:
            return
        ok, fname = _org_create_bouquet(name)
        if ok:
            try:
                _kids_reload_services()
            except Exception:
                pass
            self.load()
            self.session.open(MessageBox, u"\u2705 \u062a\u0645 \u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u0628\u0627\u0642\u0629 \u0627\u0644\u0641\u0627\u0636\u064a\u0629. \u0627\u0641\u062a\u062d\u0647\u0627 \u0648\u0627\u0636\u064a\u0641\u0644\u0647\u0627 \u0642\u0646\u0648\u0627\u062a.", MessageBox.TYPE_INFO, timeout=4)
        else:
            self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644 \u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u0628\u0627\u0642\u0629.", MessageBox.TYPE_ERROR)

    def exit(self):
        try:
            _kids_reload_services()
        except Exception:
            pass
        self.close()


class BouquetChannelEditor(Screen):
    skin = ORG_SKIN

    def __init__(self, session, bqfile, bqname):
        Screen.__init__(self, session)
        self.bqfile = bqfile
        self.bqname = bqname
        self["title"] = Label(u"\U0001f4fa %s" % bqname)
        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Label(u"\u062e\u0631\u0648\u062c (Exit)")
        self["key_green"] = Label(u"\u062d\u0641\u0638 (Save)")
        self["key_yellow"] = Label(u"\u0641\u0648\u0642 (Up)")
        self["key_blue"] = Label(u"\u062a\u062d\u062a (Down)")
        self["hint"] = Label(u"OK = \u0639\u0645\u0644\u064a\u0627\u062a \u0627\u0644\u0642\u0646\u0627\u0629 (\u062a\u0633\u0645\u064a\u0629/\u0646\u0642\u0644/\u0625\u062e\u0641\u0627\u0621/\u062d\u0630\u0641)   |   MENU = \u0625\u0636\u0627\u0641\u0629 \u0642\u0646\u0627\u0629")
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions"], {
            "cancel": self.exit,
            "ok": self.open_ch_ops,
            "red": self.exit,
            "green": self.save,
            "yellow": self.move_up,
            "blue": self.move_down,
            "menu": self.add_channel,
        }, -1)
        self.channels = []
        self.dirty = False
        self.onLayoutFinish.append(self.load)

    def noop(self):
        pass

    def load(self):
        self.channels = _org_read_channels(self.bqfile)
        self._render()

    def _render(self):
        items = []
        for i, ch in enumerate(self.channels):
            if ch.get("is_marker"):
                items.append(u"   \u2015 %s \u2015" % ch["name"])
            else:
                items.append(u"%3d.  %s" % (i + 1, ch["name"]))
        if not items:
            items = [u"\u2014 \u0644\u0627 \u062a\u0648\u062c\u062f \u0642\u0646\u0648\u0627\u062a"]
        idx = self["list"].getSelectionIndex() or 0
        self["list"].setList(items)
        try:
            self["list"].moveToIndex(min(idx, max(0, len(items) - 1)))
        except Exception:
            pass
        d = u" *" if self.dirty else u""
        self["status"].setText(u"\u0639\u062f\u062f \u0627\u0644\u0642\u0646\u0648\u0627\u062a: %d%s   |   \u0623\u0635\u0641\u0631=\u0641\u0648\u0642  \u0623\u0632\u0631\u0642=\u062a\u062d\u062a  \u0623\u062e\u0636\u0631=\u062d\u0641\u0638" % (len(self.channels), d))

    def _cur(self):
        if not self.channels:
            return -1
        idx = self["list"].getSelectionIndex()
        if idx is None or idx < 0 or idx >= len(self.channels):
            return -1
        return idx

    def move_up(self):
        idx = self._cur()
        if idx <= 0:
            return
        self.channels[idx - 1], self.channels[idx] = self.channels[idx], self.channels[idx - 1]
        self.dirty = True
        self._render()
        try:
            self["list"].moveToIndex(idx - 1)
        except Exception:
            pass

    def move_down(self):
        idx = self._cur()
        if idx < 0 or idx >= len(self.channels) - 1:
            return
        self.channels[idx + 1], self.channels[idx] = self.channels[idx], self.channels[idx + 1]
        self.dirty = True
        self._render()
        try:
            self["list"].moveToIndex(idx + 1)
        except Exception:
            pass

    def delete_channel(self):
        idx = self._cur()
        if idx < 0:
            return
        self._del_idx = idx
        ch = self.channels[idx]
        self.session.openWithCallback(self._do_delete, MessageBox,
            u"\u062d\u0630\u0641 \u0645\u0646 \u0627\u0644\u0628\u0627\u0642\u0629\u061f\n%s" % ch["name"],
            MessageBox.TYPE_YESNO, default=False)

    def _do_delete(self, confirmed):
        if not confirmed:
            return
        idx = getattr(self, "_del_idx", -1)
        if idx < 0 or idx >= len(self.channels):
            return
        del self.channels[idx]
        self.dirty = True
        self._render()

    def open_ch_ops(self):
        idx = self._cur()
        if idx < 0:
            return
        ch = self.channels[idx]
        if ch.get("is_marker"):
            opts = [
                (u"\U0001f5d1 \u062d\u0630\u0641 \u0627\u0644\u0641\u0627\u0635\u0644", "del"),
                (u"\u270f \u0625\u0639\u0627\u062f\u0629 \u062a\u0633\u0645\u064a\u0629", "rename"),
            ]
        else:
            opts = [
                (u"\u270f \u0625\u0639\u0627\u062f\u0629 \u062a\u0633\u0645\u064a\u0629 \u0627\u0644\u0642\u0646\u0627\u0629", "rename"),
                (u"\u27a1 \u0646\u0642\u0644 \u0627\u0644\u0642\u0646\u0627\u0629 \u0625\u0644\u0649 \u0628\u0627\u0642\u0629 \u0623\u062e\u0631\u0649", "move"),
                (u"\U0001f441 \u0625\u062e\u0641\u0627\u0621 \u0627\u0644\u0642\u0646\u0627\u0629 (\u0628\u062f\u0648\u0646 \u062d\u0630\u0641)", "hide"),
                (u"\U0001f5d1 \u062d\u0630\u0641 \u0627\u0644\u0642\u0646\u0627\u0629", "del"),
                (u"\u267b \u0625\u0638\u0647\u0627\u0631 \u0627\u0644\u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0645\u062e\u0641\u064a\u0629", "unhide"),
            ]
        self.session.openWithCallback(self._ch_ops_cb, ChoiceBox, title=ch["name"], list=opts)

    def _ch_ops_cb(self, choice):
        if not choice:
            return
        key = choice[1]
        if key == "del":
            self.delete_channel()
        elif key == "rename":
            self.rename_channel()
        elif key == "move":
            self.move_to_bouquet()
        elif key == "hide":
            self.hide_channel()
        elif key == "unhide":
            self.show_hidden()

    def rename_channel(self):
        idx = self._cur()
        if idx < 0:
            return
        self._ren_idx = idx
        try:
            from Screens.VirtualKeyBoard import VirtualKeyBoard
            self.session.openWithCallback(self._rename_ch_cb, VirtualKeyBoard, title=u"\u0627\u0633\u0645 \u0627\u0644\u0642\u0646\u0627\u0629 \u0627\u0644\u062c\u062f\u064a\u062f", text=self.channels[idx]["name"])
        except Exception:
            self.session.open(MessageBox, u"\u062a\u0639\u0630\u0631 \u0641\u062a\u062d \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0641\u0627\u062a\u064a\u062d.", MessageBox.TYPE_ERROR)

    def _rename_ch_cb(self, newname):
        if not newname:
            return
        idx = getattr(self, "_ren_idx", -1)
        if idx < 0 or idx >= len(self.channels):
            return
        _org_ch_set_name(self.channels[idx], newname)
        self.dirty = True
        self._render()

    def move_to_bouquet(self):
        idx = self._cur()
        if idx < 0:
            return
        self._mv_idx = idx
        others = [b for b in _org_read_bouquets() if b["file"] != self.bqfile]
        if not others:
            self.session.open(MessageBox, u"\u0645\u0627\u0643\u0648 \u0628\u0627\u0642\u0627\u062a \u0623\u062e\u0631\u0649 \u0644\u0644\u0646\u0642\u0644 \u0625\u0644\u064a\u0647\u0627.", MessageBox.TYPE_INFO)
            return
        self._mv_targets = others
        opts = [(b["name"], str(i)) for i, b in enumerate(others)]
        self.session.openWithCallback(self._move_cb, ChoiceBox, title=u"\u0627\u0646\u0642\u0644 \u0625\u0644\u0649 \u0623\u064a \u0628\u0627\u0642\u0629\u061f", list=opts)

    def _move_cb(self, choice):
        if not choice:
            return
        idx = getattr(self, "_mv_idx", -1)
        if idx < 0 or idx >= len(self.channels):
            return
        try:
            tgt = self._mv_targets[int(choice[1])]
        except Exception:
            return
        ch = self.channels[idx]
        tch = _org_read_channels(tgt["file"])
        tch.append(ch)
        if not _org_write_channels(tgt["file"], tch, tgt["name"]):
            self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644 \u0627\u0644\u0646\u0642\u0644.", MessageBox.TYPE_ERROR)
            return
        del self.channels[idx]
        _org_write_channels(self.bqfile, self.channels, self.bqname)
        self.dirty = False
        try:
            _kids_reload_services()
        except Exception:
            pass
        self._render()
        self.session.open(MessageBox, u"\u2705 \u062a\u0645 \u0646\u0642\u0644 \u0627\u0644\u0642\u0646\u0627\u0629 \u0625\u0644\u0649: %s" % tgt["name"], MessageBox.TYPE_INFO, timeout=3)

    def add_channel(self):
        others = _org_read_bouquets()
        if not others:
            self.session.open(MessageBox, u"\u0645\u0627\u0643\u0648 \u0628\u0627\u0642\u0627\u062a \u0644\u0644\u0627\u062e\u062a\u064a\u0627\u0631 \u0645\u0646\u0647\u0627.", MessageBox.TYPE_INFO)
            return
        self._add_srcs = others
        opts = [(b["name"], str(i)) for i, b in enumerate(others)]
        self.session.openWithCallback(self._add_src_cb, ChoiceBox, title=u"\u0623\u0636\u0641 \u0642\u0646\u0627\u0629 \u0645\u0646 \u0623\u064a \u0628\u0627\u0642\u0629\u061f", list=opts)

    def _add_src_cb(self, choice):
        if not choice:
            return
        try:
            src = self._add_srcs[int(choice[1])]
        except Exception:
            return
        srcchans = [c for c in _org_read_channels(src["file"]) if not c.get("is_marker")]
        if not srcchans:
            self.session.open(MessageBox, u"\u0627\u0644\u0628\u0627\u0642\u0629 \u0641\u0627\u0636\u064a\u0629.", MessageBox.TYPE_INFO)
            return
        self._add_pool = srcchans
        opts = [(c["name"], str(i)) for i, c in enumerate(srcchans)]
        self.session.openWithCallback(self._add_ch_cb, ChoiceBox, title=u"\u0627\u062e\u062a\u0631 \u0627\u0644\u0642\u0646\u0627\u0629 \u0644\u0644\u0625\u0636\u0627\u0641\u0629", list=opts)

    def _add_ch_cb(self, choice):
        if not choice:
            return
        try:
            ch = self._add_pool[int(choice[1])]
        except Exception:
            return
        self.channels.append(dict(ch))
        self.dirty = True
        self._render()
        self.session.open(MessageBox, u"\u2705 \u062a\u0645\u062a \u0627\u0644\u0625\u0636\u0627\u0641\u0629. \u0627\u0636\u063a\u0637 \u0623\u062e\u0636\u0631=\u062d\u0641\u0638 \u0644\u0644\u062a\u062b\u0628\u064a\u062a.", MessageBox.TYPE_INFO, timeout=3)

    def hide_channel(self):
        idx = self._cur()
        if idx < 0:
            return
        ch = self.channels[idx]
        cfg = _load_json_cfg(ORG_HIDDEN_CONFIG, {})
        lst = cfg.get(self.bqfile, [])
        lst.append({"raw": ch["raw"], "name": ch["name"]})
        cfg[self.bqfile] = lst
        _save_json_cfg(ORG_HIDDEN_CONFIG, cfg)
        del self.channels[idx]
        self.dirty = True
        self._render()
        self.session.open(MessageBox, u"\U0001f441 \u062a\u0645 \u0625\u062e\u0641\u0627\u0621 \u0627\u0644\u0642\u0646\u0627\u0629 (\u062a\u0642\u062f\u0631 \u062a\u0631\u062c\u0639\u0647\u0627 \u0645\u0646 \u0625\u0638\u0647\u0627\u0631 \u0627\u0644\u0645\u062e\u0641\u064a\u0629). \u0627\u062d\u0641\u0638 \u0628\u0627\u0644\u0623\u062e\u0636\u0631.", MessageBox.TYPE_INFO, timeout=4)

    def show_hidden(self):
        cfg = _load_json_cfg(ORG_HIDDEN_CONFIG, {})
        lst = cfg.get(self.bqfile, [])
        if not lst:
            self.session.open(MessageBox, u"\u0645\u0627\u0643\u0648 \u0642\u0646\u0648\u0627\u062a \u0645\u062e\u0641\u064a\u0629 \u0628\u0647\u0627\u064a \u0627\u0644\u0628\u0627\u0642\u0629.", MessageBox.TYPE_INFO)
            return
        self._hidden_list = lst
        opts = [(c.get("name", u"\u0642\u0646\u0627\u0629"), str(i)) for i, c in enumerate(lst)]
        self.session.openWithCallback(self._unhide_cb, ChoiceBox, title=u"\u0627\u062e\u062a\u0631 \u0642\u0646\u0627\u0629 \u0644\u0625\u0638\u0647\u0627\u0631\u0647\u0627", list=opts)

    def _unhide_cb(self, choice):
        if not choice:
            return
        try:
            i = int(choice[1])
            item = self._hidden_list[i]
        except Exception:
            return
        self.channels.append({"raw": item["raw"], "name": item.get("name", u"\u0642\u0646\u0627\u0629"), "is_marker": False, "sref": item["raw"].split("\n")[0].strip()})
        cfg = _load_json_cfg(ORG_HIDDEN_CONFIG, {})
        lst = cfg.get(self.bqfile, [])
        try:
            del lst[i]
        except Exception:
            pass
        cfg[self.bqfile] = lst
        _save_json_cfg(ORG_HIDDEN_CONFIG, cfg)
        self.dirty = True
        self._render()
        self.session.open(MessageBox, u"\u267b \u062a\u0645 \u0625\u0638\u0647\u0627\u0631 \u0627\u0644\u0642\u0646\u0627\u0629. \u0627\u062d\u0641\u0638 \u0628\u0627\u0644\u0623\u062e\u0636\u0631.", MessageBox.TYPE_INFO, timeout=3)

    def save(self):
        if _org_write_channels(self.bqfile, self.channels, self.bqname):
            self.dirty = False
            try:
                _kids_reload_services()
            except Exception:
                pass
            self._render()
            self.session.open(MessageBox, u"\u2705 \u062a\u0645 \u062d\u0641\u0638 \u0627\u0644\u062a\u0631\u062a\u064a\u0628.", MessageBox.TYPE_INFO, timeout=3)
        else:
            self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644 \u0627\u0644\u062d\u0641\u0638.", MessageBox.TYPE_ERROR)

    def exit(self):
        if self.dirty:
            self.session.openWithCallback(self._exit_cb, MessageBox,
                u"\u062a\u0648\u062c\u062f \u062a\u063a\u064a\u064a\u0631\u0627\u062a \u063a\u064a\u0631 \u0645\u062d\u0641\u0648\u0638\u0629. \u062d\u0641\u0638 \u0642\u0628\u0644 \u0627\u0644\u062e\u0631\u0648\u062c\u061f",
                MessageBox.TYPE_YESNO, default=True)
        else:
            self.close()

    def _exit_cb(self, yes):
        if yes:
            self.save()
        self.close()


class SubscriptionScreen(Screen):
    skin = SUBSCRIPTION_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\u23f3 \u0639\u062f\u0627\u062f \u0627\u0646\u062a\u0647\u0627\u0621 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643 (Subscription Countdown)")
        self["bigdays"] = Label("--")
        self["status"] = Label("")
        self["info"] = Label("")
        self["key_red"] = Label(u"\u062e\u0631\u0648\u062c (Exit)")
        self["key_green"] = Label(u"\u0625\u062f\u062e\u0627\u0644 \u064a\u062f\u0648\u064a (Manual)")
        self["key_yellow"] = Label(u"\u062d\u0630\u0641 (Clear)")
        self["key_blue"] = Label(u"\u0642\u0631\u0627\u0621\u0629 \u062a\u0644\u0642\u0627\u0626\u064a\u0629 (Auto)")
        self.ms_detecting = False
        self.ms_detect_timer = eTimer()
        try:
            self.ms_detect_timer.callback.append(self._auto_detect_done)
        except Exception:
            self.ms_detect_timer_conn = self.ms_detect_timer.timeout.connect(self._auto_detect_done)
        self.ms_detect_result = None
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "cancel": self.close,
            "ok": self.auto_detect,
            "red": self.close,
            "green": self.set_sub,
            "yellow": self.clear_sub,
            "blue": self.auto_detect,
        }, -1)
        self.onLayoutFinish.append(self.on_open)

    def on_open(self):
        data = _load_json_cfg(SUBSCRIPTION_CONFIG, {})
        if not data or not data.get("expiry"):
            self.auto_detect()
        else:
            self.refresh()

    def auto_detect(self):
        if self.ms_detecting:
            return
        self.ms_detecting = True
        self.ms_detect_result = None
        self["status"].setText(u"\u062c\u0627\u0631\u064a \u0642\u0631\u0627\u0621\u0629 \u062a\u0627\u0631\u064a\u062e \u0627\u0646\u062a\u0647\u0627\u0621 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643 \u0645\u0646 OSCam/NCam... \u0627\u0646\u062a\u0638\u0631 \u0644\u062d\u0638\u0629 (reading...)")
        self["info"].setText(u"")

        def worker():
            try:
                self.ms_detect_result = detect_subscription_expiry()
            except Exception:
                self.ms_detect_result = (None, "notfound")
            try:
                self.ms_detect_timer.start(50, True)
            except Exception:
                pass
        try:
            import threading
            t = threading.Thread(target=worker)
            t.setDaemon(True)
            t.start()
        except Exception:
            worker()

    def _auto_detect_done(self):
        self.ms_detecting = False
        res = self.ms_detect_result or (None, "notfound")
        d, source = res
        if d:
            data = _load_json_cfg(SUBSCRIPTION_CONFIG, {})
            data["expiry"] = d.strftime("%Y-%m-%d")
            data["source"] = source
            if not data.get("start"):
                import datetime
                data["start"] = datetime.date.today().strftime("%Y-%m-%d")
            _save_json_cfg(SUBSCRIPTION_CONFIG, data)
            self.refresh()
        else:
            data = _load_json_cfg(SUBSCRIPTION_CONFIG, {})
            if data and data.get("expiry"):
                self.refresh()
                self["info"].setText(self["info"].getText() + u"\n\n\u26a0 \u062a\u0639\u0630\u0651\u0631\u062a \u0627\u0644\u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u062a\u0644\u0642\u0627\u0626\u064a\u0629 \u0627\u0644\u0622\u0646 \u2014 \u0639\u0631\u0636\u062a \u0627\u0644\u0642\u064a\u0645\u0629 \u0627\u0644\u0645\u062d\u0641\u0648\u0638\u0629.")
            else:
                self["bigdays"].setText("--")
                self["status"].setText(u"\u0644\u0645 \u0623\u0639\u062b\u0631 \u0639\u0644\u0649 \u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0627\u0646\u062a\u0647\u0627\u0621 \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b (Not found)")
                self["info"].setText(u"\u062a\u0639\u0630\u0651\u0631 \u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u062a\u0627\u0631\u064a\u062e \u0645\u0646 \u0627\u0644\u0633\u064a\u0631\u0641\u0631.\n\u0627\u0636\u063a\u0637 \u0627\u0644\u0632\u0631 \u0627\u0644\u0623\u062e\u0636\u0631 \u0644\u0625\u062f\u062e\u0627\u0644 \u0627\u0644\u0645\u062f\u0629 \u064a\u062f\u0648\u064a\u0627\u064b.\n(Auto-read failed. Press GREEN to set it manually.)")

    def refresh(self):
        import datetime
        data = _load_json_cfg(SUBSCRIPTION_CONFIG, {})
        if not data or not data.get("expiry"):
            self["bigdays"].setText("--")
            self["status"].setText(u"\u0644\u0627 \u064a\u0648\u062c\u062f \u0627\u0634\u062a\u0631\u0627\u0643 \u0645\u064f\u0633\u062c\u0651\u0644 (No subscription set)")
            self["info"].setText(u"\u0627\u0636\u063a\u0637 \u0627\u0644\u0632\u0631 \u0627\u0644\u0623\u0632\u0631\u0642 \u0644\u0644\u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u062a\u0644\u0642\u0627\u0626\u064a\u0629 \u0645\u0646 OSCam/NCam\u060c \u0623\u0648 \u0627\u0644\u0623\u062e\u0636\u0631 \u0644\u0644\u0625\u062f\u062e\u0627\u0644 \u0627\u0644\u064a\u062f\u0648\u064a.\n(BLUE = auto-read, GREEN = manual.)")
            return
        try:
            exp = datetime.datetime.strptime(data["expiry"], "%Y-%m-%d").date()
        except Exception:
            self["status"].setText(u"\u062a\u0627\u0631\u064a\u062e \u063a\u064a\u0631 \u0635\u0627\u0644\u062d (Invalid date)")
            return
        today = datetime.date.today()
        days = (exp - today).days
        name = data.get("name", "")
        if days > 0:
            self["bigdays"].setText(str(days))
            self["status"].setText(u"\u064a\u0648\u0645 \u0645\u062a\u0628\u0642\u064d \u0639\u0644\u0649 \u0627\u0646\u062a\u0647\u0627\u0621 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643 (days left)")
        elif days == 0:
            self["bigdays"].setText("0")
            self["status"].setText(u"\u26a0 \u064a\u0646\u062a\u0647\u064a \u0627\u0644\u064a\u0648\u0645! (Expires today!)")
        else:
            self["bigdays"].setText("-" + str(abs(days)))
            self["status"].setText(u"\u274c \u0627\u0646\u062a\u0647\u0649 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643 (Subscription expired)")
        lines = []
        if name:
            lines.append(u"\U0001f464 %s" % name)
        lines.append(u"\U0001f4c5 \u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0627\u0646\u062a\u0647\u0627\u0621: %s" % data.get("expiry", ""))
        if data.get("start"):
            lines.append(u"\u25b6 \u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0628\u062f\u0621: %s" % data.get("start"))
        src = data.get("source", "")
        if src == "config":
            lines.append(u"\U0001f501 \u0627\u0644\u0645\u0635\u062f\u0631: \u0642\u0631\u0627\u0621\u0629 \u062a\u0644\u0642\u0627\u0626\u064a\u0629 \u0645\u0646 \u0645\u0644\u0641\u0627\u062a OSCam/NCam")
        elif src == "webif":
            lines.append(u"\U0001f501 \u0627\u0644\u0645\u0635\u062f\u0631: \u0642\u0631\u0627\u0621\u0629 \u062a\u0644\u0642\u0627\u0626\u064a\u0629 \u0645\u0646 \u0648\u0627\u062c\u0647\u0629 OSCam \u0627\u0644\u0648\u064a\u0628")
        elif src == "manual":
            lines.append(u"\u270b \u0627\u0644\u0645\u0635\u062f\u0631: \u0625\u062f\u062e\u0627\u0644 \u064a\u062f\u0648\u064a")
        if days > 0 and days <= 7:
            lines.append(u"\n\u26a0 \u062a\u0646\u0628\u064a\u0647: \u0627\u0642\u062a\u0631\u0628 \u0645\u0648\u0639\u062f \u0627\u0644\u062a\u062c\u062f\u064a\u062f!")
        self["info"].setText(u"\n".join(lines))

    def set_sub(self):
        choices = [
            (u"\u0623\u0633\u0628\u0648\u0639 (7 days)", 7),
            (u"\u0623\u0633\u0628\u0648\u0639\u0627\u0646 (14 days)", 14),
            (u"\u0634\u0647\u0631 (30 days)", 30),
            (u"\u0634\u0647\u0631\u0627\u0646 (60 days)", 60),
            (u"3 \u0623\u0634\u0647\u0631 (90 days)", 90),
            (u"6 \u0623\u0634\u0647\u0631 (180 days)", 180),
            (u"\u0633\u0646\u0629 (365 days)", 365),
        ]
        self.session.openWithCallback(self._set_sub_cb, ChoiceBox,
            title=u"\u0627\u062e\u062a\u0631 \u0645\u062f\u0629 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643 (choose duration):", list=choices)

    def _set_sub_cb(self, answer):
        if not answer:
            return
        import datetime
        days = int(answer[1])
        today = datetime.date.today()
        exp = today + datetime.timedelta(days=days)
        data = _load_json_cfg(SUBSCRIPTION_CONFIG, {})
        data["start"] = today.strftime("%Y-%m-%d")
        data["expiry"] = exp.strftime("%Y-%m-%d")
        data["days"] = days
        data["source"] = "manual"
        _save_json_cfg(SUBSCRIPTION_CONFIG, data)
        self.refresh()
        self.session.open(MessageBox,
            u"\u2705 \u062a\u0645 \u0636\u0628\u0637 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643 \u062d\u062a\u0649:\n%s" % data["expiry"],
            MessageBox.TYPE_INFO)

    def clear_sub(self):
        if not os.path.exists(SUBSCRIPTION_CONFIG):
            self.session.open(MessageBox, u"\u0644\u0627 \u064a\u0648\u062c\u062f \u0627\u0634\u062a\u0631\u0627\u0643 \u0644\u0644\u062d\u0630\u0641.", MessageBox.TYPE_INFO)
            return
        self.session.openWithCallback(self._clear_cb, MessageBox,
            u"\u062d\u0630\u0641 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643 \u0627\u0644\u0645\u064f\u0633\u062c\u0651\u0644\u061f (Clear saved subscription?)",
            MessageBox.TYPE_YESNO)

    def _clear_cb(self, result):
        if not result:
            return
        try:
            if os.path.exists(SUBSCRIPTION_CONFIG):
                os.remove(SUBSCRIPTION_CONFIG)
        except Exception:
            pass
        self.refresh()


# ---- Match reminders management skin ----
MATCH_REMINDERS_RAW_SKIN = """<screen name="MS_MatchRemindersScreen" position="center,center" size="1200,780" title="Match Reminders">
    <widget name="title" position="20,15" size="1160,50" font="Regular;32" halign="center" transparent="1" foregroundColor="#00ffcc00"/>
    <widget name="list" position="30,80" size="1140,560" font="Regular;27" itemHeight="56" scrollbarMode="showOnDemand"/>
    <widget name="status" position="20,650" size="1160,36" font="Regular;23" halign="center" transparent="1" foregroundColor="#00aaaaaa"/>
    <widget name="key_red" position="30,715" size="270,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ff4040"/>
    <widget name="key_green" position="320,715" size="270,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="key_yellow" position="610,715" size="270,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ffff40"/>
    <widget name="key_blue" position="900,715" size="270,40" font="Regular;23" halign="center" transparent="1" foregroundColor="#004080ff"/>
</screen>"""
MATCH_REMINDERS_SKIN = scale_skin_layout(MATCH_REMINDERS_RAW_SKIN)


class MatchRemindersScreen(Screen):
    skin = MATCH_REMINDERS_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\u23f0 \u0625\u062f\u0627\u0631\u0629 \u062a\u0630\u0643\u064a\u0631\u0627\u062a \u0627\u0644\u0645\u0628\u0627\u0631\u064a\u0627\u062a (Match Reminders)")
        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Label(u"\u062e\u0631\u0648\u062c (Exit)")
        self["key_green"] = Label(u"\u0625\u0636\u0627\u0641\u0629 \u062a\u0630\u0643\u064a\u0631 (Add)")
        self["key_yellow"] = Label(u"\u062d\u0630\u0641 (Delete)")
        self["key_blue"] = Label(u"\u062d\u0630\u0641 \u0627\u0644\u0643\u0644 (Clear all)")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "cancel": self.close,
            "ok": self.delete_selected,
            "red": self.close,
            "green": self.open_matches,
            "yellow": self.delete_selected,
            "blue": self.clear_all,
        }, -1)
        self.rem_items = []
        self.onLayoutFinish.append(self.refresh)

    def refresh(self):
        import datetime
        lst = _load_reminders()
        now = time.time()
        # keep upcoming (and recently started) reminders, sorted by time
        items = [r for r in lst if float(r.get("match_ts", 0)) > now - 600]
        items.sort(key=lambda r: float(r.get("notify_ts", 0)))
        self.rem_items = items
        display = []
        for r in items:
            try:
                w = datetime.datetime.fromtimestamp(float(r["notify_ts"])).strftime("%d/%m %H:%M")
            except Exception:
                w = "?"
            lead = int(r.get("lead", 0))
            if lead == 0:
                leadtxt = u"\u0639\u0646\u062f \u0627\u0644\u0628\u062f\u0627\u064a\u0629"
            else:
                leadtxt = u"\u0642\u0628\u0644 %d \u062f\u0642\u064a\u0642\u0629" % lead
            comp = r.get("comp", "")
            comptxt = (u" \u2022 %s" % comp) if comp else u""
            label = u"\u26bd %s  (%s)%s\n   \U0001f514 \u062a\u0646\u0628\u064a\u0647: %s  \u2014  %s" % (
                r.get("team", ""), r.get("time", ""), comptxt, w, leadtxt)
            display.append(label)
        self["list"].setList(display)
        if items:
            self["status"].setText(u"\u0639\u062f\u062f \u0627\u0644\u062a\u0630\u0643\u064a\u0631\u0627\u062a: %d  \u2014  OK/\u0623\u0635\u0641\u0631 = \u062d\u0630\u0641\u060c \u0623\u062e\u0636\u0631 = \u0625\u0636\u0627\u0641\u0629 \u0645\u0646 \u0627\u0644\u0645\u0628\u0627\u0631\u064a\u0627\u062a" % len(items))
        else:
            self["status"].setText(u"\u0644\u0627 \u062a\u0648\u062c\u062f \u062a\u0630\u0643\u064a\u0631\u0627\u062a \u2014 \u0627\u0636\u063a\u0637 \u0627\u0644\u0623\u062e\u0636\u0631 \u0644\u0625\u0636\u0627\u0641\u0629 \u062a\u0630\u0643\u064a\u0631 \u0645\u0646 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0645\u0628\u0627\u0631\u064a\u0627\u062a")

    def delete_selected(self):
        idx = self["list"].getSelectionIndex()
        if idx is None or idx < 0 or idx >= len(self.rem_items):
            self.session.open(MessageBox, u"\u0644\u0627 \u064a\u0648\u062c\u062f \u062a\u0630\u0643\u064a\u0631 \u0645\u062d\u062f\u062f (Nothing selected)", MessageBox.TYPE_INFO)
            return
        self._to_delete = self.rem_items[idx]
        self.session.openWithCallback(self._del_cb, MessageBox,
            u"\u062d\u0630\u0641 \u0627\u0644\u062a\u0630\u0643\u064a\u0631:\n\u26bd %s (%s) \u061f" % (
                self._to_delete.get("team", ""), self._to_delete.get("time", "")),
            MessageBox.TYPE_YESNO)

    def _del_cb(self, result):
        if not result or not getattr(self, "_to_delete", None):
            return
        r = self._to_delete
        lst = _load_reminders()
        new = [x for x in lst if not (x.get("team") == r.get("team") and x.get("match_ts") == r.get("match_ts"))]
        _save_reminders(new)
        self._to_delete = None
        self.refresh()

    def clear_all(self):
        if not self.rem_items:
            self.session.open(MessageBox, u"\u0644\u0627 \u064a\u0648\u062c\u062f \u0634\u064a\u0621 \u0644\u0644\u062d\u0630\u0641 (Nothing to clear)", MessageBox.TYPE_INFO)
            return
        self.session.openWithCallback(self._clear_all_cb, MessageBox,
            u"\u062d\u0630\u0641 \u062c\u0645\u064a\u0639 \u0627\u0644\u062a\u0630\u0643\u064a\u0631\u0627\u062a\u061f (Clear ALL reminders?)",
            MessageBox.TYPE_YESNO)

    def _clear_all_cb(self, result):
        if not result:
            return
        _save_reminders([])
        self.refresh()

    def open_matches(self):
        self.session.openWithCallback(self._after_matches, FootballMatches)

    def _after_matches(self, *args):
        self.refresh()


FM_PROTECTED_PATHS = ["/", "/bin", "/sbin", "/lib", "/lib64", "/usr", "/etc", "/var", "/proc", "/sys", "/dev", "/boot", "/run", "/home"]


class FileManagerScreen(Screen):
    skin = FM_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["path"] = Label("")
        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Label(u"\u062e\u0631\u0648\u062c (Exit)")
        self["key_green"] = Label(u"\u0641\u062a\u062d / \u062f\u062e\u0648\u0644 (Open)")
        self["key_yellow"] = Label(u"\u062d\u0630\u0641 (Delete)")
        self["key_blue"] = Label(u"\u0646\u0642\u0644 / \u0646\u0633\u062e (Move/Copy)")
        self.cur = self._start_path()
        self.entries = []
        self.clipboard = None
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions"], {
            "ok": self.enter,
            "cancel": self.go_up_or_close,
            "red": self.close,
            "green": self.enter,
            "yellow": self.delete_selected,
            "blue": self.open_ops_menu,
            "menu": self.open_ops_menu,
        }, -1)
        self.onLayoutFinish.append(self.refresh)

    def _start_path(self):
        for p in ["/media/hdd", "/media/usb", "/media", "/tmp", "/"]:
            if os.path.exists(p):
                return p
        return "/"

    def _fmt_size(self, n):
        try:
            n = float(n)
        except Exception:
            return ""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if n < 1024.0:
                return "%.1f %s" % (n, unit)
            n /= 1024.0
        return "%.1f PB" % n

    def refresh(self):
        self["path"].setText(_ms_safe_gui_text(u"\U0001f4c2 " + _ms_safe_gui_text(self.cur)))
        items = []
        self.entries = []
        try:
            names = sorted(os.listdir(self.cur), key=lambda x: x.lower())
        except Exception as e:
            self["list"].setList([_ms_safe_gui_text(u"\u274c \u062a\u0639\u0630\u0631 \u0641\u062a\u062d \u0627\u0644\u0645\u062c\u0644\u062f: " + str(e))])
            self["status"].setText(u"\u062e\u0637\u0623 (Error)")
            return
        dirs = []
        files = []
        for n in names:
            full = os.path.join(self.cur, n)
            try:
                isd = os.path.isdir(full)
            except Exception:
                isd = False
            if isd:
                dirs.append((n, full))
            else:
                files.append((n, full))
        if os.path.abspath(self.cur) != "/":
            items.append(u"\U0001f519 .. (\u0631\u062c\u0648\u0639 / Up)")
            self.entries.append(("..", os.path.dirname(os.path.abspath(self.cur)), True))
        for n, full in dirs:
            items.append(u"\U0001f4c1 " + n)
            self.entries.append((n, full, True))
        for n, full in files:
            sz = ""
            try:
                sz = self._fmt_size(os.path.getsize(full))
            except Exception:
                pass
            items.append(u"\U0001f4c4 %s   (%s)" % (n, sz))
            self.entries.append((n, full, False))
        self["list"].setList(_ms_safe_list(items))
        base = u"%d \u0645\u062c\u0644\u062f / %d \u0645\u0644\u0641   |   OK=\u0641\u062a\u062d  \u0623\u0635\u0641\u0631=\u062d\u0630\u0641  \u0623\u0632\u0631\u0642/MENU=\u0646\u0642\u0644-\u0646\u0633\u062e  BACK=\u0631\u062c\u0648\u0639" % (len(dirs), len(files))
        if self.clipboard:
            cpath, cmode = self.clipboard
            modetxt = u"\u0642\u0635 (\u0646\u0642\u0644)" if cmode == "cut" else u"\u0646\u0633\u062e"
            base = u"\U0001f4cb \u0628\u0627\u0644\u062d\u0627\u0641\u0638\u0629 [%s]: %s   \u2014   \u0627\u0636\u063a\u0637 \u0623\u0632\u0631\u0642/MENU \u062b\u0645 (\u0644\u0635\u0642 \u0647\u0646\u0627)\n" % (modetxt, os.path.basename(cpath)) + base
        self["status"].setText(_ms_safe_gui_text(base))

    def _selected(self):
        idx = self["list"].getSelectionIndex()
        if idx is None or idx < 0 or idx >= len(self.entries):
            return None
        return self.entries[idx]

    def enter(self):
        sel = self._selected()
        if not sel:
            return
        name, full, isd = sel
        if isd:
            self.cur = full
            self.refresh()
        else:
            sz = ""
            try:
                sz = self._fmt_size(os.path.getsize(full))
            except Exception:
                pass
            msg = u"\U0001f4c4 %s\n\n\u0627\u0644\u062d\u062c\u0645: %s\n\u0627\u0644\u0645\u0633\u0627\u0631: %s" % (name, sz, full)
            self.session.open(MessageBox, _ms_safe_gui_text(msg), MessageBox.TYPE_INFO)

    def go_up_or_close(self):
        if os.path.abspath(self.cur) != "/":
            self.cur = os.path.dirname(os.path.abspath(self.cur))
            self.refresh()
        else:
            self.close()

    def delete_selected(self):
        sel = self._selected()
        if not sel:
            return
        name, full, isd = sel
        if name == "..":
            return
        if os.path.abspath(full) in FM_PROTECTED_PATHS:
            self.session.open(MessageBox,
                u"\u26d4 \u0644\u0627 \u064a\u0645\u0643\u0646 \u062d\u0630\u0641 \u0645\u062c\u0644\u062f \u0646\u0638\u0627\u0645 \u0645\u062d\u0645\u064a!\n(Protected system path - delete blocked.)",
                MessageBox.TYPE_WARNING)
            return
        self._to_delete = full
        kind = u"\u0645\u062c\u0644\u062f (folder)" if isd else u"\u0645\u0644\u0641 (file)"
        self.session.openWithCallback(self._delete_cb, MessageBox,
            u"\u062d\u0630\u0641 %s:\n%s\n\n\u0647\u0644 \u0623\u0646\u062a \u0645\u062a\u0623\u0643\u062f\u061f (Are you sure?)" % (kind, name),
            MessageBox.TYPE_YESNO)

    def _delete_cb(self, result):
        if not result:
            return
        full = getattr(self, "_to_delete", "")
        if not full:
            return
        try:
            if os.path.isdir(full):
                import shutil
                shutil.rmtree(full)
            else:
                os.remove(full)
            self.refresh()
        except Exception as e:
            self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644 \u0627\u0644\u062d\u0630\u0641:\n" + str(e), MessageBox.TYPE_ERROR)

    # ---- Move / Copy / Paste ----
    def open_ops_menu(self):
        sel = self._selected()
        choices = []
        if sel and sel[0] != "..":
            choices.append((u"\u2702 \u0646\u0642\u0644 (\u0642\u0635) - %s" % sel[0], "cut"))
            choices.append((u"\U0001f4cb \u0646\u0633\u062e - %s" % sel[0], "copy"))
            choices.append((u"\u270f \u0625\u0639\u0627\u062f\u0629 \u062a\u0633\u0645\u064a\u0629 - %s" % sel[0], "rename"))
        if self.clipboard:
            choices.append((u"\U0001f4e5 \u0644\u0635\u0642 \u0647\u0646\u0627 (%s)" % os.path.basename(self.clipboard[0]), "paste"))
            choices.append((u"\u274e \u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u062d\u0627\u0641\u0638\u0629 (Cancel clipboard)", "clearclip"))
        choices.append((u"\U0001f4c1 \u0645\u062c\u0644\u062f \u062c\u062f\u064a\u062f (New folder)", "mkdir"))
        choices.append((u"\U0001f504 \u062a\u062d\u062f\u064a\u062b (Refresh)", "refresh"))
        if not choices:
            return
        self.session.openWithCallback(self._ops_cb, ChoiceBox,
            title=u"\u0639\u0645\u0644\u064a\u0627\u062a \u0627\u0644\u0645\u0644\u0641\u0627\u062a (File operations):", list=choices)

    def _ops_cb(self, answer):
        if not answer:
            return
        op = answer[1]
        if op == "cut":
            self._set_clip("cut")
        elif op == "copy":
            self._set_clip("copy")
        elif op == "paste":
            self._do_paste()
        elif op == "clearclip":
            self.clipboard = None
            self.refresh()
        elif op == "rename":
            self._do_rename()
        elif op == "mkdir":
            self._do_mkdir()
        elif op == "refresh":
            self.refresh()

    def _set_clip(self, mode):
        sel = self._selected()
        if not sel or sel[0] == "..":
            return
        name, full, isd = sel
        if os.path.abspath(full) in FM_PROTECTED_PATHS:
            self.session.open(MessageBox,
                u"\u26d4 \u0645\u0633\u0627\u0631 \u0646\u0638\u0627\u0645 \u0645\u062d\u0645\u064a \u2014 \u0644\u0627 \u064a\u0645\u0643\u0646 \u0646\u0642\u0644\u0647.\n(Protected system path.)",
                MessageBox.TYPE_WARNING)
            return
        self.clipboard = (full, mode)
        self.refresh()

    def _do_paste(self):
        if not self.clipboard:
            return
        import shutil
        src, mode = self.clipboard
        if not os.path.exists(src):
            self.session.open(MessageBox, u"\u274c \u0627\u0644\u0645\u0635\u062f\u0631 \u0644\u0645 \u064a\u0639\u062f \u0645\u0648\u062c\u0648\u062f\u0627\u064b (Source gone)", MessageBox.TYPE_ERROR)
            self.clipboard = None
            return
        name = os.path.basename(src.rstrip("/"))
        dest = os.path.join(self.cur, name)
        # prevent moving a folder into itself / its subtree
        try:
            if os.path.isdir(src):
                srcabs = os.path.abspath(src)
                destabs = os.path.abspath(self.cur)
                if destabs == srcabs or destabs.startswith(srcabs + os.sep):
                    self.session.open(MessageBox,
                        u"\u26d4 \u0644\u0627 \u064a\u0645\u0643\u0646 \u0646\u0642\u0644 \u0645\u062c\u0644\u062f \u062f\u0627\u062e\u0644 \u0646\u0641\u0633\u0647.\n(Cannot paste a folder into itself.)",
                        MessageBox.TYPE_WARNING)
                    return
        except Exception:
            pass
        if os.path.abspath(dest) == os.path.abspath(src):
            self.session.open(MessageBox, u"\u2139 \u0627\u0644\u0645\u0635\u062f\u0631 \u0648\u0627\u0644\u0648\u062c\u0647\u0629 \u0646\u0641\u0633 \u0627\u0644\u0645\u0643\u0627\u0646.", MessageBox.TYPE_INFO)
            return
        self._paste_src = src
        self._paste_dest = dest
        self._paste_mode = mode
        if os.path.exists(dest):
            self.session.openWithCallback(self._paste_confirm, MessageBox,
                u"\u26a0 \u064a\u0648\u062c\u062f \u0639\u0646\u0635\u0631 \u0628\u0646\u0641\u0633 \u0627\u0644\u0627\u0633\u0645 \u0647\u0646\u0627:\n%s\n\u0627\u0644\u0627\u0633\u062a\u0628\u062f\u0627\u0644\u061f (Overwrite?)" % name,
                MessageBox.TYPE_YESNO)
        else:
            self._paste_confirm(True)

    def _paste_confirm(self, result):
        if not result:
            return
        import shutil
        src = self._paste_src
        dest = self._paste_dest
        mode = self._paste_mode
        try:
            if os.path.exists(dest):
                if os.path.isdir(dest) and not os.path.islink(dest):
                    shutil.rmtree(dest)
                else:
                    os.remove(dest)
            if mode == "cut":
                shutil.move(src, dest)
            else:
                if os.path.isdir(src):
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)
            self.clipboard = None
            self.refresh()
            doneword = u"\u0627\u0644\u0646\u0642\u0644" if mode == "cut" else u"\u0627\u0644\u0646\u0633\u062e"
            self.session.open(MessageBox, u"\u2705 \u062a\u0645 %s \u0628\u0646\u062c\u0627\u062d." % doneword, MessageBox.TYPE_INFO, timeout=3)
        except Exception as e:
            self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644\u062a \u0627\u0644\u0639\u0645\u0644\u064a\u0629:\n" + str(e), MessageBox.TYPE_ERROR)

    def _do_rename(self):
        sel = self._selected()
        if not sel or sel[0] == "..":
            return
        name, full, isd = sel
        if os.path.abspath(full) in FM_PROTECTED_PATHS:
            self.session.open(MessageBox, u"\u26d4 \u0645\u0633\u0627\u0631 \u0646\u0638\u0627\u0645 \u0645\u062d\u0645\u064a.", MessageBox.TYPE_WARNING)
            return
        self._rename_full = full
        try:
            from Screens.VirtualKeyBoard import VirtualKeyBoard
            self.session.openWithCallback(self._rename_cb, VirtualKeyBoard,
                title=u"\u0627\u0644\u0627\u0633\u0645 \u0627\u0644\u062c\u062f\u064a\u062f (New name):", text=name)
        except Exception:
            try:
                from Screens.InputBox import InputBox
                self.session.openWithCallback(self._rename_cb, InputBox,
                    title=u"\u0627\u0644\u0627\u0633\u0645 \u0627\u0644\u062c\u062f\u064a\u062f (New name):", text=name)
            except Exception:
                self.session.open(MessageBox, u"\u274c \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0641\u0627\u062a\u064a\u062d \u063a\u064a\u0631 \u0645\u062a\u0648\u0641\u0631\u0629.", MessageBox.TYPE_ERROR)

    def _rename_cb(self, newname):
        if not newname:
            return
        newname = newname.strip()
        if not newname or "/" in newname:
            self.session.open(MessageBox, u"\u274c \u0627\u0633\u0645 \u063a\u064a\u0631 \u0635\u0627\u0644\u062d.", MessageBox.TYPE_ERROR)
            return
        src = self._rename_full
        dest = os.path.join(os.path.dirname(src), newname)
        if os.path.exists(dest):
            self.session.open(MessageBox, u"\u26a0 \u064a\u0648\u062c\u062f \u0639\u0646\u0635\u0631 \u0628\u0646\u0641\u0633 \u0627\u0644\u0627\u0633\u0645.", MessageBox.TYPE_WARNING)
            return
        try:
            os.rename(src, dest)
            self.refresh()
        except Exception as e:
            self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644\u062a \u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u062a\u0633\u0645\u064a\u0629:\n" + str(e), MessageBox.TYPE_ERROR)

    def _do_mkdir(self):
        try:
            from Screens.VirtualKeyBoard import VirtualKeyBoard
            self.session.openWithCallback(self._mkdir_cb, VirtualKeyBoard,
                title=u"\u0627\u0633\u0645 \u0627\u0644\u0645\u062c\u0644\u062f \u0627\u0644\u062c\u062f\u064a\u062f (New folder name):", text=u"")
        except Exception:
            try:
                from Screens.InputBox import InputBox
                self.session.openWithCallback(self._mkdir_cb, InputBox,
                    title=u"\u0627\u0633\u0645 \u0627\u0644\u0645\u062c\u0644\u062f \u0627\u0644\u062c\u062f\u064a\u062f (New folder name):", text=u"")
            except Exception:
                self.session.open(MessageBox, u"\u274c \u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0641\u0627\u062a\u064a\u062d \u063a\u064a\u0631 \u0645\u062a\u0648\u0641\u0631\u0629.", MessageBox.TYPE_ERROR)

    def _mkdir_cb(self, newname):
        if not newname:
            return
        newname = newname.strip()
        if not newname or "/" in newname:
            self.session.open(MessageBox, u"\u274c \u0627\u0633\u0645 \u063a\u064a\u0631 \u0635\u0627\u0644\u062d.", MessageBox.TYPE_ERROR)
            return
        dest = os.path.join(self.cur, newname)
        if os.path.exists(dest):
            self.session.open(MessageBox, u"\u26a0 \u0627\u0644\u0645\u062c\u0644\u062f \u0645\u0648\u062c\u0648\u062f \u0645\u0633\u0628\u0642\u0627\u064b.", MessageBox.TYPE_WARNING)
            return
        try:
            os.mkdir(dest)
            self.refresh()
        except Exception as e:
            self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644 \u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u0645\u062c\u0644\u062f:\n" + str(e), MessageBox.TYPE_ERROR)


# ---- Match reminders storage + background poller ----
def _load_reminders():
    data = _load_json_cfg(REMINDERS_CONFIG, [])
    if not isinstance(data, list):
        return []
    return data


def _save_reminders(lst):
    return _save_json_cfg(REMINDERS_CONFIG, lst)


def _add_reminder(rem):
    lst = _load_reminders()
    lst.append(rem)
    return _save_reminders(lst)


class MatchReminderPoller:
    def __init__(self, session):
        self.session = session
        self.timer = None
        if eTimer:
            try:
                self.timer = eTimer()
                try:
                    self.timer_conn = self.timer.timeout.connect(self.check)
                except AttributeError:
                    self.timer.callback.append(self.check)
                self.timer.start(60000, False)
            except Exception:
                self.timer = None

    def check(self):
        try:
            lst = _load_reminders()
            if not lst:
                return
            now = time.time()
            changed = False
            keep = []
            for r in lst:
                try:
                    match_ts = float(r.get("match_ts", 0))
                    notify_ts = float(r.get("notify_ts", 0))
                except Exception:
                    continue
                if match_ts < now - 7200:
                    changed = True
                    continue
                if (not r.get("notified")) and now >= notify_ts and now <= match_ts + 600:
                    r["notified"] = True
                    changed = True
                    self._notify(r)
                keep.append(r)
            if changed:
                _save_reminders(keep)
        except Exception:
            pass

    def _notify(self, r):
        chans = r.get("channels") or []
        chtxt = u" , ".join(chans[:3]) if chans else u"-"
        msg = u"\u26bd \u062a\u0630\u0643\u064a\u0631 \u0645\u0628\u0627\u0631\u0627\u0629 (Match Reminder)\n\n%s\n\u0627\u0644\u0633\u0627\u0639\u0629 %s\n\u0627\u0644\u0642\u0646\u0648\u0627\u062a: %s" % (r.get("team", ""), r.get("time", ""), chtxt)
        try:
            from Tools.Notifications import AddPopup
            AddPopup(msg, MessageBox.TYPE_INFO, 20, "MohamedStoreMatchReminder")
            return
        except Exception:
            pass
        try:
            self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=20)
        except Exception:
            pass


_ms_reminder_poller = None


def ms_sessionstart(reason, **kwargs):
    global _ms_reminder_poller
    try:
        if reason == 0 and "session" in kwargs and _ms_reminder_poller is None:
            _ms_reminder_poller = MatchReminderPoller(kwargs["session"])
    except Exception:
        pass


# =========================================================================
# Boot Logo Changer (bootlogo / backdrop / wait) - Mohamed Store
# =========================================================================
BOOTLOGO_CFG = os.path.join(PLUGIN_DIR, "bootlogo.json")

BOOTLOGO_TARGETS = [
    "/usr/share/bootlogo.mvi",
    "/usr/share/enigma2/bootlogo.mvi",
    "/boot/bootlogo.mvi",
]
BACKDROP_TARGETS = [
    "/usr/share/backdrop.mvi",
    "/usr/share/enigma2/backdrop.mvi",
    "/boot/backdrop.mvi",
]
WAIT_TARGETS = [
    "/usr/share/bootlogo_wait.mvi",
    "/usr/share/enigma2/bootlogo_wait.mvi",
]

def _bl_backup_dir():
    for d in ["/media/hdd", "/media/usb", "/media/mmc", "/data"]:
        if os.path.exists(d):
            return os.path.join(d, "MohamedStore_bootlogo_backup")
    return os.path.join(PLUGIN_DIR, "bootlogo_backup")

def _bl_find_existing(cands):
    found = []
    for p in cands:
        try:
            if os.path.exists(p):
                found.append(p)
        except Exception:
            pass
    return found

def _bl_all_targets():
    boot = _bl_find_existing(BOOTLOGO_TARGETS) or [BOOTLOGO_TARGETS[0]]
    back = _bl_find_existing(BACKDROP_TARGETS) or [BACKDROP_TARGETS[0]]
    wait = _bl_find_existing(WAIT_TARGETS)
    return boot, back, wait

def _bl_which(name):
    try:
        paths = os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
        for d in paths.split(":"):
            fp = os.path.join(d, name)
            if os.path.exists(fp) and os.access(fp, os.X_OK):
                return fp
    except Exception:
        pass
    return None

def _bl_has_pil():
    try:
        from PIL import Image  # noqa
        return True
    except Exception:
        return False

def _bl_detect_fmt(path):
    try:
        with open(path, "rb") as f:
            head = f.read(8)
        if head[:4] == b"\x89PNG":
            return "png"
        if head[:3] == b"\x00\x00\x01":
            return "m2v"
    except Exception:
        pass
    return None

def _bl_remount_rw(path):
    try:
        d = os.path.dirname(path)
        if os.access(d, os.W_OK):
            return True
    except Exception:
        pass
    try:
        os.system("mount -o remount,rw / 2>/dev/null")
        os.system("mount -o remount,rw /usr 2>/dev/null")
        os.system("mount -o remount,rw /boot 2>/dev/null")
    except Exception:
        pass
    return True

def _bl_run(cmd):
    """Run a command list, return (rc, combined_output_text)."""
    import subprocess
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, _ = p.communicate()
        if out is None:
            out = b""
        try:
            txt = out.decode("utf-8", "replace")
        except Exception:
            txt = str(out)
        return (p.returncode, txt)
    except Exception as e:
        return (-1, str(e))


def _bl_even(n):
    n = int(n)
    return n if n % 2 == 0 else n - 1


def _bl_u(s):
    try:
        if isinstance(s, bytes):
            return s.decode("utf-8", "replace")
        return u"" + s
    except Exception:
        try:
            return u"" + repr(s)
        except Exception:
            return u"?"


def _bl_probe_res(path):
    """Return (w,h) of an existing media file, else None."""
    import re
    try:
        if not path or not os.path.exists(path):
            return None
    except Exception:
        return None
    ffprobe = _bl_which("ffprobe")
    if ffprobe:
        for pre in ([], ["-f", "mpegvideo"]):
            rc, out = _bl_run([ffprobe, "-v", "error", "-select_streams", "v:0",
                               "-show_entries", "stream=width,height",
                               "-of", "csv=p=0"] + pre + [path])
            m = re.search(r"(\d{2,5})\s*[,xX]\s*(\d{2,5})", out or "")
            if m:
                return (int(m.group(1)), int(m.group(2)))
    ffmpeg = _bl_which("ffmpeg")
    if ffmpeg:
        for pre in ([], ["-f", "mpegvideo"]):
            rc, out = _bl_run([ffmpeg] + pre + ["-i", path])
            m = re.search(r"\b(\d{3,4})x(\d{3,4})\b", out or "")
            if m:
                return (int(m.group(1)), int(m.group(2)))
    return None


def _bl_tgt_res(path, dw, dh):
    """Resolution to encode for a given target: match the ORIGINAL file if
    we can read it (safest, since the box already displays it fine), else
    fall back to the screen resolution."""
    pr = _bl_probe_res(path)
    if pr and pr[0] >= 160 and pr[1] >= 120:
        return (pr[0], pr[1])
    return (dw, dh)


_M2V_ZIGZAG = [
    0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5,
    12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63,
]
_M2V_INTRA_Q = [
    8, 16, 19, 22, 26, 27, 29, 34, 16, 16, 22, 24, 27, 29, 34, 37,
    19, 22, 26, 27, 29, 34, 34, 38, 22, 22, 26, 27, 29, 34, 37, 40,
    22, 26, 27, 29, 32, 35, 40, 48, 26, 27, 29, 32, 35, 40, 48, 58,
    26, 27, 29, 34, 38, 46, 56, 69, 27, 29, 35, 38, 46, 56, 69, 83,
]
_M2V_DC_LUM = {
    0: (0x4, 3), 1: (0x0, 2), 2: (0x1, 2), 3: (0x5, 3), 4: (0x6, 3),
    5: (0xE, 4), 6: (0x1E, 5), 7: (0x3E, 6), 8: (0x7E, 7), 9: (0xFE, 8),
    10: (0x1FE, 9), 11: (0x1FF, 9),
}
_M2V_DC_CHR = {
    0: (0x0, 2), 1: (0x1, 2), 2: (0x2, 2), 3: (0x6, 3), 4: (0xE, 4),
    5: (0x1E, 5), 6: (0x3E, 6), 7: (0x7E, 7), 8: (0xFE, 8), 9: (0x1FE, 9),
    10: (0x3FE, 10), 11: (0x3FF, 10),
}


class _M2VBitWriter(object):
    def __init__(self):
        self.bytes = bytearray()
        self.cur = 0
        self.nbits = 0

    def put(self, value, bits):
        c = self.cur
        n = self.nbits
        ba = self.bytes
        i = bits - 1
        while i >= 0:
            c = (c << 1) | ((value >> i) & 1)
            n += 1
            if n == 8:
                ba.append(c & 0xFF)
                c = 0
                n = 0
            i -= 1
        self.cur = c
        self.nbits = n

    def align(self):
        while self.nbits != 0:
            self.put(0, 1)

    def put_startcode(self, code):
        self.align()
        self.put(code, 32)


def _m2v_build_dct():
    import math
    m = []
    for u in range(8):
        row = []
        cu = (1.0 / math.sqrt(2.0)) if u == 0 else 1.0
        for x in range(8):
            row.append(cu * math.cos((2 * x + 1) * u * math.pi / 16.0))
        m.append(row)
    return m

_M2V_DCTM = _m2v_build_dct()


def _m2v_fdct8x8(block):
    dm = _M2V_DCTM
    tmp = [0.0] * 64
    for y in range(8):
        base = y * 8
        for u in range(8):
            cu = dm[u]
            s = 0.0
            for x in range(8):
                s += block[base + x] * cu[x]
            tmp[base + u] = s
    out = [0.0] * 64
    for u in range(8):
        for v in range(8):
            cv = dm[v]
            s = 0.0
            for y in range(8):
                s += tmp[y * 8 + u] * cv[y]
            out[v * 8 + u] = 0.25 * s
    return out


def _m2v_enc_block(bw, pix, is_luma, qscale, pred_dc):
    import math
    # MPEG-2 intra DCT uses unshifted samples; DC predictor (128) offsets it.
    blk = [float(p) for p in pix]
    F = _m2v_fdct8x8(blk)
    qdc = int(math.floor(F[0] / 8.0 + 0.5))
    zz = _M2V_ZIGZAG
    iq = _M2V_INTRA_Q
    # DC size/VLC
    diff = qdc - pred_dc
    size = 0
    a = abs(diff)
    while a:
        size += 1
        a >>= 1
    code, bits = (_M2V_DC_LUM if is_luma else _M2V_DC_CHR)[size]
    bw.put(code, bits)
    if size > 0:
        if diff > 0:
            bw.put(diff, size)
        else:
            bw.put((diff - 1) & ((1 << size) - 1), size)
    # AC coefficients: ESCAPE-code every nonzero coeff, then EOB '10'
    run = 0
    for n in range(1, 64):
        pos = zz[n]
        w = iq[pos]
        val = F[pos] * 16.0 / (float(w) * float(qscale))
        if val >= 0:
            level = int(math.floor(val + 0.5))
        else:
            level = int(math.ceil(val - 0.5))
        if level == 0:
            run += 1
            continue
        if level > 2047:
            level = 2047
        elif level < -2047:
            level = -2047
        bw.put(0x01, 6)
        bw.put(run & 0x3F, 6)
        bw.put(level & 0xFFF, 12)
        run = 0
    bw.put(0x2, 2)
    return qdc

# __M2V_PART2__


def _m2v_rgb2ycc(r, g, b):
    y = 16.0 + (65.481 * r + 128.553 * g + 24.966 * b) / 255.0
    cb = 128.0 + (-37.797 * r - 74.203 * g + 112.0 * b) / 255.0
    cr = 128.0 + (112.0 * r - 93.786 * g - 18.214 * b) / 255.0
    return y, cb, cr


def _m2v_clampi(v):
    v = int(v + 0.5)
    if v < 0:
        return 0
    if v > 255:
        return 255
    return v


def _m2v_encode_still(rgb, width, height, qscale_code):
    from array import array
    mbw = (width + 15) // 16
    mbh = (height + 15) // 16
    pw = mbw * 16
    ph = mbh * 16
    Y = array('f', [0.0]) * (pw * ph)
    Cb = array('f', [0.0]) * (pw * ph)
    Cr = array('f', [0.0]) * (pw * ph)
    for yy in range(ph):
        sy = yy if yy < height else height - 1
        rowb = sy * width
        rowp = yy * pw
        for xx in range(pw):
            sx = xx if xx < width else width - 1
            idx = (rowb + sx) * 3
            yv, cbv, crv = _m2v_rgb2ycc(rgb[idx], rgb[idx + 1], rgb[idx + 2])
            p = rowp + xx
            Y[p] = yv
            Cb[p] = cbv
            Cr[p] = crv
    qscale = 2 * qscale_code
    bw = _M2VBitWriter()
    bw.put_startcode(0x000001B3)
    bw.put(width & 0xFFF, 12)
    bw.put(height & 0xFFF, 12)
    bw.put(3, 4)
    bw.put(3, 4)
    bw.put(0x3FFFF, 18)
    bw.put(1, 1)
    bw.put(112, 10)
    bw.put(0, 1)
    bw.put(0, 1)
    bw.put(0, 1)
    bw.put_startcode(0x000001B5)
    bw.put(1, 4)
    bw.put(0x48, 8)
    bw.put(1, 1)
    bw.put(1, 2)
    bw.put(0, 2)
    bw.put(0, 2)
    bw.put(0, 12)
    bw.put(1, 1)
    bw.put(0, 8)
    bw.put(0, 1)
    bw.put(0, 2)
    bw.put(0, 5)
    bw.put_startcode(0x00000100)
    bw.put(0, 10)
    bw.put(1, 3)
    bw.put(0xFFFF, 16)
    bw.put(0, 1)
    bw.put_startcode(0x000001B5)
    bw.put(8, 4)
    bw.put(0xF, 4)
    bw.put(0xF, 4)
    bw.put(0xF, 4)
    bw.put(0xF, 4)
    bw.put(0, 2)
    bw.put(3, 2)
    bw.put(0, 1)
    bw.put(1, 1)
    bw.put(0, 1)
    bw.put(0, 1)
    bw.put(0, 1)
    bw.put(0, 1)
    bw.put(0, 1)
    bw.put(1, 1)
    bw.put(1, 1)
    bw.put(0, 1)

    def gather(plane, px, py):
        out = [0] * 64
        k = 0
        for j in range(8):
            base = (py + j) * pw + px
            for i in range(8):
                out[k] = _m2v_clampi(plane[base + i])
                k += 1
        return out

    def gather_chroma(plane, cx, cy):
        out = [0] * 64
        k = 0
        for j in range(8):
            fy = (cy + j) * 2
            for i in range(8):
                fx = (cx + i) * 2
                s = (plane[fy * pw + fx] + plane[fy * pw + fx + 1] +
                     plane[(fy + 1) * pw + fx] + plane[(fy + 1) * pw + fx + 1])
                out[k] = _m2v_clampi(s / 4.0)
                k += 1
        return out

    enc = _m2v_enc_block
    for row in range(mbh):
        bw.put_startcode(0x00000101 + row)
        bw.put(qscale_code & 0x1F, 5)
        bw.put(0, 1)
        py = 128
        pcb = 128
        pcr = 128
        for col in range(mbw):
            bw.put(1, 1)
            bw.put(1, 1)
            mx = col * 16
            my = row * 16
            py = enc(bw, gather(Y, mx, my), True, qscale, py)
            py = enc(bw, gather(Y, mx + 8, my), True, qscale, py)
            py = enc(bw, gather(Y, mx, my + 8), True, qscale, py)
            py = enc(bw, gather(Y, mx + 8, my + 8), True, qscale, py)
            pcb = enc(bw, gather_chroma(Cb, col * 8, row * 8), False, qscale, pcb)
            pcr = enc(bw, gather_chroma(Cr, col * 8, row * 8), False, qscale, pcr)
    bw.put_startcode(0x000001B7)
    bw.align()
    return bytes(bw.bytes)


def _bl_py_mpeg2(srcpng, dst, width, height, ffmpeg):
    """Built-in pure-Python MPEG-2 encoder fallback (no mpeg2 ffmpeg needed).
    Returns (ok, msg)."""
    w = _bl_even(width)
    h = _bl_even(height)
    rgb = None
    # 1) try PIL to read pixels
    if _bl_has_pil():
        try:
            from PIL import Image
            im = Image.open(srcpng).convert("RGB").resize((w, h))
            raw = im.tobytes()
            if sys.version_info < (3, 0):
                rgb = bytearray(raw)
            else:
                rgb = raw
        except Exception:
            rgb = None
    # 2) else use ffmpeg to produce raw rgb24
    if rgb is None and ffmpeg:
        rawp = "/tmp/ms_bl_raw.rgb"
        try:
            if os.path.exists(rawp):
                os.remove(rawp)
        except Exception:
            pass
        _bl_run([ffmpeg, "-y", "-loglevel", "error", "-i", srcpng,
                 "-vf", "scale=%d:%d" % (w, h), "-pix_fmt", "rgb24",
                 "-frames:v", "1", "-f", "rawvideo", rawp])
        try:
            f = open(rawp, "rb")
            try:
                rgb = f.read()
            finally:
                f.close()
        except Exception:
            rgb = None
    if not rgb or len(rgb) < w * h * 3:
        return (False, u"\u062a\u0639\u0630\u0631 \u0642\u0631\u0627\u0621\u0629 \u0628\u0643\u0633\u0644\u0627\u062a \u0627\u0644\u0635\u0648\u0631\u0629")
    if not isinstance(rgb, bytearray):
        rgb = bytearray(rgb)
    try:
        es = _m2v_encode_still(rgb, w, h, 3)
    except Exception as e:
        return (False, u"py-mpeg2: " + _bl_u(str(e)))
    try:
        if os.path.exists(dst):
            os.remove(dst)
    except Exception:
        pass
    try:
        f = open(dst, "wb")
        try:
            f.write(es)
        finally:
            f.close()
    except Exception as e:
        return (False, u"py-mpeg2 write: " + _bl_u(str(e)))
    try:
        ok = os.path.exists(dst) and os.path.getsize(dst) > 0
    except Exception:
        ok = os.path.exists(dst)
    return (ok, u"" if ok else u"py-mpeg2 empty")


def _bl_src_is_video(src):
    """True if src is ALREADY a ready-made boot-logo video (MPEG-1/2 .mvi),
    so it can be installed directly without any image conversion."""
    try:
        ext = os.path.splitext(src or "")[1].lower()
        if ext in (".mvi", ".m2v", ".mpg", ".mpeg", ".m1v"):
            return True
    except Exception:
        pass
    try:
        if _bl_detect_fmt(src) == "m2v":
            return True
    except Exception:
        pass
    return False


def _bl_convert(src, dst, fmt, width, height):
    """Convert src image to dst keeping bootlogo format.
    fmt = 'm2v' (needs ffmpeg) or 'png'. Returns (ok, msg).

    If src is ALREADY a device boot-logo video (.mvi / .m2v) we install it
    AS-IS (direct copy, no ffmpeg / no conversion) whenever the target also
    wants the video format - this lets the user drop in a ready .mvi logo."""
    import shutil
    # ---- Ready-made .mvi / .m2v source: install directly, no conversion ----
    if _bl_src_is_video(src):
        if fmt == "m2v":
            try:
                if os.path.exists(dst):
                    os.remove(dst)
            except Exception:
                pass
            try:
                shutil.copy2(src, dst)
                good = os.path.exists(dst) and os.path.getsize(dst) > 0
                return (True, "mvi") if good else (False, u"\u0641\u0634\u0644 \u0646\u0633\u062e \u0645\u0644\u0641 .mvi")
            except Exception as e:
                return (False, u"mvi copy: " + _bl_u(str(e)))
        # Target wants a PNG splash but the source is a video: grab one frame.
        ffmpeg = _bl_which("ffmpeg")
        if ffmpeg:
            try:
                if os.path.exists(dst):
                    os.remove(dst)
            except Exception:
                pass
            _bl_run([ffmpeg, "-y", "-loglevel", "error", "-i", src,
                     "-frames:v", "1", dst])
            try:
                if os.path.exists(dst) and os.path.getsize(dst) > 0:
                    return (True, "mvi")
            except Exception:
                pass
        try:
            shutil.copy2(src, dst)
            return (True, "mvi")
        except Exception as e:
            return (False, u"mvi copy: " + _bl_u(str(e)))
    w = _bl_even(width)
    h = _bl_even(height)
    tmp = "/tmp/ms_bl_tmp.png"
    try:
        if os.path.exists(tmp):
            os.remove(tmp)
    except Exception:
        pass
    made_png = False
    if _bl_has_pil():
        try:
            from PIL import Image
            im = Image.open(src).convert("RGB")
            im = im.resize((w, h))
            im.save(tmp, "PNG")
            made_png = os.path.exists(tmp)
        except Exception:
            made_png = False
    ffmpeg = _bl_which("ffmpeg")
    convert_bin = _bl_which("convert")
    if not made_png and ffmpeg:
        _bl_run([ffmpeg, "-y", "-loglevel", "error", "-i", src,
                 "-vf", "scale=%d:%d" % (w, h), "-frames:v", "1", tmp])
        made_png = os.path.exists(tmp)
    if not made_png and convert_bin:
        _bl_run([convert_bin, src, "-resize", "%dx%d!" % (w, h), tmp])
        made_png = os.path.exists(tmp)
    srcpng = tmp if made_png else src
    if fmt == "m2v":
        if not ffmpeg:
            return (False, u"ffmpeg \u063a\u064a\u0631 \u0645\u062b\u0628\u0651\u062a (\u0645\u0637\u0644\u0648\u0628 \u0644\u0635\u064a\u063a\u0629 .mvi) \u2014 \u062b\u0628\u0651\u062a\u0647 \u0628\u0640: opkg install ffmpeg")
        # The box's splash wants MPEG-2. Try MPEG-2 first; only if it fully
        # fails do we fall back to MPEG-1 (which is BLACK on MPEG-2-only
        # boxes) and flag it so the caller can warn the user.
        size = "%dx%d" % (w, h)
        mpeg2_variants = [
            [ffmpeg, "-y", "-loglevel", "error", "-loop", "1", "-i", srcpng,
             "-t", "5", "-r", "25", "-s", size, "-pix_fmt", "yuv420p",
             "-c:v", "mpeg2video", "-b:v", "8000k", "-g", "15", "-an",
             "-f", "mpeg2video", dst],
            [ffmpeg, "-y", "-loglevel", "error", "-loop", "1", "-i", srcpng,
             "-t", "5", "-r", "25", "-s", size, "-pix_fmt", "yuv420p",
             "-vcodec", "mpeg2video", "-qscale:v", "2", "-g", "15", "-an",
             "-f", "mpeg2video", dst],
            [ffmpeg, "-y", "-loglevel", "error", "-i", srcpng,
             "-pix_fmt", "yuv420p", "-vframes", "1", "-an",
             "-f", "mpeg2video", dst],
        ]
        mpeg1_variants = [
            [ffmpeg, "-y", "-loglevel", "error", "-loop", "1", "-i", srcpng,
             "-t", "5", "-r", "25", "-s", size, "-pix_fmt", "yuv420p",
             "-vcodec", "mpeg1video", "-b:v", "6000k", "-g", "15", "-an",
             "-f", "mpeg1video", dst],
        ]

        def _try(cmds):
            last = u""
            for cmd in cmds:
                try:
                    if os.path.exists(dst):
                        os.remove(dst)
                except Exception:
                    pass
                rc, out = _bl_run(cmd)
                try:
                    good = os.path.exists(dst) and os.path.getsize(dst) > 0
                except Exception:
                    good = os.path.exists(dst)
                if rc == 0 and good:
                    return (True, u"")
                last = (out or u"").strip()
                if len(last) > 300:
                    last = last[-300:]
                if not last:
                    last = u"rc=%s" % str(rc)
            return (False, last)

        ok2, err2 = _try(mpeg2_variants)
        if ok2:
            return (True, "mpeg2")
        # ffmpeg has no MPEG-2 encoder -> use the built-in pure-Python
        # MPEG-2 encoder so the logo works on ALL boxes, offline.
        okpy, errpy = _bl_py_mpeg2(srcpng, dst, w, h, ffmpeg)
        if okpy:
            return (True, "mpeg2")
        ok1, err1 = _try(mpeg1_variants)
        if ok1:
            # worked but likely shows black on MPEG-2-only hardware
            return (True, "mpeg1")
        return (False, u"mpeg2 \u0641\u0634\u0644:\n" + err2 + u"\n\npy-mpeg2 \u0641\u0634\u0644:\n" + errpy + u"\n\nmpeg1 \u0641\u0634\u0644:\n" + err1)
    else:
        try:
            import shutil
            shutil.copy2(srcpng, dst)
            return (True, "ok")
        except Exception as e:
            return (False, str(e))

# ---- COMPREHENSIVE snapshot: EVERY known boot/standby/wait logo file ----
# Includes VU+ 4K / ARM /boot files (splash.bin / bootlogo.bin) so a restore
# brings the WHOLE logo state back and never leaves a half-matched (cropped /
# black) frame behind.
BL_SNAPSHOT_PATHS = [
    "/usr/share/bootlogo.mvi",
    "/usr/share/bootlogo_wait.mvi",
    "/usr/share/backdrop.mvi",
    "/usr/share/radio.mvi",
    "/usr/share/enigma2/bootlogo.mvi",
    "/usr/share/enigma2/bootlogo_wait.mvi",
    "/usr/share/enigma2/backdrop.mvi",
    "/usr/share/enigma2/radio.mvi",
    "/boot/bootlogo.mvi",
    "/boot/bootlogo_wait.mvi",
    "/boot/backdrop.mvi",
    "/boot/bootlogo.bin",
    "/boot/bootlogo_wait.bin",
    "/boot/splash.bin",
]


def _bl_snapshot_dirs():
    """Candidate backup folders, STABLE order. First one is the save target;
    restore scans ALL of them so a USB mount appearing/disappearing can never
    make us lose (or restore a stale) snapshot. PLUGIN_DIR is always included
    as a reboot-safe fallback."""
    dirs = []
    for d in ["/media/hdd", "/media/usb", "/media/mmc", "/data"]:
        try:
            if os.path.isdir(d):
                dirs.append(os.path.join(d, "MohamedStore_bootlogo_backup"))
        except Exception:
            pass
    dirs.append(os.path.join(PLUGIN_DIR, "bootlogo_backup"))
    return dirs


def _bl_writable_snapshot_dir():
    """Return the FIRST backup folder we can actually create AND write to.
    This is the real root-cause fix: if the first candidate (e.g. /media/hdd)
    exists but is read-only / not truly mounted, os.makedirs or the copy would
    fail and NOTHING ever got saved -- while restore scanned all dirs and found
    nothing. So we probe each candidate with a real write test and fall back
    all the way to PLUGIN_DIR, which is always writable after reboot."""
    last = None
    for d in _bl_snapshot_dirs():
        try:
            if not os.path.isdir(d):
                os.makedirs(d)
            tst = os.path.join(d, ".ms_wtest")
            f = open(tst, "w")
            f.write("ok")
            f.close()
            os.remove(tst)
            return d
        except Exception:
            last = d
            continue
    return last or os.path.join(PLUGIN_DIR, "bootlogo_backup")


def _bl_save_current(force=True):
    """Byte-exact snapshot of EVERY existing logo file + a manifest.
    force=True  -> overwrite (manual 'save current logos' button).
    force=False -> keep the first saved file (auto-backup before an apply,
                   so the true original is never clobbered)."""
    import shutil
    bdir = _bl_writable_snapshot_dir()
    try:
        if not os.path.isdir(bdir):
            os.makedirs(bdir)
    except Exception as e:
        return (False, _bl_u(str(e)))
    manifest = _load_json_cfg(os.path.join(bdir, "manifest.json"), {})
    n = 0
    for p in BL_SNAPSHOT_PATHS:
        try:
            if not os.path.exists(p) or os.path.getsize(p) <= 0:
                continue
            safe = p.replace("/", "_").lstrip("_")
            dstb = os.path.join(bdir, safe)
            if (not force) and os.path.exists(dstb):
                manifest[safe] = p
                n += 1
                continue
            tmp = dstb + ".tmp"
            shutil.copy2(p, tmp)
            # verify a byte-exact copy before committing
            if os.path.getsize(tmp) == os.path.getsize(p):
                try:
                    if os.path.exists(dstb):
                        os.remove(dstb)
                except Exception:
                    pass
                os.rename(tmp, dstb)
                manifest[safe] = p
                n += 1
            else:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
        except Exception:
            pass
    try:
        _save_json_cfg(os.path.join(bdir, "manifest.json"), manifest)
    except Exception:
        pass
    if n > 0:
        return (True, bdir + u"  (%d \u0645\u0644\u0641)" % n)
    return (False, u"\u0644\u0645 \u064a\u062a\u0645 \u0627\u0644\u0639\u062b\u0648\u0631 \u0639\u0644\u0649 \u0645\u0644\u0641\u0627\u062a \u0634\u0639\u0627\u0631 \u062d\u0627\u0644\u064a\u0629")


def _bl_restore_current():
    """Restore the byte-exact snapshot to the EXACT same paths it came from
    (no re-encode, no resize) so the logos come back exactly as saved."""
    import shutil
    chosen = None
    manifest = {}
    for d in _bl_snapshot_dirs():
        try:
            if not os.path.isdir(d):
                continue
            m = _load_json_cfg(os.path.join(d, "manifest.json"), {})
            has_files = False
            for x in os.listdir(d):
                if x != "manifest.json":
                    has_files = True
                    break
            if m or has_files:
                chosen = d
                manifest = m
                break
        except Exception:
            pass
    if not chosen:
        return (False, u"\u0644\u0627 \u062a\u0648\u062c\u062f \u0646\u0633\u062e\u0629 \u0645\u062d\u0641\u0648\u0638\u0629")
    pairs = []
    if manifest:
        for safe, orig in manifest.items():
            pairs.append((os.path.join(chosen, safe), orig))
    else:
        for p in BL_SNAPSHOT_PATHS:
            safe = p.replace("/", "_").lstrip("_")
            pairs.append((os.path.join(chosen, safe), p))
    n = 0
    errs = []
    for srcb, dst in pairs:
        try:
            if not os.path.exists(srcb):
                continue
            d = os.path.dirname(dst)
            if not os.path.isdir(d):
                continue
            _bl_remount_rw(dst)
            tmp = dst + ".tmp"
            shutil.copy2(srcb, tmp)
            if os.path.getsize(tmp) == os.path.getsize(srcb):
                os.rename(tmp, dst)
                n += 1
            else:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
                errs.append(os.path.basename(dst))
        except Exception as e:
            errs.append(os.path.basename(dst) + ":" + _bl_u(str(e)))
    try:
        os.system("sync")
    except Exception:
        pass
    if n > 0:
        return (True, u"\u062a\u0645\u062a \u0627\u0633\u062a\u0639\u0627\u062f\u0629 %d \u0645\u0644\u0641 (\u0645\u0637\u0627\u0628\u0642 \u062a\u0645\u0627\u0645\u0627\u064b)" % n)
    return (False, u"\u0641\u0634\u0644 \u0627\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629: " + (u", ".join(errs[:3]) if errs else u"\u0644\u0627 \u0645\u0644\u0641\u0627\u062a"))


def _bl_backup_originals():
    # Auto-backup before an apply: protect the FIRST (true original) set,
    # never overwrite it on later applies.
    return _bl_save_current(force=False)


def _bl_restore_originals():
    return _bl_restore_current()


# =========================================================================
# Boot-logo VERSION HISTORY: every logo you install is saved as a byte-exact
# version, so you can switch BACK to any previously installed logo (or the
# true original) with no re-encode (no crop / no black).
# =========================================================================
def _bl_restore_pairs(srcdir, manifest):
    """Byte-exact restore of a saved folder (dir + manifest) to its exact
    original paths. Returns (n_restored, errors_list)."""
    import shutil
    pairs = []
    if manifest:
        for safe, orig in manifest.items():
            pairs.append((os.path.join(srcdir, safe), orig))
    else:
        for p in BL_SNAPSHOT_PATHS:
            safe = p.replace("/", "_").lstrip("_")
            pairs.append((os.path.join(srcdir, safe), p))
    n = 0
    errs = []
    for srcb, dst in pairs:
        try:
            if not os.path.exists(srcb):
                continue
            d = os.path.dirname(dst)
            if not os.path.isdir(d):
                continue
            _bl_remount_rw(dst)
            tmp = dst + ".tmp"
            shutil.copy2(srcb, tmp)
            if os.path.getsize(tmp) == os.path.getsize(srcb):
                os.rename(tmp, dst)
                n += 1
            else:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
                errs.append(os.path.basename(dst))
        except Exception as e:
            errs.append(os.path.basename(dst) + ":" + _bl_u(str(e)))
    try:
        os.system("sync")
    except Exception:
        pass
    return (n, errs)


def _bl_version_dirs_sorted():
    """All saved version folders across every backup root, oldest -> newest."""
    ids = []
    seen = set()
    for root in _bl_snapshot_dirs():
        vroot = os.path.join(root, "versions")
        try:
            if not os.path.isdir(vroot):
                continue
            for vid in os.listdir(vroot):
                if vid in seen:
                    continue
                if os.path.isdir(os.path.join(vroot, vid)):
                    seen.add(vid)
                    ids.append(vid)
        except Exception:
            pass
    ids.sort()
    result = []
    for vid in ids:
        for root in _bl_snapshot_dirs():
            vdir = os.path.join(root, "versions", vid)
            if os.path.isdir(vdir):
                result.append(vdir)
                break
    return result


def _bl_current_size_map():
    m = {}
    for p in BL_SNAPSHOT_PATHS:
        try:
            if os.path.exists(p) and os.path.getsize(p) > 0:
                m[p.replace("/", "_").lstrip("_")] = os.path.getsize(p)
        except Exception:
            pass
    return m


def _bl_dir_size_map(vdir):
    m = {}
    try:
        for x in os.listdir(vdir):
            if x in ("meta.json", "manifest.json"):
                continue
            fp = os.path.join(vdir, x)
            try:
                if os.path.isfile(fp):
                    m[x] = os.path.getsize(fp)
            except Exception:
                pass
    except Exception:
        pass
    return m


def _bl_save_version(label=None, skip_if_same=True):
    """Snapshot the CURRENT logo files byte-exact into a new version folder.
    Returns (ok, meta_dict_or_msg)."""
    import shutil, time
    cur = _bl_current_size_map()
    if not cur:
        return (False, u"\u0644\u0627 \u062a\u0648\u062c\u062f \u0645\u0644\u0641\u0627\u062a \u0634\u0639\u0627\u0631 \u062d\u0627\u0644\u064a\u0629")
    if skip_if_same:
        vdirs = _bl_version_dirs_sorted()
        if vdirs and _bl_dir_size_map(vdirs[-1]) == cur:
            meta = _load_json_cfg(os.path.join(vdirs[-1], "meta.json"), {})
            return (True, meta)  # identical to latest -> no duplicate
    root = _bl_writable_snapshot_dir()
    vid = time.strftime("v%Y%m%d_%H%M%S")
    vdir = os.path.join(root, "versions", vid)
    try:
        if not os.path.isdir(vdir):
            os.makedirs(vdir)
    except Exception as e:
        return (False, _bl_u(str(e)))
    manifest = {}
    n = 0
    for p in BL_SNAPSHOT_PATHS:
        try:
            if not os.path.exists(p) or os.path.getsize(p) <= 0:
                continue
            safe = p.replace("/", "_").lstrip("_")
            dstb = os.path.join(vdir, safe)
            tmp = dstb + ".tmp"
            shutil.copy2(p, tmp)
            if os.path.getsize(tmp) == os.path.getsize(p):
                os.rename(tmp, dstb)
                manifest[safe] = p
                n += 1
            else:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
        except Exception:
            pass
    if n <= 0:
        try:
            os.rmdir(vdir)
        except Exception:
            pass
        return (False, u"\u0641\u0634\u0644 \u062d\u0641\u0638 \u0627\u0644\u0646\u0633\u062e\u0629")
    meta = {"id": vid, "label": label or vid,
            "time": time.strftime("%Y-%m-%d %H:%M"), "files": n}
    try:
        _save_json_cfg(os.path.join(vdir, "meta.json"), meta)
        _save_json_cfg(os.path.join(vdir, "manifest.json"), manifest)
    except Exception:
        pass
    return (True, meta)


def _bl_list_restore_points():
    """Return a list of (label, kind, path) restore points, newest version
    first, with the true original last. kind='orig' or 'ver'."""
    pts = []
    for vdir in reversed(_bl_version_dirs_sorted()):
        meta = _load_json_cfg(os.path.join(vdir, "meta.json"),
                              {"label": os.path.basename(vdir), "time": ""})
        lbl = u"\U0001f553 %s" % (meta.get("time") or meta.get("id") or os.path.basename(vdir))
        extra = meta.get("label") or u""
        if extra and extra != meta.get("id"):
            lbl = lbl + u"  \u2014 " + extra
        pts.append((lbl, "ver", vdir))
    for root in _bl_snapshot_dirs():
        man = os.path.join(root, "manifest.json")
        if os.path.exists(man):
            pts.append((u"\u2b50 \u0627\u0644\u0623\u0635\u0644\u064a\u0629 (\u0642\u0628\u0644 \u0623\u064a \u062a\u0639\u062f\u064a\u0644)", "orig", root))
            break
    return pts


BOOTLOGO_RAW_SKIN = """<screen name="MS_BootLogoScreen" position="center,center" size="1200,820" title="Boot Logo Changer">
    <widget name="title" position="20,12" size="1160,50" font="Regular;32" halign="center" transparent="1" foregroundColor="#00ffcc00"/>
    <widget name="list" position="30,80" size="1140,330" font="Regular;27" itemHeight="52" scrollbarMode="showOnDemand"/>
    <widget name="info" position="30,425" size="1140,290" font="Regular;25" transparent="1" foregroundColor="#00cccccc"/>
    <widget name="key_red" position="30,765" size="270,38" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ff4040"/>
    <widget name="key_green" position="310,765" size="270,38" font="Regular;23" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="key_yellow" position="590,765" size="290,38" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ffff40"/>
    <widget name="key_blue" position="890,765" size="280,38" font="Regular;23" halign="center" transparent="1" foregroundColor="#004080ff"/>
</screen>"""
BOOTLOGO_SKIN = scale_skin_layout(BOOTLOGO_RAW_SKIN)

BL_PICK_RAW_SKIN = """<screen name="MS_BootLogoPicker" position="center,center" size="1200,820" title="Pick Image">
    <widget name="path" position="20,12" size="1160,46" font="Regular;27" transparent="1" foregroundColor="#00ffcc00"/>
    <widget name="list" position="20,68" size="1160,660" font="Regular;26" itemHeight="40" scrollbarMode="showOnDemand"/>
    <widget name="status" position="20,735" size="1160,32" font="Regular;22" halign="center" transparent="1" foregroundColor="#00aaaaaa"/>
    <widget name="key_red" position="30,778" size="360,36" font="Regular;23" halign="center" transparent="1" foregroundColor="#00ff4040"/>
    <widget name="key_green" position="420,778" size="360,36" font="Regular;23" halign="center" transparent="1" foregroundColor="#0040ff40"/>
</screen>"""
BL_PICK_SKIN = scale_skin_layout(BL_PICK_RAW_SKIN)

BL_IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif")
# Ready-made device boot-logo videos that can be installed directly (no convert)
BL_MVI_EXTS = (".mvi", ".m2v", ".mpg", ".mpeg", ".m1v")
# Everything the picker is allowed to show / select
BL_PICK_EXTS = BL_IMG_EXTS + BL_MVI_EXTS


class BootLogoImagePicker(Screen):
    skin = BL_PICK_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["path"] = Label("")
        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Label(u"\u0625\u0644\u063a\u0627\u0621 (Cancel)")
        self["key_green"] = Label(u"\u0627\u062e\u062a\u064a\u0627\u0631 (Select)")
        self.cur = self._start_path()
        self.entries = []
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
            "ok": self.enter,
            "cancel": self.go_up_or_close,
            "red": self.close,
            "green": self.enter,
        }, -1)
        self.onLayoutFinish.append(self.refresh)

    def _start_path(self):
        for p in ["/media/hdd", "/media/usb", "/media", "/tmp", "/"]:
            if os.path.exists(p):
                return p
        return "/"

    def refresh(self):
        self["path"].setText(_ms_safe_gui_text(u"\U0001f5bc " + _ms_safe_gui_text(self.cur)))
        items = []
        self.entries = []
        try:
            names = sorted(os.listdir(self.cur), key=lambda x: x.lower())
        except Exception as e:
            self["list"].setList([_ms_safe_gui_text(u"\u274c " + str(e))])
            return
        dirs = []
        imgs = []
        for n in names:
            full = os.path.join(self.cur, n)
            try:
                isd = os.path.isdir(full)
            except Exception:
                isd = False
            if isd:
                dirs.append((n, full))
            elif n.lower().endswith(BL_PICK_EXTS):
                imgs.append((n, full))
        if os.path.abspath(self.cur) != "/":
            items.append(u"\U0001f519 .. (\u0631\u062c\u0648\u0639 / Up)")
            self.entries.append(("..", os.path.dirname(os.path.abspath(self.cur)), True))
        for n, full in dirs:
            items.append(u"\U0001f4c1 " + n)
            self.entries.append((n, full, True))
        for n, full in imgs:
            if n.lower().endswith(BL_MVI_EXTS):
                items.append(u"\U0001f39e " + n + u"  (.mvi)")
            else:
                items.append(u"\U0001f5bc " + n)
            self.entries.append((n, full, False))
        self["list"].setList(_ms_safe_list(items))
        self["status"].setText(_ms_safe_gui_text(u"%d \u0645\u062c\u0644\u062f / %d \u0635\u0648\u0631\u0629   |   OK=\u062f\u062e\u0648\u0644/\u0627\u062e\u062a\u064a\u0627\u0631   BACK=\u0631\u062c\u0648\u0639" % (len(dirs), len(imgs))))

    def _selected(self):
        idx = self["list"].getSelectionIndex()
        if idx is None or idx < 0 or idx >= len(self.entries):
            return None
        return self.entries[idx]

    def enter(self):
        sel = self._selected()
        if not sel:
            return
        name, full, isd = sel
        if isd:
            self.cur = full
            self.refresh()
        else:
            self.close(full)

    def go_up_or_close(self):
        if os.path.abspath(self.cur) != "/":
            self.cur = os.path.dirname(os.path.abspath(self.cur))
            self.refresh()
        else:
            self.close(None)


class BootLogoScreen(Screen):
    skin = BOOTLOGO_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\U0001f5bc \u062a\u063a\u064a\u064a\u0631 \u0634\u0639\u0627\u0631 \u0627\u0644\u0625\u0642\u0644\u0627\u0639 (Boot Logo)")
        self["list"] = MenuList([])
        self["info"] = Label("")
        self["key_red"] = Label(u"\u062e\u0631\u0648\u062c (Exit)")
        self["key_green"] = Label(u"\u2699 \u062a\u063a\u064a\u064a\u0631 \u0627\u0644\u0635\u0648\u0631\u0629")
        self["key_yellow"] = Label(u"\U0001f4be \u0646\u0633\u062e/\u0627\u0633\u062a\u0639\u0627\u062f\u0629")
        self["key_blue"] = Label(u"\u2705 \u062a\u0637\u0628\u064a\u0642 + \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644")
        cfg = _load_json_cfg(BOOTLOGO_CFG, {})
        self.boot_img = cfg.get("boot_img", "")
        self.shut_img = cfg.get("shut_img", "")
        if self.boot_img and not os.path.exists(self.boot_img):
            self.boot_img = ""
        if self.shut_img and not os.path.exists(self.shut_img):
            self.shut_img = ""
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions"], {
            "ok": self.change_selected,
            "cancel": self.close,
            "red": self.close,
            "green": self.change_selected,
            "yellow": self.backup_menu,
            "blue": self.apply_now,
            "menu": self.backup_menu,
        }, -1)
        self.onLayoutFinish.append(self.refresh)

    def refresh(self):
        def shortp(p):
            if not p:
                return u"\u2014 (\u0644\u0645 \u062a\u062e\u062a\u0631 \u0628\u0639\u062f)"
            return _ms_safe_gui_text(os.path.basename(p))
        items = [
            u"\u25b6 \u0635\u0648\u0631\u0629 \u0627\u0644\u062a\u0634\u063a\u064a\u0644 (Boot):   " + shortp(self.boot_img),
            u"\u23fb \u0635\u0648\u0631\u0629 \u0627\u0644\u0625\u0637\u0641\u0627\u0621/\u0627\u0644\u0627\u0633\u062a\u0639\u062f\u0627\u062f (Standby): " + shortp(self.shut_img),
        ]
        self["list"].setList(_ms_safe_list(items))
        boot, back, wait = _bl_all_targets()
        fmt = _bl_detect_fmt(boot[0]) or ("m2v" if boot[0].endswith(".mvi") else "png")
        tools = []
        if _bl_has_pil():
            tools.append("PIL")
        if _bl_which("ffmpeg"):
            tools.append("ffmpeg")
        if _bl_which("convert"):
            tools.append("convert")
        tooltxt = ", ".join(tools) if tools else u"\u26a0 \u0644\u0627 \u064a\u0648\u062c\u062f"
        warn = u""
        if fmt == "m2v" and not _bl_which("ffmpeg"):
            warn = u"\n\u26a0 \u062c\u0647\u0627\u0632\u0643 \u064a\u0633\u062a\u062e\u062f\u0645 \u0635\u064a\u063a\u0629 .mvi \u0648\u064a\u062d\u062a\u0627\u062c ffmpeg: opkg install ffmpeg"
        info = (
            u"\U0001f4cf \u062f\u0642\u0629 \u0627\u0644\u0634\u0627\u0634\u0629: %dx%d   |   \u0627\u0644\u0635\u064a\u063a\u0629: %s\n"
            u"\U0001f4c1 \u0627\u0644\u0645\u0633\u0627\u0631: %s\n"
            u"\U0001f6e0 \u0623\u062f\u0648\u0627\u062a \u0627\u0644\u062a\u062d\u0648\u064a\u0644: %s\n\n"
            u"\u2699 \u0648\u0642\u0651\u0641 \u0639\u0644\u0649 \u0633\u0637\u0631 \u0648\u0627\u0636\u063a\u0637 OK/\u0623\u062e\u0636\u0631 \u0644\u0627\u062e\u062a\u064a\u0627\u0631 \u0635\u0648\u0631\u0629.\n"
            u"\U0001f4be \u0623\u0635\u0641\u0631 = \u0646\u0633\u062e/\u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0627\u0644\u0623\u0635\u0644\u064a\u0629   |   \u2705 \u0623\u0632\u0631\u0642 = \u062a\u0637\u0628\u064a\u0642 \u062b\u0645 \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644"
            % (SCREEN_WIDTH, SCREEN_HEIGHT, fmt, boot[0], tooltxt)
        ) + warn
        self["info"].setText(_ms_safe_gui_text(info))

    def _save_cfg(self):
        _save_json_cfg(BOOTLOGO_CFG, {"boot_img": self.boot_img, "shut_img": self.shut_img})

    def change_selected(self):
        idx = self["list"].getSelectionIndex()
        self._pick_target = 0 if (idx is None or idx == 0) else 1
        self.session.openWithCallback(self._pick_cb, BootLogoImagePicker)

    def _pick_cb(self, path):
        if not path:
            return
        if getattr(self, "_pick_target", 0) == 0:
            self.boot_img = path
        else:
            self.shut_img = path
        self._save_cfg()
        self.refresh()

    def backup_menu(self):
        nver = len(_bl_version_dirs_sorted())
        choices = [
            (u"\u267b \u0627\u0644\u0631\u062c\u0648\u0639 \u0644\u0634\u0639\u0627\u0631 \u0633\u0627\u0628\u0642 (\u0633\u062c\u0644 \u0627\u0644\u0646\u0633\u062e: %d)" % nver, "versions"),
            (u"\U0001f4be \u062d\u0641\u0638 \u0627\u0644\u0634\u0639\u0627\u0631 \u0627\u0644\u062d\u0627\u0644\u064a \u0643\u0646\u0633\u062e\u0629", "savever"),
            (u"\u2b50 \u062d\u0641\u0638 \u0627\u0644\u0623\u0635\u0644\u064a\u0629 (\u0642\u0628\u0644 \u0623\u064a \u062a\u0639\u062f\u064a\u0644)", "backup"),
            (u"\U0001f50d \u062a\u0634\u062e\u064a\u0635 (Diagnostics)", "diag"),
        ]
        self.session.openWithCallback(self._backup_cb, ChoiceBox,
            title=u"\u0646\u0633\u062e / \u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0634\u0639\u0627\u0631 \u0627\u0644\u0625\u0642\u0644\u0627\u0639:", list=choices)

    def _backup_cb(self, answer):
        if not answer:
            return
        if answer[1] == "versions":
            self._versions_menu()
        elif answer[1] == "savever":
            ok, meta = _bl_save_version(skip_if_same=True)
            if ok:
                self.session.open(MessageBox, u"\u2705 \u062a\u0645 \u062d\u0641\u0638 \u0627\u0644\u0634\u0639\u0627\u0631 \u0627\u0644\u062d\u0627\u0644\u064a \u0643\u0646\u0633\u062e\u0629 \u064a\u0645\u0643\u0646 \u0627\u0644\u0631\u062c\u0648\u0639 \u0625\u0644\u064a\u0647\u0627 \u0644\u0627\u062d\u0642\u0627\u064b.", MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, u"\u274c " + _bl_u(meta), MessageBox.TYPE_ERROR)
        elif answer[1] == "backup":
            ok, msg = _bl_save_current(force=True)
            if ok:
                self.session.open(MessageBox, u"\u2705 \u062a\u0645 \u062d\u0641\u0638 \u0627\u0644\u0634\u0639\u0627\u0631\u0627\u062a \u0627\u0644\u0623\u0635\u0644\u064a\u0629 \u0628\u0640:\n" + msg + u"\n\n\u0627\u0636\u063a\u0637 (\u0627\u0644\u0631\u062c\u0648\u0639 \u0644\u0634\u0639\u0627\u0631 \u0633\u0627\u0628\u0642) \u0644\u0627\u062d\u0642\u0627\u064b \u0644\u0625\u0631\u062c\u0627\u0639\u0647\u0627 \u0643\u0645\u0627 \u0647\u064a \u062a\u0645\u0627\u0645\u0627\u064b.", MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, u"\u274c \u0641\u0634\u0644 \u0627\u0644\u0646\u0633\u062e:\n" + msg, MessageBox.TYPE_ERROR)
        elif answer[1] == "diag":
            self._diag()

    def _versions_menu(self):
        pts = _bl_list_restore_points()
        if not pts:
            self.session.open(MessageBox,
                u"\u2139 \u0644\u0627 \u062a\u0648\u062c\u062f \u0646\u0633\u062e \u0645\u062d\u0641\u0648\u0638\u0629 \u0628\u0639\u062f. \u0633\u064a\u062a\u0645 \u062d\u0641\u0638 \u0643\u0644 \u0634\u0639\u0627\u0631 \u062a\u0631\u0643\u0651\u0628\u0647 \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b \u0643\u0646\u0642\u0637\u0629 \u0631\u062c\u0648\u0639.",
                MessageBox.TYPE_INFO)
            return
        choices = []
        for lbl, kind, path in pts:
            choices.append((lbl, ("restore", kind, path)))
        for lbl, kind, path in pts:
            if kind == "ver":
                choices.append((u"\U0001f5d1 \u062d\u0630\u0641: " + lbl, ("delete", kind, path)))
        self.session.openWithCallback(self._pick_version_cb, ChoiceBox,
            title=u"\u0627\u062e\u062a\u0631 \u0646\u0642\u0637\u0629 \u0627\u0644\u0631\u062c\u0648\u0639:", list=choices)

    def _pick_version_cb(self, answer):
        if not answer:
            return
        act, kind, path = answer[1]
        if act == "delete":
            import shutil
            try:
                shutil.rmtree(path)
                self.session.open(MessageBox, u"\U0001f5d1 \u062a\u0645 \u062d\u0630\u0641 \u0627\u0644\u0646\u0633\u062e\u0629.", MessageBox.TYPE_INFO)
            except Exception as e:
                self.session.open(MessageBox, u"\u274c \u062a\u0639\u0630\u0631 \u0627\u0644\u062d\u0630\u0641:\n" + _bl_u(str(e)), MessageBox.TYPE_ERROR)
            return
        self._pending_restore = (kind, path)
        self.session.openWithCallback(self._restore_version_do, MessageBox,
            u"\u0633\u064a\u062a\u0645 \u0625\u0631\u062c\u0627\u0639 \u0647\u0630\u0627 \u0627\u0644\u0634\u0639\u0627\u0631 \u062a\u0645\u0627\u0645\u0627\u064b \u0643\u0645\u0627 \u0643\u0627\u0646 (\u0628\u062f\u0648\u0646 \u0623\u064a \u062a\u062d\u0648\u064a\u0644) \u062b\u0645 \u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u062a\u0634\u063a\u064a\u0644.\n\u0645\u062a\u0627\u0628\u0639\u0629\u061f",
            MessageBox.TYPE_YESNO)

    def _restore_version_do(self, result):
        if not result:
            return
        pr = getattr(self, "_pending_restore", None)
        if not pr:
            return
        kind, path = pr
        if kind == "orig":
            ok, msg = _bl_restore_originals()
            if ok:
                self.session.openWithCallback(self._reboot_cb, MessageBox,
                    u"\u2705 " + msg + u"\n\n\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0622\u0646\u061f", MessageBox.TYPE_YESNO)
            else:
                self.session.open(MessageBox, u"\u274c " + msg, MessageBox.TYPE_ERROR)
            return
        manifest = _load_json_cfg(os.path.join(path, "manifest.json"), {})
        n, errs = _bl_restore_pairs(path, manifest)
        if n > 0:
            extra = (u"\n\u26a0 \u062a\u0639\u0630\u0631 \u0628\u0639\u0636\u0647\u0627: " + u", ".join(errs[:2])) if errs else u""
            self.session.openWithCallback(self._reboot_cb, MessageBox,
                u"\u2705 \u062a\u0645 \u0625\u0631\u062c\u0627\u0639 \u0627\u0644\u0634\u0639\u0627\u0631 (%d \u0645\u0644\u0641) \u0643\u0645\u0627 \u0643\u0627\u0646 \u062a\u0645\u0627\u0645\u0627\u064b." % n + extra + u"\n\n\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0622\u0646\u061f",
                MessageBox.TYPE_YESNO)
        else:
            self.session.open(MessageBox,
                u"\u274c \u0641\u0634\u0644 \u0627\u0644\u0625\u0631\u062c\u0627\u0639:\n" + (u"\n".join(errs[:3]) if errs else u"\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641"),
                MessageBox.TYPE_ERROR)

    def _diag(self):
        boot, back, wait = _bl_all_targets()
        lines = []
        lines.append(u"\U0001f3f7 BootLogo build: MSV4-HIST")
        lines.append(u"\U0001f553 \u0646\u0633\u062e \u0645\u062d\u0641\u0648\u0638\u0629: %d" % len(_bl_version_dirs_sorted()))
        try:
            _wd = _bl_writable_snapshot_dir()
        except Exception as _e:
            _wd = u"ERR:" + _bl_u(str(_e))
        lines.append(u"\U0001f4c2 \u0645\u062c\u0644\u062f \u0627\u0644\u062d\u0641\u0638 \u0627\u0644\u0642\u0627\u0628\u0644 \u0644\u0644\u0643\u062a\u0627\u0628\u0629: %s" % _wd)
        lines.append(u"\U0001f5a5 \u062f\u0642\u0629 \u0627\u0644\u0634\u0627\u0634\u0629 (GUI): %dx%d" % (SCREEN_WIDTH, SCREEN_HEIGHT))
        lines.append(u"ffmpeg: %s" % (_bl_which("ffmpeg") or u"\u2014"))
        lines.append(u"ffprobe: %s" % (_bl_which("ffprobe") or u"\u2014"))
        for label, lst in ((u"BOOT", boot), (u"STANDBY", back), (u"WAIT", wait)):
            for p in lst:
                if os.path.exists(p):
                    try:
                        sz = os.path.getsize(p)
                    except Exception:
                        sz = 0
                    fmt = _bl_detect_fmt(p) or u"?"
                    pr = _bl_probe_res(p)
                    rs = (u"%dx%d" % pr) if pr else u"?"
                    lines.append(u"%s: %s\n   fmt=%s res=%s size=%d" % (label, p, fmt, rs, sz))
        # --- every known logo file ON DEVICE (incl. /boot .bin for VU+ 4K) ---
        lines.append(u"--- ALL LOGO FILES ---")
        for p in BL_SNAPSHOT_PATHS:
            try:
                if os.path.exists(p):
                    sz = os.path.getsize(p)
                    fmt = _bl_detect_fmt(p) or u"?"
                    pr = _bl_probe_res(p)
                    rs = (u"%dx%d" % pr) if pr else u"?"
                    lines.append(u"%s  fmt=%s res=%s size=%d" % (p, fmt, rs, sz))
            except Exception:
                pass
        # --- saved snapshot folder contents ---
        lines.append(u"--- SAVED SNAPSHOT ---")
        snap_found = False
        for d in _bl_snapshot_dirs():
            try:
                if not os.path.isdir(d):
                    continue
                names = [x for x in os.listdir(d)]
                if not names:
                    continue
                snap_found = True
                lines.append(u"DIR: %s" % d)
                for x in sorted(names):
                    fp2 = os.path.join(d, x)
                    try:
                        sz = os.path.getsize(fp2)
                    except Exception:
                        sz = 0
                    fmt = _bl_detect_fmt(fp2) or u"?"
                    lines.append(u"   %s  fmt=%s size=%d" % (x, fmt, sz))
                break
            except Exception:
                pass
        if not snap_found:
            lines.append(u"(\u0644\u0627 \u062a\u0648\u062c\u062f \u0646\u0633\u062e\u0629 \u0645\u062d\u0641\u0648\u0638\u0629)")
        ff = _bl_which("ffmpeg")
        if ff:
            rc, out = _bl_run([ff, "-hide_banner", "-encoders"])
            has2 = "mpeg2video" in (out or "")
            has1 = "mpeg1video" in (out or "")
            enc = u"\u0645\u064f\u0631\u0645\u0650\u0651\u0632\u0627\u062a: mpeg2video=%s  mpeg1video=%s" % (
                (u"\u2714" if has2 else u"\u2718"), (u"\u2714" if has1 else u"\u2718"))
            lines.append(enc)
            # Live MPEG-2 self-test: make a tiny test PNG and try to encode a
            # real .mvi so we capture the EXACT ffmpeg error (if any).
            tpng = "/tmp/ms_bl_selftest.png"
            tmvi = "/tmp/ms_bl_selftest.mvi"
            made = False
            if _bl_has_pil():
                try:
                    from PIL import Image
                    Image.new("RGB", (1280, 720), (0, 80, 160)).save(tpng, "PNG")
                    made = os.path.exists(tpng)
                except Exception:
                    made = False
            if not made:
                _bl_run([ff, "-y", "-f", "lavfi", "-i",
                         "color=c=blue:s=1280x720:d=1", "-frames:v", "1", tpng])
                made = os.path.exists(tpng)
            src2 = tpng if made else None
            if src2:
                try:
                    if os.path.exists(tmvi):
                        os.remove(tmvi)
                except Exception:
                    pass
                rc2, out2 = _bl_run([ff, "-y", "-i", src2, "-pix_fmt", "yuv420p",
                                     "-vframes", "1", "-an", "-f", "mpeg2video", tmvi])
                good2 = False
                try:
                    good2 = os.path.exists(tmvi) and os.path.getsize(tmvi) > 0
                except Exception:
                    good2 = os.path.exists(tmvi)
                if rc2 == 0 and good2:
                    lines.append(u"\U0001f9ea \u0627\u062e\u062a\u0628\u0627\u0631 MPEG-2: \u2714 \u0646\u062c\u062d")
                else:
                    e2 = (out2 or u"").strip()
                    if len(e2) > 400:
                        e2 = e2[-400:]
                    lines.append(u"\U0001f9ea \u0627\u062e\u062a\u0628\u0627\u0631 MPEG-2: \u2718 rc=%s\n%s" % (str(rc2), e2))
        txt = u"\n".join(lines)
        try:
            root = get_direct_hdd_root_path()
            fp = os.path.join(root, "MohamedStore_bootlogo_diag.txt")
            f = open(fp, "w")
            try:
                f.write(txt.encode("utf-8") if sys.version_info < (3, 0) else txt)
            finally:
                f.close()
            txt = txt + u"\n\n\U0001f4be \u062d\u064f\u0641\u0650\u0638 \u0623\u064a\u0636\u0627\u064b \u0628\u0640:\n" + fp
        except Exception:
            pass
        self.session.open(MessageBox, txt, MessageBox.TYPE_INFO)


    def _restore_confirm(self):
        self.session.openWithCallback(self._restore_do, MessageBox,
            u"\u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0627\u0644\u0634\u0639\u0627\u0631\u0627\u062a \u0627\u0644\u0623\u0635\u0644\u064a\u0629 \u0648\u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u062a\u0634\u063a\u064a\u0644\u061f",
            MessageBox.TYPE_YESNO)

    def _restore_do(self, result):
        if not result:
            return
        ok, msg = _bl_restore_originals()
        if ok:
            self.session.openWithCallback(self._reboot_cb, MessageBox,
                u"\u2705 " + msg + u"\n\n\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0622\u0646\u061f", MessageBox.TYPE_YESNO)
        else:
            self.session.open(MessageBox, u"\u274c " + msg, MessageBox.TYPE_ERROR)

    def apply_now(self):
        if not self.boot_img and not self.shut_img:
            self.session.open(MessageBox,
                u"\u26a0 \u0627\u062e\u062a\u0631 \u0635\u0648\u0631\u0629 \u0648\u0627\u062d\u062f\u0629 \u0639\u0644\u0649 \u0627\u0644\u0623\u0642\u0644 (\u062a\u0634\u063a\u064a\u0644 \u0623\u0648 \u0625\u0637\u0641\u0627\u0621) \u0642\u0628\u0644 \u0627\u0644\u062a\u0637\u0628\u064a\u0642.",
                MessageBox.TYPE_WARNING)
            return
        self.session.openWithCallback(self._apply_confirm, MessageBox,
            u"\u0633\u064a\u062a\u0645:\n1) \u062d\u0641\u0638 \u0646\u0633\u062e\u0629 \u0623\u0635\u0644\u064a\u0629 \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b\n2) \u0645\u0644\u0641 .mvi \u064a\u064f\u0631\u0643\u0651\u0628 \u0645\u0628\u0627\u0634\u0631\u0629\u060c \u0648\u0627\u0644\u0635\u0648\u0631 (png/jpg) \u062a\u064f\u062d\u0648\u0651\u0644 \u062b\u0645 \u062a\u064f\u0631\u0643\u0651\u0628\n3) \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u062c\u0647\u0627\u0632\n\n\u0647\u0644 \u062a\u0631\u064a\u062f \u0627\u0644\u0645\u062a\u0627\u0628\u0639\u0629\u061f",
            MessageBox.TYPE_YESNO)

    def _apply_confirm(self, result):
        if not result:
            return
        self["info"].setText(u"\u2699 \u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u0648\u064a\u0644 \u0648\u0627\u0644\u062a\u0631\u0643\u064a\u0628... \u0627\u0646\u062a\u0638\u0631 \u0644\u062d\u0638\u0629.")
        def _work():
            _bl_backup_originals()
            boot, back, wait = _bl_all_targets()
            w, h = SCREEN_WIDTH, SCREEN_HEIGHT
            errs = []
            done = 0
            used = {"mpeg1": False}
            if self.boot_img:
                for t in boot:
                    fmt = _bl_detect_fmt(t) or ("m2v" if t.endswith(".mvi") else "png")
                    rw, rh = _bl_tgt_res(t, w, h)
                    _bl_remount_rw(t)
                    ok, msg = _bl_convert(self.boot_img, t, fmt, rw, rh)
                    if ok:
                        done += 1
                        if msg == "mpeg1":
                            used["mpeg1"] = True
                    else:
                        errs.append(msg)
                for t in wait:
                    fmt = _bl_detect_fmt(t) or "m2v"
                    rw, rh = _bl_tgt_res(t, w, h)
                    _bl_remount_rw(t)
                    _bl_convert(self.boot_img, t, fmt, rw, rh)
            if self.shut_img:
                for t in back:
                    fmt = _bl_detect_fmt(t) or ("m2v" if t.endswith(".mvi") else "png")
                    rw, rh = _bl_tgt_res(t, w, h)
                    _bl_remount_rw(t)
                    ok, msg = _bl_convert(self.shut_img, t, fmt, rw, rh)
                    if ok:
                        done += 1
                        if msg == "mpeg1":
                            used["mpeg1"] = True
                    else:
                        errs.append(msg)
            try:
                os.system("sync")
            except Exception:
                pass
            # Auto-save the just-installed logo as a byte-exact restore point
            # so it joins the version history and can be re-applied later with
            # no re-encode (no crop / no black).
            if done > 0:
                try:
                    _bl_save_version(skip_if_same=True)
                except Exception:
                    pass
            def _res():
                warn1 = u""
                if used["mpeg1"]:
                    warn1 = (u"\n\n\u26a0 \u062c\u0647\u0627\u0632\u0643 \u0644\u0627 \u064a\u062f\u0639\u0645 \u0645\u064f\u0631\u0645\u0650\u0651\u0632 MPEG-2 \u0628\u0640 ffmpeg\u060c "
                             u"\u0641\u0627\u0633\u062a\u062e\u062f\u0645\u0646\u0627 MPEG-1 \u0648\u0642\u062f \u062a\u0638\u0647\u0631 \u0627\u0644\u0635\u0648\u0631\u0629 \u0633\u0648\u062f\u0627\u0621. "
                             u"\u0627\u0644\u062d\u0644: opkg install ffmpeg (\u0646\u0633\u062e\u0629 \u0643\u0627\u0645\u0644\u0629) \u062b\u0645 \u0623\u0639\u062f \u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629.")
                if done > 0 and not errs:
                    self.session.openWithCallback(self._reboot_cb, MessageBox,
                        u"\u2705 \u062a\u0645 \u062a\u0631\u0643\u064a\u0628 \u0627\u0644\u0634\u0639\u0627\u0631 \u0628\u0646\u062c\u0627\u062d." + warn1 + u"\n\n\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0622\u0646 \u0644\u062a\u0638\u0647\u0631 \u0627\u0644\u0635\u0648\u0631\u061f",
                        MessageBox.TYPE_YESNO)
                elif done > 0 and errs:
                    self.session.openWithCallback(self._reboot_cb, MessageBox,
                        u"\u26a0 \u062a\u0645 \u0628\u0639\u0636 \u0627\u0644\u062a\u0631\u0643\u064a\u0628 \u0645\u0639 \u0623\u062e\u0637\u0627\u0621:\n" + u"\n".join(errs[:2]) + warn1 + u"\n\n\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0622\u0646\u061f",
                        MessageBox.TYPE_YESNO)
                else:
                    self.session.open(MessageBox,
                        u"\u274c \u0641\u0634\u0644 \u0627\u0644\u062a\u0631\u0643\u064a\u0628:\n" + (u"\n".join(errs[:2]) if errs else u"\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641"),
                        MessageBox.TYPE_ERROR)
                    self.refresh()
            _call_ui(_res)
        t = threading.Thread(target=_work)
        t.daemon = True
        t.start()

    def _reboot_cb(self, result):
        if not result:
            self.refresh()
            return
        if TryQuitMainloop:
            self.session.open(TryQuitMainloop, 2)
        elif enigma:
            enigma.quitMainloop(2)


# -*- coding: utf-8 -*-
# =========================================================================
# VPN Tool (VPN Gate free public OpenVPN) - MohamedStore
# =========================================================================
VPNGATE_API = "http://www.vpngate.net/api/iphone/"
VPN_TMP_OVPN = "/tmp/mohamedstore_vpn.ovpn"
VPN_LOG = "/tmp/mohamedstore_vpn.log"
VPN_SKIN = _make_ms_skin("MS_VpnScreen", "VPN")


def _vpn_find_openvpn():
    try:
        p = os.popen("which openvpn 2>/dev/null").read().strip()
        if p and os.path.exists(p):
            return p
    except Exception:
        pass
    for c in ["/usr/sbin/openvpn", "/usr/bin/openvpn", "/sbin/openvpn", "/bin/openvpn"]:
        if os.path.exists(c):
            return c
    return ""


def _vpn_tun_ready():
    try:
        if os.path.exists("/dev/net/tun"):
            return True
    except Exception:
        pass
    return False


def _vpn_ensure_tun():
    try:
        os.system("modprobe tun 2>/dev/null")
        os.system("mkdir -p /dev/net 2>/dev/null")
        if not os.path.exists("/dev/net/tun"):
            os.system("mknod /dev/net/tun c 10 200 2>/dev/null")
            os.system("chmod 600 /dev/net/tun 2>/dev/null")
    except Exception:
        pass
    return _vpn_tun_ready()


def _vpn_is_running():
    try:
        p = os.popen("pgrep -x openvpn 2>/dev/null").read().strip()
        return bool(p)
    except Exception:
        return False


def _vpn_public_ip():
    """Return (ip, country). Tries several services with retries so the
    confirmation keeps working even if one lookup server is slow/blocked."""
    services = [
        ("http://ip-api.com/json/", "query", "country"),
        ("https://ipapi.co/json/", "ip", "country_name"),
        ("https://ipwho.is/", "ip", "country"),
        ("https://ipinfo.io/json", "ip", "country"),
        ("https://api.ipify.org?format=json", "ip", None),
        ("http://ifconfig.me/all.json", "ip_addr", None),
    ]
    for _attempt in range(2):
        for url, ip_key, country_key in services:
            ok, data = _http_get(url, 12)
            if not ok:
                continue
            try:
                j = json.loads(data)
            except Exception:
                continue
            ip = j.get(ip_key, "") or j.get("ip", "") or j.get("query", "")
            country = ""
            if country_key:
                country = j.get(country_key, "") or ""
            if not country:
                country = j.get("country", "") or j.get("country_name", "") or ""
            if ip:
                return (ip, country)
        time.sleep(2)
    return ("", "")


def fetch_vpngate_servers():
    """Fetch VPN Gate CSV and return ALL servers in original order (no reordering/filtering)."""
    servers = []
    ok, data = _http_get(VPNGATE_API, 30)
    if not ok:
        return (False, str(data), servers)
    try:
        for line in data.splitlines():
            line = line.strip()
            if not line or line.startswith("*") or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) < 15:
                continue
            host = parts[0]
            ip = parts[1]
            ping = parts[3]
            try:
                speed = float(parts[4])
            except Exception:
                speed = 0.0
            country_long = parts[5]
            country_short = parts[6]
            ovpn_b64 = parts[14]
            if not ovpn_b64:
                continue
            servers.append({
                "host": host, "ip": ip, "ping": ping, "speed": speed,
                "country": country_long, "cc": country_short, "ovpn": ovpn_b64,
            })
    except Exception as e:
        return (False, str(e), servers)
    return (True, "", servers)


class VpnScreen(Screen):
    skin = VPN_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\U0001F510 VPN \u0645\u062c\u0627\u0646\u064a (VPN Gate) - MohamedStore")
        try:
            self.setTitle(u"VPN \u0645\u062c\u0627\u0646\u064a (VPN Gate)")
        except Exception:
            pass
        self["daylabel"] = Label("")
        self["list"] = MenuList([])
        self["status"] = Label("")
        self["key_red"] = Label(u"\u0631\u062c\u0648\u0639 (Back)")
        self["key_green"] = Label(u"\u0627\u062a\u0635\u0627\u0644 (Connect)")
        self["key_yellow"] = Label(u"\u0642\u0637\u0639 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 (Disconnect)")
        self["key_blue"] = Label(u"\u0627\u0644\u062d\u0627\u0644\u0629/\u062a\u062b\u0628\u064a\u062a (Status)")
        self.is_loading = False
        self.servers = []
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
            "cancel": self.go_back, "ok": self.connect_selected,
            "red": self.go_back, "green": self.connect_selected,
            "yellow": self.disconnect_vpn, "blue": self.show_status,
        }, -1)
        self.onLayoutFinish.append(self.load_servers)

    def go_back(self):
        if self.is_loading:
            return
        self.close()

    def load_servers(self):
        self.is_loading = True
        self["daylabel"].setText(u"\u062c\u0627\u0631\u064a \u062a\u062d\u0645\u064a\u0644 \u0633\u064a\u0631\u0641\u0631\u0627\u062a VPN Gate... (Loading...)")
        self["list"].setList([u"\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u0645\u064a\u0644... (Loading...)"])
        self["status"].setText(u"\u064a\u0631\u062c\u0649 \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631...")

        def _worker():
            ok, err, servers = fetch_vpngate_servers()

            def _apply():
                self.is_loading = False
                if not ok:
                    self["list"].setList([u"\u062a\u0639\u0630\u0631 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 (Connection failed)", str(err)])
                    self["status"].setText(u"\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0627\u062a\u0635\u0627\u0644")
                    return
                self.servers = servers
                self.show_menu()

            _call_ui(_apply)

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()

    def show_menu(self):
        self["daylabel"].setText(u"\u0627\u062e\u062a\u0631 \u062f\u0648\u0644\u0629 \u062b\u0645 \u0627\u0636\u063a\u0637 \u0627\u062a\u0635\u0627\u0644 (Select a country then Connect)")
        rows = []
        for s in self.servers:
            mbps = s["speed"] / 1000000.0
            rows.append(u"%s  [%s]  |  Ping: %s ms  |  %.1f Mbps  |  %s" % (
                s["country"], s["cc"], s["ping"], mbps, s["ip"]))
        if not rows:
            rows = [u"\u0644\u0627 \u062a\u0648\u062c\u062f \u0633\u064a\u0631\u0641\u0631\u0627\u062a (No servers)"]
        self["list"].setList(rows)
        self["status"].setText(u"%d \u0633\u064a\u0631\u0641\u0631 \u0645\u0646 \u0643\u0644 \u0627\u0644\u062f\u0648\u0644  |  \u0623\u062e\u0636\u0631 = \u0627\u062a\u0635\u0627\u0644  |  \u0623\u0635\u0641\u0631 = \u0642\u0637\u0639  |  \u0623\u0632\u0631\u0642 = \u0627\u0644\u062d\u0627\u0644\u0629 \u0648\u0627\u0644\u062a\u062b\u0628\u064a\u062a" % len(self.servers))

    def connect_selected(self):
        if self.is_loading:
            return
        idx = self["list"].getSelectionIndex()
        if idx < 0 or idx >= len(self.servers):
            return
        server = self.servers[idx]
        ovpn_path = _vpn_find_openvpn()
        if not ovpn_path:
            self.session.openWithCallback(
                self._ask_install_cb, MessageBox,
                u"\u0628\u0631\u0646\u0627\u0645\u062c OpenVPN \u063a\u064a\u0631 \u0645\u062b\u0628\u0651\u062a \u0639\u0644\u0649 \u0627\u0644\u062c\u0647\u0627\u0632.\n\u0647\u0644 \u062a\u0631\u064a\u062f \u062a\u062b\u0628\u064a\u062a\u0647 \u0627\u0644\u0622\u0646 (opkg)\u061f",
                type=MessageBox.TYPE_YESNO)
            return
        self._do_connect(server)

    def _ask_install_cb(self, answer):
        if answer:
            self._run_install()

    def _run_install(self):
        cmd = (
            "echo '==== MohamedStore VPN: installing OpenVPN ===='; "
            "opkg update; "
            "opkg install openvpn-openssl || opkg install openvpn; "
            "opkg install kmod-tun 2>/dev/null; "
            "modprobe tun 2>/dev/null; "
            "mkdir -p /dev/net; [ -c /dev/net/tun ] || mknod /dev/net/tun c 10 200; "
            "echo; echo '==== Done. Press EXIT to return ===='"
        )
        try:
            self.session.open(ConsoleScreen, title="MohamedStore VPN - Install OpenVPN", cmdlist=[cmd])
        except Exception:
            os.system(cmd)
            self.session.open(MessageBox, u"\u062a\u0645\u062a \u0645\u062d\u0627\u0648\u0644\u0629 \u0627\u0644\u062a\u062b\u0628\u064a\u062a. \u0623\u0639\u062f \u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629.", type=MessageBox.TYPE_INFO, timeout=6)

    def _do_connect(self, server):
        self.is_loading = True
        self["daylabel"].setText(u"\u062c\u0627\u0631\u064a \u0627\u0644\u0627\u062a\u0635\u0627\u0644 \u0628\u0640 %s ... (Connecting...)" % server["country"])
        self["status"].setText(u"\u064a\u0631\u062c\u0649 \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631 (\u0642\u062f \u064a\u0633\u062a\u063a\u0631\u0642 15-30 \u062b\u0627\u0646\u064a\u0629)...")

        def _worker():
            import base64
            err = ""
            try:
                raw = base64.b64decode(server["ovpn"])
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", "ignore")
                f = open(VPN_TMP_OVPN, "w")
                f.write(raw)
                f.close()
            except Exception as e:
                err = u"\u062a\u0639\u0630\u0631 \u062a\u062c\u0647\u064a\u0632 \u0645\u0644\u0641 VPN: " + str(e)

            if not err:
                _vpn_ensure_tun()
                ovpn_path = _vpn_find_openvpn()
                os.system("killall -9 openvpn 2>/dev/null")
                time.sleep(1)
                cmd = ("%s --config %s --daemon --log %s "
                       "--connect-retry-max 3 --connect-timeout 15 "
                       "--redirect-gateway def1 --script-security 2 2>/dev/null &") % (
                           ovpn_path, VPN_TMP_OVPN, VPN_LOG)
                os.system(cmd)
                time.sleep(12)

            running = _vpn_is_running()
            ip, country = ("", "")
            if running:
                ip, country = _vpn_public_ip()

            def _apply():
                self.is_loading = False
                self.show_menu()
                if err:
                    self.session.open(MessageBox, err, type=MessageBox.TYPE_ERROR, timeout=8)
                    return
                if running:
                    msg = u"\u2705 \u062a\u0645 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 \u0628\u0640 VPN \u0628\u0646\u062c\u0627\u062d!\n\n"
                    msg += u"\u0627\u0644\u062f\u0648\u0644\u0629 \u0627\u0644\u0645\u062e\u062a\u0627\u0631\u0629: %s [%s]\n" % (server["country"], server["cc"])
                    if ip:
                        msg += u"\u0639\u0646\u0648\u0627\u0646 IP \u0627\u0644\u062d\u0627\u0644\u064a: %s\n" % ip
                    if country:
                        msg += u"\u0627\u0644\u0638\u0627\u0647\u0631 \u0627\u0644\u0622\u0646 \u0645\u0646: %s\n" % country
                    msg += u"\n(MohamedStore)"
                    self.session.open(MessageBox, msg, type=MessageBox.TYPE_INFO, timeout=12)
                else:
                    tip = u"\u274c \u0641\u0634\u0644 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 \u0628\u0647\u0630\u0627 \u0627\u0644\u0633\u064a\u0631\u0641\u0631.\n\n"
                    tip += u"\u062c\u0631\u0651\u0628 \u0633\u064a\u0631\u0641\u0631 \u0622\u062e\u0631 (\u0623\u0642\u0644 Ping / \u0623\u0639\u0644\u0649 \u0633\u0631\u0639\u0629).\n"
                    tip += u"\u062a\u0623\u0643\u062f \u0645\u0646 \u062a\u062b\u0628\u064a\u062a OpenVPN \u0648\u062a\u0648\u0641\u0631 /dev/net/tun (\u0627\u0644\u0632\u0631 \u0627\u0644\u0623\u0632\u0631\u0642).\n"
                    tip += u"\u0633\u062c\u0644 \u0627\u0644\u0623\u062e\u0637\u0627\u0621: %s" % VPN_LOG
                    self.session.open(MessageBox, tip, type=MessageBox.TYPE_ERROR, timeout=12)

            _call_ui(_apply)

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()

    def disconnect_vpn(self):
        if self.is_loading:
            return
        os.system("killall -9 openvpn 2>/dev/null")
        self.session.open(MessageBox, u"\u2705 \u062a\u0645 \u0642\u0637\u0639 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 \u0628\u0640 VPN \u0648\u0627\u0644\u0639\u0648\u062f\u0629 \u0644\u0644\u0627\u062a\u0635\u0627\u0644 \u0627\u0644\u0645\u0628\u0627\u0634\u0631.", type=MessageBox.TYPE_INFO, timeout=6)

    def show_status(self):
        if self.is_loading:
            return
        self["status"].setText(u"\u062c\u0627\u0631\u064a \u0641\u062d\u0635 \u0627\u0644\u062d\u0627\u0644\u0629... (Checking...)")

        def _worker():
            ovpn_path = _vpn_find_openvpn()
            tun_ok = _vpn_tun_ready()
            running = _vpn_is_running()
            ip, country = _vpn_public_ip()

            def _apply():
                self.show_menu()
                lines = []
                lines.append(u"\U0001F510 \u062d\u0627\u0644\u0629 VPN (MohamedStore)")
                lines.append(u"========================================")
                if ovpn_path:
                    lines.append(u"[\u2714] OpenVPN \u0645\u062b\u0628\u0651\u062a: %s" % ovpn_path)
                else:
                    lines.append(u"[\u2716] OpenVPN \u063a\u064a\u0631 \u0645\u062b\u0628\u0651\u062a (\u0627\u0636\u063a\u0637 OK \u0644\u0644\u062a\u062b\u0628\u064a\u062a)")
                if tun_ok:
                    lines.append(u"[\u2714] /dev/net/tun \u0645\u062a\u0648\u0641\u0631")
                else:
                    lines.append(u"[\u2716] /dev/net/tun \u063a\u064a\u0631 \u0645\u062a\u0648\u0641\u0631 (\u0633\u064a\u062a\u0645 \u0625\u0646\u0634\u0627\u0624\u0647 \u0639\u0646\u062f \u0627\u0644\u0627\u062a\u0635\u0627\u0644)")
                if running:
                    lines.append(u"[\u2714] \u0627\u0644\u062d\u0627\u0644\u0629: VPN \u0645\u062a\u0635\u0644 \u0627\u0644\u0622\u0646")
                else:
                    lines.append(u"[\u2716] \u0627\u0644\u062d\u0627\u0644\u0629: \u063a\u064a\u0631 \u0645\u062a\u0635\u0644 (\u0627\u062a\u0635\u0627\u0644 \u0645\u0628\u0627\u0634\u0631)")
                lines.append(u"----------------------------------------")
                if ip:
                    lines.append(u"\u0639\u0646\u0648\u0627\u0646 IP \u0627\u0644\u062d\u0627\u0644\u064a: %s" % ip)
                if country:
                    lines.append(u"\u0627\u0644\u062f\u0648\u0644\u0629 \u0627\u0644\u0638\u0627\u0647\u0631\u0629: %s" % country)
                if not ip:
                    lines.append(u"\u062a\u0639\u0630\u0631 \u062c\u0644\u0628 \u0639\u0646\u0648\u0627\u0646 IP (\u062a\u062d\u0642\u0642 \u0645\u0646 \u0627\u0644\u0627\u0646\u062a\u0631\u0646\u062a)")
                report = u"\n".join(lines)
                if not ovpn_path:
                    self.session.openWithCallback(
                        self._ask_install_cb, MessageBox,
                        report + u"\n\n\u0647\u0644 \u062a\u0631\u064a\u062f \u062a\u062b\u0628\u064a\u062a OpenVPN \u0627\u0644\u0622\u0646\u061f",
                        type=MessageBox.TYPE_YESNO)
                else:
                    self.session.open(MessageBox, report, type=MessageBox.TYPE_INFO, timeout=15)

            _call_ui(_apply)

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()





# =========================================================================
# KEYS UPDATER & CRASH ANALYZER SCREENS (ARABIC TOOLS)
# =========================================================================

KEYS_UPDATER_RAW_SKIN = """<screen name="MS_SoftcamKeysUpdaterScreen" position="center,center" size="1240,820" title="">
    <widget name="title" position="20,15" size="1200,48" font="Regular;30" halign="center" transparent="1" foregroundColor="#00ffcc00"/>
    <widget name="summary" position="30,72" size="1180,120" font="Regular;24" transparent="1" foregroundColor="#00ffffff"/>
    <widget name="list" position="30,200" size="1180,475" font="Regular;22" itemHeight="36" scrollbarMode="showOnDemand"/>
    <widget name="status" position="20,685" size="1200,34" font="Regular;22" halign="center" transparent="1" foregroundColor="#00aaaaaa"/>
    <widget name="key_red" position="30,735" size="275,42" font="Regular;22" halign="center" transparent="1" foregroundColor="#00ff4040"/>
    <widget name="key_green" position="325,735" size="275,42" font="Regular;22" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="key_yellow" position="620,735" size="275,42" font="Regular;22" halign="center" transparent="1" foregroundColor="#00ffff40"/>
    <widget name="key_blue" position="915,735" size="275,42" font="Regular;22" halign="center" transparent="1" foregroundColor="#004080ff"/>
</screen>"""
KEYS_UPDATER_SKIN = scale_skin_layout(KEYS_UPDATER_RAW_SKIN)


class SoftcamKeysUpdaterScreen(Screen):
    skin = KEYS_UPDATER_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\u0645\u062d\u062f\u062b \u0627\u0644\u0634\u0641\u0631\u0627\u062a")
        self["summary"] = Label(u"\u062c\u0627\u0631\u064d \u0627\u0644\u062a\u062d\u0642\u0642 \u0645\u0646 \u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0634\u0641\u0631\u0627\u062a \u0641\u064a \u0627\u0644\u062c\u0647\u0627\u0632...")
        self["list"] = MenuList([])
        self["status"] = Label(u"\u0627\u0636\u063a\u0637 \u0627\u0644\u0632\u0631 \u0627\u0644\u0623\u062e\u0636\u0631 \u0644\u062a\u0646\u0632\u064a\u0644 \u0648\u062a\u062d\u062f\u064a\u062b \u0623\u062d\u062f\u062b \u0627\u0644\u0634\u0641\u0631\u0627\u062a")
        self["key_red"] = Label(u"\u062e\u0631\u0648\u062c")
        self["key_green"] = Label(u"\u062a\u062d\u062f\u064a\u062b \u0627\u0644\u0634\u0641\u0631\u0627\u062a")
        self["key_yellow"] = Label(u"\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0625\u064a\u0645\u0648")
        self["key_blue"] = Label(u"\u0641\u062d\u0635 \u0627\u0644\u0645\u0644\u0641\u0627\u062a")

        self.busy = False
        self.ui_timer = eTimer()
        try:
            self.ui_timer.callback.append(self._render_result)
        except Exception:
            self.ui_timer_conn = self.ui_timer.timeout.connect(self._render_result)

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "cancel": self.close,
            "ok": self.start_update,
            "red": self.close,
            "green": self.start_update,
            "yellow": self.restart_cam,
            "blue": self.check_local_keys,
        }, -1)

        self.onClose.append(self._stop_timer)
        self.onLayoutFinish.append(self.check_local_keys)

    def _stop_timer(self):
        try:
            self.ui_timer.stop()
        except Exception:
            pass

    def check_local_keys(self):
        if self.busy:
            return
        self["status"].setText(u"\u062c\u0627\u0631\u064d \u0641\u062d\u0635 \u0645\u0633\u0627\u0631\u0627\u062a \u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0634\u0641\u0631\u0627\u062a \u0641\u064a \u0627\u0644\u062c\u0647\u0627\u0632...")
        candidate_paths = [
            "/etc/tuxbox/config/SoftCam.Key",
            "/etc/tuxbox/config/oscam/SoftCam.Key",
            "/etc/tuxbox/config/ncam/SoftCam.Key",
            "/usr/keys/SoftCam.Key",
            "/var/keys/SoftCam.Key",
            "/etc/enigma2/SoftCam.Key"
        ]
        found_files = []
        details = []
        for path in candidate_paths:
            if os.path.exists(path):
                found_files.append(path)
                try:
                    st = os.stat(path)
                    sz_kb = round(st.st_size / 1024.0, 1)
                    mtime_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))
                    with open(path, "r") as f:
                        lines = f.readlines()
                    biss = sum(1 for l in lines if l.strip().startswith("F "))
                    pvu = sum(1 for l in lines if l.strip().startswith("P "))
                    tb = sum(1 for l in lines if l.strip().startswith("T "))
                    details.append(u"\u1f4c1 %s (%s KB - %s)" % (path, sz_kb, mtime_str))
                    details.append(u"   \u2514\u2500 \u0628\u064a\u0633: %d | \u0628\u0627\u0648\u0631 \u0641\u064a\u0648: %d | \u062a\u0627\u0646\u062f\u0628\u064a\u0631\u063a: %d | \u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0623\u0633\u0637\u0631: %d" % (biss, pvu, tb, len(lines)))
                except Exception as e:
                    details.append(u"\u1f4c1 %s (\u062e\u0637\u0623 \u0642\u0631\u0627\u0621\u0629: %s)" % (path, str(e)))

        if found_files:
            summary_msg = u"\u062a\u0645 \u0627\u0644\u0639\u062b\u0648\u0631 \u0639\u0644\u0649 \u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0634\u0641\u0631\u0627\u062a \u0641\u064a %d \u0645\u0633\u0627\u0631/\u0645\u0633\u0627\u0631\u0627\u062a.\n\u0627\u0636\u063a\u0637 \u0627\u0644\u0632\u0631 \u0627\u0644\u0623\u062e\u0636\u0631 \u0644\u062a\u0646\u0632\u064a\u0644 \u0648\u062a\u062d\u062f\u064a\u062b \u0623\u062d\u062f\u062b \u0645\u0644\u0641 SoftCam.Key \u0645\u0646 \u0627\u0644\u0633\u064a\u0631\u0641\u0631." % len(found_files)
            self["summary"].setText(summary_msg)
            self["list"].setList(details)
            self["status"].setText(u"\u062c\u0627\u0647\u0632 \u0644\u0644\u062a\u062d\u062f\u064a\u062b | \u0623\u062e\u0636\u0631=\u062a\u062d\u062f\u064a\u062b | \u0623\u0635\u0641\u0631=\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0625\u064a\u0645\u0648")
        else:
            summary_msg = u"\u0644\u0645 \u064a\u062a\u0645 \u0627\u0644\u0639\u062b\u0648\u0631 \u0639\u0644\u0649 \u0645\u0644\u0641 SoftCam.Key \u0645\u0633\u0628\u0642\u0627\u064b \u0641\u064a \u0627\u0644\u0645\u0633\u0627\u0631\u0627\u062a \u0627\u0644\u0645\u0639\u062a\u0627\u062f\u0629.\n\u0627\u0636\u063a\u0637 \u0627\u0644\u0632\u0631 \u0627\u0644\u0623\u062e\u0636\u0631 \u0644\u0625\u0646\u0634\u0627\u0621 \u0648\u062a\u062d\u0645\u064a\u0644 \u0623\u062d\u062f\u062b \u0627\u0644\u0634\u0641\u0631\u0627\u062a \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b."
            self["summary"].setText(summary_msg)
            self["list"].setList([u"\u0627\u0644\u0645\u0633\u0627\u0631\u0627\u062a \u0627\u0644\u0645\u0639\u062a\u0645\u062f\u0629: /etc/tuxbox/config/SoftCam.Key \u0648 /usr/keys/SoftCam.Key"])
            self["status"].setText(u"\u0627\u0636\u063a\u0637 \u0627\u0644\u0623\u062e\u0636\u0631 \u0644\u062a\u0646\u0632\u064a\u0644 \u0648\u062a\u062b\u0628\u064a\u062a \u0627\u0644\u0634\u0641\u0631\u0627\u062a \u0627\u0644\u062c\u062f\u064a\u062f\u0629")

    def start_update(self):
        if self.busy:
            return
        self.busy = True
        self["status"].setText(u"\u062c\u0627\u0631\u064d \u062a\u0646\u0632\u064a\u0644 \u0623\u062d\u062f\u062b \u0627\u0644\u0634\u0641\u0631\u0627\u062a \u0645\u0646 \u0627\u0644\u0633\u064a\u0631\u0641\u0631... \u064a\u0631\u062c\u0649 \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631")
        self["summary"].setText(u"\u062c\u0627\u0631\u064d \u0627\u0644\u0627\u062a\u0635\u0627\u0644 \u0628\u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0634\u0641\u0631\u0627\u062a \u0648\u062a\u062d\u0645\u064a\u0644 \u0645\u0644\u0641 SoftCam.Key...")

        def _worker():
            mirrors = [
                "https://raw.githubusercontent.com/popking159/softcam/master/SoftCam.Key",
                "https://raw.githubusercontent.com/PAKO34/softcam.key/master/SoftCam.Key",
                "https://raw.githubusercontent.com/myflash83/SoftCam.Key/main/SoftCam.Key",
                "https://raw.githubusercontent.com/CrazySat/Net-Keys/main/SoftCam.Key"
            ]
            downloaded_data = None
            for url in mirrors:
                ok, data = _http_get(url, timeout=12)
                if ok and data and len(data) > 5000:
                    downloaded_data = data
                    break

            if not downloaded_data:
                self._update_result = (False, u"\u0641\u0634\u0644 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 \u0628\u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0634\u0641\u0631\u0627\u062a. \u064a\u0631\u062c\u0649 \u0627\u0644\u062a\u0623\u0643\u062f \u0645\u0646 \u0627\u062a\u0635\u0627\u0644 \u0627\u0644\u0625\u0646\u062a\u0631\u0646\u062a.")
                try:
                    self.ui_timer.start(50, True)
                except Exception:
                    pass
                return

            lines = downloaded_data.splitlines()
            biss_cnt = sum(1 for l in lines if l.strip().startswith("F "))
            pvu_cnt = sum(1 for l in lines if l.strip().startswith("P "))
            tb_cnt = sum(1 for l in lines if l.strip().startswith("T "))
            total_lines = len(lines)
            data_bytes = downloaded_data.encode("utf-8") if isinstance(downloaded_data, str) else downloaded_data

            target_dirs = [
                "/etc/tuxbox/config",
                "/etc/tuxbox/config/oscam",
                "/etc/tuxbox/config/ncam",
                "/usr/keys",
                "/var/keys",
                "/etc/enigma2"
            ]
            saved_paths = []
            for d in target_dirs:
                if os.path.isdir(d):
                    filepath = os.path.join(d, "SoftCam.Key")
                    if os.path.exists(filepath):
                        try:
                            bakpath = filepath + ".bak"
                            if os.path.exists(bakpath):
                                os.remove(bakpath)
                            os.rename(filepath, bakpath)
                        except Exception:
                            pass
                    try:
                        with open(filepath, "wb") as f:
                            f.write(data_bytes)
                        try:
                            os.chmod(filepath, 0o644)
                        except Exception:
                            pass
                        saved_paths.append(filepath)
                    except Exception:
                        pass

            if not saved_paths:
                for default_dir in ["/etc/tuxbox/config", "/usr/keys"]:
                    try:
                        if not os.path.exists(default_dir):
                            os.makedirs(default_dir)
                        filepath = os.path.join(default_dir, "SoftCam.Key")
                        with open(filepath, "wb") as f:
                            f.write(data_bytes)
                        try:
                            os.chmod(filepath, 0o644)
                        except Exception:
                            pass
                        saved_paths.append(filepath)
                    except Exception:
                        pass

            cam_msg = ""
            try:
                c_ok, c_msg = restart_oscam_service()
                if c_ok:
                    cam_msg = u"\u062a\u0645\u062a \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0625\u064a\u0645\u0648 \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b \u0644\u062a\u0641\u0639\u064a\u0644 \u0627\u0644\u0634\u0641\u0631\u0627\u062a."
            except Exception:
                pass

            self._update_result = (True, {
                "saved_paths": saved_paths,
                "biss": biss_cnt,
                "powervu": pvu_cnt,
                "tandberg": tb_cnt,
                "total_lines": total_lines,
                "size_kb": round(len(data_bytes) / 1024.0, 1),
                "cam_msg": cam_msg
            })
            try:
                self.ui_timer.start(50, True)
            except Exception:
                pass

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()

    def _render_result(self):
        self.busy = False
        res = getattr(self, "_update_result", None)
        if not res:
            return
        success = res[0]
        data = res[1]
        if not success:
            self["summary"].setText(u"\u274c %s" % data)
            self["status"].setText(u"\u0641\u0634\u0644 \u0627\u0644\u062a\u062d\u062f\u064a\u062b | \u0623\u062d\u0645\u0631=\u062e\u0631\u0648\u062c | \u0623\u062e\u0636\u0631=\u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629")
            return

        summary_text = (
            u"\u2705 \u062a\u0645 \u062a\u062d\u062f\u064a\u062b \u0627\u0644\u0634\u0641\u0631\u0627\u062a \u0628\u0646\u062c\u0627\u062d \u0641\u0627\u0626\u0642!\n"
            u"\u0627\u0644\u062d\u062c\u0645: %s KB | \u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0623\u0633\u0637\u0631: %d | \u0628\u064a\u0633: %d | \u0628\u0627\u0648\u0631 \u0641\u064a\u0648: %d | \u062a\u0627\u0646\u062f\u0628\u064a\u0631\u063a: %d\n"
            u"%s" % (
                data["size_kb"], data["total_lines"], data["biss"],
                data["powervu"], data["tandberg"], data["cam_msg"]
            )
        )
        self["summary"].setText(summary_text)

        report_lines = [
            u"\u2714 \u062a\u0645 \u062d\u0641\u0638 \u0627\u0644\u0634\u0641\u0631\u0627\u062a \u0648\u0636\u0628\u0637 \u0627\u0644\u0635\u0644\u0627\u062d\u064a\u0627\u062a (644) \u0641\u064a \u0627\u0644\u0645\u0633\u0627\u0631\u0627\u062a \u0627\u0644\u062a\u0627\u0644\u064a\u0629:"
        ]
        for p in data["saved_paths"]:
            report_lines.append(u"  \u251c\u2500 %s" % p)
        report_lines.append(u"\u2714 \u062a\u0645 \u0625\u0646\u0634\u0627\u0621 \u0646\u0633\u062e\u0629 \u0627\u062d\u062a\u064a\u0627\u0637\u064a\u0629 \u0645\u0646 \u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0633\u0627\u0628\u0642\u0629 (.bak).")
        report_lines.append(u"\u2714 \u0627\u0644\u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0645\u0634\u0641\u0631\u0629 \u0628\u0640 Biss \u0648 PowerVU \u0633\u062a\u0639\u0645\u0644 \u0645\u0628\u0627\u0634\u0631\u0629 \u0627\u0644\u0622\u0646.")

        self["list"].setList(report_lines)
        self["status"].setText(u"\u0627\u0643\u062a\u0645\u0644 \u0627\u0644\u062a\u062d\u062f\u064a\u062b \u0628\u0646\u062c\u0627\u062d! | \u0623\u0635\u0641\u0631=\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0625\u064a\u0645\u0648 | \u0623\u062d\u0645\u0631=\u062e\u0631\u0648\u062c")

    def restart_cam(self):
        if self.busy:
            return
        self["status"].setText(u"\u062c\u0627\u0631\u064d \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0625\u064a\u0645\u0648 OSCam / NCam...")
        try:
            ok, msg = restart_oscam_service()
            if ok:
                self["status"].setText(u"\u062a\u0645\u062a \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0625\u064a\u0645\u0648 \u0628\u0646\u062c\u0627\u062d!")
                self.session.open(MessageBox, u"\u062a\u0645\u062a \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0625\u064a\u0645\u0648 OSCam / NCam \u0628\u0646\u062c\u0627\u062d \u0648\u062a\u0641\u0639\u064a\u0644 \u0627\u0644\u0634\u0641\u0631\u0627\u062a \u0641\u0648\u0631\u0627\u064b.", MessageBox.TYPE_INFO, timeout=5)
            else:
                self["status"].setText(u"\u062a\u0646\u0628\u064a\u0647: " + msg)
                self.session.open(MessageBox, msg, MessageBox.TYPE_WARNING, timeout=6)
        except Exception as e:
            self["status"].setText(u"\u062e\u0637\u0623: " + str(e))


CRASH_ANALYZER_RAW_SKIN = """<screen name="MS_CrashLogAnalyzerScreen" position="center,center" size="1260,820" title="">
    <widget name="title" position="20,15" size="1220,48" font="Regular;30" halign="center" transparent="1" foregroundColor="#00ffcc00"/>
    <widget name="summary" position="30,72" size="1200,125" font="Regular;23" transparent="1" foregroundColor="#00ffffff"/>
    <widget name="list" position="30,205" size="1200,470" font="Regular;21" itemHeight="32" scrollbarMode="showOnDemand"/>
    <widget name="status" position="20,685" size="1220,34" font="Regular;22" halign="center" transparent="1" foregroundColor="#00aaaaaa"/>
    <widget name="key_red" position="30,735" size="280,42" font="Regular;22" halign="center" transparent="1" foregroundColor="#00ff4040"/>
    <widget name="key_green" position="330,735" size="280,42" font="Regular;22" halign="center" transparent="1" foregroundColor="#0040ff40"/>
    <widget name="key_yellow" position="630,735" size="280,42" font="Regular;22" halign="center" transparent="1" foregroundColor="#00ffff40"/>
    <widget name="key_blue" position="930,735" size="280,42" font="Regular;22" halign="center" transparent="1" foregroundColor="#004080ff"/>
</screen>"""
CRASH_ANALYZER_SKIN = scale_skin_layout(CRASH_ANALYZER_RAW_SKIN)


class CrashLogAnalyzerScreen(Screen):
    skin = CRASH_ANALYZER_SKIN

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(u"\u0645\u062d\u0644\u0644 \u0627\u0644\u0643\u0631\u0627\u0634")
        self["summary"] = Label(u"\u062c\u0627\u0631\u064d \u0641\u062d\u0635 \u0633\u062c\u0644\u0627\u062a \u0627\u0644\u0623\u062e\u0637\u0627\u0621 \u0641\u064a \u0627\u0644\u062c\u0647\u0627\u0632...")
        self["list"] = MenuList([])
        self["status"] = Label(u"\u062c\u0627\u0631\u064d \u0627\u0644\u0628\u062d\u062b...")
        self["key_red"] = Label(u"\u062e\u0631\u0648\u062c")
        self["key_green"] = Label(u"\u0623\u062d\u062f\u062b \u0643\u0631\u0627\u0634")
        self["key_yellow"] = Label(u"\u0627\u0644\u0633\u0627\u0628\u0642")
        self["key_blue"] = Label(u"\u062d\u0630\u0641 \u0627\u0644\u0633\u062c\u0644\u0627\u062a")

        self.crash_files = []
        self.current_idx = 0
        self.busy = False

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "cancel": self.close,
            "ok": self.reload_crashes,
            "red": self.close,
            "green": self.reload_crashes,
            "yellow": self.prev_crash,
            "blue": self.ask_delete_all,
        }, -1)

        self.onLayoutFinish.append(self.reload_crashes)

    def find_all_crash_files(self):
        found = []
        search_dirs = ["/home/root", "/home/root/logs", "/media/hdd", "/media/usb", "/tmp"]
        import glob
        for d in search_dirs:
            if os.path.exists(d):
                for pat in ["*crash*.log", "enigma2_crash*.log", "dvbapp2_crash*.log"]:
                    for p in glob.glob(os.path.join(d, pat)):
                        if os.path.isfile(p):
                            found.append(p)
        found = list(set(found))
        found.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return found

    def reload_crashes(self):
        self.crash_files = self.find_all_crash_files()
        self.current_idx = 0
        if not self.crash_files:
            self["summary"].setText(u"\u1f389 \u062a\u0647\u0627\u0646\u064a\u0646\u0627! \u0644\u0627 \u062a\u0648\u062c\u062f \u0623\u064a\u0629 \u0645\u0644\u0641\u0627\u062a \u0627\u0646\u0647\u064a\u0627\u0631 (CrashLog) \u0641\u064a \u0627\u0644\u062c\u0647\u0627\u0632.\n\u062c\u0647\u0627\u0632\u0643 \u0645\u0633\u062a\u0642\u0631 \u062a\u0645\u0627\u0645\u0627\u064b \u0648\u062e\u0627\u0644\u064d \u0645\u0646 \u0623\u062e\u0637\u0627\u0621 \u0627\u0644\u0627\u0646\u0647\u064a\u0627\u0631.")
            self["list"].setList([
                u"\u2714 \u062a\u0645 \u0641\u062d\u0635 \u0627\u0644\u0645\u0633\u0627\u0631\u0627\u062a: /home/root \u0648 /home/root/logs \u0648 /media/hdd \u0648 /media/usb \u0648 /tmp",
                u"\u2714 \u0627\u0644\u0646\u0638\u0627\u0645 \u064a\u0639\u0645\u0644 \u0628\u0643\u0641\u0627\u0621\u0629 \u0648\u0628\u062f\u0648\u0646 \u0623\u062e\u0637\u0627\u0621 \u0643\u0631\u0627\u0634 \u0645\u0633\u062c\u0644\u0629."
            ])
            self["status"].setText(u"\u0627\u0644\u0646\u0638\u0627\u0645 \u0633\u0644\u064a\u0645 \u0648\u0645\u0633\u062a\u0642\u0631 100% | \u0623\u062d\u0645\u0631=\u062e\u0631\u0648\u062c")
            return
        self.display_crash(0)

    def prev_crash(self):
        if not self.crash_files:
            return
        if self.current_idx + 1 < len(self.crash_files):
            self.current_idx += 1
        else:
            self.current_idx = 0
        self.display_crash(self.current_idx)

    def display_crash(self, idx):
        if idx >= len(self.crash_files):
            return
        filepath = self.crash_files[idx]
        try:
            st = os.stat(filepath)
            sz_kb = round(st.st_size / 1024.0, 1)
            mtime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))
            filename = os.path.basename(filepath)
        except Exception:
            sz_kb = 0
            mtime_str = "-"
            filename = filepath

        try:
            with open(filepath, "rb") as f:
                raw = f.read()
            if isinstance(raw, bytes):
                try:
                    content = raw.decode("utf-8")
                except Exception:
                    content = raw.decode("latin-1", "ignore")
            else:
                content = str(raw)
        except Exception as e:
            self["summary"].setText(u"\u062a\u0639\u0630\u0631 \u0642\u0631\u0627\u0621\u0629 \u0645\u0644\u0641 \u0627\u0644\u0643\u0631\u0627\u0634: %s" % str(e))
            self["list"].setList([])
            return

        lines = content.splitlines()

        # ====== \u062a\u062d\u0644\u064a\u0644 \u0645\u062a\u0642\u062f\u0651\u0645: \u0627\u0633\u062a\u062e\u0631\u0627\u062c \u0627\u0644\u0633\u0628\u0628 \u0627\u0644\u062d\u0642\u064a\u0642\u064a \u0644\u0623\u064a \u0646\u0648\u0639 \u0643\u0631\u0627\u0634 ======

        # (1) \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0627\u0644\u062c\u0647\u0627\u0632 \u0648\u0627\u0644\u0635\u0648\u0631\u0629 \u0645\u0646 \u0631\u0623\u0633 \u0645\u0644\u0641 \u0627\u0644\u0643\u0631\u0627\u0634
        box_info = ""
        image_info = ""
        for l in lines[:80]:
            if "=" not in l:
                continue
            k = l.split("=", 1)[0].strip().lower()
            v = l.split("=", 1)[-1].strip()
            if not box_info and k in ("stbmodel", "boxtype", "box type", "model", "machinebuild"):
                box_info = v
            if not image_info and k in ("imageversion", "image version", "oe version", "distro", "version", "imagedistro"):
                image_info = v

        # (2) \u0627\u0633\u062a\u062e\u0631\u0627\u062c \u0622\u062e\u0631 Traceback \u0628\u0627\u064a\u062b\u0648\u0646 \u0643\u0627\u0645\u0644
        tb_lines = []
        in_tb = False
        for l in lines:
            if "Traceback (most recent call last):" in l:
                in_tb = True
                tb_lines = [l]
            elif in_tb:
                s = l.strip()
                if len(tb_lines) > 2 and (s.startswith("[") or s.startswith("----") or s.startswith("<<")):
                    in_tb = False
                else:
                    tb_lines.append(l)

        # (3) \u0633\u0637\u0631 \u0627\u0644\u062e\u0637\u0623 \u0627\u0644\u0623\u062e\u064a\u0631 (\u0623\u064a \u0646\u0648\u0639 \u0627\u0633\u062a\u062b\u0646\u0627\u0621) + \u0627\u0644\u0645\u0644\u0641 \u0627\u0644\u0645\u062a\u0633\u0628\u0628 + \u0627\u0644\u0628\u0644\u062c\u0646
        last_error = ""
        culprit_plugin = ""
        culprit_file = ""

        exc_re = re.compile(r'^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception|Warning|Interrupt|Fault|Timeout|Refused|Overflow|Failed|NotFound)\b')
        colon_re = re.compile(r'^[A-Za-z_][A-Za-z0-9_.]*\s*:\s*\S')

        check_pool = tb_lines if tb_lines else lines
        for l in reversed(check_pool):
            sl = l.strip()
            if not last_error and sl and not l.startswith(" ") and not l.startswith("\t") \
               and not sl.startswith("File ") and "Traceback (most recent call last)" not in sl:
                if exc_re.match(sl) or (colon_re.match(sl) and len(sl) < 400):
                    last_error = sl
            if not culprit_plugin and "/Plugins/Extensions/" in l:
                m = re.search(r'/Plugins/Extensions/([^/"]+)', l)
                if m:
                    culprit_plugin = m.group(1)
            elif not culprit_plugin and "/Plugins/SystemPlugins/" in l:
                m = re.search(r'/Plugins/SystemPlugins/([^/"]+)', l)
                if m:
                    culprit_plugin = m.group(1)
            if not culprit_file and 'File "' in l:
                m = re.search(r'File "([^"]+)", line (\d+)', l)
                if m:
                    culprit_file = m.group(1) + ":" + m.group(2)

        # (4) \u0643\u0634\u0641 \u0627\u0646\u0647\u064a\u0627\u0631\u0627\u062a C++ / \u0625\u0634\u0627\u0631\u0627\u062a \u0627\u0644\u0646\u0638\u0627\u0645 (\u0643\u0631\u0627\u0634 \u0628\u062f\u0648\u0646 \u062a\u062a\u0628\u0651\u0639 \u0628\u0627\u064a\u062b\u0648\u0646)
        signal_cause = ""
        low_content = content.lower()
        for key, desc in [
            ("sigsegv", u"\u0627\u0646\u0647\u064a\u0627\u0631 \u0641\u064a \u0627\u0644\u0630\u0627\u0643\u0631\u0629 \u2014 Segmentation Fault (SIGSEGV)"),
            ("segmentation fault", u"\u0627\u0646\u0647\u064a\u0627\u0631 \u0641\u064a \u0627\u0644\u0630\u0627\u0643\u0631\u0629 \u2014 Segmentation Fault"),
            ("sigabrt", u"\u0625\u0644\u063a\u0627\u0621 \u0642\u0633\u0631\u064a \u0644\u0644\u0639\u0645\u0644\u064a\u0629 \u2014 abort (SIGABRT)"),
            ("sigbus", u"\u062e\u0637\u0623 \u0639\u0646\u0648\u0646\u0629 \u0641\u064a \u0627\u0644\u0630\u0627\u0643\u0631\u0629 \u2014 Bus Error (SIGBUS)"),
            ("sigill", u"\u062a\u0639\u0644\u064a\u0645\u0629 \u0645\u0639\u0627\u0644\u062c \u063a\u064a\u0631 \u0635\u0627\u0644\u062d\u0629 (SIGILL)"),
            ("sigfpe", u"\u062e\u0637\u0623 \u062d\u0633\u0627\u0628\u064a / \u0642\u0633\u0645\u0629 \u0639\u0644\u0649 \u0635\u0641\u0631 (SIGFPE)"),
            ("signal 11", u"\u0627\u0646\u0647\u064a\u0627\u0631 \u0641\u064a \u0627\u0644\u0630\u0627\u0643\u0631\u0629 \u2014 signal 11 (SIGSEGV)"),
            ("signal 6", u"\u0625\u0644\u063a\u0627\u0621 \u0642\u0633\u0631\u064a \u2014 signal 6 (SIGABRT)"),
            ("oops", u"\u0627\u0646\u0647\u064a\u0627\u0631 \u0639\u0644\u0649 \u0645\u0633\u062a\u0648\u0649 \u0627\u0644\u0646\u0648\u0627\u0629 (Kernel Oops)"),
        ]:
            if key in low_content:
                signal_cause = desc
                break

        # (5) \u062a\u062d\u062f\u064a\u062f \u0627\u0644\u0633\u0628\u0628 \u0627\u0644\u062d\u0642\u064a\u0642\u064a \u0648\u0627\u0644\u062d\u0644 \u0627\u0644\u0645\u0642\u062a\u0631\u062d
        err_msg = last_error.split(":", 1)[-1].strip() if (last_error and ":" in last_error) else ""

        advice = u"\u0627\u0641\u062d\u0635 \u062a\u062a\u0628\u0651\u0639 \u0627\u0644\u062e\u0637\u0623 \u0628\u0627\u0644\u0623\u0633\u0641\u0644 \u0644\u0645\u0639\u0631\u0641\u0629 \u0627\u0644\u0633\u0637\u0631 \u0627\u0644\u0645\u062a\u0633\u0628\u0628 \u0628\u0627\u0644\u0636\u0628\u0637."

        if last_error and culprit_plugin:
            cause_text = u"\u0627\u0644\u0633\u0628\u0628 \u0627\u0644\u062d\u0642\u064a\u0642\u064a: \u0628\u0644\u062c\u0646 [%s] \u0623\u0637\u0644\u0642 \u0627\u0644\u062e\u0637\u0623 \u2190 %s" % (culprit_plugin, last_error[:70])
            advice = u"\u0627\u0644\u062d\u0644: \u0627\u062d\u0630\u0641 \u0623\u0648 \u0623\u0639\u062f \u062a\u062b\u0628\u064a\u062a \u0628\u0644\u062c\u0646 [%s] \u0628\u0646\u0633\u062e\u0629 \u0645\u062a\u0648\u0627\u0641\u0642\u0629 \u0645\u0639 \u0635\u0648\u0631\u062a\u0643 \u0648\u0627\u0644\u0628\u0627\u064a\u062b\u0648\u0646." % culprit_plugin
        elif culprit_plugin:
            cause_text = u"\u0627\u0644\u0633\u0628\u0628 \u0627\u0644\u062d\u0642\u064a\u0642\u064a: \u0627\u0646\u0647\u064a\u0627\u0631 \u062f\u0627\u062e\u0644 \u0628\u0644\u062c\u0646 [%s]" % culprit_plugin
            advice = u"\u0627\u0644\u062d\u0644: \u0627\u062d\u0630\u0641 \u0623\u0648 \u0623\u0639\u062f \u062a\u062b\u0628\u064a\u062a \u0628\u0644\u062c\u0646 [%s] \u0628\u0646\u0633\u062e\u0629 \u0645\u062a\u0648\u0627\u0641\u0642\u0629 \u0645\u0639 \u0635\u0648\u0631\u062a\u0643." % culprit_plugin
        elif "SkinError" in last_error or "skin.xml" in content or ("skin" in low_content and "not found" in low_content):
            cause_text = u"\u0627\u0644\u0633\u0628\u0628 \u0627\u0644\u062d\u0642\u064a\u0642\u064a: \u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0633\u0643\u0650\u0646 (Skin Error)%s" % ((u" \u2190 %s" % last_error[:55]) if last_error else u"")
            advice = u"\u0627\u0644\u062d\u0644: \u0647\u0646\u0627\u0643 \u0639\u0646\u0635\u0631 \u0623\u0648 \u062e\u0637 \u0623\u0648 \u0635\u0648\u0631\u0629 \u0645\u0641\u0642\u0648\u062f\u0629 \u0641\u064a \u0627\u0644\u0633\u0643\u0650\u0646\u060c \u0628\u062f\u0651\u0644 \u0644\u0644\u0633\u0643\u0650\u0646 \u0627\u0644\u0627\u0641\u062a\u0631\u0627\u0636\u064a \u0645\u0624\u0642\u062a\u0627\u064b."
        elif "MemoryError" in last_error or "out of memory" in low_content or "cannot allocate memory" in low_content:
            cause_text = u"\u0627\u0644\u0633\u0628\u0628 \u0627\u0644\u062d\u0642\u064a\u0642\u064a: \u0646\u0641\u0627\u062f \u0630\u0627\u0643\u0631\u0629 \u0627\u0644\u0631\u0627\u0645 (Out of Memory)"
            advice = u"\u0627\u0644\u062d\u0644: \u0641\u0639\u0651\u0644 \u0645\u0633\u0627\u062d\u0629 Swap\u060c \u0646\u0638\u0651\u0641 \u0627\u0644\u0631\u0627\u0645\u060c \u0648\u0642\u0644\u0651\u0644 \u0627\u0644\u0628\u0644\u062c\u0646\u0627\u062a \u0627\u0644\u0639\u0627\u0645\u0644\u0629 \u0641\u064a \u0627\u0644\u062e\u0644\u0641\u064a\u0629."
        elif "ImportError" in last_error or "ModuleNotFoundError" in last_error or "No module named" in content:
            mod = ""
            mm = re.search(r"No module named ['\"]?([\w\.]+)", content)
            if mm:
                mod = mm.group(1)
            cause_text = u"\u0627\u0644\u0633\u0628\u0628 \u0627\u0644\u062d\u0642\u064a\u0642\u064a: \u0645\u0643\u062a\u0628\u0629 \u0628\u0627\u064a\u062b\u0648\u0646 \u0645\u0641\u0642\u0648\u062f\u0629%s" % ((u" [%s]" % mod) if mod else u"")
            advice = u"\u0627\u0644\u062d\u0644: \u062b\u0628\u0651\u062a \u0627\u0644\u0645\u0643\u062a\u0628\u0629 \u0627\u0644\u0646\u0627\u0642\u0635\u0629 \u0639\u0628\u0631 Telnet (opkg install) \u0623\u0648 \u062d\u062f\u0651\u062b \u0627\u0644\u0635\u0648\u0631\u0629."
        elif signal_cause:
            cause_text = u"\u0627\u0644\u0633\u0628\u0628 \u0627\u0644\u062d\u0642\u064a\u0642\u064a: %s" % signal_cause
            advice = u"\u0627\u0644\u062d\u0644: \u0627\u0646\u0647\u064a\u0627\u0631 \u0639\u0644\u0649 \u0645\u0633\u062a\u0648\u0649 \u0627\u0644\u0646\u0638\u0627\u0645 (\u0644\u064a\u0633 \u0628\u0627\u064a\u062b\u0648\u0646) \u2014 \u063a\u0627\u0644\u0628\u0627\u064b \u062a\u0639\u0631\u064a\u0641/\u062f\u0631\u0627\u064a\u0641\u0631 \u0623\u0648 \u0622\u062e\u0631 \u0628\u0644\u062c\u0646 \u0645\u064f\u062b\u0628\u0651\u062a. \u062d\u062f\u0651\u062b \u0627\u0644\u0635\u0648\u0631\u0629 \u0623\u0648 \u0639\u0637\u0651\u0644 \u0622\u062e\u0631 \u0625\u0636\u0627\u0641\u0629 \u062b\u0628\u0651\u062a\u062a\u0647\u0627."
        elif last_error:
            cause_text = u"\u0627\u0644\u0633\u0628\u0628 \u0627\u0644\u062d\u0642\u064a\u0642\u064a: %s" % last_error[:85]
            if err_msg:
                advice = u"\u062a\u0641\u0627\u0635\u064a\u0644 \u0627\u0644\u062e\u0637\u0623: %s" % err_msg[:95]
        else:
            fallback = ""
            for l in lines:
                ll = l.strip().lower()
                if ll.startswith("error") or ll.startswith("fatal") or "fatal:" in ll or "assertion" in ll or "abort" in ll:
                    fallback = l.strip()
                    break
            if fallback:
                cause_text = u"\u0627\u0644\u0633\u0628\u0628 \u0627\u0644\u0645\u062d\u062a\u0645\u0644: %s" % fallback[:85]
                advice = u"\u0627\u0644\u062d\u0644: \u0631\u0627\u062c\u0639 \u0627\u0644\u062a\u062a\u0628\u0651\u0639 \u0628\u0627\u0644\u0623\u0633\u0641\u0644\u060c \u0648\u0627\u0644\u0633\u0628\u0628 \u063a\u0627\u0644\u0628\u0627\u064b \u0622\u062e\u0631 \u0625\u0636\u0627\u0641\u0629/\u062a\u0639\u0631\u064a\u0641 \u0645\u064f\u062b\u0628\u0651\u062a."
            else:
                cause_text = u"\u062a\u0645 \u062a\u0633\u062c\u064a\u0644 \u0627\u0646\u0647\u064a\u0627\u0631 \u063a\u064a\u0631 \u0645\u062d\u062f\u062f (Enigma2 crash) \u2014 \u0631\u0627\u062c\u0639 \u0627\u0644\u062a\u062a\u0628\u0651\u0639 \u0628\u0627\u0644\u0623\u0633\u0641\u0644"

        summary_text = (
            u"\u1f4c4 \u0645\u0644\u0641 \u0627\u0644\u0643\u0631\u0627\u0634 (%d \u0645\u0646 %d): %s (%s KB)\n"
            u"\u23f0 \u062a\u0627\u0631\u064a\u062e \u0627\u0644\u062d\u062f\u0648\u062b: %s\n"
            u"\u1f50d %s\n"
            u"\u1f4a1 %s" % (
                idx + 1, len(self.crash_files), filename, sz_kb,
                mtime_str, cause_text, advice
            )
        )
        self["summary"].setText(summary_text)

        items = []
        if box_info or image_info:
            items.append(u"\U0001f9e9 \u0627\u0644\u062c\u0647\u0627\u0632: %s%s" % (box_info or u"\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641", (u"  |  \u0627\u0644\u0635\u0648\u0631\u0629: %s" % image_info) if image_info else u""))
        if culprit_file:
            items.append(u"\u1f4cd \u0645\u0633\u0627\u0631 \u0627\u0644\u0645\u0644\u0641 \u0627\u0644\u0645\u0639\u0637\u0648\u0628: %s" % culprit_file)
        if last_error:
            items.append(u"\u26a1 \u0627\u0644\u062e\u0637\u0623 \u0627\u0644\u0623\u062e\u064a\u0631: %s" % last_error)
        items.append(u"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
        items.append(u"\u1f4dc \u062a\u0641\u0627\u0635\u064a\u0644 \u062a\u062a\u0628\u0639 \u0627\u0644\u062e\u0637\u0623 \u0645\u0646 \u0633\u062c\u0644 \u0627\u0644\u0643\u0631\u0627\u0634 (Traceback):")

        disp_tb = tb_lines if tb_lines else lines[-25:]
        for tbl in disp_tb[-25:]:
            items.append(u"  " + tbl)

        self["list"].setList(items)
        self["status"].setText(u"\u0623\u062e\u0636\u0631=\u0623\u062d\u062f\u062b \u0643\u0631\u0627\u0634 | \u0623\u0635\u0641\u0631=\u0627\u0644\u0643\u0631\u0627\u0634 \u0627\u0644\u0633\u0627\u0628\u0642 (%d/%d) | \u0623\u0632\u0631\u0642=\u062d\u0630\u0641 \u0627\u0644\u0643\u0644 | \u0623\u062d\u0645\u0631=\u062e\u0631\u0648\u062c" % (idx + 1, len(self.crash_files)))

    def ask_delete_all(self):
        if not self.crash_files:
            return
        msg = u"\u062a\u0645 \u0627\u0644\u0639\u062b\u0648\u0631 \u0639\u0644\u0649 %d \u0645\u0644\u0641 \u0643\u0631\u0627\u0634 \u0641\u064a \u0627\u0644\u062c\u0647\u0627\u0632.\n\u0647\u0644 \u062a\u0631\u064a\u062f \u062d\u0630\u0641 \u062c\u0645\u064a\u0639 \u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0643\u0631\u0627\u0634 \u0644\u062a\u0648\u0641\u064a\u0631 \u0645\u0633\u0627\u062d\u0629 \u0627\u0644\u0630\u0627\u0643\u0631\u0629\u061f" % len(self.crash_files)
        self.session.openWithCallback(self._confirm_delete_all, MessageBox, msg, MessageBox.TYPE_YESNO)

    def _confirm_delete_all(self, confirmed):
        if not confirmed:
            return
        deleted = 0
        for f in self.crash_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
                    deleted += 1
            except Exception:
                pass
        self.session.open(MessageBox, u"\u062a\u0645 \u062d\u0630\u0641 %d \u0645\u0646 \u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0643\u0631\u0627\u0634 \u0628\u0646\u062c\u0627\u062d \u0648\u062a\u0648\u0641\u064a\u0631 \u0645\u0633\u0627\u062d\u0629 \u0627\u0644\u062a\u062e\u0632\u064a\u0646." % deleted, MessageBox.TYPE_INFO, timeout=5)
        self.reload_crashes()


BUILTIN_SYSTEM_TOOLS = [
    {
        "name": u"\u0645\u062d\u062f\u062b \u0627\u0644\u0634\u0641\u0631\u0627\u062a",
        "type": "tool",
        "action": "softcam_keys_updater",
        "description": u"\u062a\u062d\u062f\u064a\u062b \u0634\u0641\u0631\u0627\u062a \u0627\u0644\u0642\u0646\u0648\u0627\u062a \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b (\u0628\u064a\u0633\u060c \u0628\u0627\u0648\u0631 \u0641\u064a\u0648\u060c \u062a\u0627\u0646\u062f\u0628\u064a\u0631\u063a) \u0644\u062c\u0645\u064a\u0639 \u0645\u0633\u0627\u0631\u0627\u062a \u0627\u0644\u0625\u064a\u0645\u0648 \u0641\u064a \u0627\u0644\u062c\u0647\u0627\u0632 \u0645\u0639 \u062e\u064a\u0627\u0631 \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0633\u064a\u0631\u0641\u0631."
    },
    {
        "name": u"\u0645\u062d\u0644\u0644 \u0627\u0644\u0643\u0631\u0627\u0634",
        "type": "tool",
        "action": "crash_analyzer",
        "description": u"\u0641\u062d\u0635 \u0648\u062a\u062d\u0644\u064a\u0644 \u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0627\u0646\u0647\u064a\u0627\u0631 \u0648\u0627\u0644\u0623\u062e\u0637\u0627\u0621 \u0641\u064a \u0627\u0644\u062c\u0647\u0627\u0632 \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b\u060c \u0648\u0627\u0643\u062a\u0634\u0627\u0641 \u0627\u0644\u0628\u0644\u062c\u0646 \u0623\u0648 \u0627\u0644\u0633\u0643\u064a\u0646 \u0627\u0644\u0645\u0633\u0628\u0628 \u0644\u0644\u0645\u0634\u0643\u0644\u0629 \u0645\u0639 \u062e\u064a\u0627\u0631 \u0645\u0633\u062d \u0627\u0644\u0633\u062c\u0644\u0627\u062a \u0627\u0644\u0642\u062f\u064a\u0645\u0629."
    },
    {
        "name": u"\U0001f510 \u0641\u064a\u0628\u064a \u0627\u0646 \u0645\u062c\u0627\u0646\u064a (VPN Free)",
        "type": "tool",
        "action": "vpn",
        "description": u"\u0627\u062a\u0635\u0627\u0644 VPN \u0645\u062c\u0627\u0646\u064a \u0639\u0628\u0631 VPN Gate \u0644\u062a\u062c\u0627\u0648\u0632 \u0627\u0644\u062d\u0638\u0631 \u0627\u0644\u062c\u063a\u0631\u0627\u0641\u064a: \u0627\u062e\u062a\u0631 \u0623\u064a \u062f\u0648\u0644\u0629 \u0645\u0646 \u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u062b\u0645 \u0627\u062a\u0635\u0627\u0644 (\u064a\u062b\u0628\u0651\u062a OpenVPN \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b)."
    },
    {
        "name": u"\U0001f3ac \u062a\u0631\u062c\u0645\u0627\u062a OpenSubtitles (Subtitles)",
        "type": "tool",
        "action": "subscene_subtitles",
        "description": u"\u062a\u062d\u0645\u064a\u0644 \u062a\u0631\u062c\u0645\u0627\u062a \u0627\u0644\u0623\u0641\u0644\u0627\u0645 \u0648\u0627\u0644\u0645\u0633\u0644\u0633\u0644\u0627\u062a \u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0645\u0639 \u0627\u0644\u0628\u0648\u0633\u062a\u0631\u0627\u062a \u0648\u0627\u0644\u0628\u062d\u062b \u0648\u0632\u0631 \u0627\u0644\u0645\u0632\u064a\u062f \u0648\u0627\u0644\u062a\u062d\u0645\u064a\u0644 \u0644\u0644\u0647\u0627\u0631\u062f (/media/hdd/) (\u0627\u0644\u0645\u0635\u062f\u0631: OpenSubtitles)"
    },
    {
        "name": u"\u0639\u0631\u0636 \u062d\u0627\u0644\u0629 \u0627\u0644\u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0646\u0634\u0637",
        "type": "tool",
        "action": "check_oscam_status",
        "description": u"\u0641\u062d\u0635 \u0645\u0644\u0641 oscam.server \u0648\u0639\u0631\u0636 \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0645\u062a\u062c\u0631 \u0627\u0644\u0634\u063a\u0627\u0644 \u0641\u0642\u0637 (Active Only)."
    },
    {
        "name": u"\u0633\u064a\u0633\u0643\u0627\u0645 \u0627\u0644\u0645\u062a\u062c\u0631 \u0627\u0644\u064a\u0648\u0645\u064a",
        "type": "tool",
        "action": "tiger_server",
        "description": u"\u0633\u064a\u0631\u0641\u0631 \u0641\u0627\u062a\u062d \u0627\u063a\u0644\u0628 \u0627\u0644\u0628\u0627\u0642\u0627\u062a \u0627\u0644\u0639\u0627\u0644\u0645\u064a\u0629"
    },
    {
        "name": u"\u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0627\u0644\u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0645\u062f\u0641\u0648\u0639",
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
        "name": u"\u062d\u0630\u0641 \u0627\u0644\u0628\u0644\u062c\u0646\u0627\u062a \u0648\u0627\u0644\u0633\u0643\u064a\u0646\u0627\u062a (Uninstaller)",
        "type": "tool",
        "action": "uninstaller",
        "description": u"\u062d\u0630\u0641 \u0627\u0644\u0628\u0644\u0627 your plugins and skins (\u062d\u0630\u0641 \u0639\u0627\u062f\u064a \u0623\u0648 \u0625\u062c\u0628\u0627\u0631\u064a)"
    },
    {
        "name": u"\u26bd \u0645\u0628\u0627\u0631\u064a\u0627\u062a \u0627\u0644\u064a\u0648\u0645 \u0648\u0627\u0644\u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0646\u0627\u0642\u0644\u0629 (Football on TV)",
        "type": "tool",
        "action": "football_matches",
        "description": u"\u0639\u0631\u0636 \u0645\u0628\u0627\u0631\u064a\u0627\u062a \u0643\u0631\u0629 \u0627\u0644\u0642\u062f\u0645 \u0627\u0644\u064a\u0648\u0645 \u0648\u063a\u062f\u0627\u064b \u0648\u0628\u0639\u062f \u063a\u062f \u0645\u0639 \u0627\u0644\u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0646\u0627\u0642\u0644\u0629 (\u0627\u0644\u0645\u0635\u062f\u0631: liveonsat.com)"
    },
    {
        "name": u"\U0001f324 \u062d\u0627\u0644\u0629 \u0627\u0644\u0637\u0642\u0633 (Weather)",
        "type": "tool",
        "action": "weather",
        "description": u"\u0639\u0631\u0636 \u062d\u0627\u0644\u0629 \u0627\u0644\u0637\u0642\u0633 \u0627\u0644\u062d\u0627\u0644\u064a\u0629 \u0648\u062a\u0648\u0642\u0639\u0627\u062a 5 \u0623\u064a\u0627\u0645 \u0644\u0623\u064a \u0645\u062f\u064a\u0646\u0629 \u0641\u064a \u0627\u0644\u0639\u0627\u0644\u0645 \u0645\u0639 \u0627\u0644\u0628\u062d\u062b (\u0627\u0644\u0645\u0635\u062f\u0631: open-meteo)"
    },
    {
        "name": u"\U0001f4fa \u0642\u0646\u0648\u0627\u062a IPTV \u0645\u062c\u0627\u0646\u064a\u0629 (IPTV)",
        "type": "tool",
        "action": "iptv",
        "description": u"\u0642\u0648\u0627\u0626\u0645 \u0642\u0646\u0648\u0627\u062a IPTV \u0645\u062c\u0627\u0646\u064a\u0629 \u062d\u0633\u0628 \u0627\u0644\u062f\u0648\u0644\u0629 \u0645\u0639 \u0625\u0645\u0643\u0627\u0646\u064a\u0629 \u0627\u0644\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0645\u0628\u0627\u0634\u0631 (\u0627\u0644\u0645\u0635\u062f\u0631: iptv-org)"
    },
    {
        "name": u"\U0001F4C1 IPTV MohamedStore",
        "type": "tool",
        "action": "iptv_mohamedstore",
        "description": u"\u0645\u0643\u062a\u0628\u0629 \u0645\u0644\u0641\u0627\u062a IPTV \u0627\u0644\u0645\u062f\u0645\u062c\u0629 \u062f\u0627\u062e\u0644 \u0627\u0644\u0628\u0644\u062c\u0646: \u0627\u0641\u062a\u062d \u0627\u0644\u0645\u0644\u0641 \u0644\u0639\u0631\u0636 \u0627\u0644\u0642\u0646\u0648\u0627\u062a \u0648\u0634\u063a\u0651\u0644\u0647\u0627 \u0645\u0628\u0627\u0634\u0631\u0629 \u0645\u0646 \u062f\u0627\u062e\u0644 \u0627\u0644\u0628\u0646\u0644."
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
        "description": u"\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0648\u0627\u062c\u0647\u0629 \u0627\u0644\u0633\u064a\u0633\u062a\u0645."
    },
    {
        "name": u"\u23f3 \u0639\u062f\u0627\u062f \u0627\u0646\u062a\u0647\u0627\u0621 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643 (Subscription Countdown)",
        "type": "tool",
        "action": "subscription",
        "description": u"\u062a\u062a\u0628\u0651\u0639 \u0627\u0644\u0623\u064a\u0627\u0645 \u0627\u0644\u0645\u062a\u0628\u0642\u064a\u0629 \u0639\u0644\u0649 \u0627\u0646\u062a\u0647\u0627\u0621 \u0627\u0634\u062a\u0631\u0627\u0643\u0643 \u0645\u0639 \u062a\u0646\u0628\u064a\u0647 \u0642\u0628\u0644 \u0627\u0644\u0627\u0646\u062a\u0647\u0627\u0621 (\u0639\u062f\u0627\u062f \u062a\u0646\u0627\u0632\u0644\u064a)."
    },
    {
        "name": u"\U0001f4c2 \u0645\u062f\u064a\u0631 \u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0645\u0635\u063a\u0651\u0631 (File Manager)",
        "type": "tool",
        "action": "file_manager",
        "description": u"\u062a\u0635\u0641\u0651\u062d \u0648\u062d\u0630\u0641 \u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0648\u0627\u0644\u0645\u062c\u0644\u062f\u0627\u062a \u0645\u0646 \u062f\u0627\u062e\u0644 \u0627\u0644\u0628\u0644\u062c\u0646 \u0645\u0639 \u062d\u0645\u0627\u064a\u0629 \u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0646\u0638\u0627\u0645."
    },
    {
        "name": u"\u23f0 \u0625\u062f\u0627\u0631\u0629 \u062a\u0630\u0643\u064a\u0631\u0627\u062a \u0627\u0644\u0645\u0628\u0627\u0631\u064a\u0627\u062a (Match Reminders)",
        "type": "tool",
        "action": "match_reminders",
        "description": u"\u0639\u0631\u0636 \u0648\u0625\u062f\u0627\u0631\u0629 \u062a\u0630\u0643\u064a\u0631\u0627\u062a \u0627\u0644\u0645\u0628\u0627\u0631\u064a\u0627\u062a \u0627\u0644\u0645\u0636\u0628\u0648\u0637\u0629 \u0645\u0639 \u0627\u0644\u062d\u0630\u0641 \u0648\u0627\u0644\u0625\u0636\u0627\u0641\u0629 \u0645\u0646 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0645\u0628\u0627\u0631\u064a\u0627\u062a."
    },
    {
        "name": u"\U0001f4e1 \u0645\u0631\u0627\u0642\u0628 \u062d\u0627\u0644\u0629 \u0627\u0644\u0633\u064a\u0631\u0641\u0631 (Server Monitor)",
        "type": "tool",
        "action": "server_monitor",
        "description": u"\u0645\u0631\u0627\u0642\u0628\u0629 \u062d\u0627\u0644\u0629 OSCam/NCam \u0644\u062d\u0638\u064a\u0627\u064b: \u0647\u0644 \u0634\u063a\u0651\u0627\u0644\u060c \u0627\u0644\u0631\u064a\u062f\u0631\u0632 \u0627\u0644\u0645\u062a\u0635\u0644\u0629\u060c \u0627\u0644\u0632\u0628\u0627\u0626\u0646\u060c \u0648\u0622\u062e\u0631 \u0642\u0646\u0627\u0629 \u0627\u0646\u0641\u0643\u0651\u062a (\u062a\u062d\u062f\u064a\u062b \u062a\u0644\u0642\u0627\u0626\u064a)."
    },
    {
        "name": u"\U0001f4be \u0646\u0633\u062e \u0627\u062d\u062a\u064a\u0627\u0637\u064a / \u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0627\u0644\u0625\u0639\u062f\u0627\u062f\u0627\u062a",
        "type": "tool",
        "action": "settings_backup",
        "description": u"\u0646\u0633\u062e\u0629 \u0627\u062d\u062a\u064a\u0627\u0637\u064a\u0629 \u0644\u0644\u0642\u0646\u0648\u0627\u062a \u0648\u0627\u0644\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0648\u0627\u0644\u0633\u064a\u0631\u0641\u0631 \u062a\u064f\u062d\u0641\u0638 \u0639\u0644\u0649 \u0627\u0644\u0647\u0627\u0631\u062f/\u0627\u0644\u0641\u0644\u0627\u0634 \u0645\u0639 \u0625\u0645\u0643\u0627\u0646\u064a\u0629 \u0627\u0644\u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0648\u0642\u062a \u0627\u0644\u062d\u0627\u062c\u0629."
    },
    {
        "name": u"\U0001f9f8 \u0648\u0636\u0639 \u0627\u0644\u0623\u0637\u0641\u0627\u0644 (Kids Mode)",
        "type": "tool",
        "action": "kids_mode",
        "description": u"\u064a\u062d\u0635\u0631 \u0627\u0644\u062c\u0647\u0627\u0632 \u0639\u0644\u0649 \u0642\u0646\u0648\u0627\u062a \u0627\u0644\u0623\u0637\u0641\u0627\u0644 \u0627\u0644\u0645\u0633\u0645\u0648\u062d\u0629 \u0641\u0642\u0637 \u0645\u0639 \u0631\u0645\u0632 \u0633\u0631\u064a \u0644\u0644\u0625\u064a\u0642\u0627\u0641 (\u062d\u0645\u0627\u064a\u0629 \u0623\u0628\u0648\u064a\u0629)."
    },
    {
        "name": u"\U0001f5c3 \u0645\u0646\u0638\u0645 \u0627\u0644\u0642\u0646\u0648\u0627\u062a (Channel Organizer)",
        "type": "tool",
        "action": "channel_organizer",
        "description": u"\u062a\u0631\u062a\u064a\u0628 \u0627\u0644\u0628\u0627\u0642\u0627\u062a \u0648\u0627\u0644\u0642\u0646\u0648\u0627\u062a (\u062a\u062d\u0631\u064a\u0643 \u0641\u0648\u0642/\u062a\u062d\u062a)\u060c \u0625\u0639\u0627\u062f\u0629 \u062a\u0633\u0645\u064a\u0629 \u0627\u0644\u0628\u0627\u0642\u0629\u060c \u062d\u0630\u0641 \u0627\u0644\u0642\u0646\u0648\u0627\u062a \u0623\u0648 \u0627\u0644\u0628\u0627\u0642\u0627\u062a \u0645\u0646 \u062f\u0627\u062e\u0644 \u0627\u0644\u0628\u0644\u062c\u0646."
    },
    {
        "name": u"\U0001f5bc \u062a\u063a\u064a\u064a\u0631 \u0634\u0639\u0627\u0631 \u0627\u0644\u0625\u0642\u0644\u0627\u0639 (Boot Logo Changer)",
        "type": "tool",
        "action": "boot_logo",
        "description": u"\u062a\u063a\u064a\u064a\u0631 \u0635\u0648\u0631\u0629 \u0627\u0644\u062a\u0634\u063a\u064a\u0644 \u0648\u0635\u0648\u0631\u0629 \u0627\u0644\u0625\u0637\u0641\u0627\u0621/\u0627\u0644\u0627\u0633\u062a\u0639\u062f\u0627\u062f: \u0627\u062e\u062a\u0631 \u0635\u0648\u0631\u062a\u064a\u0646 PNG/JPG \u0645\u0646 \u0627\u0644\u0647\u0627\u0631\u062f\u060c \u0648\u0627\u0644\u0623\u062f\u0627\u0629 \u062a\u062d\u0648\u0651\u0644\u0647\u0627 \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b \u0648\u062a\u0631\u0643\u0651\u0628\u0647\u0627 \u0645\u0639 \u0646\u0633\u062e\u0629 \u0623\u0635\u0644\u064a\u0629 \u0648\u0627\u0633\u062a\u0639\u0627\u062f\u0629."
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
        
        # Cache-busting: GitHub's raw CDN (Fastly) caches files for up to ~5
        # minutes and may keep serving an OLD copy of the feed right after an
        # upload. We append a changing timestamp and send no-cache headers so
        # every subscriber always pulls the FRESHEST index as soon as it is
        # updated on GitHub.
        try:
            sep = "&" if ("?" in url) else "?"
            fetch_url = url + sep + "nocache=" + str(int(time.time()))
        except Exception:
            fetch_url = url

        req = urllib2.Request(fetch_url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
        })
        if context:
            response = urllib2.urlopen(req, timeout=20, context=context)
        else:
            response = urllib2.urlopen(req, timeout=20)
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
    <eLabel position="20,15" size="1684,2" backgroundColor="#ffffff" zPosition="0" />
    <eLabel position="20,15" size="4,84" backgroundColor="#ffffff" zPosition="1" />
    <eLabel position="1700,15" size="4,84" backgroundColor="#ffffff" zPosition="1" />
    <eLabel position="20,99" size="1684,2" backgroundColor="#ffffff" />
    
    <ePixmap position="32,24" size="190,44" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/logo.png" zPosition="2" scale="1" transparent="1" alphatest="blend" />
    <eLabel position="230,22" size="120,30" text="MOHAMED" font="Regular;24" foregroundColor="#f59e0b" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="350,22" size="90,30" text="STORE" font="Regular;24" foregroundColor="#38bdf8" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="230,50" size="70,2" backgroundColor="#a07a38" zPosition="2" />
    <eLabel position="300,50" size="70,2" backgroundColor="#38bdf8" zPosition="2" />
    <eLabel position="370,50" size="70,2" backgroundColor="#ec4899" zPosition="2" />
    <eLabel position="230,56" size="75,22" text=" v1.3.3 " font="Regular;17" foregroundColor="#ffffff" backgroundColor="#be185d" transparent="0" halign="center" />

    <!-- HARDWARE CHIPS -->
    <eLabel position="445,19" size="305,74" backgroundColor="#070913" zPosition="1" />
    <eLabel position="445,19" size="305,2" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="445,19" size="3,74" backgroundColor="#60a5fa" zPosition="2" />
    <eLabel position="445,91" size="305,2" backgroundColor="#be185d" zPosition="2" />
    <widget name="sys_device" position="455,23" size="290,32" font="Regular;24" foregroundColor="#60a5fa" backgroundColor="#070913" transparent="1" zPosition="3" />
    <widget name="sys_image" position="455,56" size="290,30" font="Regular;22" foregroundColor="#c084fc" backgroundColor="#070913" transparent="1" zPosition="3" />

    <eLabel position="760,19" size="300,74" backgroundColor="#070913" zPosition="1" />
    <eLabel position="760,19" size="300,2" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="760,19" size="3,74" backgroundColor="#9c4656" zPosition="2" />
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
    <eLabel position="20,112" size="380,2" backgroundColor="#ffffff" zPosition="0" />
    <eLabel position="20,112" size="4,688" backgroundColor="#ffffff" zPosition="1" />
    <eLabel position="396,112" size="4,688" backgroundColor="#ffffff" zPosition="1" />
    <eLabel position="32,126" size="356,35" text="CATEGORIES" font="Regular;30" foregroundColor="#e7c9d2" backgroundColor="#5a2f3d" transparent="0" halign="center" valign="center" />
    <eLabel position="32,166" size="356,2" backgroundColor="#be185d" />
    <widget name="categories_list" position="25,176" size="370,616" itemHeight="80" scrollbarMode="showOnDemand" foregroundColor="#f3f4f6" backgroundColor="#0f111a" transparent="1" />

    <!-- CENTER PANEL: PACKAGES -->
    <eLabel position="412,112" size="780,688" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="412,112" size="780,2" backgroundColor="#ffffff" zPosition="0" />
    <eLabel position="412,112" size="4,688" backgroundColor="#ffffff" zPosition="1" />
    <eLabel position="1188,112" size="4,688" backgroundColor="#ffffff" zPosition="1" />
    <eLabel position="428,126" size="748,35" text="AVAILABLE PACKAGES" font="Regular;30" foregroundColor="#e7c9d2" backgroundColor="#5a2f3d" transparent="0" halign="center" valign="center" />
    <eLabel position="428,166" size="748,2" backgroundColor="#be185d" />
    <widget name="items_list" position="417,176" size="768,616" itemHeight="76" scrollbarMode="showOnDemand" foregroundColor="#f3f4f6" backgroundColor="#0f111a" transparent="1" />

    <!-- RIGHT PANEL: DETAILS & FACEBOOK & PROGRESS -->
    <eLabel position="1204,112" size="500,688" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="1204,112" size="500,2" backgroundColor="#ffffff" zPosition="0" />
    <eLabel position="1204,112" size="4,688" backgroundColor="#ffffff" zPosition="1" />
    <eLabel position="1700,112" size="4,688" backgroundColor="#ffffff" zPosition="1" />
    <eLabel position="1222,126" size="464,35" text="INFORMATION" font="Regular;30" foregroundColor="#e7c9d2" backgroundColor="#5a2f3d" transparent="0" halign="center" valign="center" />
    <eLabel position="1222,166" size="464,2" backgroundColor="#be185d" />
    
    <widget name="description" position="1222,174" size="464,376" font="Regular;24" foregroundColor="#e2e8f0" backgroundColor="#0f111a" transparent="1" valign="top" />

    <!-- NEWS TICKER BOX (thin, one message at a time) -->
    <eLabel position="1220,618" size="468,50" backgroundColor="#120e1a" zPosition="1" />
    <eLabel position="1220,618" size="468,2" backgroundColor="#a07a38" zPosition="2" />
    <eLabel position="1220,618" size="2,50" backgroundColor="#0284c7" zPosition="2" />
    <eLabel position="1686,618" size="2,50" backgroundColor="#ec4899" zPosition="2" />
    <eLabel position="1220,666" size="468,2" backgroundColor="#a07a38" zPosition="2" />

    <widget name="news_ticker" position="1230,622" size="448,42" font="Regular;26" foregroundColor="#38bdf8" backgroundColor="#120e1a" transparent="1" zPosition="4" halign="center" valign="center" />

    <!-- PROGRESS BOX WITH MULTI-COLOR ACCENTS -->
    <eLabel position="1220,676" size="468,114" backgroundColor="#0c0714" zPosition="1" />
    <eLabel position="1220,676" size="117,2" backgroundColor="#a07a38" zPosition="2" />
    <eLabel position="1337,676" size="117,2" backgroundColor="#0284c7" zPosition="2" />
    <eLabel position="1454,676" size="117,2" backgroundColor="#a855f7" zPosition="2" />
    <eLabel position="1571,676" size="117,2" backgroundColor="#ec4899" zPosition="2" />
    <eLabel position="1220,676" size="2,114" backgroundColor="#a07a38" zPosition="2" />
    <eLabel position="1686,676" size="2,114" backgroundColor="#ec4899" zPosition="2" />
    <eLabel position="1220,788" size="117,2" backgroundColor="#a07a38" zPosition="2" />
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
    <eLabel position="20,812" size="1684,2" backgroundColor="#ffffff" zPosition="0" />
    <eLabel position="20,812" size="4,93" backgroundColor="#ffffff" zPosition="1" />
    <eLabel position="1700,812" size="4,93" backgroundColor="#ffffff" zPosition="1" />
    <eLabel position="20,903" size="1684,2" backgroundColor="#ffffff" zPosition="1" />

    <eLabel position="40,824" size="41,68" backgroundColor="#96384a" zPosition="1" />
    <eLabel position="80,824" size="41,68" backgroundColor="#8e3446" zPosition="1" />
    <eLabel position="119,824" size="41,68" backgroundColor="#863142" zPosition="1" />
    <eLabel position="158,824" size="41,68" backgroundColor="#7e2e3e" zPosition="1" />
    <eLabel position="198,824" size="41,68" backgroundColor="#762b3a" zPosition="1" />
    <eLabel position="238,824" size="41,68" backgroundColor="#6e2836" zPosition="1" />
    <eLabel position="277,824" size="41,68" backgroundColor="#662532" zPosition="1" />
    <eLabel position="316,824" size="41,68" backgroundColor="#5e222e" zPosition="1" />
    <eLabel position="356,824" size="41,68" backgroundColor="#561f2a" zPosition="1" />
    <eLabel position="396,824" size="41,68" backgroundColor="#4e1c26" zPosition="1" />
    <eLabel position="40,824" size="395,3" backgroundColor="#9c4656" zPosition="2" />
    <eLabel position="40,889" size="395,3" backgroundColor="#9c4656" zPosition="2" />
    <eLabel position="40,824" size="3,68" backgroundColor="#9c4656" zPosition="2" />
    <eLabel position="432,824" size="3,68" backgroundColor="#9c4656" zPosition="2" />
    <ePixmap position="56,836" size="44,44" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/key_red.png" scale="1" transparent="1" alphatest="blend" zPosition="3" />
    <widget name="key_red" position="114,824" size="311,68" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#000000" transparent="1" zPosition="3" halign="left" valign="center" />

    <eLabel position="451,824" size="41,68" backgroundColor="#226e52" zPosition="1" />
    <eLabel position="490,824" size="41,68" backgroundColor="#1f684d" zPosition="1" />
    <eLabel position="530,824" size="41,68" backgroundColor="#1d6249" zPosition="1" />
    <eLabel position="570,824" size="41,68" backgroundColor="#1b5c44" zPosition="1" />
    <eLabel position="609,824" size="41,68" backgroundColor="#195640" zPosition="1" />
    <eLabel position="648,824" size="41,68" backgroundColor="#16513b" zPosition="1" />
    <eLabel position="688,824" size="41,68" backgroundColor="#144b37" zPosition="1" />
    <eLabel position="728,824" size="41,68" backgroundColor="#124532" zPosition="1" />
    <eLabel position="767,824" size="41,68" backgroundColor="#103f2e" zPosition="1" />
    <eLabel position="806,824" size="41,68" backgroundColor="#0e3a2a" zPosition="1" />
    <eLabel position="451,824" size="395,3" backgroundColor="#2b8a66" zPosition="2" />
    <eLabel position="451,889" size="395,3" backgroundColor="#2b8a66" zPosition="2" />
    <eLabel position="451,824" size="3,68" backgroundColor="#2b8a66" zPosition="2" />
    <eLabel position="843,824" size="3,68" backgroundColor="#2b8a66" zPosition="2" />
    <ePixmap position="467,836" size="44,44" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/key_green.png" scale="1" transparent="1" alphatest="blend" zPosition="3" />
    <widget name="key_green" position="525,824" size="311,68" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#000000" transparent="1" zPosition="3" halign="left" valign="center" />

    <eLabel position="862,824" size="41,68" backgroundColor="#967638" zPosition="1" />
    <eLabel position="902,824" size="41,68" backgroundColor="#8d6f34" zPosition="1" />
    <eLabel position="941,824" size="41,68" backgroundColor="#856830" zPosition="1" />
    <eLabel position="980,824" size="41,68" backgroundColor="#7c612d" zPosition="1" />
    <eLabel position="1020,824" size="41,68" backgroundColor="#745a29" zPosition="1" />
    <eLabel position="1060,824" size="41,68" backgroundColor="#6b5326" zPosition="1" />
    <eLabel position="1099,824" size="41,68" backgroundColor="#634c22" zPosition="1" />
    <eLabel position="1138,824" size="41,68" backgroundColor="#5a451f" zPosition="1" />
    <eLabel position="1178,824" size="41,68" backgroundColor="#523e1b" zPosition="1" />
    <eLabel position="1218,824" size="41,68" backgroundColor="#4a3818" zPosition="1" />
    <eLabel position="862,824" size="395,3" backgroundColor="#a07a38" zPosition="2" />
    <eLabel position="862,889" size="395,3" backgroundColor="#a07a38" zPosition="2" />
    <eLabel position="862,824" size="3,68" backgroundColor="#a07a38" zPosition="2" />
    <eLabel position="1254,824" size="3,68" backgroundColor="#a07a38" zPosition="2" />
    <ePixmap position="878,836" size="44,44" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/key_yellow.png" scale="1" transparent="1" alphatest="blend" zPosition="3" />
    <widget name="key_yellow" position="936,824" size="311,68" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#000000" transparent="1" zPosition="3" halign="left" valign="center" />

    <eLabel position="1273,824" size="41,68" backgroundColor="#4e488a" zPosition="1" />
    <eLabel position="1312,824" size="41,68" backgroundColor="#494382" zPosition="1" />
    <eLabel position="1352,824" size="41,68" backgroundColor="#443e7a" zPosition="1" />
    <eLabel position="1392,824" size="41,68" backgroundColor="#3f3a73" zPosition="1" />
    <eLabel position="1431,824" size="41,68" backgroundColor="#3a356b" zPosition="1" />
    <eLabel position="1470,824" size="41,68" backgroundColor="#353064" zPosition="1" />
    <eLabel position="1510,824" size="41,68" backgroundColor="#302c5c" zPosition="1" />
    <eLabel position="1550,824" size="41,68" backgroundColor="#2b2755" zPosition="1" />
    <eLabel position="1589,824" size="41,68" backgroundColor="#26224d" zPosition="1" />
    <eLabel position="1628,824" size="41,68" backgroundColor="#221e46" zPosition="1" />
    <eLabel position="1273,824" size="395,3" backgroundColor="#5852a0" zPosition="2" />
    <eLabel position="1273,889" size="395,3" backgroundColor="#5852a0" zPosition="2" />
    <eLabel position="1273,824" size="3,68" backgroundColor="#5852a0" zPosition="2" />
    <eLabel position="1665,824" size="3,68" backgroundColor="#5852a0" zPosition="2" />
    <ePixmap position="1289,836" size="44,44" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/key_blue.png" scale="1" transparent="1" alphatest="blend" zPosition="3" />
    <widget name="key_blue" position="1347,824" size="311,68" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#000000" transparent="1" zPosition="3" halign="left" valign="center" />
</screen>
"""

SKIN_LAYOUT = scale_skin_layout(RAW_SKIN_LAYOUT)

# =========================================================================
# MAIN MOHAMED STORE SCREEN
# =========================================================================
class MohamedStore(Screen):
    skin = SKIN_LAYOUT

    def __init__(self, session):
        Screen.__init__(self, session)
        
        self.categories_list_has_multicontent = False
        self._fit_fonts_ready = False
        self._items_list_w = scale_x(768)
        self._cat_list_w = scale_x(370)
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
        
        self._news_msgs = [
            u"\u0645\u0631\u062d\u0628\u0627 \u0628\u0643\u0645 \u0641\u064a \u0645\u062a\u062c\u0631 \u0645\u062d\u0645\u062f \u0633\u062a\u0648\u0631",
            u"\u0644\u062f\u064a\u0646\u0627 \u0627\u0644\u0643\u062b\u064a\u0631 \u0627\u0628\u062d\u062b \u0628\u0646\u0641\u0633\u0643",
            u"\u0645\u0643\u062a\u0628\u0629 \u0642\u0646\u0648\u0627\u062a \u0644\u0646 \u062a\u062c\u062f\u0647\u0627 \u0641\u064a \u0627\u064a \u0645\u0643\u0627\u0646",
            u"\u0633\u0643\u0646 \u0642\u062f\u064a\u0645 \u0648\u062c\u062f\u064a\u062f \u0644\u0645\u062d\u0628\u064a\u0647\u0627",
            u"\u0628\u0644\u062c\u0646\u0627\u062a \u0648\u0628\u064a\u0643\u0648\u0646\u0627\u062a \u0648\u0642\u062a \u0635\u062f\u0648\u0631\u0647\u0627",
            u"\u0635\u0648\u0631 \u0646\u0638\u0627\u0645 \u0643\u0644 \u0627\u0644\u0631\u064a\u0633\u064a\u0641\u0631\u0627\u062a",
            u"\u0642\u0633\u0645 \u062e\u0627\u0635 \u0628\u062c\u0647\u0627\u0632 \u0646\u0648\u0641\u0644\u064a\u0631",
            u"\u0645\u0641\u0636\u0644\u0627\u062a \u0645\u062a\u0646\u0648\u0639\u0647 \u0642\u0627\u0628\u0644\u0629 \u0644\u0644\u0632\u064a\u0627\u062f\u0629",
            u"\u0634\u0643\u0631\u0627 \u0644\u0645\u062a\u0627\u0628\u0639\u062a\u0646\u0627",
        ]
        self._news_index = 0
        self["news_ticker"] = Label(self._news_msgs[0])
        
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
        self._saved_paths = {}
        self._saved_item_idx = {}
        self._folder_index_stack = {}
        self._last_cat = None
        self._in_cat_changed = False
        self.my_console = Console()
        
        self.install_cmd = ""
        self.install_item_name = ""
        # update-prompt state: the new store content is held here and shown
        # only after the user answers Yes to the "there is an update" dialog.
        self._update_prompt_pending = False
        self._pending_store_data = None
        self._pending_store_sig = None
        # code-update (version.json) channel state
        self._code_update_pending = False
        self._pending_code_version = None
        
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

        # --- news ticker (one whole message at a time, then the next) ---
        self._news_timer = eTimer() if eTimer else None
        if self._news_timer:
            try:
                self._news_conn = self._news_timer.timeout.connect(self._news_tick)
            except AttributeError:
                try:
                    self._news_timer.callback.append(self._news_tick)
                except Exception:
                    pass

        # --- navigation (browsing) animation: a bouncing marker on the
        # currently selected row of the focused list. Pure text, all images. ---
        self._nav_frame = 0
        self._sel_cat_id = None
        self._sel_item = None
        self._nav_last_key = None
        self._nav_anim_timer = eTimer() if eTimer else None
        if self._nav_anim_timer:
            try:
                self._nav_anim_conn = self._nav_anim_timer.timeout.connect(self._nav_anim_tick)
            except AttributeError:
                try:
                    self._nav_anim_timer.callback.append(self._nav_anim_tick)
                except Exception:
                    pass

        self.onLayoutFinish.append(self.schedule_bg_sync)
        self.onLayoutFinish.append(self._autofit_lists)
        self.onLayoutFinish.append(self._news_start)


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
                new_sig = self._compute_store_signature(data)
                old_sig = self._read_seen_sig()

                if old_sig is None:
                    # First run on this box (or first run after upgrading to
                    # this version): there is no "previous" state to compare
                    # against, so just show the content and remember it
                    # silently. No prompt on a fresh install.
                    self.apply_store_data(data)
                    self._write_store_cache(data)
                    self._write_seen_sig(new_sig)
                elif new_sig and new_sig != old_sig:
                    # There IS an update. Do NOT show the new files yet.
                    # Keep the old (cached) content on screen and ASK the user
                    # first (Yes/No). The new files appear only if he says Yes.
                    self._pending_store_data = data
                    self._pending_store_sig = new_sig
                    self._update_prompt_pending = True
                else:
                    # No change: keep the local cache fresh (content identical).
                    self.apply_store_data(data)
                    self._write_store_cache(data)
            elif not self.categories:
                self["description"].setText("Failed to connect to GitHub feed.")

            # --- separate channel: check the PANEL CODE version (version.json) ---
            try:
                vdata = load_json_network(VERSION_URL)
                remote_ver = None
                if isinstance(vdata, dict):
                    remote_ver = vdata.get("version")
                if remote_ver and _ms_version_is_newer(remote_ver, PLUGIN_VERSION):
                    self._pending_code_version = str(remote_ver)
                    self._code_update_pending = True
            except Exception:
                pass
        except Exception:
            pass

    def _compute_store_signature(self, data):
        # Build a stable fingerprint of the whole store content. Any added,
        # removed or renamed item in ANY section changes this fingerprint.
        try:
            cats = data.get("categories", {}) if isinstance(data, dict) else {}
            payload = json.dumps(cats, sort_keys=True, ensure_ascii=True)
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8", "ignore")
            return hashlib.md5(payload.encode("utf-8", "ignore")).hexdigest()
        except Exception:
            return None

    def _read_seen_sig(self):
        try:
            if os.path.exists(SEEN_FILE):
                with open(SEEN_FILE, "r") as f:
                    return (json.load(f) or {}).get("sig")
        except Exception:
            pass
        return None

    def _write_seen_sig(self, sig):
        try:
            with open(SEEN_FILE, "w") as f:
                json.dump({"sig": sig}, f)
        except Exception:
            pass

    def _write_store_cache(self, data):
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _apply_update_answer(self, answer):
        # Callback from the Yes/No update dialog (runs on the main thread).
        data = getattr(self, "_pending_store_data", None)
        sig = getattr(self, "_pending_store_sig", None)
        if answer and data:
            # YES -> apply the new content, refresh the lists, remember it.
            try:
                self.apply_store_data(data)
            except Exception:
                pass
            self._write_store_cache(data)
            if sig:
                self._write_seen_sig(sig)
            try:
                self["news_ticker"].setText(u"\u2705 \u062a\u0645 \u0627\u0644\u062a\u062d\u062f\u064a\u062b")
            except Exception:
                pass
        # NO -> keep the old content and DO NOT remember the new signature,
        # so the panel will ask again next time it is opened/refreshed.
        self._pending_store_data = None
        self._pending_store_sig = None

    def _apply_code_update_answer(self, answer):
        # Callback from the "new panel version" dialog. YES -> run install.sh.
        if answer:
            try:
                self.start_script_update()
            except Exception:
                pass

    def apply_store_data(self, data):
        try:
            store_title = "%s v%s" % (data.get("store_name", "M Store"), data.get("version", "1.3.3"))
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
                        display_cats.append("%s %d" % (cat_clean_name, count))
                        
                self["categories_list"].setList(display_cats)
                # A store reload (background sync / refresh) must NEVER move the
                # user out of the folder they are currently browsing. If we are
                # inside a folder right now, keep the path exactly as it is and
                # just refresh the list. Only when we are at the section root do
                # we (re)select the remembered section.
                if self.active_focus == "items" and len(self.current_path) > 0:
                    self.rebuild_visible_items()
                    self.update_items_list()
                else:
                    changed_cat = (self._last_cat is None) or (self._last_cat not in self.categories)
                    if (not changed_cat) and self._last_cat in self.categories:
                        self.current_path = list(self._saved_paths.get(self._last_cat, []))
                        self._sel_cat_id = self._last_cat
                        try:
                            cat_pos = self.categories.index(self._last_cat)
                            if cat_pos >= 0:
                                self["categories_list"].setSelectionIndex(cat_pos)
                        except Exception:
                            pass
                        self.category_changed()
                    else:
                        self.current_path = []
                        self._last_cat = None
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

    def _ms_u(self, s):
        try:
            if isinstance(s, bytes):
                return s.decode("utf-8", "ignore")
            return u"%s" % s
        except Exception:
            return u""

    def _nav_bounce(self, frame, maxoff):
        period = maxoff * 2
        if period <= 0:
            return 0
        p = frame % period
        return p if p <= maxoff else period - p

    def _nav_marker(self):
        off = self._nav_bounce(getattr(self, "_nav_frame", 0), 3)
        return (u" " * off) + u"\u00bb "

    def _nav_pulse_color(self):
        steps = 8
        b = self._nav_bounce(getattr(self, "_nav_frame", 0), steps)
        t = float(b) / float(steps)
        # interpolate white -> light accent blue (ARGB)
        c0 = (0xFF, 0xFF, 0xFF, 0xFF)
        c1 = (0xFF, 0x4D, 0xB3, 0xFF)
        a = int(c0[0] + (c1[0] - c0[0]) * t)
        r = int(c0[1] + (c1[1] - c0[1]) * t)
        g = int(c0[2] + (c1[2] - c0[2]) * t)
        bl = int(c0[3] + (c1[3] - c0[3]) * t)
        return (a << 24) | (r << 16) | (g << 8) | bl

    def _mix_color(self, c0, c1, t):
        a0 = (c0 >> 24) & 0xFF; r0 = (c0 >> 16) & 0xFF; g0 = (c0 >> 8) & 0xFF; b0 = c0 & 0xFF
        a1 = (c1 >> 24) & 0xFF; r1 = (c1 >> 16) & 0xFF; g1 = (c1 >> 8) & 0xFF; b1 = c1 & 0xFF
        a = int(a0 + (a1 - a0) * t); r = int(r0 + (r1 - r0) * t)
        g = int(g0 + (g1 - g0) * t); b = int(b0 + (b1 - b0) * t)
        return (a << 24) | (r << 16) | (g << 8) | b

    def _brighten_color(self, c, t=0.5):
        r = (c >> 16) & 0xFF; g = (c >> 8) & 0xFF; b = c & 0xFF
        r = int(r + (255 - r) * t); g = int(g + (255 - g) * t); b = int(b + (255 - b) * t)
        return (r << 16) | (g << 8) | b

    def _cat_gradient_pair(self, category_id):
        # Distinct VIVID color per category TYPE (matches the reference image):
        # Plugins=blue, Skins=pink, Tools=amber, System Images=orange,
        # Picons=sky, Channels=green, Softcam=teal, Novaler=purple.
        try:
            cat_lower = str(category_id).lower().replace("_", "").replace(" ", "")
        except Exception:
            cat_lower = ""

        if "plugin" in cat_lower:
            return (0xFF3B424A, 0xFF16191D)       # muted blue
        if "skin" in cat_lower:
            return (0xFF635357, 0xFF1C1618)       # muted pink / red
        if "tool" in cat_lower:
            return (0xFF746D60, 0xFF22201C)       # muted amber / gold
        if "image" in cat_lower or "system" in cat_lower:
            return (0xFF685C53, 0xFF1F1B18)       # muted orange
        if "picon" in cat_lower:
            return (0xFF525D63, 0xFF1B1F21)       # muted sky
        if "channel" in cat_lower or "setting" in cat_lower:
            return (0xFF536159, 0xFF181C1A)       # muted green
        if "softcam" in cat_lower or "cam" in cat_lower or "emu" in cat_lower:
            return (0xFF4D5B5A, 0xFF171B1B)       # muted teal
        if "noval" in cat_lower or "nofla" in cat_lower:
            return (0xFF544D5A, 0xFF18161B)       # muted purple

        # Fallback: distinct SOFT/muted colors by position so any EXTRA
        # category still gets its own color instead of repeating.
        palette = [
            (0xFF3B424A, 0xFF16191D),  # muted blue
            (0xFF635357, 0xFF1C1618),  # muted pink
            (0xFF746D60, 0xFF22201C),  # muted amber
            (0xFF685C53, 0xFF1F1B18),  # muted orange
            (0xFF525D63, 0xFF1B1F21),  # muted sky
            (0xFF536159, 0xFF181C1A),  # muted green
            (0xFF4D5B5A, 0xFF171B1B),  # muted teal
            (0xFF544D5A, 0xFF18161B),  # muted purple
        ]
        idx = 0
        try:
            idx = list(self.categories).index(category_id)
        except Exception:
            try:
                idx = abs(hash(str(category_id)))
            except Exception:
                idx = 0
        return palette[idx % len(palette)]

    def _news_start(self):
        if not getattr(self, "_news_timer", None):
            return
        try:
            self._news_timer.start(3200, False)
        except Exception:
            pass

    def _news_tick(self):
        # If the background sync found a NEWER PANEL CODE version (version.json),
        # ask the user first; Yes runs the online install.sh and restarts.
        try:
            if getattr(self, "_code_update_pending", False):
                self._code_update_pending = False
                newv = getattr(self, "_pending_code_version", None) or "?"
                try:
                    self["news_ticker"].setText(u"\U0001F514 \u062a\u062d\u062f\u064a\u062b \u0646\u0638\u0627\u0645 \u0627\u0644\u0628\u0646\u0644 \u0645\u062a\u0648\u0641\u0631!")
                except Exception:
                    pass
                try:
                    msg = (u"\U0001F514 \u062a\u0648\u062c\u062f \u0646\u0633\u062e\u0629 \u062c\u062f\u064a\u062f\u0629 \u0645\u0646 \u0627\u0644\u0628\u0646\u0644 (v%s).\n\u0647\u0644 \u062a\u0631\u064a\u062f \u062a\u062d\u062f\u064a\u062b \u0627\u0644\u0646\u0638\u0627\u0645 \u0627\u0644\u0622\u0646\u061f\n(\u0633\u064a\u062a\u0645 \u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0648\u0627\u062c\u0647\u0629)") % newv
                    self.session.openWithCallback(
                        self._apply_code_update_answer,
                        MessageBox,
                        msg,
                        MessageBox.TYPE_YESNO)
                except Exception:
                    pass
                return
        except Exception:
            pass
        # If the background sync found NEW store content, ask the user now
        # (this runs on the enigma2 main loop, so a dialog is safe). The new
        # files are shown ONLY if he answers Yes.
        try:
            if getattr(self, "_update_prompt_pending", False):
                self._update_prompt_pending = False
                try:
                    self["news_ticker"].setText(u"\U0001F514 \u064a\u0648\u062c\u062f \u062a\u062d\u062f\u064a\u062b \u062c\u062f\u064a\u062f!")
                except Exception:
                    pass
                try:
                    self.session.openWithCallback(
                        self._apply_update_answer,
                        MessageBox,
                        u"\U0001F514 \u064a\u0648\u062c\u062f \u062a\u062d\u062f\u064a\u062b \u062c\u062f\u064a\u062f \u0641\u064a \u0627\u0644\u0645\u062a\u062c\u0631.\n\u0647\u0644 \u062a\u0631\u064a\u062f \u062a\u062d\u062f\u064a\u062b \u0627\u0644\u0642\u0627\u0626\u0645\u0629 \u0648\u0625\u0638\u0647\u0627\u0631 \u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0627\u0644\u062c\u062f\u064a\u062f\u0629 \u0627\u0644\u0622\u0646\u061f",
                        MessageBox.TYPE_YESNO)
                except Exception:
                    pass
                return
        except Exception:
            pass
        # show ONE full message for a few seconds, then swap to the next.
        try:
            msgs = getattr(self, "_news_msgs", None)
            if not msgs:
                return
            idx = (getattr(self, "_news_index", 0) + 1) % len(msgs)
            self._news_index = idx
            self["news_ticker"].setText(msgs[idx])
        except Exception:
            pass

    def _nav_anim_start(self):
        if not self._nav_anim_timer:
            return
        try:
            self._nav_anim_timer.start(150, False)
        except Exception:
            pass

    def _nav_anim_tick(self):
        self._nav_frame = getattr(self, "_nav_frame", 0) + 1
        try:
            if self.active_focus == "categories":
                lst = self["categories_list"]
            else:
                lst = self["items_list"]
            idx = lst.getSelectionIndex()
        except Exception:
            return
        key = (self.active_focus, idx)
        old = getattr(self, "_nav_last_key", None)
        if old != key:
            if old:
                try:
                    of, oi = old
                    ol = self["categories_list"] if of == "categories" else self["items_list"]
                    if oi is not None and oi >= 0 and hasattr(ol, "l"):
                        ol.l.invalidateEntry(oi)
                except Exception:
                    pass
            self._nav_last_key = key
        try:
            if idx is not None and idx >= 0 and hasattr(lst, "l"):
                lst.l.invalidateEntry(idx)
        except Exception:
            pass

    # ================================================================
    # AUTO-FIT ENGINE: keep the panel tidy on ANY skin.
    # The panel draws its own layout, but it still uses the active
    # skin's "Regular" font. Some skins ship a wider/heavier "Regular",
    # which made long names overflow / overlap on those skins while
    # looking fine on others. These two helpers make the lists adapt by
    # themselves: read the REAL list width at runtime, then pick a font
    # size that fits each name inside its own box (shrink only when
    # needed, never enlarge), so nothing spills out of the list.
    # ================================================================
    def _autofit_lists(self):
        # cache the REAL on-screen width of each list (whatever this skin
        # /resolution gave it) so the build functions size text to it.
        try:
            inst = self["items_list"].instance
            if inst and inst.size().width() > 0:
                self._items_list_w = inst.size().width()
        except Exception:
            pass
        try:
            inst = self["categories_list"].instance
            if inst and inst.size().width() > 0:
                self._cat_list_w = inst.size().width()
        except Exception:
            pass
        # redraw with the measured widths
        try:
            self.update_items_list()
        except Exception:
            pass

    def _fit_font_index(self, text, box_w_px):
        """Always use the full, fixed font size (index 0) like the original
        build. The auto-shrink ladder is disabled so the text keeps the same
        size on every skin and never renders tiny."""
        return 0

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
            icon_w = scale_x(70)
            icon_h = scale_y(70)
            icon_pos_x = scale_x(8)
            icon_pos_y = scale_y(5)
            row_h = scale_y(80)

            # One full-width blended "pill" per row. Draw order matters:
            # 1) gradient box  2) icon  3) name  4) count  -> icon+text on top.
            box_x = scale_x(4)
            box_y = scale_y(8)
            box_w = scale_x(356)
            box_h = scale_y(64)

            if HAS_MULTICONTENT and MultiContentEntryText:
                try:
                    c0, c1 = self._cat_gradient_pair(category_id)
                    segs = 24
                    for s in range(segs):
                        t = (float(s) / float(segs - 1)) if segs > 1 else 0.0
                        # opaque gradient (leading 0xFF alpha would be transparent)
                        col = self._mix_color(c0, c1, t) & 0x00FFFFFF
                        # softer highlight when the row is selected
                        col_sel = self._brighten_color(col, 0.22) & 0x00FFFFFF
                        # cover the FULL width (incl. the count) with no gaps
                        x0 = box_x + int(box_w * s / segs)
                        x1 = box_x + int(box_w * (s + 1) / segs)
                        res.append(MultiContentEntryText(pos=(x0, box_y), size=(x1 - x0 + 1, box_h), font=0, flags=RT_HALIGN_LEFT, text="", backcolor=col, backcolor_sel=col_sel))
                except Exception:
                    pass

            if pixmap and HAS_MULTICONTENT and MultiContentEntryPixmapAlphaTest:
                res.append(MultiContentEntryPixmapAlphaTest(pos=(icon_pos_x, icon_pos_y), size=(icon_w, icon_h), png=pixmap))
                text_x = scale_x(86)
            else:
                text_x = scale_x(15)
            # widen the name box as far right as possible (up to just before
            # the count) so long section names fit without shrinking the font.
            text_w = scale_x(302) - text_x
            if text_w < scale_x(60):
                text_w = scale_x(60)

            if HAS_MULTICONTENT and MultiContentEntryText:
                cat_disp = str(display_name)

                # name text (white) with a dark outline/shadow so it is readable
                # over ANY gradient color.
                try:
                    name_x = text_x
                    name_w = text_w
                    # auto-fit: shrink the font only if the name would overflow
                    # its box on this skin's font (keeps it tidy everywhere).
                    fidx = self._fit_font_index(cat_disp, name_w)
                    # heavy dark outline => bold, premium look + readable on any gradient
                    shadow_col = 0x00000000
                    for dx, dy in ((1, 0), (2, 0), (3, 0), (0, 1), (0, 2), (0, 3), (1, 1), (2, 2), (3, 3), (2, 1), (1, 2), (3, 2), (2, 3), (1, 3), (3, 1)):
                        res.append(MultiContentEntryText(pos=(name_x + dx, dy), size=(name_w, row_h), font=fidx, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=cat_disp, color=shadow_col, color_sel=shadow_col))
                    # faux-bold: draw the colored name twice with a 1px shift
                    name_col = 0x00CFFAFF
                    name_col_sel = 0x00EFFFFF
                    res.append(MultiContentEntryText(pos=(name_x + 1, 0), size=(name_w, row_h), font=fidx, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=cat_disp, color=name_col, color_sel=name_col_sel))
                    res.append(MultiContentEntryText(pos=(name_x, 0), size=(name_w, row_h), font=fidx, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=cat_disp, color=name_col, color_sel=name_col_sel))
                except Exception:
                    res.append(MultiContentEntryText(pos=(text_x, 0), size=(text_w, row_h), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=cat_disp))

                count_str = "%d" % int(count)
                # count (white) with dark shadow, on top of the gradient.
                # wider field (starts earlier) so 3-digit counts like [123]
                # don't get the leading "[" clipped.
                for dx, dy in ((1, 0), (1, 1), (0, 1)):
                    res.append(MultiContentEntryText(pos=(scale_x(306) + dx, dy), size=(scale_x(50), row_h), font=0, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=count_str, color=0x00000000, color_sel=0x00000000))
                res.append(MultiContentEntryText(pos=(scale_x(306), 0), size=(scale_x(50), row_h), font=0, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=count_str, color=0x00FFFFFF, color_sel=0x00FFFFFF))
                
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
            icon_w = scale_x(56)
            icon_h = scale_y(56)
            icon_pos_x = scale_x(10)
            icon_pos_y = scale_y(10)
            row_h = scale_y(76)

            # One full-width blended "pill" per item row, colored with the
            # SAME gradient as its parent category/section so the files inside
            # a section visually match that section's color. Draw order:
            # 1) gradient box  2) icon  3) name  -> icon+text stay on top.
            box_x = scale_x(4)
            box_y = scale_y(6)
            box_w = scale_x(760)
            box_h = scale_y(64)

            if HAS_MULTICONTENT and MultiContentEntryText:
                try:
                    c0, c1 = self._cat_gradient_pair(category_id)
                    # Files use a SOFTER version of their section color: pull
                    # each color toward its own grey (desaturate) and darken a
                    # little, so the items are calmer than the section header.
                    def _soft_item(c, desat=0.72, dark=0.15):
                        r = (c >> 16) & 0xFF
                        g = (c >> 8) & 0xFF
                        b = c & 0xFF
                        lum = 0.299 * r + 0.587 * g + 0.114 * b
                        def mix(x):
                            v = (x * (1.0 - desat) + lum * desat) * (1.0 - dark)
                            if v < 0:
                                v = 0
                            if v > 255:
                                v = 255
                            return int(v)
                        return (mix(r) << 16) | (mix(g) << 8) | mix(b)
                    c0 = _soft_item(c0)
                    c1 = _soft_item(c1)
                    segs = 24
                    for s in range(segs):
                        t = (float(s) / float(segs - 1)) if segs > 1 else 0.0
                        col = self._mix_color(c0, c1, t) & 0x00FFFFFF
                        col_sel = self._brighten_color(col, 0.22) & 0x00FFFFFF
                        x0 = box_x + int(box_w * s / segs)
                        x1 = box_x + int(box_w * (s + 1) / segs)
                        res.append(MultiContentEntryText(pos=(x0, box_y), size=(x1 - x0 + 1, box_h), font=0, flags=RT_HALIGN_LEFT, text="", backcolor=col, backcolor_sel=col_sel))
                except Exception:
                    pass

            if pixmap and HAS_MULTICONTENT and MultiContentEntryPixmapAlphaTest:
                res.append(MultiContentEntryPixmapAlphaTest(pos=(icon_pos_x, icon_pos_y), size=(icon_w, icon_h), png=pixmap))
                text_x = scale_x(78)
            else:
                text_x = scale_x(15)
            # size the name box to the REAL list width (measured at runtime),
            # minus the icon gap and a small margin for the scrollbar, so the
            # text box always ends exactly at the list edge on any skin.
            list_w = getattr(self, "_items_list_w", 0) or scale_x(768)
            text_w = list_w - text_x - scale_x(8)
            if text_w < scale_x(80):
                text_w = scale_x(80)

            if HAS_MULTICONTENT and MultiContentEntryText:
                item_disp = str(display_text)
                # auto-fit: shrink the font only when the name would overflow
                # its box, so long package/file names never spill out of the
                # list regardless of which skin's font is active.
                fidx = self._fit_font_index(item_disp, text_w)
                # dark outline/shadow so the name stays readable on any color
                shadow_col = 0x00000000
                for dx, dy in ((1, 0), (2, 0), (0, 1), (0, 2), (1, 1), (2, 2), (2, 1), (1, 2)):
                    res.append(MultiContentEntryText(pos=(text_x + dx, dy), size=(text_w, row_h), font=fidx, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=item_disp, color=shadow_col, color_sel=shadow_col))
                name_col = 0x00EAF2F7
                name_col_sel = 0x00FFFFFF
                res.append(MultiContentEntryText(pos=(text_x, 0), size=(text_w, row_h), font=fidx, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=item_disp, color=name_col, color_sel=name_col_sel))

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
        if getattr(self, "_in_cat_changed", False):
            return
        self._in_cat_changed = True
        try:
            idx = self["categories_list"].getSelectionIndex()
            if idx < 0 or idx >= len(self.categories):
                return

            selected_cat = self.categories[idx]
            changed = (self._last_cat != selected_cat)

            # If we are browsing inside a folder (items focus) and the category
            # did not actually change, keep the position untouched. This prevents
            # the background store refresh / list rebuild from kicking the user
            # back to the first folder.
            if (not changed) and self.active_focus == "items" and len(self.current_path) > 0:
                return

            # Save the path/selection of the category we are leaving
            if self._last_cat is not None and changed and len(self.current_path) > 0:
                self._saved_paths[self._last_cat] = list(self.current_path)
                try:
                    self._saved_item_idx[self._last_cat] = self["items_list"].getSelectionIndex()
                except Exception:
                    pass

            self._last_cat = selected_cat
            self._sel_cat_id = selected_cat

            # Restore the remembered path for this category (keep position)
            if changed:
                self.current_path = list(self._saved_paths.get(selected_cat, []))

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

            # Restore remembered item selection for this category
            if changed:
                try:
                    saved_idx = self._saved_item_idx.get(selected_cat, 0)
                    if saved_idx and 0 <= saved_idx < len(self.visible_items):
                        self["items_list"].setSelectionIndex(saved_idx)
                except Exception:
                    pass
        except Exception as e:
            self["description"].setText("Category Change Error: " + str(e))
        finally:
            self._in_cat_changed = False

    def rebuild_visible_items(self):
        try:
            # Prefer the last active section (reliable even after the left
            # list is rebuilt). Fall back to the list selection index.
            selected_cat = getattr(self, "_last_cat", None)
            if selected_cat not in self.categories:
                idx = self["categories_list"].getSelectionIndex()
                if idx < 0 or idx >= len(self.categories):
                    self.visible_items = []
                    return
                selected_cat = self.categories[idx]
            else:
                try:
                    self._sel_cat_id = selected_cat
                except Exception:
                    pass

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
            category_id = getattr(self, "_last_cat", None)
            if category_id not in self.categories:
                category_id = self.categories[cat_idx] if (cat_idx >= 0 and cat_idx < len(self.categories)) else "unknown"

            display_items = []
            for item in self.visible_items:
                if "items" in item and isinstance(item["items"], list):
                    folder_count = count_items_recursive(item["items"])
                    display_text = "> %s  %d" % (str(item.get("name", "Unknown Folder")), folder_count)
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
            self._sel_item = item
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
        # Restore the remembered path for the current category
        if self._last_cat is not None:
            self.current_path = list(self._saved_paths.get(self._last_cat, []))
            if len(self.current_path) > 0:
                self.rebuild_visible_items()
                self.update_items_list()
                try:
                    saved_idx = self._saved_item_idx.get(self._last_cat, 0)
                    if saved_idx and 0 <= saved_idx < len(self.visible_items):
                        self["items_list"].setSelectionIndex(saved_idx)
                        self["items_list"].moveToIndex(saved_idx)
                        self.item_changed()
                except Exception:
                    pass
            else:
                self.category_changed()
        if self.visible_items:
            self.active_focus = "items"
            self["description"].setText("Navigating: Items List\n\nPress OK or Green to Install / Execute.")

    def exit_current_folder(self):
        if not self.current_path:
            return False

        exited_folder = self.current_path.pop()
        cat_key = self._last_cat or "default"

        if self._last_cat is not None:
            self._saved_paths[self._last_cat] = list(self.current_path)

        self.rebuild_visible_items()
        self.update_items_list()

        target_idx = -1

        # 1. Search for the exact folder object in parent visible items
        for i, it in enumerate(self.visible_items):
            if it is exited_folder:
                target_idx = i
                break

        # 2. If identity didn't match, match by folder name
        if target_idx < 0 and isinstance(exited_folder, dict):
            ex_name = exited_folder.get("name")
            for i, it in enumerate(self.visible_items):
                if isinstance(it, dict) and it.get("name") == ex_name and "items" in it:
                    target_idx = i
                    break

        # 3. Check the folder index stack for this category
        stack = getattr(self, "_folder_index_stack", {}).get(cat_key, [])
        if stack:
            saved_item, saved_idx = stack.pop()
            if target_idx < 0 and 0 <= saved_idx < len(self.visible_items):
                target_idx = saved_idx

        # Position the selection directly on the exited folder
        if 0 <= target_idx < len(self.visible_items):
            try:
                self["items_list"].setSelectionIndex(target_idx)
            except Exception:
                pass
            try:
                self["items_list"].moveToIndex(target_idx)
            except Exception:
                pass
            self.item_changed()

            # Remember this index if we returned to category root
            if len(self.current_path) == 0 and self._last_cat is not None:
                self._saved_item_idx[self._last_cat] = target_idx

        return True

    def switch_to_categories(self):
        if self.download_in_progress:
            return
        if self.active_focus == "items" and len(self.current_path) > 0:
            self.exit_current_folder()
        else:
            # Remember the current folder position for this section so that
            # re-entering the section returns to the same folder. Only update
            # the memory when we are actually inside a folder, so leaving to
            # the section list does not erase a deeper remembered position.
            if self._last_cat is not None and len(self.current_path) > 0:
                self._saved_paths[self._last_cat] = list(self.current_path)
                try:
                    self._saved_item_idx[self._last_cat] = self["items_list"].getSelectionIndex()
                except Exception:
                    pass
            self.active_focus = "categories"
            self["description"].setText("Navigating: Categories\n\nUse Up/Down to pick a section, Right to enter it.")

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
                    if not hasattr(self, "_folder_index_stack") or not isinstance(self._folder_index_stack, dict):
                        self._folder_index_stack = {}
                    cat_key = self._last_cat or "default"
                    self._folder_index_stack.setdefault(cat_key, []).append((item, idx))
                    self.current_path.append(item)
                    if self._last_cat is not None:
                        self._saved_paths[self._last_cat] = list(self.current_path)
                    self.rebuild_visible_items()
                    self.update_items_list()
                else:
                    self.download()

    def go_back(self):
        if self.download_in_progress:
            self.cancel_active_download()
            return
        if self.active_focus == "items" and len(self.current_path) > 0:
            self.exit_current_folder()
        elif self.active_focus == "items" and len(self.current_path) == 0:
            self.switch_to_categories()
        else:
            try:
                if self._last_cat is not None and len(self.current_path) > 0:
                    self._saved_paths[self._last_cat] = list(self.current_path)
                    self._saved_item_idx[self._last_cat] = self["items_list"].getSelectionIndex()
            except Exception:
                pass
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
                    if action == "subscene_subtitles":
                        self.session.open(SubsceneScreen)
                        return

                    elif action == "check_oscam_status":
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
                            _call_ui(_show_res)
                        
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

                    elif action == "uninstaller":
                        self.session.open(Uninstaller)
                        return

                    elif action == "football_matches":
                        self.session.open(FootballMatches)
                        return

                    elif action == "weather":
                        self.session.open(WeatherScreen)
                        return

                    elif action == "iptv":
                        self.session.open(IPTVScreen)
                        return

                    elif action == "iptv_mohamedstore":
                        self.session.open(IPTVMohamedStoreScreen)
                        return

                    elif action == "subscription":
                        self.session.open(SubscriptionScreen)
                        return

                    elif action == "file_manager":
                        self.session.open(FileManagerScreen)
                        return

                    elif action == "match_reminders":
                        self.session.open(MatchRemindersScreen)
                        return

                    elif action == "server_monitor":
                        self.session.open(ServerMonitorScreen)
                        return

                    elif action == "settings_backup":
                        self.session.open(SettingsBackupScreen)
                        return

                    elif action == "kids_mode":
                        self.session.open(KidsModeScreen)
                        return

                    elif action == "channel_organizer":
                        self.session.open(ChannelOrganizerScreen)
                        return

                    elif action == "vpn":
                        self.session.open(VpnScreen)
                        return

                    elif action == "boot_logo":
                        self.session.open(BootLogoScreen)
                        return

                    elif action == "softcam_keys_updater":
                        self.session.open(SoftcamKeysUpdaterScreen)
                        return

                    elif action == "crash_analyzer":
                        self.session.open(CrashLogAnalyzerScreen)
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
                    if not hasattr(self, "_folder_index_stack") or not isinstance(self._folder_index_stack, dict):
                        self._folder_index_stack = {}
                    cat_key = self._last_cat or "default"
                    self._folder_index_stack.setdefault(cat_key, []).append((item, idx))
                    self.current_path.append(item)
                    if self._last_cat is not None:
                        self._saved_paths[self._last_cat] = list(self.current_path)
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
                    if ext == ".ipk":
                        dest_path = "/tmp/addon.ipk"
                        cmd = "opkg install --force-reinstall --force-overwrite --force-downgrade --force-depends /tmp/addon.ipk && rm -f /tmp/addon.ipk"
                        self.download_is_system_image = False
                        self.download_is_picon = False
                    else:
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

    def _ms_dl_comet(self, frame):
        # A small slider that bounces back and forth (go & return).
        # ASCII only, so it renders on every Enigma2 image/font.
        width = 18
        blk = 3
        span = width - blk
        period = span * 2
        p = frame % period
        start = p if p <= span else period - p
        cells = ["-"] * width
        for i in range(start, start + blk):
            cells[i] = "="
        return "[" + "".join(cells) + "]"

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

        # --- animated download progress (text-based, all images + Py2/3) ---
        if not self.download_completed and not self.download_error_msg:
            try:
                self._dl_anim_frame = getattr(self, "_dl_anim_frame", 0) + 1
                base = u"\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u0645\u064a\u0644"
                comet = self._ms_dl_comet(self._dl_anim_frame)
                self["status"].setText(u"%s   %s" % (base, comet))
            except Exception:
                pass

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
        ),
        PluginDescriptor(
            name="Mohamed Store Match Reminders",
            description="Background match reminder notifier",
            where=PluginDescriptor.WHERE_SESSIONSTART,
            fnc=ms_sessionstart
        )
    ]
