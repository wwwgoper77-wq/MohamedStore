import os
import json
import re
import urllib.request

GITHUB_USER = "wwwgoper77-wq"
REPO_NAME = "MohamedStore"
BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main"

data = {
    "store_name": "M Store",
    "version": "1.0",
    "categories": {
        "plugins": [],
        "skins": [],
        "tools": [],
        "system_images": [],
        "picons": [],
        "channels": [],
        "novaler": []
    }
}

META_STORE_FILE = "feed/metadata_store.json"
INDEX_FILE = "feed/index.json"

EXTENSIONS = (
    ".ipk", ".deb", ".sh", ".zip", ".tar.gz", ".tgz", ".tar",
    ".tar.xz", ".py", ".tv", ".img", ".nfi", ".bin", ".rar", ".7z"
)

metadata_store = {}

def get_file_basename(url_or_path):
    if not url_or_path:
        return ""
    return str(url_or_path).split("?")[0].split("/")[-1].strip()

# 1. قراءة الخزنة الحالية
if os.path.exists(META_STORE_FILE):
    try:
        with open(META_STORE_FILE, "r", encoding="utf-8") as f:
            metadata_store = json.load(f)
    except Exception:
        metadata_store = {}

# 2. قراءة أحدث تعديل يدوي قمت بكتابته في index.json وحفظه فوراً في الخزنة
if os.path.exists(INDEX_FILE):
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            old_index = json.load(f)

        def sync_user_edits(item):
            if not isinstance(item, dict):
                return
            fn = get_file_basename(item.get("file", ""))
            c_name = item.get("name", "").strip()
            desc = item.get("description", "").strip()
            if fn:
                if fn not in metadata_store:
                    metadata_store[fn] = {}
                if c_name:
                    metadata_store[fn]["name"] = c_name
                if desc:
                    metadata_store[fn]["description"] = desc

        for cat, items in old_index.get("categories", {}).items():
            if isinstance(items, list):
                for el in items:
                    if isinstance(el, dict) and "items" in el:
                        for it in el.get("items", []):
                            sync_user_edits(it)
                    elif isinstance(el, dict):
                        sync_user_edits(el)
    except Exception as e:
        print("Notice reading index.json:", e)


CUSTOM_MAP = {
    "AJPanel": ("AJPanel", "لوحة تحكم شاملة ومدير ملفات وسكربتات وأدوات متقدمة للانيجما2"),
    "ArabicSavior": ("Arabic Savior", "إصلاح وعرض اللغة العربية بشكل سليم في القوائم والترجمات"),
    "E2BissKeyEditor": ("E2 Biss Key Editor", "محرر شفرات البيس Biss وتعديلها بسهولة عبر الريموت"),
    "EPGGrabber": ("EPG Grabber", "جلب وتحميل الدليل الإلكتروني للبرامج EPG للقنوات الفضائية"),
    "EPGTranslator": ("EPG Translator", "ترجمة نصوص ومعلومات الدليل الإلكتروني EPG إلى العربية فورياً"),
    "FuryBiss": ("Fury Biss", "جلب وتحديث شفرات البيس للقنوات المشفرة تلقائياً عبر الإنترنت"),
    "IPStreamer": ("IP Streamer", "بث واستقبال روابط وقنوات البث المباشر عبر الشبكة المنزلية"),
    "InternetSpeed": ("Internet Speed", "أداة قياس سرعة الإنترنت المباشرة والـ Ping على الرسيفر"),
    "MC oscam": ("MC Oscam", "أداة إدارة وتشغيل سيرفرات ومحاكي الأوسكام Oscam"),
    "MC stream": ("MC Stream", "مشغل ومحول تدفقات البث والوسائط المتعددة للأجهزة"),
    "MixAudio": ("Mix Audio", "خلط ومزامنة القنوات الصوتية مع البث المباشر للتايم شفت"),
    "MyTranslator": ("My Translator", "ترجمة سريعة للقوائم والأحداث والمحتوى التلفزيوني"),
    "RaedQuickSignal": ("Raed Quick Signal", "إظهار إشارة القنوات ومستوى التردد والتشفير بشكل سريع"),
    "SubsSupport": ("Subs Support", "تحميل وتشغيل ملفات الترجمة للأفلام والقنوات التلفزيونية"),
    "TMBD": ("TMDB", "جلب بوسترات ومعلومات وقصص الأفلام والمسلسلات من قاعدة TMDB"),
    "TranslatorProAI": ("Translator Pro AI", "ترجمة احترافية فورية مدعومة بالذكاء الاصطناعي"),
    "YouTube": ("YouTube", "تطبيق تشغيل مقاطع وبثوث اليوتيوب بدقة عالية على الانيجما2"),
    "Zoom": ("Zoom Screen", "تكبير وتعديل أبعاد الشاشة ومطابقة الفيديو للإطار"),
    "TiviMate": ("TiviMate E2", "مشغل اشتراكات الـ IPTV بواجهة تيفيمات الاحترافية والسريعة"),
    "uninstaller": ("Plugin Uninstaller", "أداة حذف وإزالة البلجنات وحزم التثبيت وحذف مخلفاتها"),
    "timeshift-delay": ("Timeshift Delay Egami", "ضبط وتأخير التايم شفت وتأخير الصوت لمطابقة التعليق"),
    "FootOnSat": ("FootOnSat", "جدول مباريات اليوم والقنوات الناقلة والمعلقين والترددات مباشرة"),

    "Ncam v15.8": ("تثبيت محاكي Ncam v15.8", "سكربت تثبيت وتحديث أحدث إصدار من محاكي الشفرات Ncam"),
    "backup_channels": ("أخذ نسخة احتياطية للقنوات", "سكربت حفظ وباك اب لقائمة القنوات والمفضلات لديك"),
    "clean_crash": ("تنظيف ملفات الكراش Crash", "سكربت حذف ملفات الكراش واللوغ المؤقتة لتوفير الذاكرة"),
    "clean_ram": ("تنظيف وتسريع الرام RAM", "سكربت تفريغ ذاكرة الرام المؤقتة وتسريع استجابة الرسيفر"),
    "fix_network": ("إصلاح وإعادة تشغيل الشبكة", "سكربت حل مشاكل الاتصال بالإنترنت وإعادة ضبط الشبكة"),
    "restart_cam": ("إعادة تشغيل الكامات Cam", "سكربت عمل ريستارت لمحاكيات الشفرات Oscam و Ncam عند التوقف"),
    "satellites-update": ("تحديث ملف الأقمار Satellites", "تحديث جميع ترددات وأقمار الستلايت لأحدث الترددات الحالية"),
    "update_packages": ("تحديث حزم وفيدات الصورة", "سكربت تحديث مستودعات وفيد الصورة وإصلاح الحزم المفقودة"),

    "Athantimes": ("مواقيت الأذان AthanTimes", "بلجن عرض أوقات الصلاة والأذان بدقة للشاشات"),
    "ajpanel": ("AJPanel Novaler", "لوحة تحكم وأدوات شاملة لأجهزة نوفالير"),
    "alternativesoftcammanager": ("Alternative Softcam Manager", "مدير محاكيات الكامات والسيرفرات لتشغيل الشفرات"),
    "ansite": ("Ansite Panel", "لوحة خدمات وإضافات وسكربتات داعمة"),
    "audiopip": ("Audio PIP", "تشغيل الصوت في الخلفية مع خاصية صورة داخل صورة"),
    "camnova": ("Cam Nova", "مشغل وسيرفر كام نوفالير لفتح القنوات الفضائية"),
    "e2m3u2bouquet": ("E2m3u2bouquet", "تحويل وتوليد باقات ومفضلات القنوات من ملفات وروابط M3U"),
    "feeds-finder": ("Feeds Finder", "أداة البحث التلقائي عن الفيدات الرياضية المباشرة"),
    "freeserver": ("Free Server", "جلب وتحديث سيرفرات الشيرنج المجانية تلقائياً"),
    "netspeedtest": ("Net SpeedTest", "أداة قياس سرعة الإنترنت والاتصال"),
    "screengrabber": ("Screen Grabber", "أداة التقاط صور الشاشة للرسيفر بجودة عالية"),
    "tvspro": ("TVS Pro", "مشغل القنوات التلفزيونية والوسائط المتعددة"),
    "weather-msn": ("MSN Weather", "عرض حالة الطقس والتوقعات الجوية للمدن العالمية"),
    "xcplugin-forever": ("XC Plugin Forever", "مشغل اشتراكات الـ IPTV بنظام Xtream Codes"),
    "xstreamity": ("Xstreamity IPTV", "مشغل IPTV احترافي للأفلام والمسلسلات والبث المباشر")
}

DEVICE_MAP = [
    ("vuduo4kse", "VU+ Duo 4K SE"),
    ("vuduo4k", "VU+ Duo 4K"),
    ("vuuno4kse", "VU+ Uno 4K SE"),
    ("vuuno4k", "VU+ Uno 4K"),
    ("vuultimo4k", "VU+ Ultimo 4K"),
    ("vusolo4k", "VU+ Solo 4K"),
    ("vuzero4k", "VU+ Zero 4K"),
    ("vusolo2", "VU+ Solo 2"),
    ("vusolose", "VU+ Solo SE"),
    ("vuduo2", "VU+ Duo 2"),
    ("vuzero", "VU+ Zero"),
    ("novaler4kpro", "Novaler 4K Pro"),
    ("novaler4kse", "Novaler 4K SE"),
    ("novaler4k", "Novaler 4K"),
    ("sf8008supreme", "Octagon SF8008 Supreme"),
    ("sf8008mini", "Octagon SF8008 Mini"),
    ("sf8008m", "Octagon SF8008m"),
    ("sf8008", "Octagon SF8008 4K"),
    ("sf4008", "Octagon SF4008 4K"),
    ("sf3038", "Octagon SF3038"),
    ("sfx6008", "Octagon SFX6008"),
    ("sx88v2", "Octagon SX88 v2"),
    ("sx988", "Octagon SX988 4K"),
    ("multibox4kpro", "Multibox 4K Pro"),
    ("multibox4kse", "Multibox 4K SE"),
    ("multibox", "Multibox 4K"),
    ("zgemmah17combo", "Zgemma H17 Combo"),
    ("zgemmah82h", "Zgemma H8.2H"),
    ("zgemmah92h", "Zgemma H9.2H"),
    ("zgemmah9combo", "Zgemma H9 Combo"),
    ("zgemmah9twin", "Zgemma H9 Twin"),
    ("zgemmah7", "Zgemma H7"),
    ("zgemmah11", "Zgemma H11"),
    ("dm920", "Dreambox DM920"),
    ("dm900", "Dreambox DM900"),
    ("dm7080", "Dreambox DM7080"),
    ("dm820", "Dreambox DM820"),
    ("dm520", "Dreambox DM520"),
    ("gbquad4k", "GigaBlue Quad 4K"),
    ("gbtrio4kpro", "GigaBlue Trio 4K Pro"),
    ("gbtrio4k", "GigaBlue Trio 4K"),
    ("gbue4k", "GigaBlue UE 4K")
]


def clean_skin_name(fn):
    name = fn
    for ext in [".ipk", ".tar.gz", ".tar.xz", ".zip", ".deb", ".rar", ".7z"]:
        if name.endswith(ext):
            name = name[:-len(ext)]
            break
    name = re.sub(r'^(enigma2-plugin-skins?-|enigma2-skin-|skin-)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'(_all|_mips|_arm.*)$', '', name, flags=re.IGNORECASE)
    name = name.replace("-", " ").replace("_", " ").strip()
    return name


def format_system_image(fn, brand_disp="Image"):
    fn_clean = fn.lower().replace(".", "").replace("-", "").replace("_", "")
    
    dev_name = "Enigma2 Device"
    for k, disp in DEVICE_MAP:
        if k in fn_clean:
            dev_name = disp
            break

    brand = brand_disp
    fn_lower = fn.lower()
    if "openatv" in fn_lower: brand = "OpenATV"
    elif "egami" in fn_lower: brand = "Egami"
    elif "openbh" in fn_lower or "blackhole" in fn_lower: brand = "OpenBH"
    elif "openpli" in fn_lower or "pli" in fn_lower: brand = "OpenPLi"
    elif "pure2" in fn_lower or "pure" in fn_lower: brand = "PurE2"
    elif "openvix" in fn_lower or "vix" in fn_lower: brand = "OpenViX"
    elif "opendroid" in fn_lower: brand = "OpenDroid"
    elif "openhdf" in fn_lower: brand = "OpenHDF"
    elif "vti" in fn_lower: brand = "VTi"
    elif "openspa" in fn_lower: brand = "OpenSPA"
    elif "openvision" in fn_lower: brand = "OpenVision"
    elif "openeight" in fn_lower: brand = "OpenEight"

    ver_match = re.search(r'(\d+\.\d+(\.\d+)?)', fn)
    ver_str = f" {ver_match.group(1)}" if ver_match else ""

    install_type = ""
    if "usb" in fn_lower: install_type = " (USB)"
    elif "mmc" in fn_lower: install_type = " (MMC)"
    elif "multi" in fn_lower: install_type = " (Multiboot)"
    elif "emmc" in fn_lower: install_type = " (EMMC)"

    final_name = f"صورة {brand}{ver_str} لجهاز {dev_name}"
    final_desc = f"صورة نظام {brand}{ver_str} الرسمية لجهاز {dev_name}{install_type}"
    return final_name, final_desc


def get_smart_name_and_desc(fn, clean_name, release_body="", default_desc="", is_skin=False, is_sys_img=False, disp_folder=""):
    clean_k = get_file_basename(fn)
    
    # 1. مطابقة الخزنة الدائمة (إذا عدلت الاسم أو الوصف يدوياً)
    matched_entry = None
    if clean_k in metadata_store:
        matched_entry = metadata_store[clean_k]
    else:
        for k, v in metadata_store.items():
            if k.lower() == clean_k.lower():
                matched_entry = v
                break

    if matched_entry:
        u_name = matched_entry.get("name", "").strip()
        u_desc = matched_entry.get("description", "").strip()
        if u_name or u_desc:
            return (u_name if u_name else clean_name), (u_desc if u_desc else default_desc)

    # 2. صور النظام
    if is_sys_img:
        return format_system_image(fn, disp_folder)

    # 3. السكينات
    if is_skin:
        eng_skin_name = clean_skin_name(fn)
        skin_desc = f"سكين {eng_skin_name} عالي الدقة FHD بتصميم أنيق وخفيف"
        return eng_skin_name, skin_desc

    # 4. التسميات التلقائية
    auto_name = clean_name
    auto_desc = default_desc
    fn_l = fn.lower()

    if "ipaudiopro" in fn_l or "ipa udio" in fn_l:
        if "py2.7" in fn: auto_name = "IPAudio Pro v1.7 (Py2.7)"
        elif "py3.11" in fn: auto_name = "IPAudio Pro v1.7 (Py3.11)"
        elif "py3.12" in fn: auto_name = "IPAudio Pro v1.9 (Py3.12)"
        elif "py3.13" in fn and "ff8.0" in fn: auto_name = "IPAudio Pro v1.9 (Py3.13 - FF8.0)"
        elif "py3.13" in fn: auto_name = "IPAudio Pro v1.9 (Py3.13)"
        elif "py3.14" in fn: auto_name = "IPAudio Pro v1.9 (Py3.14)"
        elif "py3.9" in fn: auto_name = "IPAudio Pro v1.7 (Py3.9)"
        else: auto_name = "IPAudio Pro All"
        auto_desc = "تشغيل الصوتيات والقنوات الصوتية لمطابقة التعليق العربي"
        return auto_name, auto_desc

    if "beengo" in fn_l:
        ver = fn.split("beengo-")[-1].split("_")[0]
        return f"Beengo IPTV ({ver})", "مشغل الوسائط والبث المباشر لخدمة بينجو"

    if "novacam-supreme" in fn_l:
        ver = fn.split("novacam-supreme-")[-1].split("_")[0]
        return f"Novacam Supreme ({ver})", "سيرفر ومحاكي نوفاكام سوبريم المطور للقنوات المشفرة"

    if "novacampro" in fn_l:
        ver = fn.split("novacampro-")[-1].split("_")[0]
        return f"Novacam Pro ({ver})", "محاكي وسيرفر نوفاكام برو لأجهزة نوفالير"

    if "novalerstore" in fn_l:
        ver = fn.split("novalerstore-")[-1].split("_")[0]
        return f"Novaler Store ({ver})", "متجر وبنل نوفالير الرسمي لتثبيت وتحديث الإضافات"

    if "suptv" in fn_l:
        ver = fn.split("suptv-")[-1].split("_")[0]
        return f"SupTV ({ver})", "تطبيق وسيرفر سوب تيفي الشهير للشيرنج و IPTV"

    if "oscam" in fn_l:
        if "levi45" in fn: return "Oscam Emu Levi45 v11965", "محاكي أوسكام إيمو محدث بآخر الشفرات وكسر التشفير"
        elif "11878" in fn: return "Oscam Emu r802 v11878", "محاكي أوسكام إيمو مستقر وسريع في كسر التشفير"
        elif "11886" in fn: return "Oscam Emu r803 v11886", "محاكي أوسكام إيمو محدث لفتح القنوات الفضائية"
        elif "oscamicam" in fn: return "Oscam ICam v11725", "محاكي أوسكام آيكام لتشغيل باقات وقنوات ICam"
        elif "798" in fn: return "Oscam All Images r798 (ARM+MIPS)", "محاكي أوسكام الشامل لجميع الصور ومعالجات ARM و MIPS"
        elif "801" in fn: return "Oscam All Images r801 (ARM+MIPS)", "أحدث إصدار من أوسكام الشامل المتوافق مع كافة الصور"

    if "picon" in fn_l or "picons" in fn_l:
        if "7.0w" in fn_l or "7.ow" in fn_l or "8.0w" in fn_l or "nile" in fn_l:
            return "بيكونات قمر نايل سات (Nilesat 7W / 8W)", "شعارات ولوجوهات قنوات نايل سات بجودة عالية وشفافة"
        elif "13e" in fn_l or "hotbird" in fn_l:
            return "بيكونات قمر هوتبيرد (Hotbird 13E)", "شعارات وقنوات القمر الأوروبي هوتبيرد 13 شرق"
        elif "16.0e" in fn_l or "16e" in fn_l:
            return "بيكونات قمر يوتلسات (Eutelsat 16E)", "شعارات قنوات قمر يوتلسات 16 شرق بدقة عالية"
        elif "26" in fn_l or "badr" in fn_l:
            return "بيكونات قمر عربسات بدر (Badr 26E)", "شعارات وقنوات قمر عربسات بدر 26 شرق"
        elif "39e" in fn_l or "hellas" in fn_l:
            return "بيكونات قمر هيلاسات (Hellas Sat 39E)", "شعارات وقنوات قمر هيلاسات 39 شرق الرياضي"
        elif "all" in fn_l:
            return "حزمة البيكونات الشاملة (جميع الأقمار)", "مجموعة شعارات القنوات الشاملة لمعظم الأقمار الفضائية"

    if "mnasr" in fn_l:
        return "ملف قنوات ومفضلات مرتب (MNASR)", "ملف قنوات ومفضلات شامل ومرتب لجميع الأقمار العربية والأوروبية"

    for k, (n, d) in CUSTOM_MAP.items():
        if k.lower() in fn_l or k.lower() in clean_name.lower():
            return n, d

    if release_body and release_body.strip():
        lines = [l.strip() for l in release_body.split("\n") if l.strip() and not l.strip().startswith("#")]
        if lines:
            auto_desc = lines[0]

    return auto_name, auto_desc


def image_url(prefix):
    if not prefix:
        return ""
    prefix = prefix.lower().strip()
    for folder in ["Icons", "images"]:
        if os.path.isdir(folder):
            for file in sorted(os.listdir(folder)):
                if file.lower().startswith(prefix) and file.lower().endswith(".png"):
                    return f"{BASE_URL}/{folder}/{file}"
    return ""


def clean_filename(filename):
    for ext in [".tar.gz", ".tar.xz", ".tar.bz2", ".ipk", ".deb", ".zip", ".sh", ".rar", ".7z", ".tv", ".img", ".nfi"]:
        if filename.lower().endswith(ext):
            return filename[:-len(ext)]
    return os.path.splitext(filename)[0]


def normalize_text(text):
    return re.sub(r'[^a-z0-9]', '', str(text).lower())



# ============================================================
# GitHub Releases
# ============================================================
# طريقة العمل:
#
# Release title:
#   system images
#
# أو:
#   system images / Egami
#
# أو:
#   skins / OpenATV
#
# أو:
#   plugins
#
# القسم يؤخذ من Release Title، وليس من اسم الملف.
# الحافظة اختيارية وتؤخذ من Release Title أيضاً.
# كل Assets داخل Release المصنف تذهب إلى نفس القسم/الحافظة.
# ============================================================

release_assets_pool = []

github_token = os.environ.get("GITHUB_TOKEN", "")

headers = {
    "User-Agent": "MohamedStore-Feed",
    "Accept": "application/vnd.github+json"
}
if github_token:
    headers["Authorization"] = f"Bearer {github_token}"


# أسماء الأقسام المقبولة في عنوان الـ Release
SECTION_ALIASES = {
    "plugin": "plugins",
    "plugins": "plugins",
    "بلجن": "plugins",
    "بلجنات": "plugins",

    "skin": "skins",
    "skins": "skins",
    "سكين": "skins",
    "سكن": "skins",

    "tool": "tools",
    "tools": "tools",
    "ادوات": "tools",
    "أدوات": "tools",

    "system image": "system_images",
    "system images": "system_images",
    "system_image": "system_images",
    "system_images": "system_images",
    "system-images": "system_images",
    "systemimages": "system_images",
    "system": "system_images",
    "صور النظام": "system_images",

    "picon": "picons",
    "picons": "picons",
    "بيكون": "picons",
    "بيكونات": "picons",

    "channel": "channels",
    "channels": "channels",
    "قناة": "channels",
    "قنوات": "channels",

    "novaler": "novaler",
    "novaler packages": "novaler",
    "novaler package": "novaler",
    "نوفلير": "novaler",
    "نوفالير": "novaler",
}


def normalize_section_name(value):
    if not value:
        return ""

    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)
    value = value.strip("`*_[] ")

    key = value.lower()
    return SECTION_ALIASES.get(key, "")


def parse_release_title(title):
    """
    يقرأ عنوان Release فقط.

    أمثلة صحيحة:
        system images
        system images / Egami
        skins / OpenATV
        picons / Nilesat
        channels / Iraq
        plugins
        tools
        novaler

    ندعم أيضاً:
        system images | Egami
        system images > Egami
        system images : Egami

    ولا نعتمد أبداً على اسم الـ Asset لمعرفة القسم.
    """

    title = str(title or "").strip()
    if not title:
        return "", ""

    # أولاً: عنوان قسم فقط.
    direct = normalize_section_name(title)
    if direct:
        return direct, ""

    # نبحث عن فاصل واضح بين القسم والحافظة.
    # لا نستخدم "-" كفاصل عام لأن أسماء الأقسام/الحافظات قد تحتوي "-".
    separators = [
        r"\s*/\s*",
        r"\s*\|\s*",
        r"\s*>\s*",
        r"\s*:\s*",
    ]

    for separator in separators:
        parts = re.split(separator, title, maxsplit=1)
        if len(parts) != 2:
            continue

        section = normalize_section_name(parts[0])
        folder = parts[1].strip()

        if section:
            folder = folder.strip("`*_[] ")
            folder = re.sub(r"\s+", " ", folder)

            # منع تحويل قيم فارغة أو رموز إلى حافظة.
            if folder in ("", ".", ".."):
                folder = ""

            return section, folder

    return "", ""


# ============================================================
# قراءة metadata القديمة + آخر index
# ============================================================

def save_metadata_from_index(item):
    """
    يحفظ الاسم والوصف الموجودين في index.json.
    وجود المفتاح نفسه يعتبر تعديلاً محفوظاً، حتى لو كانت القيمة فارغة.
    """
    if not isinstance(item, dict):
        return

    fn = get_file_basename(item.get("file", ""))
    if not fn:
        return

    if fn not in metadata_store or not isinstance(metadata_store[fn], dict):
        metadata_store[fn] = {}

    if "name" in item:
        metadata_store[fn]["name"] = str(item.get("name", ""))

    if "description" in item:
        metadata_store[fn]["description"] = str(item.get("description", ""))


if os.path.exists(INDEX_FILE):
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            old_index = json.load(f)

        for cat_items in old_index.get("categories", {}).values():
            if not isinstance(cat_items, list):
                continue

            for element in cat_items:
                if not isinstance(element, dict):
                    continue

                if isinstance(element.get("items"), list):
                    for item in element["items"]:
                        save_metadata_from_index(item)
                else:
                    save_metadata_from_index(element)

    except Exception as e:
        print("Notice reading old index.json:", e)


def get_saved_metadata(filename):
    fn = get_file_basename(filename)
    if not fn:
        return None

    if fn in metadata_store and isinstance(metadata_store[fn], dict):
        return metadata_store[fn]

    low = fn.lower()
    for key, value in metadata_store.items():
        if str(key).lower() == low and isinstance(value, dict):
            return value

    return None


def get_final_name_desc(
    fn,
    clean_name,
    release_body="",
    default_desc="",
    is_skin=False,
    is_sys_img=False,
    disp_folder=""
):
    """
    يحافظ على الاسم والوصف المخزنين في metadata_store.
    إذا عدّل المستخدم الاسم/الوصف في index.json فلن يرجعا للقيمة القديمة.
    """
    saved = get_saved_metadata(fn)

    if saved is not None:
        # المفتاح موجود حتى لو القيمة فارغة.
        saved_name = saved["name"] if "name" in saved else None
        saved_desc = saved["description"] if "description" in saved else None

        # إذا كان موجوداً نستخدمه كما هو.
        if saved_name is not None and saved_desc is not None:
            return str(saved_name), str(saved_desc)

        if saved_name is not None:
            # الوصف القديم غير موجود، دع المولد يحدد الوصف.
            generated_name, generated_desc = get_smart_name_and_desc(
                fn,
                clean_name,
                release_body,
                default_desc,
                is_skin=is_skin,
                is_sys_img=is_sys_img,
                disp_folder=disp_folder
            )
            return str(saved_name), generated_desc

        if saved_desc is not None:
            generated_name, generated_desc = get_smart_name_and_desc(
                fn,
                clean_name,
                release_body,
                default_desc,
                is_skin=is_skin,
                is_sys_img=is_sys_img,
                disp_folder=disp_folder
            )
            return generated_name, str(saved_desc)

    return get_smart_name_and_desc(
        fn,
        clean_name,
        release_body,
        default_desc,
        is_skin=is_skin,
        is_sys_img=is_sys_img,
        disp_folder=disp_folder
    )


# ============================================================
# تحميل كل Releases
# ============================================================

page = 1

while True:
    try:
        api_rel = (
            f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}"
            f"/releases?per_page=100&page={page}"
        )

        req = urllib.request.Request(api_rel, headers=headers)

        with urllib.request.urlopen(req, timeout=30) as response:
            releases = json.loads(response.read().decode("utf-8"))

        if not releases or not isinstance(releases, list):
            break

        for release in releases:
            # المهم هنا: Release title
            release_title = release.get("name", "") or ""

            # fallback للـ tag إذا لم يوجد name
            if not release_title:
                release_title = release.get("tag_name", "") or ""

            section, folder = parse_release_title(release_title)

            # Release غير مصنف لا نرمي ملفاته داخل Plugins.
            if not section:
                print(
                    "Release skipped - unknown section:",
                    release_title
                )
                continue

            release_body = release.get("body", "") or ""

            for asset in release.get("assets", []):
                filename = asset.get("name", "") or ""

                if not filename.lower().endswith(EXTENSIONS):
                    continue

                release_assets_pool.append({
                    "filename": filename,
                    "url": asset.get("browser_download_url", ""),
                    "body": release_body,
                    "release_title": release_title,
                    "section": section,
                    "folder": folder,
                    "asset_id": asset.get("id")
                })

        if len(releases) < 100:
            break

        page += 1

    except Exception as e:
        print("Releases notice:", e)
        break


# ============================================================
# إنشاء عناصر Release
# ============================================================

def make_release_item(asset):
    fn = asset["filename"]
    section = asset["section"]
    folder = asset.get("folder", "") or ""

    clean = clean_filename(fn)

    if section == "system_images":
        default_desc = (
            f"صورة نظام {folder}"
            if folder else
            "System Image"
        )
        is_sys_img = True
        is_skin = False

    elif section == "skins":
        default_desc = (
            f"Skin {folder}"
            if folder else
            "Skin"
        )
        is_sys_img = False
        is_skin = True

    elif section == "picons":
        default_desc = (
            f"Picons {folder}"
            if folder else
            "Picons Package"
        )
        is_sys_img = False
        is_skin = False

    elif section == "channels":
        default_desc = (
            f"Channels {folder}"
            if folder else
            "Channels Settings"
        )
        is_sys_img = False
        is_skin = False

    elif section == "novaler":
        default_desc = (
            f"Novaler {folder}"
            if folder else
            "Novaler Package"
        )
        is_sys_img = False
        is_skin = False

    elif section == "tools":
        default_desc = (
            f"Tool {folder}"
            if folder else
            "Tool Package"
        )
        is_sys_img = False
        is_skin = False

    else:
        default_desc = (
            f"Plugin {folder}"
            if folder else
            "Plugin Extension"
        )
        is_sys_img = False
        is_skin = False

    final_name, final_desc = get_final_name_desc(
        fn,
        clean,
        asset.get("body", ""),
        default_desc,
        is_skin=is_skin,
        is_sys_img=is_sys_img,
        disp_folder=folder
    )

    disp_name = clean.replace(
        "enigma2-plugin-extensions-", ""
    ).replace(
        "enigma2-plugin-", ""
    )

    item = {
        "name": final_name,
        "description": final_desc,
        "file": asset["url"],
        "image": image_url(
            disp_name.split("_")[0]
        ) or image_url(section)
    }

    return item


# ============================================================
# ملفات المستودع المحلي
# ============================================================

def make_local_item(
    fn,
    file_url,
    default_desc,
    is_skin=False,
    is_sys_img=False,
    disp_folder=""
):
    clean = clean_filename(fn)

    final_name, final_desc = get_final_name_desc(
        fn,
        clean,
        "",
        default_desc,
        is_skin=is_skin,
        is_sys_img=is_sys_img,
        disp_folder=disp_folder
    )

    disp_name = clean.replace(
        "enigma2-plugin-extensions-", ""
    ).replace(
        "enigma2-plugin-", ""
    )

    return {
        "name": final_name,
        "description": final_desc,
        "file": file_url,
        "image": image_url(
            disp_name.split("_")[0]
        )
    }


def build_local_groups(
    cat_key,
    default_desc,
    is_skin=False,
    is_sys_img=False
):
    """
    ملفات المستودع:
        section/file
        section/folder/file

    نفس فكرة الحافظات القديمة.
    """
    groups = {}

    if not os.path.isdir(cat_key):
        return groups

    for root, dirs, files in os.walk(cat_key):
        for fn in sorted(files):
            if not fn.lower().endswith(EXTENSIONS):
                continue

            rel_dir = os.path.relpath(
                root,
                cat_key
            ).replace("\\", "/")

            folder = "" if rel_dir == "." else rel_dir

            group_key = normalize_text(folder) if folder else "all"
            display_folder = (
                folder.split("/")[-1]
                if folder else
                "All"
            )

            if group_key not in groups:
                groups[group_key] = {
                    "name": display_folder,
                    "items": [],
                    "seen": set()
                }

            rel_file = os.path.relpath(
                os.path.join(root, fn),
                cat_key
            ).replace("\\", "/")

            file_url = f"{BASE_URL}/{cat_key}/{rel_file}"

            item = make_local_item(
                fn,
                file_url,
                default_desc,
                is_skin=is_skin,
                is_sys_img=is_sys_img,
                disp_folder=display_folder
            )

            groups[group_key]["items"].append(item)
            groups[group_key]["seen"].add(fn)

    return groups


# ============================================================
# إضافة Releases إلى القسم/الحافظة التي يحددها Release
# ============================================================

def add_release_groups(section):
    groups = {}

    for asset in release_assets_pool:
        if asset["section"] != section:
            continue

        folder = asset.get("folder", "") or ""
        group_key = normalize_text(folder) if folder else "all"
        display_folder = folder if folder else "All"

        if group_key not in groups:
            groups[group_key] = {
                "name": display_folder,
                "items": [],
                "seen": set()
            }

        fn = asset["filename"]

        # لا نكرر نفس Asset داخل نفس الحافظة.
        # إذا كان الاسم نفسه في Releases مختلفة نستخدم الرابط كتمييز.
        identity = (
            str(asset.get("asset_id", "")),
            asset.get("url", "")
        )

        if identity in groups[group_key]["seen"]:
            continue

        groups[group_key]["seen"].add(identity)
        groups[group_key]["items"].append(
            make_release_item(asset)
        )

    return groups


def merge_groups(local_groups, release_groups):
    result = {}

    # المحلي أولاً
    for key, value in local_groups.items():
        result[key] = {
            "name": value["name"],
            "items": list(value["items"]),
            "seen_names": {
                get_file_basename(x.get("file", ""))
                for x in value["items"]
            }
        }

    # Release ثانياً
    for key, value in release_groups.items():
        if key not in result:
            result[key] = {
                "name": value["name"],
                "items": [],
                "seen_names": set()
            }

        for item in value["items"]:
            filename = get_file_basename(item.get("file", ""))

            # لا نمنع Release فقط لأنه يشبه ملفاً محلياً.
            # الرابط هو مصدر الحقيقة للتحميل.
            if filename not in result[key]["seen_names"]:
                result[key]["items"].append(item)
                result[key]["seen_names"].add(filename)

    return result


def groups_to_feed(groups):
    output = []

    for key in sorted(groups.keys()):
        group = groups[key]

        # القسم بدون حافظة يبقى قائمة مباشرة.
        # سنعالج ذلك خارج هذه الدالة.
        output.append({
            "name": group["name"],
            "items": group["items"]
        })

    return output


# ============================================================
# System Images
# ============================================================

local_sys = build_local_groups(
    "system_images",
    "System Image",
    is_skin=False,
    is_sys_img=True
)

release_sys = add_release_groups("system_images")
merged_sys = merge_groups(local_sys, release_sys)

data["categories"]["system_images"] = groups_to_feed(
    merged_sys
)


# ============================================================
# Skins
# ============================================================

local_skins = build_local_groups(
    "skins",
    "Skin",
    is_skin=True,
    is_sys_img=False
)

release_skins = add_release_groups("skins")
merged_skins = merge_groups(local_skins, release_skins)

data["categories"]["skins"] = groups_to_feed(
    merged_skins
)


# ============================================================
# الأقسام التي قد تكون مباشرة أو تحتوي حافظات
# ============================================================

def build_general_category(cat_key, default_desc):
    local_groups = build_local_groups(
        cat_key,
        default_desc,
        is_skin=False,
        is_sys_img=False
    )

    release_groups = add_release_groups(cat_key)

    # إذا لم توجد حافظات في المحلي ولا في Releases:
    # نرجع List مباشرة كما كان النظام القديم.
    has_real_folder = (
        any(k != "all" for k in local_groups.keys())
        or any(k != "all" for k in release_groups.keys())
    )

    if not has_real_folder:
        items = []

        if "all" in local_groups:
            items.extend(local_groups["all"]["items"])

        if "all" in release_groups:
            items.extend(release_groups["all"]["items"])

        return items

    merged = merge_groups(
        local_groups,
        release_groups
    )

    return groups_to_feed(merged)


data["categories"]["plugins"] = build_general_category(
    "plugins",
    "Plugin Extension"
)

data["categories"]["tools"] = build_general_category(
    "tools",
    "Tool Package"
)

data["categories"]["picons"] = build_general_category(
    "picons",
    "Picons Package"
)

data["categories"]["channels"] = build_general_category(
    "channels",
    "Channels Settings"
)

data["categories"]["novaler"] = build_general_category(
    "novaler",
    "Novaler Package"
)


# ============================================================
# حفظ metadata + index
# ============================================================

os.makedirs("feed", exist_ok=True)

with open(INDEX_FILE, "w", encoding="utf-8") as f:
    json.dump(
        data,
        f,
        indent=4,
        ensure_ascii=False
    )

with open(META_STORE_FILE, "w", encoding="utf-8") as f:
    json.dump(
        metadata_store,
        f,
        indent=4,
        ensure_ascii=False
    )

print("============================================================")
print("M Store Feed generated successfully.")
print("Release title controls section and optional folder.")
print("All assets inside a classified Release are included.")
print("No filename-based Release classification is used.")
print("Manual name/description changes are preserved.")
print("============================================================")
