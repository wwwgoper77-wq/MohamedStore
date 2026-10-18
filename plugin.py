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
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
            "cancel": self.go_back, "ok": self.ok_pressed,
            "red": self.go_back, "green": self.ok_pressed,
            "yellow": self.do_search, "blue": self.refresh_current,
        }, -1)
        self.onLayoutFinish.append(self.show_menu)

    def show_menu(self):
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



BUILTIN_SYSTEM_TOOLS = [
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
        "name": u"\u0639\u0631\u0636 \u062d\u0627\u0644\u0629 \u0627\u0644\u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0646\u0634\u0637 (Check OSCam Status)",
        "type": "tool",
        "action": "check_oscam_status",
        "description": u"\u0641\u062d\u0635 \u0645\u0644\u0641 oscam.server \u0648\u0639\u0631\u0636 \u0645\u0639\u0644\u0648\u0645\u0627\u062a \u0633\u064a\u0631\u0641\u0631 \u0627\u0644\u0645\u062a\u062c\u0631 \u0627\u0644\u0634\u063a\u0627\u0644 \u0641\u0642\u0637 (Active Only)."
    },
    {
        "name": u"\u0633\u064a\u0633\u0643\u0627\u0645 \u0627\u0644\u0645\u062a\u062c\u0631 \u0627\u0644\u064a\u0648\u0645\u064a (Store Daily CCcam Server)",
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
        "name": u"\U0001f4be \u0646\u0633\u062e \u0627\u062d\u062a\u064a\u0627\u0637\u064a / \u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0627\u0644\u0625\u0639\u062f\u0627\u062f\u0627\u062a (Backup & Restore)",
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

SKIN_LAYOUT = scale_skin_layout(RAW_SKIN_LAYOUT)

# =========================================================================
# MAIN MOHAMED STORE SCREEN
# =========================================================================
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
        ),
        PluginDescriptor(
            name="Mohamed Store Match Reminders",
            description="Background match reminder notifier",
            where=PluginDescriptor.WHERE_SESSIONSTART,
            fnc=ms_sessionstart
        )
    ]
