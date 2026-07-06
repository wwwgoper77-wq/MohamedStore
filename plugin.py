# -*- coding: utf-8 -*-
# ==========================================
# Mohamed Store - Enigma2 Plugin Extension
# Redesigned Premium UI & Optimized Layout
# Python 2 & Python 3 fully compatible
# Supports: OpenATV, OpenPLi, DreamOS, Egami, BlackHole, etc.
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

# Try importing standby and main loop controllers safely
try:
    from Screens.Standby import TryQuitMainloop
except ImportError:
    TryQuitMainloop = None

try:
    import enigma
except ImportError:
    enigma = None

# Try importing Enigma2 MultiContent classes safely
try:
    from enigma import gFont, RT_HALIGN_LEFT, eListboxPythonMultiContent
    HAS_MULTICONTENT = True
except ImportError:
    gFont = None
    RT_HALIGN_LEFT = 0
    eListboxPythonMultiContent = None
    HAS_MULTICONTENT = False

# Load PNG utility safely
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

# Core configuration variables
VERSION_URL = "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/version.json"
STORE_URL = "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/feed/index.json"
PLUGIN_VERSION = "1.0"

# Robust path resolution to locate images relative to plugin root on any image/installation
try:
    PLUGIN_DIR = os.path.dirname(__file__)
except NameError:
    PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore"
ICON_FOLDER = os.path.join(PLUGIN_DIR, "images", "Icons")
FALLBACK_ICON_FOLDER = "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/Icons"

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
    else:
        filename = None
        
    if filename:
        full_path = os.path.join(ICON_FOLDER, filename)
        if os.path.exists(full_path):
            return full_path
        # Absolute fallback if relative path fails
        fallback_path = os.path.join(FALLBACK_ICON_FOLDER, filename)
        if os.path.exists(fallback_path):
            return fallback_path
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
    # Redesigned skin with OLED Obsidian Dark (#0C0D12), Slate card container background (#151720),
    # sleek 1px slate borders (#222634), and modern Electric Blue accents (#0088FF)
    # Optimized layout boundaries with user-requested larger TV font sizes:
    # Title: 34, Category names: 28, Packages: 26, Description: 24, Footer keys: 24
    skin = """
<screen name="MohamedStore" position="center,center" size="1280,720" title="Mohamed Store" flags="wfNoBorder">
    <!-- Screen Background (OLED Dark Obsidian Fallback) -->
    <eLabel position="0,0" size="1280,720" backgroundColor="#0C0D12" zPosition="-11" />
    <!-- Screen Background Image (Sleek abstract dark texture) -->
    <ePixmap position="0,0" size="1280,720" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/background.png" zPosition="-10" transparent="0" alphatest="off" />

    <!-- ==================== HEADER PANEL ==================== -->
    <eLabel position="30,30" size="1220,90" backgroundColor="#20151720" zPosition="-1" />
    <eLabel position="30,30" size="1220,2" backgroundColor="#0088FF" /> <!-- Top Accent -->
    <eLabel position="30,30" size="1,90" backgroundColor="#222634" /> <!-- Left Border -->
    <eLabel position="1249,30" size="1,90" backgroundColor="#222634" /> <!-- Right Border -->
    <eLabel position="30,119" size="1220,1" backgroundColor="#222634" /> <!-- Bottom Border -->
    
    <eLabel position="60,48" size="400,50" text="MOHAMED STORE" font="Regular;34" foregroundColor="#FFFFFF" backgroundColor="#20151720" transparent="1" />
    <eLabel position="440,60" size="500,30" text="Premium Addon Repository" font="Regular;18" foregroundColor="#A8ADB7" backgroundColor="#20151720" transparent="1" />
    <eLabel position="1100,60" size="120,30" text="v1.0" font="Regular;18" foregroundColor="#A8ADB7" backgroundColor="#20151720" transparent="1" halign="right" />

    <!-- ==================== CATEGORIES PANEL ==================== -->
    <eLabel position="30,140" size="300,440" backgroundColor="#20151720" zPosition="-1" />
    <eLabel position="30,140" size="300,2" backgroundColor="#0088FF" /> <!-- Top Accent -->
    <eLabel position="30,140" size="1,440" backgroundColor="#222634" /> <!-- Left Border -->
    <eLabel position="329,140" size="1,440" backgroundColor="#222634" /> <!-- Right Border -->
    <eLabel position="30,579" size="300,1" backgroundColor="#222634" /> <!-- Bottom Border -->
    
    <eLabel position="50,155" size="260,30" text="CATEGORIES" font="Regular;16" foregroundColor="#A8ADB7" backgroundColor="#20151720" transparent="1" />
    <widget name="categories_list" position="45,195" size="270,365" itemHeight="60" scrollbarMode="showOnDemand" foregroundColor="#FFFFFF" backgroundColor="#20151720" selectionColor="#0088FF" selectionFontColor="#FFFFFF" font="Regular;28" />

    <!-- ==================== PACKAGES PANEL ==================== -->
    <eLabel position="350,140" size="520,440" backgroundColor="#20151720" zPosition="-1" />
    <eLabel position="350,140" size="520,2" backgroundColor="#0088FF" /> <!-- Top Accent -->
    <eLabel position="350,140" size="1,440" backgroundColor="#222634" /> <!-- Left Border -->
    <eLabel position="869,140" size="1,440" backgroundColor="#222634" /> <!-- Right Border -->
    <eLabel position="350,579" size="520,1" backgroundColor="#222634" /> <!-- Bottom Border -->
    
    <eLabel position="370,155" size="480,30" text="AVAILABLE PACKAGES" font="Regular;16" foregroundColor="#A8ADB7" backgroundColor="#20151720" transparent="1" />
    <widget name="items_list" position="365,195" size="490,365" itemHeight="60" scrollbarMode="showOnDemand" foregroundColor="#FFFFFF" backgroundColor="#20151720" selectionColor="#0088FF" selectionFontColor="#FFFFFF" font="Regular;26" />

    <!-- ==================== DETAILS PANEL ==================== -->
    <eLabel position="890,140" size="360,440" backgroundColor="#20151720" zPosition="-1" />
    <eLabel position="890,140" size="360,2" backgroundColor="#0088FF" /> <!-- Top Accent -->
    <eLabel position="890,140" size="1,440" backgroundColor="#222634" /> <!-- Left Border -->
    <eLabel position="1249,140" size="1,440" backgroundColor="#222634" /> <!-- Right Border -->
    <eLabel position="890,579" size="360,1" backgroundColor="#222634" /> <!-- Bottom Border -->
    
    <eLabel position="910,155" size="320,30" text="DETAILS" font="Regular;16" foregroundColor="#A8ADB7" backgroundColor="#20151720" transparent="1" />
    <widget name="description" position="910,195" size="320,365" font="Regular;24" foregroundColor="#FFFFFF" backgroundColor="#20151720" transparent="1" valign="top" />

    <!-- ==================== FOOTER PANEL ==================== -->
    <eLabel position="30,600" size="1220,90" backgroundColor="#20151720" zPosition="-1" />
    <eLabel position="30,600" size="1220,2" backgroundColor="#0088FF" /> <!-- Top Accent -->
    <eLabel position="30,600" size="1,90" backgroundColor="#222634" /> <!-- Left Border -->
    <eLabel position="1249,600" size="1,90" backgroundColor="#222634" /> <!-- Right Border -->
    <eLabel position="30,689" size="1220,1" backgroundColor="#222634" /> <!-- Bottom Border -->
    
    <!-- Red = Exit -->
    <eLabel position="60,638" size="14,14" backgroundColor="#E74C3C" />
    <widget name="key_red" position="85,622" size="240,40" font="Regular;24" foregroundColor="#FFFFFF" backgroundColor="#20151720" transparent="1" halign="left" />

    <!-- Green = Install -->
    <eLabel position="350,638" size="14,14" backgroundColor="#2ECC71" />
    <widget name="key_green" position="375,622" size="240,40" font="Regular;24" foregroundColor="#FFFFFF" backgroundColor="#20151720" transparent="1" halign="left" />

    <!-- Yellow = Refresh (Static visual button) -->
    <eLabel position="640,638" size="14,14" backgroundColor="#F1C40F" />
    <eLabel position="665,622" size="240,40" text="Refresh" font="Regular;24" foregroundColor="#FFFFFF" backgroundColor="#20151720" transparent="1" halign="left" />

    <!-- Blue = Update (Static visual button) -->
    <eLabel position="930,638" size="14,14" backgroundColor="#0088FF" />
    <eLabel position="955,622" size="240,40" text="Update" font="Regular;24" foregroundColor="#FFFFFF" backgroundColor="#20151720" transparent="1" halign="left" />
</screen>
"""

    def __init__(self, session):
        Screen.__init__(self, session)
        
        # Safe MultiContent initialization for categories list
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
                        self["categories_list"].l.setFont(0, gFont("Regular", 28))
                    except Exception as fe:
                        print("[MohamedStore] Failed to set font: " + str(fe))
                self["categories_list"].l.setBuildFunc(self.build_category_entry)
                self.categories_list_has_multicontent = True
            except Exception as e:
                print("[MohamedStore] Failed to init MenuList with eListboxPythonMultiContent: " + str(e))
                self["categories_list"] = MenuList([])
        else:
            self["categories_list"] = MenuList([])
            
        self["items_list"] = MenuList([])
        self["description"] = Label("Checking for updates...")
        self["key_red"] = Label("Exit")
        self["key_green"] = Label("Install")
        
        self.store_data = {}
        self.categories = []
        self.visible_items = []
        self.current_path = []  # Keeps track of the nested folder objects we are currently inside
        self.active_focus = "categories"
        self.my_console = Console()
        
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"], {
            "cancel": self.go_back,
            "red": self.close,
            "green": self.download,
            "ok": self.press_ok,
            "up": self.go_up,
            "down": self.go_down,
            "left": self.switch_to_categories,
            "right": self.switch_to_items,
        }, -1)
        
        self["categories_list"].onSelectionChanged.append(self.category_changed)
        self["items_list"].onSelectionChanged.append(self.item_changed)
        
        self.onLayoutFinish.append(self.check_for_updates)

    def build_category_entry(self, *args):
        """
        Build function called dynamically by Enigma2 for each list item in Categories.
        Handles both unpacked arguments and single-tuple arguments to be 100% compatible
        across all Enigma2 images (OpenATV, OpenPLi, Egami, DreamOS, BlackHole, etc.).
        """
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
                print("[MohamedStore] Error loading PNG: " + str(e))

        res = [category_id]  # First element is selection user-data (key)
        
        if pixmap and HAS_MULTICONTENT and MultiContentEntryPixmapAlphaTest:
            res.append(MultiContentEntryPixmapAlphaTest(pos=(12, 14), size=(32, 32), png=pixmap))
            text_x = 54
            text_w = 206 # Adjusted for the new 270 width of categories_list (270 - 54 - 10)
        else:
            text_x = 12
            text_w = 248 # Adjusted for the new 270 width of categories_list (270 - 12 - 10)

        if HAS_MULTICONTENT and MultiContentEntryText:
            align = RT_HALIGN_LEFT | RT_VALIGN_CENTER
            # Fix: Pass the registered font index (0) as an integer instead of the gFont object directly
            # This completely avoids "TypeError: 'gFont' object cannot be interpreted as an integer" in modern Enigma2 images
            res.append(MultiContentEntryText(pos=(text_x, 0), size=(text_w, 60), font=0, flags=align, text=display_name))
            
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
        print("[MohamedStore] check_for_updates called")
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

    def updateAnswer(self, answer):
        if answer:
            self["description"].setText("Downloading and installing self-update...\nPlease wait...")
            update_url = "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/MohamedStore/plugin.py"
            dest_path = "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/plugin.py"
            temp_path = "/tmp/plugin.py"
            
            # Robust, secure update command:
            cmd = (
                "rm -f {temp_path} && "
                "(wget --no-check-certificate -O {temp_path} '{update_url}' || curl -k -L -o {temp_path} '{update_url}') && "
                "[ -s {temp_path} ] && grep -q 'class MohamedStore' {temp_path} && "
                "mv -f {temp_path} {dest_path} && "
                "rm -f {dest_path}c {dest_path}o && "
                "rm -rf /usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/__pycache__"
            ).format(temp_path=temp_path, update_url=update_url, dest_path=dest_path)
            
            self.my_console.ePopen(cmd + " 2>&1", self.update_finished)
        else:
            self.load_store()

    def update_finished(self, result, retval, extra_args=None):
        if retval == 0:
            self.session.openWithCallback(
                self.restartGUICallback,
                MessageBox,
                "Mohamed Store updated successfully!\n\nRestart GUI now?",
                MessageBox.TYPE_YESNO
            )
        else:
            error = result.strip() if result else "Unknown network or file validation error"
            print("[MohamedStore] Self-Update Failed: " + str(error))
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
            
            store_title = "%s v%s" % (data.get("store_name", "M Store"), data.get("version", "1.0"))
            self.setTitle(store_title)
            
            self.store_data = data["categories"]
            if isinstance(self.store_data, dict):
                self.categories = list(self.store_data.keys())
            else:
                self.categories = []
            
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
            
            list_names = []
            for item in self.visible_items:
                if "items" in item and isinstance(item["items"], list):
                    list_names.append("> " + str(item.get("name", "Unknown Folder")))
                else:
                    list_names.append("%s  (v%s)" % (str(item.get("name", "Unknown")), str(item.get("version", "1.0"))))
            
            self["items_list"].setList(list_names)
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
            
            if "items" in item and isinstance(item["items"], list):
                info_text = "Section: %s\n\nFolder: %s\n\nPress OK to view packages inside this folder." % (
                    path_str,
                    str(item.get("name", ""))
                )
            else:
                info_text = "Section: %s\n\nName: %s\nVersion: %s\n\nDescription:\n%s" % (
                    path_str,
                    str(item.get("name", "")),
                    str(item.get("version", "")),
                    str(item.get("description", "No description available."))
                )
            self["description"].setText(info_text)
        except Exception as e:
            self["description"].setText("Item Change Error: " + str(e))

    def switch_to_items(self):
        if self.visible_items:
            self.active_focus = "items"
            self["description"].setText("Navigating: Items List\n\nPress OK or Green to Install.")

    def switch_to_categories(self):
        if self.active_focus == "items" and len(self.current_path) > 0:
            self.current_path.pop()
            self.rebuild_visible_items()
            self.update_items_list()
        else:
            self.active_focus = "categories"
            self.current_path = []
            self.category_changed()

    def go_up(self):
        try:
            if self.active_focus == "categories":
                self["categories_list"].up()
            else:
                self["items_list"].up()
        except:
            pass

    def go_down(self):
        try:
            if self.active_focus == "categories":
                self["categories_list"].down()
            else:
                self["items_list"].down()
        except:
            pass

    def press_ok(self):
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
        if self.active_focus == "items" and len(self.current_path) > 0:
            self.current_path.pop()
            self.rebuild_visible_items()
            self.update_items_list()
        elif self.active_focus == "items" and len(self.current_path) == 0:
            self.switch_to_categories()
        else:
            self.close()

    def download(self):
        try:
            idx = self["items_list"].getSelectionIndex()
            if idx >= 0 and idx < len(self.visible_items) and self.visible_items:
                item = self.visible_items[idx]
                
                if "items" in item and isinstance(item["items"], list):
                    self.current_path.append(item)
                    self.rebuild_visible_items()
                    self.update_items_list()
                    return
                
                url = item.get("file", "").strip()
                if not url:
                    self["description"].setText("Error: Download URL is missing in JSON.")
                    return
                
                self["description"].setText("Downloading and installing %s...\nPlease wait..." % str(item.get("name", "")))
                
                if url.endswith(".deb"):
                    cmd = "(wget --no-check-certificate -O /tmp/addon.deb '{url}' || curl -k -L -o /tmp/addon.deb '{url}') && dpkg -i /tmp/addon.deb && rm -f /tmp/addon.deb"
                else:
                    cmd = "(wget --no-check-certificate -O /tmp/addon.ipk '{url}' || curl -k -L -o /tmp/addon.ipk '{url}') && opkg install --force-overwrite /tmp/addon.ipk && rm -f /tmp/addon.ipk"
                cmd = cmd.format(url=url)
                    
                self.my_console.ePopen(cmd + " 2>&1", self.download_finished)
        except Exception as e:
            print("[MohamedStore] Download Error: " + str(e))
            self["description"].setText("Execution error, check system log.")

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
            self["description"].setText("Installation completed successfully. Restart skipped.")

# Descriptor hooks for Enigma2
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
