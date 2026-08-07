# -*- coding: utf-8 -*-
# ==========================================
# Mohamed Store - Modern Grid Dashboard Edition v1.3.1
# Python 2 & Python 3 fully compatible
# Multi-Content Item & Category Icon Rendering Supported
# Updated Blue Key with Telnet Install Script Execution
# ==========================================

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
import threading
import time

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
    from enigma import gFont, RT_HALIGN_LEFT, eListboxPythonMultiContent
    HAS_MULTICONTENT = True
except ImportError:
    gFont = None
    RT_HALIGN_LEFT = 0
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

VERSION_URL = "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/version.json"
STORE_URL = "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/feed/index.json"
UPDATE_SCRIPT_CMD = "wget -O - https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/install.sh | sh"
PLUGIN_VERSION = "1.3.1"

try:
    PLUGIN_DIR = os.path.dirname(__file__)
except NameError:
    PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore"
ICON_FOLDER = os.path.join(PLUGIN_DIR, "images", "Icons")
FALLBACK_ICON_FOLDER = "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/Icons"

BUILTIN_SYSTEM_TOOLS = [
    {
        "name": u"ط¥طµظ„ط§ط­ ط§ظ„ظ…ظƒطھط¨ط§طھ ظˆط§ظ„ط§ط¹طھظ…ط§ط¯ط§طھ",
        "type": "tool",
        "cmd": "opkg update && opkg install --force-reinstall python-requests curl ffmpeg python-json python-codecs openssl",
        "description": u"طھط­ط¯ط« ط­ط²ظ… ط§ظ„ظ†ط¸ط§ظ… ظˆط¥ط¹ط§ط¯ط© طھط«ط¨ظٹطھ ط§ظ„ظ…ظƒطھط¨ط§طھ ط§ظ„ط£ط³ط§ط³ظٹط© ط§ظ„ظ†ط§ظ‚طµط©."
    },
    {
        "name": u"طھظ†ط¸ظٹظپ ط§ظ„ط°ط§ظƒط±ط© ظˆط§ظ„ظ…ظ„ظپط§طھ ط§ظ„ط¥ظ„ظƒطھط±ظˆظ†ظٹط© ط§ظ„ظ…ط¤ظ‚طھط©",
        "type": "tool",
        "cmd": "rm -rf /tmp/*.ipk /tmp/*.tar.gz /tmp/*.zip /var/volatile/tmp/*",
        "description": u"ط­ط°ظپ ط¬ظ…ظٹط¹ ظ…ظ„ظپط§طھ ط§ظ„طھط«ط¨ظٹطھ ظˆط§ظ„ظ…ظ„ظپط§طھ ط§ظ„ط£ط³ط§ط³ظٹط© ظ…ظ† /tmp."
    },
    {
        "name": u"ط¥ط¹ط§ط¯ط© طھط´ط؛ظٹظ„ ط§ظ„ظˆط§ط¬ظ‡ط© (Restart GUI)",
        "type": "tool",
        "cmd": "restart_gui",
        "description": u"ط¥ط¹ط§ط¯ط© طھط´ط؛ظٹظ„ ظˆط§ط¬ظ‡ط© ط§ظ„ط³ظٹط³طھظ…."
    }
]

def get_category_icon_path(category_id):
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
    elif "channel" in cat_lower:
        filename = "channels.png"
    else:
        filename = None
        
    if filename:
        full_path = os.path.join(ICON_FOLDER, filename)
        if os.path.exists(full_path):
            return full_path
        fallback_path = os.path.join(FALLBACK_ICON_FOLDER, filename)
        if os.path.exists(fallback_path):
            return fallback_path
    return None


def get_item_icon_path(item, category_id):
    if not isinstance(item, dict):
        return get_category_icon_path(category_id)

    # 1. Direct explicit icon/image/thumbnail property check
    for key in ("icon", "image", "thumbnail"):
        val = item.get(key)
        if val and isinstance(val, (str, getattr(sys, 'unicode', str))):
            val = val.strip()
            if os.path.isabs(val) and os.path.exists(val):
                return val
            path1 = os.path.join(ICON_FOLDER, val)
            if os.path.exists(path1):
                return path1
            path2 = os.path.join(FALLBACK_ICON_FOLDER, val)
            if os.path.exists(path2):
                return path2

    # 2. Check icon file matching item id or name (e.g. skin_blackharmony.png)
    item_id = item.get("id") or item.get("name") or ""
    if item_id:
        clean_name = str(item_id).lower().replace(" ", "_").replace("-", "_") + ".png"
        path1 = os.path.join(ICON_FOLDER, clean_name)
        if os.path.exists(path1):
            return path1
        path2 = os.path.join(FALLBACK_ICON_FOLDER, clean_name)
        if os.path.exists(path2):
            return path2

    # 3. Check for specific folder or tool icons
    if "items" in item and isinstance(item["items"], list):
        for folder_icon in ("folder.png", "subfolder.png", "directory.png"):
            path1 = os.path.join(ICON_FOLDER, folder_icon)
            if os.path.exists(path1):
                return path1
            path2 = os.path.join(FALLBACK_ICON_FOLDER, folder_icon)
            if os.path.exists(path2):
                return path2

    if item.get("type") == "tool":
        for tool_icon in ("tools.png", "tool.png"):
            path1 = os.path.join(ICON_FOLDER, tool_icon)
            if os.path.exists(path1):
                return path1
            path2 = os.path.join(FALLBACK_ICON_FOLDER, tool_icon)
            if os.path.exists(path2):
                return path2

    # 4. Fallback to category icon
    cat_icon = get_category_icon_path(category_id)
    if cat_icon:
        return cat_icon

    # 5. Generic package fallback
    for generic in ("package.png", "default.png", "plugins.png"):
        path1 = os.path.join(ICON_FOLDER, generic)
        if os.path.exists(path1):
            return path1
        path2 = os.path.join(FALLBACK_ICON_FOLDER, generic)
        if os.path.exists(path2):
            return path2

    return None


def load_json(url):
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
            response = urllib2.urlopen(req, timeout=12, context=context)
        else:
            response = urllib2.urlopen(req, timeout=12)
        data = response.read()
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        return json.loads(data)
    except Exception as e:
        print("[MohamedStore] load_json error: " + str(e))
        return None


class MohamedStore(Screen):
    skin = """
<screen name="MohamedStore" position="center,center" size="1724,920" title="Mohamed Store" flags="wfNoBorder">
    <!-- Background Base -->
    <eLabel position="0,0" size="1724,920" backgroundColor="#05070c" zPosition="-11" />
    <ePixmap position="0,0" size="1724,920" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/background.png" zPosition="-10" transparent="0" alphatest="off" />

    <!-- TOP HEADER PANEL -->
    <eLabel position="20,15" size="1684,80" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="20,15" size="1684,2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="20,15" size="4,80" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="1700,15" size="4,80" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="20,95" size="1684,2" backgroundColor="#e11d48" />
    
    <ePixmap position="35,25" size="230,50" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/logo.png" zPosition="2" transparent="1" alphatest="blend" />
    <eLabel position="285,34" size="260,35" text="MOHAMED STORE" font="Regular;28" foregroundColor="#f43f5e" backgroundColor="#0f111a" transparent="1" />
    <widget name="device_label" position="560,34" size="940,35" font="Regular;24" foregroundColor="#c084fc" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="1550,30" size="130,40" text=" v1.3.1 " font="Regular;26" foregroundColor="#ffffff" backgroundColor="#be185d" transparent="0" halign="center" />

    <!-- LEFT PANEL: CATEGORIES -->
    <eLabel position="20,112" size="380,688" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="20,112" size="380,2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="20,112" size="4,688" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="396,112" size="4,688" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="32,126" size="356,35" text="CATEGORIES" font="Regular;30" foregroundColor="#f43f5e" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="32,166" size="356,2" backgroundColor="#be185d" />
    
    <widget name="categories_list" position="25,176" size="370,616" itemHeight="80" scrollbarMode="showOnDemand" foregroundColor="#f3f4f6" backgroundColor="#0f111a" selectionColor="#be185d" selectionFontColor="#ffffff" font="Regular;32" />

    <!-- CENTER PANEL: PACKAGES -->
    <eLabel position="412,112" size="780,688" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="412,112" size="780,2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="412,112" size="4,688" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="1188,112" size="4,688" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="428,126" size="748,35" text="AVAILABLE PACKAGES" font="Regular;30" foregroundColor="#f43f5e" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="428,166" size="748,2" backgroundColor="#be185d" />
    <widget name="items_list" position="417,176" size="768,616" itemHeight="76" scrollbarMode="showOnDemand" foregroundColor="#f3f4f6" backgroundColor="#0f111a" selectionColor="#be185d" selectionFontColor="#ffffff" font="Regular;32" />

    <!-- RIGHT PANEL: DETAILS & PROGRESS BOX -->
    <eLabel position="1204,112" size="500,688" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="1204,112" size="500,2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="1204,112" size="4,688" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="1700,112" size="4,688" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="1222,126" size="464,35" text="INFORMATION" font="Regular;30" foregroundColor="#f43f5e" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="1222,166" size="464,2" backgroundColor="#be185d" />
    
    <widget name="description" position="1222,178" size="464,380" font="Regular;30" foregroundColor="#e2e8f0" backgroundColor="#0f111a" transparent="1" valign="top" />

    <eLabel position="1220,568" size="468,222" backgroundColor="#05070c" zPosition="1" />
    <eLabel position="1220,568" size="468,2" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="1220,568" size="2,222" backgroundColor="#e11d48" zPosition="2" />
    <eLabel position="1686,568" size="2,222" backgroundColor="#e11d48" zPosition="2" />
    <eLabel position="1220,788" size="468,2" backgroundColor="#be185d" zPosition="2" />
    
    <widget name="progress" position="1238,584" size="432,16" borderWidth="2" borderColor="#be185d" backgroundColor="#0f111a" zPosition="3" />
    <widget name="percentage" position="1238,610" size="130,32" font="Regular;28" foregroundColor="#f43f5e" backgroundColor="#05070c" transparent="1" zPosition="3" halign="left" />
    <widget name="speed" position="1406,610" size="264,32" font="Regular;28" foregroundColor="#c084fc" backgroundColor="#05070c" transparent="1" zPosition="3" halign="right" />
    <widget name="size" position="1238,652" size="432,32" font="Regular;26" foregroundColor="#f3f4f6" backgroundColor="#05070c" transparent="1" zPosition="3" halign="center" />
    <widget name="status" position="1238,695" size="432,45" font="Regular;26" foregroundColor="#e879f9" backgroundColor="#05070c" transparent="1" zPosition="3" halign="center" />

    <!-- FOOTER BAR -->
    <eLabel position="20,812" size="1684,93" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="20,812" size="1684,2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="20,812" size="4,93" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="1700,812" size="4,93" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="20,903" size="1684,2" backgroundColor="#be185d" zPosition="1" />

    <!-- Red Button: Exit -->
    <eLabel position="40,824" size="395,68" backgroundColor="#1a1025" zPosition="1" />
    <eLabel position="40,824" size="6,68" backgroundColor="#ef4444" zPosition="2" />
    <widget name="key_red" position="58,824" size="365,68" font="Regular;32" foregroundColor="#f87171" backgroundColor="transparent" transparent="1" zPosition="3" halign="left" valign="center" />

    <!-- Green Button: Install / Open -->
    <eLabel position="451,824" size="395,68" backgroundColor="#1a1025" zPosition="1" />
    <eLabel position="451,824" size="6,68" backgroundColor="#22c55e" zPosition="2" />
    <widget name="key_green" position="469,824" size="365,68" font="Regular;32" foregroundColor="#4ade80" backgroundColor="transparent" transparent="1" zPosition="3" halign="left" valign="center" />

    <!-- Yellow Button: Refresh Store -->
    <eLabel position="862,824" size="395,68" backgroundColor="#1a1025" zPosition="1" />
    <eLabel position="862,824" size="6,68" backgroundColor="#eab308" zPosition="2" />
    <widget name="key_yellow" position="880,824" size="365,68" font="Regular;32" foregroundColor="#facc15" backgroundColor="transparent" transparent="1" zPosition="3" halign="left" valign="center" />

    <!-- Blue Button: Update Script -->
    <eLabel position="1273,824" size="395,68" backgroundColor="#1a1025" zPosition="1" />
    <eLabel position="1273,824" size="6,68" backgroundColor="#2563eb" zPosition="2" />
    <widget name="key_blue" position="1291,824" size="365,68" font="Regular;32" foregroundColor="#60a5fa" backgroundColor="transparent" transparent="1" zPosition="3" halign="left" valign="center" />
</screen>
"""

    def __init__(self, session):
        Screen.__init__(self, session)
        
        # Setup Categories List MultiContent
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
                        self["categories_list"].l.setFont(0, gFont("Regular", 32))
                    except Exception as fe:
                        print("[MohamedStore] Failed to set font for categories_list: " + str(fe))
                self["categories_list"].l.setBuildFunc(self.build_category_entry)
                self.categories_list_has_multicontent = True
            except Exception as e:
                print("[MohamedStore] Failed to init categories_list with eListboxPythonMultiContent: " + str(e))
                self["categories_list"] = MenuList([])
        else:
            self["categories_list"] = MenuList([])

        # Setup Items List MultiContent
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
                        self["items_list"].l.setFont(0, gFont("Regular", 32))
                    except Exception as fe:
                        print("[MohamedStore] Failed to set font for items_list: " + str(fe))
                self["items_list"].l.setBuildFunc(self.build_item_entry)
                self.items_list_has_multicontent = True
            except Exception as e:
                print("[MohamedStore] Failed to init items_list with eListboxPythonMultiContent: " + str(e))
                self["items_list"] = MenuList([])
        else:
            self["items_list"] = MenuList([])

        self["description"] = Label("Checking for updates...")
        self["device_label"] = Label(self.get_device_and_image_info())
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
        except:
            pass

        self.download_in_progress = False
        self.download_is_update_script = False
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
                except:
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
        
        self.onLayoutFinish.append(self.check_for_updates)

    def get_device_and_image_info(self):
        device_name = "VU+ Zero 4K"
        image_name = "EGAMI"
        try:
            if os.path.exists("/proc/stb/info/model"):
                with open("/proc/stb/info/model", "r") as f:
                    device_name = f.read().strip().upper()
            elif os.path.exists("/etc/image-version"):
                with open("/etc/image-version", "r") as f:
                    for line in f:
                        if "box_type" in line or "model" in line:
                            device_name = line.split("=")[-1].strip().upper()
                            break

            if os.path.exists("/etc/image-version"):
                with open("/etc/image-version", "r") as f:
                    for line in f:
                        if "imagename" in line or "creator" in line or "name" in line:
                            val = line.split("=")[-1].strip().upper()
                            if val:
                                image_name = val
                                break
        except Exception as e:
            print("[MohamedStore] Device/Image info error: " + str(e))
        
        return "Device: %s | Image: %s" % (device_name, image_name)

    def build_category_entry(self, *args):
        if len(args) == 1 and isinstance(args[0], tuple):
            category_id, display_name = args[0]
        elif len(args) >= 2:
            category_id, display_name = args[0], args[1]
        else:
            category_id = "unknown"
            display_name = "Unknown"

        icon_path = get_category_icon_path(category_id)
        pixmap = None
        if icon_path:
            try:
                if loadPNG:
                    pixmap = loadPNG(icon_path)
            except Exception as e:
                print("[MohamedStore] Error loading category PNG: " + str(e))

        res = [category_id]
        
        if pixmap and HAS_MULTICONTENT and MultiContentEntryPixmapAlphaTest:
            res.append(MultiContentEntryPixmapAlphaTest(pos=(12, 12), size=(56, 56), png=pixmap))
            text_x = 80
            text_w = 280
        else:
            text_x = 15
            text_w = 340

        if HAS_MULTICONTENT and MultiContentEntryText:
            align = RT_HALIGN_LEFT | RT_VALIGN_CENTER
            res.append(MultiContentEntryText(pos=(text_x, 0), size=(text_w, 80), font=0, flags=align, text=display_name))
            
        return res

    def build_item_entry(self, *args):
        if len(args) == 1 and isinstance(args[0], tuple):
            item, display_text, category_id = args[0]
        elif len(args) >= 3:
            item, display_text, category_id = args[0], args[1], args[2]
        elif len(args) == 2:
            item, display_text = args[0], args[1]
            category_id = "unknown"
        else:
            item = {}
            display_text = "Unknown Item"
            category_id = "unknown"

        icon_path = get_item_icon_path(item, category_id)
        pixmap = None
        if icon_path:
            try:
                if loadPNG:
                    pixmap = loadPNG(icon_path)
            except Exception as e:
                print("[MohamedStore] Error loading item PNG: " + str(e))

        res = [item]
        
        if pixmap and HAS_MULTICONTENT and MultiContentEntryPixmapAlphaTest:
            res.append(MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(56, 56), png=pixmap))
            text_x = 78
            text_w = 670
        else:
            text_x = 15
            text_w = 740

        if HAS_MULTICONTENT and MultiContentEntryText:
            align = RT_HALIGN_LEFT | RT_VALIGN_CENTER
            res.append(MultiContentEntryText(pos=(text_x, 0), size=(text_w, 76), font=0, flags=align, text=display_text))
            
        return res

    def is_newer_version(self, online, current):
        try:
            online_parts = [int(x) for x in online.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            max_len = max(len(online_parts), len(current_parts))
            online_parts += [0] * (max_len - len(online_parts))
            current_parts += [0] * (max_len - len(current_parts))
            return online_parts > current_parts
        except Exception as e:
            print("[MohamedStore] Version Check Parsing Error: " + str(e))
            try:
                return float(online) > float(current)
            except:
                return online != current

    def check_for_updates(self):
        try:
            ver_data = load_json(VERSION_URL)
            if ver_data and "plugin_version" in ver_data:
                online_version = str(ver_data["plugin_version"])
                if self.is_newer_version(online_version, PLUGIN_VERSION):
                    self.session.openWithCallback(
                        self.updateAnswer,
                        MessageBox,
                        "A new version of Mohamed Store is available.\nDo you want to update now?",
                        MessageBox.TYPE_YESNO
                    )
                    return
        except Exception as e:
            print("[MohamedStore] Update Check Exception: " + str(e))
            
        self.load_store()

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

    def updateAnswer(self, answer):
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
        self.download_aborted = False
        self.download_completed = False
        self.download_error_msg = ""
        self.download_total_bytes = 0
        self.downloaded_bytes = 0
        self.download_start_time = time.time()
        self.download_last_update_bytes = 0
        self.download_last_update_time = self.download_start_time
        self.download_current_speed = 0.0

        self["description"].setText("Downloading update script...\nProgress & counter active.\nPress RED or BACK to cancel.")
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
        except:
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
        except:
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
            error = result.strip() if result else "Unknown network or execution error"
            self["description"].setText(
                "Self-Update Failed!\n\nExit Code: " + str(retval) + "\n\n" + str(error)
            )

    def restartGUICallback(self, answer):
        if answer:
            try:
                if TryQuitMainloop:
                    self.session.open(TryQuitMainloop, 3)
                else:
                    enigma.quitMainloop(3)
            except:
                try:
                    enigma.quitMainloop(3)
                except:
                    try:
                        enigma.eApp.getInstance().quit(3)
                    except:
                        pass
        else:
            self.load_store()

    def load_store(self):
        try:
            data = load_json(STORE_URL)
            if not data or "categories" not in data:
                self["description"].setText("Failed to load store data from GitHub.")
                return
            
            store_title = "%s v%s" % (data.get("store_name", "M Store"), data.get("version", "1.3.1"))
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
                    display_name = str(cat).replace("_", " ").capitalize()
                    if self.categories_list_has_multicontent:
                        display_cats.append((cat, display_name))
                    else:
                        display_cats.append(display_name)
                        
                self["categories_list"].setList(display_cats)
                self.current_path = []
                self.category_changed()
            else:
                self["description"].setText("Store is empty.")
        except Exception as e:
            self["description"].setText("Load Store Error: " + str(e))

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
        except Exception as e:
            print("[MohamedStore] rebuild_visible_items error: " + str(e))
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
                    display_text = "> " + str(item.get("name", "Unknown Folder"))
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
            cat_name = str(self.categories[cat_idx]).replace("_", " ").capitalize() if cat_idx >= 0 else "Unknown"
            
            path_parts = [cat_name]
            for folder in self.current_path:
                path_parts.append(str(folder.get("name", "")))
            path_str = " > ".join(path_parts)
            
            if item.get("type") == "tool":
                self["key_green"].setText("Execute")
                info_text = "Section: %s\n\nTool Name: %s\n\nDescription:\n%s" % (
                    path_str,
                    str(item.get("name", "")),
                    str(item.get("description", "System tool execution."))
                )
            elif "items" in item and isinstance(item["items"], list):
                self["key_green"].setText("Open")
                info_text = "Section: %s\n\nFolder: %s\n\nPress OK or Green to view items inside this folder." % (
                    path_str,
                    str(item.get("name", ""))
                )
            else:
                self["key_green"].setText("Install")
                info_text = "Section: %s\n\nName: %s\nVersion: %s\n\nDescription:\n%s" % (
                    path_str,
                    str(item.get("name", "")),
                    str(item.get("version", "")),
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
        except:
            pass

    def go_down(self):
        if self.download_in_progress:
            return
        try:
            if self.active_focus == "categories":
                self["categories_list"].down()
            else:
                self["items_list"].down()
        except:
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

                dest_path = ""
                cmd = ""
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
                    cmd = "if ! grep -q '" + filename + "' /etc/enigma2/bouquets.tv; then echo '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "" + filename + "" ORDER BY bouquet' >> /etc/enigma2/bouquets.tv; fi && (wget -qO - http://127.0.0.1/web/servicelistreload?mode=0 || curl -s http://127.0.0.1/web/servicelistreload?mode=0 || true)"
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
                except:
                    pass
                
                self.download_in_progress = True
                
                if self.download_timer:
                    self.download_timer.start(100, False)
                    
                self.download_thread_obj = threading.Thread(target=self.start_download_thread)
                self.download_thread_obj.daemon = True
                self.download_thread_obj.start()
                
        except Exception as e:
            print("[MohamedStore] Download Error: " + str(e))
            self["description"].setText("Execution error, check system log.")

    def tool_execution_finished(self, result, retval, extra_args=None):
        if retval == 0:
            self.session.open(MessageBox, "Tool executed successfully!", MessageBox.TYPE_INFO)
        else:
            error = result.strip() if result else "Execution error"
            self.session.open(MessageBox, "Tool execution failed:\n" + str(error), MessageBox.TYPE_ERROR)
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
            except Exception as qe:
                print("[MohamedStore] Quote error: " + str(qe))
                url = url.replace(" ", "%20")
                
            req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            if context:
                try:
                    opener = urllib2.build_opener(urllib2.HTTPSHandler(context=context))
                except Exception as oe:
                    print("[MohamedStore] Failed to build opener with context: " + str(oe))
                    opener = urllib2.build_opener()
            else:
                opener = urllib2.build_opener()
                
            response = opener.open(req, timeout=12)
                
            try:
                self.download_total_bytes = int(response.info().get('Content-Length', 0))
            except:
                self.download_total_bytes = 0
                
            dir_name = os.path.dirname(self.download_dest_path)
            if dir_name and not os.path.exists(dir_name):
                try:
                    os.makedirs(dir_name)
                except:
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
                    except:
                        pass
            else:
                self.download_completed = True
        except Exception as e:
            self.download_error_msg = str(e)
            if os.path.exists(self.download_dest_path):
                try:
                    os.remove(self.download_dest_path)
                except:
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
                except:
                    pass
            self["percentage"].setText("%d%%" % pct)
            
            dl_mb = float(self.downloaded_bytes) / (1024 * 1024)
            tot_mb = float(self.download_total_bytes) / (1024 * 1024)
            self["size"].setText("%.2f MB / %.2f MB" % (dl_mb, tot_mb))
        else:
            if ProgressBar:
                try:
                    self["progress"].setValue(0)
                except:
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
                except:
                    pass
                self.my_console.ePopen(self.install_cmd + " 2>&1", self.update_finished)
            else:
                try:
                    self["progress"].hide()
                    self["percentage"].hide()
                    self["speed"].hide()
                    self["size"].hide()
                    self["status"].hide()
                except:
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
            except:
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
        except:
            pass
            
        self["key_red"].setText("Exit")
        self["description"].setText("Download cancelled by user.")
        
        if self.download_dest_path and os.path.exists(self.download_dest_path):
            try:
                os.remove(self.download_dest_path)
            except:
                pass

    def install_confirmation_category_callback(self, answer):
        pass

    def install_confirmation_callback(self, answer):
        if answer:
            self["description"].setText("Installing %s...\nPlease wait..." % self.install_item_name)
            self.my_console.ePopen(self.install_cmd + " 2>&1", self.download_finished)
        else:
            self["description"].setText("Installation completed successfully. Restart skipped.")
            self.item_changed()

    def download_finished(self, result, retval, extra_args=None):
        if retval == 0:
            self.session.openWithCallback(self.restartCallback, MessageBox, "Installation completed successfully!\n\nRestart GUI now?", MessageBox.TYPE_YESNO)
        else:
            error = result.strip() if result else "Unknown error"
            print("[MohamedStore] Install output:\n" + str(error))
            self["description"].setText(
                "Installation Failed!\n\nExit Code: " + str(retval) + "\n\n" + str(error)
            )

    def restartCallback(self, answer):
        if answer:
            try:
                if TryQuitMainloop:
                    self.session.open(TryQuitMainloop, 3)
                elif enigma:
                    enigma.quitMainloop(3)
            except:
                try:
                    if enigma:
                        enigma.quitMainloop(3)
                except:
                    try:
                        enigma.eApp.getInstance().quit(3)
                    except:
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
