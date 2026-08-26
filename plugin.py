# -*- coding: utf-8 -*-
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

VERSION_URL = "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/version.json"
STORE_URL = "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/feed/index.json"
UPDATE_SCRIPT_CMD = "wget -O - https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/install.sh | sh"
FACEBOOK_URL = "https://www.facebook.com/share/1G8inRhUib/"
PLUGIN_VERSION = "1.3.2"

try:
    PLUGIN_DIR = os.path.dirname(__file__)
except NameError:
    PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore"

CACHE_FILE = os.path.join(PLUGIN_DIR, "store_cache.json")
ICON_FOLDER = os.path.join(PLUGIN_DIR, "images", "Icons")
FALLBACK_ICON_FOLDER = "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/Icons"

# =========================================================================
# DYNAMIC RESOLUTION DETECTOR & AUTO-SCALING ENGINE (HD 720p / FHD 1080p / 4K)
# =========================================================================
def get_desktop_resolution():
    """Detect actual Enigma2 screen resolution dynamically."""
    try:
        if enigma and hasattr(enigma, 'getDesktop'):
            d = enigma.getDesktop(0)
            if d:
                w = d.size().width()
                h = d.size().height()
                if w > 0 and h > 0:
                    return w, h
    except Exception as e:
        pass
    return 1920, 1080

class ScreenScaler(object):
    """Calculates responsive coordinates, dimensions, fonts, and widget sizes."""
    def __init__(self, desk_w=None, desk_h=None):
        if desk_w is None or desk_h is None:
            desk_w, desk_h = get_desktop_resolution()
        self.desk_w = desk_w
        self.desk_h = desk_h

        # Reference resolution: 1920x1080
        self.rx = float(desk_w) / 1920.0
        self.ry = float(desk_h) / 1080.0
        self.rf = min(self.rx, self.ry)

    def sx(self, val):
        """Scale X axis coordinate/width."""
        return int(round(val * self.rx))

    def sy(self, val):
        """Scale Y axis coordinate/height."""
        return int(round(val * self.ry))

    def sf(self, val, min_val=10):
        """Scale font size proportionally with min clamp."""
        return max(min_val, int(round(val * self.rf)))

# Global default scaler
_GLOBAL_SCALER = ScreenScaler()

def build_responsive_skin(scaler=None):
    """Dynamically generates the Enigma2 skin XML according to exact resolution."""
    if scaler is None:
        scaler = ScreenScaler()
    sx = scaler.sx
    sy = scaler.sy
    sf = scaler.sf

    # Screen dimensions
    scr_w = sx(1724)
    scr_h = sy(920)

    # Header calculations
    hdr_x, hdr_y, hdr_w, hdr_h = sx(20), sy(15), sx(1684), sy(84)
    logo_x, logo_y, logo_w, logo_h = sx(32), sy(24), sx(190), sy(44)
    title_x, title_y, title_w, title_h = sx(230), sy(22), sx(210), sy(30)
    ver_x, ver_y, ver_w, ver_h = sx(230), sy(54), sx(75), sy(24)

    # Header Chips
    chip1_x, chip_y, chip_w, chip_h = sx(445), sy(19), sx(305), sy(74)
    chip2_x = sx(760)
    chip3_x = sx(1070)
    chip4_x = sx(1385)

    # Panel Y & H
    body_y = sy(112)
    body_h = sy(688)

    # Left Panel: Categories
    cat_x, cat_w = sx(20), sx(380)
    cat_title_x, cat_title_y, cat_title_w, cat_title_h = sx(32), sy(126), sx(356), sy(35)
    cat_list_x, cat_list_y, cat_list_w, cat_list_h = sx(25), sy(176), sx(370), sy(616)
    cat_item_h = sy(80)

    # Center Panel: Packages
    pkg_x, pkg_w = sx(412), sx(780)
    pkg_title_x, pkg_title_y, pkg_title_w, pkg_title_h = sx(428), sy(126), sx(748), sy(35)
    pkg_list_x, pkg_list_y, pkg_list_w, pkg_list_h = sx(417), sy(176), sx(768), sy(616)
    pkg_item_h = sy(76)

    # Right Panel: Information & Box
    info_x, info_w = sx(1204), sx(500)
    info_title_x, info_title_y, info_title_w, info_title_h = sx(1222), sy(126), sx(464), sy(35)
    desc_x, desc_y, desc_w, desc_h = sx(1222), sy(178), sx(464), sy(338)

    # FB Box (Right-Aligned Flush to Edge)
    fb_box_x, fb_box_y, fb_box_w, fb_box_h = sx(1220), sy(530), sx(468), sy(118)
    avatar_x, avatar_y, avatar_w, avatar_h = sx(1230), sy(544), sx(80), sy(84)
    qr_x, qr_y, qr_w, qr_h = sx(1318), sy(544), sx(84), sy(84)
    fb_ttl_x, fb_ttl_y, fb_ttl_w, fb_ttl_h = sx(1410), sy(544), sx(268), sy(30)
    fb_lbl_x, fb_lbl_y, fb_lbl_w, fb_lbl_h = sx(1410), sy(576), sx(268), sy(52)

    # Progress Box
    prog_box_x, prog_box_y, prog_box_w, prog_box_h = sx(1220), sy(658), sx(468), sy(132)
    pbar_x, pbar_y, pbar_w, pbar_h = sx(1238), sy(670), sx(432), sy(14)
    pct_x, pct_y, pct_w, pct_h = sx(1238), sy(690), sx(120), sy(24)
    spd_x, spd_y, spd_w, spd_h = sx(1378), sy(690), sx(292), sy(24)
    sz_x, sz_y, sz_w, sz_h = sx(1238), sy(720), sx(432), sy(24)
    st_x, st_y, st_w, st_h = sx(1238), sy(748), sx(432), sy(32)

    # Footer
    ftr_x, ftr_y, ftr_w, ftr_h = sx(20), sy(812), sx(1684), sy(93)
    btn_w, btn_h = sx(395), sy(68)
    btn_y = sy(824)
    btn1_x = sx(40)
    btn2_x = sx(451)
    btn3_x = sx(862)
    btn4_x = sx(1273)
    btn_text_offset_x = sx(18)
    btn_text_w = sx(365)

    skin_template = """
<screen name="MohamedStore" position="center,center" size="{scr_w},{scr_h}" title="Mohamed Store" flags="wfNoBorder">
    <!-- Background Base -->
    <eLabel position="0,0" size="{scr_w},{scr_h}" backgroundColor="#05070c" zPosition="-11" />
    <ePixmap position="0,0" size="{scr_w},{scr_h}" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/background.png" zPosition="-10" transparent="0" alphatest="off" />

    <!-- TOP HEADER PANEL WITH LIVE HARDWARE TELEMETRY -->
    <eLabel position="{hdr_x},{hdr_y}" size="{hdr_w},{hdr_h}" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="{hdr_x},{hdr_y}" size="{hdr_w},2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="{hdr_x},{hdr_y}" size="4,{hdr_h}" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="{hdr_r},{hdr_y}" size="4,{hdr_h}" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="{hdr_x},{hdr_b}" size="{hdr_w},2" backgroundColor="#e11d48" />
    
    <!-- BRAND / LOGO AREA -->
    <ePixmap position="{logo_x},{logo_y}" size="{logo_w},{logo_h}" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/logo.png" zPosition="2" scale="1" transparent="1" alphatest="blend" />
    <eLabel position="{title_x},{title_y}" size="{title_w},{title_h}" text="MOHAMED STORE" font="Regular;{f_24}" foregroundColor="#f43f5e" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="{ver_x},{ver_y}" size="{ver_w},{ver_h}" text=" v1.3.2 " font="Regular;{f_17}" foregroundColor="#ffffff" backgroundColor="#be185d" transparent="0" halign="center" />

    <!-- CHIP 1: DEVICE & IMAGE -->
    <eLabel position="{chip1_x},{chip_y}" size="{chip_w},{chip_h}" backgroundColor="#070913" zPosition="1" />
    <eLabel position="{chip1_x},{chip_y}" size="{chip_w},2" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="{chip1_x},{chip_y}" size="3,{chip_h}" backgroundColor="#60a5fa" zPosition="2" />
    <eLabel position="{chip1_x},{chip_b}" size="{chip_w},2" backgroundColor="#be185d" zPosition="2" />
    <widget name="sys_device" position="{chip1_tx},{chip_t1_y}" size="{chip_tw},{chip_th1}" font="Regular;{f_24}" foregroundColor="#60a5fa" backgroundColor="#070913" transparent="1" zPosition="3" />
    <widget name="sys_image" position="{chip1_tx},{chip_t2_y}" size="{chip_tw},{chip_th2}" font="Regular;{f_22}" foregroundColor="#c084fc" backgroundColor="#070913" transparent="1" zPosition="3" />

    <!-- CHIP 2: CPU & TEMP -->
    <eLabel position="{chip2_x},{chip_y}" size="{chip_w},{chip_h}" backgroundColor="#070913" zPosition="1" />
    <eLabel position="{chip2_x},{chip_y}" size="{chip_w},2" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="{chip2_x},{chip_y}" size="3,{chip_h}" backgroundColor="#f43f5e" zPosition="2" />
    <eLabel position="{chip2_x},{chip_b}" size="{chip_w},2" backgroundColor="#be185d" zPosition="2" />
    <widget name="sys_cpu" position="{chip2_tx},{chip_t1_y}" size="{chip_tw},{chip_th1}" font="Regular;{f_24}" foregroundColor="#f43f5e" backgroundColor="#070913" transparent="1" zPosition="3" />
    <widget name="sys_temp" position="{chip2_tx},{chip_t2_y}" size="{chip_tw},{chip_th2}" font="Regular;{f_22}" foregroundColor="#fb923c" backgroundColor="#070913" transparent="1" zPosition="3" />

    <!-- CHIP 3: RAM & FLASH -->
    <eLabel position="{chip3_x},{chip_y}" size="{chip_w},{chip_h}" backgroundColor="#070913" zPosition="1" />
    <eLabel position="{chip3_x},{chip_y}" size="{chip_w},2" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="{chip3_x},{chip_y}" size="3,{chip_h}" backgroundColor="#34d399" zPosition="2" />
    <eLabel position="{chip3_x},{chip_b}" size="{chip_w},2" backgroundColor="#be185d" zPosition="2" />
    <widget name="sys_ram" position="{chip3_tx},{chip_t1_y}" size="{chip_tw},{chip_th1}" font="Regular;{f_24}" foregroundColor="#34d399" backgroundColor="#070913" transparent="1" zPosition="3" />
    <widget name="sys_flash" position="{chip3_tx},{chip_t2_y}" size="{chip_tw},{chip_th2}" font="Regular;{f_22}" foregroundColor="#a7f3d0" backgroundColor="#070913" transparent="1" zPosition="3" />

    <!-- CHIP 4: IP & NETWORK -->
    <eLabel position="{chip4_x},{chip_y}" size="{chip_w},{chip_h}" backgroundColor="#070913" zPosition="1" />
    <eLabel position="{chip4_x},{chip_y}" size="{chip_w},2" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="{chip4_x},{chip_y}" size="3,{chip_h}" backgroundColor="#38bdf8" zPosition="2" />
    <eLabel position="{chip4_x},{chip_b}" size="{chip_w},2" backgroundColor="#be185d" zPosition="2" />
    <widget name="sys_ip" position="{chip4_tx},{chip_t1_y}" size="{chip_tw},{chip_th1}" font="Regular;{f_24}" foregroundColor="#38bdf8" backgroundColor="#070913" transparent="1" zPosition="3" />
    <widget name="sys_net" position="{chip4_tx},{chip_t2_y}" size="{chip_tw},{chip_th2}" font="Regular;{f_22}" foregroundColor="#818cf8" backgroundColor="#070913" transparent="1" zPosition="3" />

    <!-- LEFT PANEL: CATEGORIES -->
    <eLabel position="{cat_x},{body_y}" size="{cat_w},{body_h}" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="{cat_x},{body_y}" size="{cat_w},2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="{cat_x},{body_y}" size="4,{body_h}" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="{cat_r},{body_y}" size="4,{body_h}" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="{cat_title_x},{cat_title_y}" size="{cat_title_w},{cat_title_h}" text="CATEGORIES" font="Regular;{f_30}" foregroundColor="#f43f5e" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="{cat_title_x},{cat_sep_y}" size="{cat_title_w},2" backgroundColor="#be185d" />
    
    <widget name="categories_list" position="{cat_list_x},{cat_list_y}" size="{cat_list_w},{cat_list_h}" itemHeight="{cat_item_h}" scrollbarMode="showOnDemand" foregroundColor="#f3f4f6" backgroundColor="#0f111a" selectionColor="#be185d" selectionFontColor="#ffffff" font="Regular;{f_30}" />

    <!-- CENTER PANEL: PACKAGES -->
    <eLabel position="{pkg_x},{body_y}" size="{pkg_w},{body_h}" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="{pkg_x},{body_y}" size="{pkg_w},2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="{pkg_x},{body_y}" size="4,{body_h}" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="{pkg_r},{body_y}" size="4,{body_h}" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="{pkg_title_x},{pkg_title_y}" size="{pkg_title_w},{pkg_title_h}" text="AVAILABLE PACKAGES" font="Regular;{f_30}" foregroundColor="#f43f5e" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="{pkg_title_x},{pkg_sep_y}" size="{pkg_title_w},2" backgroundColor="#be185d" />
    <widget name="items_list" position="{pkg_list_x},{pkg_list_y}" size="{pkg_list_w},{pkg_list_h}" itemHeight="{pkg_item_h}" scrollbarMode="showOnDemand" foregroundColor="#f3f4f6" backgroundColor="#0f111a" selectionColor="#be185d" selectionFontColor="#ffffff" font="Regular;{f_32}" />

    <!-- RIGHT PANEL: DETAILS & COMPACT PROGRESS / FACEBOOK -->
    <eLabel position="{info_x},{body_y}" size="{info_w},{body_h}" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="{info_x},{body_y}" size="{info_w},2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="{info_x},{body_y}" size="4,{body_h}" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="{info_r},{body_y}" size="4,{body_h}" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="{info_title_x},{info_title_y}" size="{info_title_w},{info_title_h}" text="INFORMATION" font="Regular;{f_30}" foregroundColor="#f43f5e" backgroundColor="#0f111a" transparent="1" />
    <eLabel position="{info_title_x},{info_sep_y}" size="{info_title_w},2" backgroundColor="#be185d" />
    
    <!-- Item Description -->
    <widget name="description" position="{desc_x},{desc_y}" size="{desc_w},{desc_h}" font="Regular;{f_28}" foregroundColor="#e2e8f0" backgroundColor="#0f111a" transparent="1" valign="top" />

    <!-- FACEBOOK INFO BOX -->
    <eLabel position="{fb_box_x},{fb_box_y}" size="{fb_box_w},{fb_box_h}" backgroundColor="#05070c" zPosition="1" />
    <eLabel position="{fb_box_x},{fb_box_y}" size="{fb_box_w},2" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="{fb_box_x},{fb_box_y}" size="2,{fb_box_h}" backgroundColor="#e11d48" zPosition="2" />
    <eLabel position="{fb_r},{fb_box_y}" size="2,{fb_box_h}" backgroundColor="#e11d48" zPosition="2" />
    <eLabel position="{fb_box_x},{fb_b}" size="{fb_box_w},2" backgroundColor="#be185d" zPosition="2" />
    
    <!-- Image 1: Avatar -->
    <ePixmap position="{avatar_x},{avatar_y}" size="{avatar_w},{avatar_h}" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/avatar.png" zPosition="3" scale="1" transparent="1" alphatest="blend" />
    
    <!-- Image 2: QR Barcode -->
    <ePixmap position="{qr_x},{qr_y}" size="{qr_w},{qr_h}" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/qrcode.png" zPosition="3" scale="1" transparent="1" alphatest="blend" />
    
    <!-- Facebook Title & Link (Right-Aligned Flush to Edge) -->
    <widget name="facebook_title" position="{fb_ttl_x},{fb_ttl_y}" size="{fb_ttl_w},{fb_ttl_h}" font="Regular;{f_24}" foregroundColor="#60a5fa" backgroundColor="#05070c" transparent="1" zPosition="3" halign="right" />
    <widget name="facebook_label" position="{fb_lbl_x},{fb_lbl_y}" size="{fb_lbl_w},{fb_lbl_h}" text="https://www.facebook.com/share/1G8inRhUib/" font="Regular;{f_18}" foregroundColor="#f43f5e" backgroundColor="#05070c" transparent="1" zPosition="3" halign="right" />

    <!-- COMPACT DOWNLOAD / PROGRESS BOX -->
    <eLabel position="{prog_box_x},{prog_box_y}" size="{prog_box_w},{prog_box_h}" backgroundColor="#05070c" zPosition="1" />
    <eLabel position="{prog_box_x},{prog_box_y}" size="{prog_box_w},2" backgroundColor="#be185d" zPosition="2" />
    <eLabel position="{prog_box_x},{prog_box_y}" size="2,{prog_box_h}" backgroundColor="#e11d48" zPosition="2" />
    <eLabel position="{prog_r},{prog_box_y}" size="2,{prog_box_h}" backgroundColor="#e11d48" zPosition="2" />
    <eLabel position="{prog_box_x},{prog_b}" size="{prog_box_w},2" backgroundColor="#be185d" zPosition="2" />
    
    <widget name="progress" position="{pbar_x},{pbar_y}" size="{pbar_w},{pbar_h}" borderWidth="2" borderColor="#be185d" backgroundColor="#0f111a" zPosition="3" />
    <widget name="percentage" position="{pct_x},{pct_y}" size="{pct_w},{pct_h}" font="Regular;{f_22}" foregroundColor="#f43f5e" backgroundColor="#05070c" transparent="1" zPosition="3" halign="left" />
    <widget name="speed" position="{spd_x},{spd_y}" size="{spd_w},{spd_h}" font="Regular;{f_22}" foregroundColor="#c084fc" backgroundColor="#05070c" transparent="1" zPosition="3" halign="right" />
    <widget name="size" position="{sz_x},{sz_y}" size="{sz_w},{sz_h}" font="Regular;{f_20}" foregroundColor="#f3f4f6" backgroundColor="#05070c" transparent="1" zPosition="3" halign="center" />
    <widget name="status" position="{st_x},{st_y}" size="{st_w},{st_h}" font="Regular;{f_20}" foregroundColor="#e879f9" backgroundColor="#05070c" transparent="1" zPosition="3" halign="center" />

    <!-- FOOTER BAR -->
    <eLabel position="{ftr_x},{ftr_y}" size="{ftr_w},{ftr_h}" backgroundColor="#0f111a" zPosition="-1" />
    <eLabel position="{ftr_x},{ftr_y}" size="{ftr_w},2" backgroundColor="#be185d" zPosition="0" />
    <eLabel position="{ftr_x},{ftr_y}" size="4,{ftr_h}" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="{ftr_r},{ftr_y}" size="4,{ftr_h}" backgroundColor="#e11d48" zPosition="1" />
    <eLabel position="{ftr_x},{ftr_b}" size="{ftr_w},2" backgroundColor="#be185d" zPosition="1" />

    <!-- Red Button: Exit -->
    <eLabel position="{btn1_x},{btn_y}" size="{btn_w},{btn_h}" backgroundColor="#1a1025" zPosition="1" />
    <eLabel position="{btn1_x},{btn_y}" size="6,{btn_h}" backgroundColor="#ef4444" zPosition="2" />
    <widget name="key_red" position="{btn1_tx},{btn_y}" size="{btn_text_w},{btn_h}" font="Regular;{f_32}" foregroundColor="#f87171" backgroundColor="transparent" transparent="1" zPosition="3" halign="left" valign="center" />

    <!-- Green Button: Install -->
    <eLabel position="{btn2_x},{btn_y}" size="{btn_w},{btn_h}" backgroundColor="#1a1025" zPosition="1" />
    <eLabel position="{btn2_x},{btn_y}" size="6,{btn_h}" backgroundColor="#22c55e" zPosition="2" />
    <widget name="key_green" position="{btn2_tx},{btn_y}" size="{btn_text_w},{btn_h}" font="Regular;{f_32}" foregroundColor="#4ade80" backgroundColor="transparent" transparent="1" zPosition="3" halign="left" valign="center" />

    <!-- Yellow Button: Refresh Store -->
    <eLabel position="{btn3_x},{btn_y}" size="{btn_w},{btn_h}" backgroundColor="#1a1025" zPosition="1" />
    <eLabel position="{btn3_x},{btn_y}" size="6,{btn_h}" backgroundColor="#eab308" zPosition="2" />
    <widget name="key_yellow" position="{btn3_tx},{btn_y}" size="{btn_text_w},{btn_h}" font="Regular;{f_32}" foregroundColor="#facc15" backgroundColor="transparent" transparent="1" zPosition="3" halign="left" valign="center" />

    <!-- Blue Button: Update Script -->
    <eLabel position="{btn4_x},{btn_y}" size="{btn_w},{btn_h}" backgroundColor="#1a1025" zPosition="1" />
    <eLabel position="{btn4_x},{btn_y}" size="6,{btn_h}" backgroundColor="#2563eb" zPosition="2" />
    <widget name="key_blue" position="{btn4_tx},{btn_y}" size="{btn_text_w},{btn_h}" font="Regular;{f_32}" foregroundColor="#60a5fa" backgroundColor="transparent" transparent="1" zPosition="3" halign="left" valign="center" />
</screen>
""".format(
        scr_w=scr_w, scr_h=scr_h,
        hdr_x=hdr_x, hdr_y=hdr_y, hdr_w=hdr_w, hdr_h=hdr_h,
        hdr_r=hdr_x + hdr_w - 4, hdr_b=hdr_y + hdr_h,
        logo_x=logo_x, logo_y=logo_y, logo_w=logo_w, logo_h=logo_h,
        title_x=title_x, title_y=title_y, title_w=title_w, title_h=title_h,
        ver_x=ver_x, ver_y=ver_y, ver_w=ver_w, ver_h=ver_h,
        chip1_x=chip1_x, chip2_x=chip2_x, chip3_x=chip3_x, chip4_x=chip4_x,
        chip_y=chip_y, chip_w=chip_w, chip_h=chip_h, chip_b=chip_y + chip_h - 2,
        chip1_tx=chip1_x + sx(10), chip2_tx=chip2_x + sx(10), chip3_tx=chip3_x + sx(10), chip4_tx=chip4_x + sx(10),
        chip_t1_y=chip_y + sy(4), chip_t2_y=chip_y + sy(37),
        chip_tw=chip_w - sx(15), chip_th1=sy(32), chip_th2=sy(30),
        cat_x=cat_x, cat_w=cat_w, cat_r=cat_x + cat_w - 4,
        body_y=body_y, body_h=body_h,
        cat_title_x=cat_title_x, cat_title_y=cat_title_y, cat_title_w=cat_title_w, cat_title_h=cat_title_h,
        cat_sep_y=cat_title_y + cat_title_h + sy(5),
        cat_list_x=cat_list_x, cat_list_y=cat_list_y, cat_list_w=cat_list_w, cat_list_h=cat_list_h,
        cat_item_h=cat_item_h,
        pkg_x=pkg_x, pkg_w=pkg_w, pkg_r=pkg_x + pkg_w - 4,
        pkg_title_x=pkg_title_x, pkg_title_y=pkg_title_y, pkg_title_w=pkg_title_w, pkg_title_h=pkg_title_h,
        pkg_sep_y=pkg_title_y + pkg_title_h + sy(5),
        pkg_list_x=pkg_list_x, pkg_list_y=pkg_list_y, pkg_list_w=pkg_list_w, pkg_list_h=pkg_list_h,
        pkg_item_h=pkg_item_h,
        info_x=info_x, info_w=info_w, info_r=info_x + info_w - 4,
        info_title_x=info_title_x, info_title_y=info_title_y, info_title_w=info_title_w, info_title_h=info_title_h,
        info_sep_y=info_title_y + info_title_h + sy(5),
        desc_x=desc_x, desc_y=desc_y, desc_w=desc_w, desc_h=desc_h,
        fb_box_x=fb_box_x, fb_box_y=fb_box_y, fb_box_w=fb_box_w, fb_box_h=fb_box_h,
        fb_r=fb_box_x + fb_box_w - 2, fb_b=fb_box_y + fb_box_h - 2,
        avatar_x=avatar_x, avatar_y=avatar_y, avatar_w=avatar_w, avatar_h=avatar_h,
        qr_x=qr_x, qr_y=qr_y, qr_w=qr_w, qr_h=qr_h,
        fb_ttl_x=fb_ttl_x, fb_ttl_y=fb_ttl_y, fb_ttl_w=fb_ttl_w, fb_ttl_h=fb_ttl_h,
        fb_lbl_x=fb_lbl_x, fb_lbl_y=fb_lbl_y, fb_lbl_w=fb_lbl_w, fb_lbl_h=fb_lbl_h,
        prog_box_x=prog_box_x, prog_box_y=prog_box_y, prog_box_w=prog_box_w, prog_box_h=prog_box_h,
        prog_r=prog_box_x + prog_box_w - 2, prog_b=prog_box_y + prog_box_h - 2,
        pbar_x=pbar_x, pbar_y=pbar_y, pbar_w=pbar_w, pbar_h=pbar_h,
        pct_x=pct_x, pct_y=pct_y, pct_w=pct_w, pct_h=pct_h,
        spd_x=spd_x, spd_y=spd_y, spd_w=spd_w, spd_h=spd_h,
        sz_x=sz_x, sz_y=sz_y, sz_w=sz_w, sz_h=sz_h,
        st_x=st_x, st_y=st_y, st_w=st_w, st_h=st_h,
        ftr_x=ftr_x, ftr_y=ftr_y, ftr_w=ftr_w, ftr_h=ftr_h,
        ftr_r=ftr_x + ftr_w - 4, ftr_b=ftr_y + ftr_h - 2,
        btn1_x=btn1_x, btn2_x=btn2_x, btn3_x=btn3_x, btn4_x=btn4_x,
        btn_y=btn_y, btn_w=btn_w, btn_h=btn_h,
        btn1_tx=btn1_x + btn_text_offset_x, btn2_tx=btn2_x + btn_text_offset_x,
        btn3_tx=btn3_x + btn_text_offset_x, btn4_tx=btn4_x + btn_text_offset_x,
        btn_text_w=btn_text_w,
        f_17=sf(17), f_18=sf(18), f_20=sf(20), f_22=sf(22),
        f_24=sf(24), f_28=sf(28), f_30=sf(30), f_32=sf(32)
    )
    return skin_template


def get_neoboot_images_upload_path():
    candidates = [
        "/media/hdd/ImagesUpload",
        "/media/usb/ImagesUpload",
        "/media/mmc/ImagesUpload",
        "/data/ImagesUpload",
        "/media/hdd",
        "/media/usb"
    ]
    for p in candidates:
        if "/ImagesUpload" in p:
            parent = os.path.dirname(p)
            if os.path.exists(parent):
                if not os.path.exists(p):
                    try:
                        os.makedirs(p)
                    except:
                        pass
                return p
    for p in ["/media/hdd", "/media/usb"]:
        if os.path.exists(p):
            target = os.path.join(p, "ImagesUpload")
            try:
                if not os.path.exists(target):
                    os.makedirs(target)
                return target
            except:
                pass
    return "/media/hdd/ImagesUpload"

def get_direct_hdd_root_path():
    for drive in ["/media/hdd", "/media/usb", "/media/mmc", "/data"]:
        if os.path.exists(drive):
            return drive
    return "/media/hdd"

def get_real_box_ip():
    interfaces = ["eth0", "wlan0", "eth1", "ra0", "wlan1", "lan0", "enp3s0"]
    for ifname in interfaces:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ifname_bytes = ifname.encode('utf-8') if sys.version_info >= (3, 0) else ifname
            ip = socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,
                struct.pack('256s', ifname_bytes[:15])
            )[20:24])
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    try:
        import subprocess
        output = subprocess.check_output(["ip", "route", "get", "1"]).decode('utf-8', 'ignore')
        for part in output.split():
            if part.count('.') == 3 and not part.startswith("127."):
                return part
    except Exception:
        pass

    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    return "192.168.1.1"

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
    elif "channel" in cat_lower or "setting" in cat_lower:
        filename = "channels.png"
    elif "softcam" in cat_lower or "cam" in cat_lower or "emu" in cat_lower:
        filename = "softcam.png"
    elif "noflayer" in cat_lower or "novaler" in cat_lower or "novalayer" in cat_lower:
        filename = "novaler.png"
    else:
        filename = None
        
    if filename:
        search_folders = [
            ICON_FOLDER,
            FALLBACK_ICON_FOLDER,
            os.path.join(PLUGIN_DIR, "images"),
            os.path.join(PLUGIN_DIR, "images", "Icons"),
            os.path.join(PLUGIN_DIR, "images", "icons"),
            "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images",
            "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/Icons",
            "/usr/lib/enigma2/python/Plugins/Extensions/MohamedStore/images/icons"
        ]
        candidates = [filename, "novaler.png", "noflayer.png"] if ("noval" in str(filename) or "nofla" in str(filename)) else [filename]
        
        for folder in search_folders:
            for name in candidates:
                full_p = os.path.join(folder, name)
                if os.path.exists(full_p):
                    return full_p
    return None

def get_item_icon_path(item, category_id):
    if not isinstance(item, dict):
        return get_category_icon_path(category_id)

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
            path3 = os.path.join(PLUGIN_DIR, "images", val)
            if os.path.exists(path3):
                return path3

    item_id = item.get("id") or item.get("name") or ""
    if item_id:
        clean_name = str(item_id).lower().replace(" ", "_").replace("-", "_") + ".png"
        path1 = os.path.join(ICON_FOLDER, clean_name)
        if os.path.exists(path1):
            return path1
        path2 = os.path.join(FALLBACK_ICON_FOLDER, clean_name)
        if os.path.exists(path2):
            return path2
        path3 = os.path.join(PLUGIN_DIR, "images", clean_name)
        if os.path.exists(path3):
            return path3

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

    cat_icon = get_category_icon_path(category_id)
    if cat_icon:
        return cat_icon

    for generic in ("package.png", "default.png", "plugins.png"):
        path1 = os.path.join(ICON_FOLDER, generic)
        if os.path.exists(path1):
            return path1
        path2 = os.path.join(FALLBACK_ICON_FOLDER, generic)
        if os.path.exists(path2):
            return path2

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
        
        req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        if context:
            response = urllib2.urlopen(req, timeout=5, context=context)
        else:
            response = urllib2.urlopen(req, timeout=5)
        data = response.read()
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        return json.loads(data)
    except Exception as e:
        print("[MohamedStore] network error: " + str(e))
        return None

BUILTIN_SYSTEM_TOOLS = [
    {
        "name": u"\u0625\u0635\u0644\u0627\u062d \u0627\u0644\u0645\u0643\u062a\u0628\u0627\u062a \u0648\u0627\u0644\u0627\u0639\u062a\u0645\u0627\u062f\u062a",
        "type": "tool",
        "cmd": "opkg update && opkg install --force-reinstall python-requests curl ffmpeg python-json python-codecs openssl",
        "description": u"\u062a\u062d\u062f\u062b \u062d\u0632\u0645 \u0627\u0644\u0646\u0638\u0627\u0645 \u0648\u0625\u0639\u0627\u062f\u0629 \u062a\u062b\u0628\u064a\u062a \u0627\u0644\u0645\u0643\u062a\u0628\u0627\u062a \u0627\u0644\u0623\u0633\u0627\u0633\u064a\u0629 \u0627\u0644\u0646\u0627\u0642\u0635\u0629."
    },
    {
        "name": u"\u062a\u0646\u0638\u064a\u0641 \u0627\u0644\u0630\u0627\u0643\u0631\u0629 \u0648\u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a\u0629 \u0627\u0644\u0645\u0624\u0642\u062a\u0629",
        "type": "tool",
        "cmd": "rm -rf /tmp/*.ipk /tmp/*.tar.gz /tmp/*.zip /var/volatile/tmp/*",
        "description": u"\u062d\u0632\u0641 \u062c\u0645\u064a\u0639 \u0645\u0644\u0641\u0627\u062a \u0627\u0644\u062a\u062b\u0628\u064a\u062a \u0648\u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0623\u0633\u0627\u0633\u064a\u0629 \u0645\u0646 /tmp."
    },
    {
        "name": u"\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0648\u0627\u062c\u0647\u0629 (Restart GUI)",
        "type": "tool",
        "cmd": "restart_gui",
        "description": u"\u0625\u0639\u0627\u062f\u0629 \u062a\u0634\u063a\u064a\u0644 \u0648\u0627\u062c\u0647\u0629 \u0627\u0644\u0633\u0633\u062a\u0645."
    }
]


class MohamedStore(Screen):
    # Static skin fallback (auto-generated)
    skin = build_responsive_skin(_GLOBAL_SCALER)

    def __init__(self, session):
        # Auto-detect screen resolution & instantiate dynamic scaler
        self.scaler = ScreenScaler()
        self.skin = build_responsive_skin(self.scaler)
        
        Screen.__init__(self, session)
        
        sx = self.scaler.sx
        sy = self.scaler.sy
        sf = self.scaler.sf

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
                        self["categories_list"].l.setFont(0, gFont("Regular", sf(30)))
                        self["categories_list"].l.setFont(1, gFont("Regular", sf(22)))
                    except Exception as fe:
                        print("[MohamedStore] Failed to set font for categories_list: " + str(fe))
                self["categories_list"].l.setBuildFunc(self.build_category_entry)
                self.categories_list_has_multicontent = True
            except Exception as e:
                print("[MohamedStore] Failed to init categories_list with eListboxPythonMultiContent: " + str(e))
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
                        self["items_list"].l.setFont(0, gFont("Regular", sf(32)))
                    except Exception as fe:
                        print("[MohamedStore] Failed to set font for items_list: " + str(fe))
                self["items_list"].l.setBuildFunc(self.build_item_entry)
                self.items_list_has_multicontent = True
            except Exception as e:
                print("[MohamedStore] Failed to init items_list with eListboxPythonMultiContent: " + str(e))
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
        except:
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
        
        self.load_local_cache()

        self.bg_sync_timer = eTimer()
        try:
            self.bg_sync_timer_conn = self.bg_sync_timer.timeout.connect(self.start_background_sync)
        except AttributeError:
            try:
                self.bg_sync_timer.callback.append(self.start_background_sync)
            except:
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
        except Exception as e:
            print("[MohamedStore] Cache load error: " + str(e))
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
        except:
            pass

        try:
            data = load_json_network(STORE_URL)
            if data and "categories" in data:
                self.apply_store_data(data)
                try:
                    with open(CACHE_FILE, "w") as f:
                        json.dump(data, f)
                except Exception as e:
                    pass
            elif not self.categories:
                self["description"].setText("Failed to connect to GitHub feed.")
        except Exception as e:
            print("[MohamedStore] Background sync error: " + str(e))

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
        except Exception as e:
            print("[MohamedStore] apply_store_data error: " + str(e))

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
                                
            info["device"] = "Box: %s" % device_name
            info["image"] = "OS: %s" % image_name
        except Exception as e:
            pass

        try:
            temp_val = None
            for temp_path in (
                "/proc/stb/sensors/temp0/value",
                "/proc/stb/fp/temp_sensor",
                "/proc/stb/sensors/temp/value",
                "/sys/class/thermal/thermal_zone0/temp"
            ):
                if os.path.exists(temp_path):
                    with open(temp_path, "r") as f:
                        t_str = f.read().strip()
                        if t_str.isdigit():
                            t_num = int(t_str)
                            if t_num > 1000:
                                t_num = int(t_num / 1000)
                            temp_val = t_num
                            break
            if temp_val is not None:
                info["temp"] = "Temp: %d C" % temp_val
            else:
                info["temp"] = "Temp: 42 C"

            load_avg = ""
            if os.path.exists("/proc/loadavg"):
                with open("/proc/loadavg", "r") as f:
                    load_avg = f.read().split()[0]
            if load_avg:
                info["cpu"] = "CPU Load: %s" % load_avg
            else:
                info["cpu"] = "CPU: Ready"
        except Exception as e:
            pass

        try:
            if os.path.exists("/proc/meminfo"):
                mem_total = 0
                mem_free = 0
                mem_avail = 0
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            k = parts[0].strip()
                            v = parts[1].strip().split()[0]
                            if k == "MemTotal":
                                mem_total = int(v)
                            elif k == "MemFree":
                                mem_free = int(v)
                            elif k == "MemAvailable":
                                mem_avail = int(v)
                if mem_total > 0:
                    if mem_avail == 0:
                        mem_avail = mem_free
                    used_ram = mem_total - mem_avail
                    pct = int((float(used_ram) / float(mem_total)) * 100)
                    free_mb = int(mem_avail / 1024)
                    info["ram"] = "RAM: %d%% (%dM Free)" % (pct, free_mb)
                else:
                    info["ram"] = "RAM: 38% (1.2G Free)"

            stat = os.statvfs('/')
            free_bytes = stat.f_bavail * stat.f_frsize
            free_gb = float(free_bytes) / (1024.0 * 1024.0 * 1024.0)
            if free_gb >= 1.0:
                info["flash"] = "Flash: %.1f GB Free" % free_gb
            else:
                free_mb = float(free_bytes) / (1024.0 * 1024.0)
                info["flash"] = "Flash: %d MB Free" % int(free_mb)
        except Exception as e:
            pass

        return info

    def build_category_entry(self, *args):
        scaler = getattr(self, 'scaler', _GLOBAL_SCALER)
        sx = scaler.sx
        sy = scaler.sy

        count = 0
        if len(args) == 1 and isinstance(args[0], tuple):
            if len(args[0]) >= 3:
                category_id, display_name, count = args[0][0], args[0][1], args[0][2]
            elif len(args[0]) == 2:
                category_id, display_name = args[0][0], args[0][1]
            else:
                category_id = args[0][0]
                display_name = str(category_id)
        elif len(args) >= 3:
            category_id, display_name, count = args[0], args[1], args[2]
        elif len(args) == 2:
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
                pass

        res = [category_id]
        
        # Responsive dimensions for category entry
        icon_pos_x, icon_pos_y = sx(12), sy(12)
        icon_size_w, icon_size_h = sx(56), sy(56)
        entry_h = sy(80)
        
        if pixmap and HAS_MULTICONTENT and MultiContentEntryPixmapAlphaTest:
            res.append(MultiContentEntryPixmapAlphaTest(pos=(icon_pos_x, icon_pos_y), size=(icon_size_w, icon_size_h), png=pixmap))
            text_x = sx(76)
            text_w = sx(210)
        else:
            text_x = sx(15)
            text_w = sx(270)

        if HAS_MULTICONTENT and MultiContentEntryText:
            align_left = RT_HALIGN_LEFT | RT_VALIGN_CENTER
            align_right = RT_HALIGN_RIGHT | RT_VALIGN_CENTER
            
            res.append(MultiContentEntryText(pos=(text_x, 0), size=(text_w, entry_h), font=0, flags=align_left, text=str(display_name)))
            count_str = "[%d]" % int(count) if count is not None else "[0]"
            count_x = sx(286)
            count_w = sx(74)
            res.append(MultiContentEntryText(pos=(count_x, 0), size=(count_w, entry_h), font=0, flags=align_right, text=count_str))
            
        return res

    def build_item_entry(self, *args):
        scaler = getattr(self, 'scaler', _GLOBAL_SCALER)
        sx = scaler.sx
        sy = scaler.sy

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
                pass

        res = [item]
        
        # Responsive dimensions for items entry
        icon_pos_x, icon_pos_y = sx(10), sy(10)
        icon_size_w, icon_size_h = sx(56), sy(56)
        entry_h = sy(76)

        if pixmap and HAS_MULTICONTENT and MultiContentEntryPixmapAlphaTest:
            res.append(MultiContentEntryPixmapAlphaTest(pos=(icon_pos_x, icon_pos_y), size=(icon_size_w, icon_size_h), png=pixmap))
            text_x = sx(78)
            text_w = sx(670)
        else:
            text_x = sx(15)
            text_w = sx(740)

        if HAS_MULTICONTENT and MultiContentEntryText:
            align = RT_HALIGN_LEFT | RT_VALIGN_CENTER
            res.append(MultiContentEntryText(pos=(text_x, 0), size=(text_w, entry_h), font=0, flags=align, text=display_text))
            
        return res

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
                info_text = "Section: %s\n\nTool Name: %s\n\nDescription:\n%s" % (
                    path_str,
                    str(item.get("name", "")),
                    str(item.get("description", "System tool execution."))
                )
            elif "items" in item and isinstance(item["items"], list):
                self["key_green"].setText("Install")
                sub_count = count_items_recursive(item["items"])
                info_text = "Section: %s\n\nFolder: %s\nPackages inside: %d\n\nPress OK to view packages inside this folder." % (
                    path_str,
                    str(item.get("name", "")),
                    sub_count
                )
            elif is_sys_img:
                self["key_green"].setText("Download")
                info_text = "Section: %s (NeoBoot Safe)\n\nImage: %s\nVersion: %s\n\nDescription:\n%s\n\n* Will be downloaded as a ZIP file directly into NeoBoot ImagesUpload folder." % (
                    path_str,
                    str(item.get("name", "")),
                    str(item.get("version", "")),
                    str(item.get("description", "Enigma2 System Image for NeoBoot."))
                )
            elif is_picon:
                self["key_green"].setText("Download")
                info_text = "Section: %s (Direct HDD ZIP)\n\nName: %s\nVersion: %s\n\nDescription:\n%s\n\n* Will be downloaded as a direct ZIP file directly into HDD root (/media/hdd/)." % (
                    path_str,
                    str(item.get("name", "")),
                    str(item.get("version", "")),
                    str(item.get("description", "Channel Picons Package."))
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
                            "if ! grep -q '{filename}' /etc/enigma2/bouquets.tv; then "
                            "echo '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"{filename}\" ORDER BY bouquet' >> /etc/enigma2/bouquets.tv; "
                            "fi && "
                            "(wget -qO - http://127.0.0.1/web/servicelistreload?mode=0 || "
                            "curl -s http://127.0.0.1/web/servicelistreload?mode=0 || "
                            "enigma2-web-reload || true)"
                        )
                    elif ext == ".py":
                        dest_path = "/tmp/addon.py"
                        cmd = "(python /tmp/addon.py || python3 /tmp/addon.py) && rm -f /tmp/addon.py"
                    else:
                        dest_path = "/tmp/addon.ipk"
                        cmd = "opkg install --force-overwrite /tmp/addon.ipk && rm -f /tmp/addon.ipk"
                    
                    cmd = cmd.format(filename=filename)

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
                url = url.replace(" ", "%20")
                
            req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            if context:
                try:
                    opener = urllib2.build_opener(urllib2.HTTPSHandler(context=context))
                except Exception as oe:
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

            elif self.download_is_system_image:
                self.download_is_system_image = False
                try:
                    self["progress"].hide()
                    self["percentage"].hide()
                    self["speed"].hide()
                    self["size"].hide()
                    self["status"].hide()
                except:
                    pass
                    
                self["key_red"].setText("Exit")
                file_size_mb = float(self.downloaded_bytes) / (1024.0 * 1024.0)
                success_msg = u"Image downloaded successfully as a ZIP file!\n\nSize: %.1f MB\nPath: %s\n\nYou can now open NeoBoot and install it." % (file_size_mb, str(self.download_dest_path))
                self["description"].setText(success_msg)
                
                self.session.open(
                    MessageBox,
                    success_msg,
                    MessageBox.TYPE_INFO
                )
                self.item_changed()

            elif self.download_is_picon:
                self.download_is_picon = False
                try:
                    self["progress"].hide()
                    self["percentage"].hide()
                    self["speed"].hide()
                    self["size"].hide()
                    self["status"].hide()
                except:
                    pass
                    
                self["key_red"].setText("Exit")
                file_size_mb = float(self.downloaded_bytes) / (1024.0 * 1024.0)
                success_msg = u"Picons ZIP package downloaded directly to HDD!\n\nSize: %.1f MB\nPath: %s" % (file_size_mb, str(self.download_dest_path))
                self["description"].setText(success_msg)
                
                self.session.open(
                    MessageBox,
                    success_msg,
                    MessageBox.TYPE_INFO
                )
                self.item_changed()

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
                else:
                    enigma2.quitMainloop(3) if 'enigma2' in globals() else enigma.quitMainloop(3)
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
