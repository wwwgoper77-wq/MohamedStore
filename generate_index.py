import os
import json
import re
import urllib.request
from urllib.parse import quote

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

metadata_store = {}

def get_file_basename(url_or_path):
    if not url_or_path:
        return ""
    return str(url_or_path).split("?")[0].split("/")[-1].strip()

# 1. قراءة الخزنة
if os.path.exists(META_STORE_FILE):
    try:
        with open(META_STORE_FILE, "r", encoding="utf-8") as f:
            metadata_store = json.load(f)
    except Exception:
        metadata_store = {}

# 2. قراءة التعديلات اليدوية المحفوظة
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

    "Ncam v15.8": ("Ncam v15.8 Installer", "سكربت تثبيت وتحديث أحدث إصدار من محاكي الشفرات Ncam"),
    "backup_channels": ("Backup Channels Script", "سكربت حفظ وباك اب لقائمة القنوات والمفضلات لديك"),
    "clean_crash": ("Clean Crash Logs", "سكربت حذف ملفات الكراش واللوغ المؤقتة لتوفير الذاكرة"),
    "clean_ram": ("Clean RAM Memory", "سكربت تفريغ ذاكرة الرام المؤقتة وتسريع استجابة الرسيفر"),
    "fix_network": ("Fix Network Connection", "سكربت حل مشاكل الاتصال بالإنترنت وإعادة ضبط الشبكة"),
    "restart_cam": ("Restart Softcams", "سكربت عمل ريستارت لمحاكيات الشفرات Oscam و Ncam عند التوقف"),
    "satellites-update": ("Satellites XML Update", "تحديث جميع ترددات وأقمار الستلايت لأحدث الترددات الحالية"),
    "update_packages": ("Update Image Feeds", "سكربت تحديث مستودعات وفيد الصورة وإصلاح الحزم المفقودة"),

    "Athantimes": ("AthanTimes", "بلجن عرض أوقات الصلاة والأذان بدقة للشاشات"),
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
    ("vuduo", "VU+ Duo"),
    ("vusolo", "VU+ Solo"),
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

# تجاهل الملفات غير الصالحة أو السكربتات المؤقتة داخل حافظات الصور
IGNORED_FILES = {".ds_store", "thumbs.db", ".gitkeep", "readme.md", ".gitignore"}
VALID_SYS_IMAGE_EXTS = {".zip", ".tar.gz", ".tar.xz", ".nfi", ".img", ".bin", ".bz2"}

def clean_filename(filename):
    name = filename
    for ext in [".tar.gz", ".tar .gz", ".tar.xz", ".tar .xz", ".ipk", ".deb", ".zip", ".sh", ".py", ".tv", ".img", ".nfi", ".bin", ".rar", ".7z"]:
        if name.lower().endswith(ext):
            name = name[:-len(ext)]
            break
    if "." in name:
        name = os.path.splitext(name)[0]
    return name.strip()


def clean_skin_name(fn):
    name = clean_filename(fn)
    name = re.sub(r'^(enigma2-plugin-skins?-|enigma2-skin-|skin-)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'(_all|_mips|_arm.*)$', '', name, flags=re.IGNORECASE)
    name = name.replace("-", " ").replace("_", " ").strip()
    return name


def detect_brand_from_filename(fn_lower):
    if "openatv" in fn_lower: return "OpenATV"
    if "egami" in fn_lower: return "Egami"
    if "openbh" in fn_lower or "blackhole" in fn_lower: return "OpenBH"
    if "openpli" in fn_lower or "pli" in fn_lower: return "OpenPLi"
    if "pure2" in fn_lower or "pure" in fn_lower: return "PurE2"
    if "openvix" in fn_lower or "vix" in fn_lower: return "OpenViX"
    if "opendroid" in fn_lower: return "OpenDroid"
    if "openhdf" in fn_lower: return "OpenHDF"
    if re.search(r'(^|[^a-z])vti([^a-z]|$)', fn_lower): return "VTi"
    if "openspa" in fn_lower: return "OpenSPA"
    if "openvision" in fn_lower: return "OpenVision"
    if "openeight" in fn_lower: return "OpenEight"
    return "All"


def format_system_image(fn, brand_disp="Image"):
    fn_clean = fn.lower().replace(".", "").replace("-", "").replace("_", "").replace(" ", "")
    
    dev_name = ""
    for k, disp in DEVICE_MAP:
        if k in fn_clean:
            dev_name = disp
            break

    brand = detect_brand_from_filename(fn.lower())
    if brand == "All" and brand_disp != "Image" and brand_disp != "All":
        # تنظيف اسم الحافظة مثل OpenBH (NeoBoot Safe)
        clean_brand_folder = brand_disp.split("(")[0].strip()
        brand = clean_brand_folder if clean_brand_folder else brand_disp

    ver_match = re.search(r'(\d+\.\d+(\.\d+)?)', fn)
    ver_str = f" {ver_match.group(1)}" if ver_match else ""

    install_type = ""
    fn_lower = fn.lower()
    if "usb" in fn_lower: install_type = " (USB)"
    elif "mmc" in fn_lower: install_type = " (MMC)"
    elif "multi" in fn_lower: install_type = " (Multiboot)"
    elif "emmc" in fn_lower: install_type = " (EMMC)"

    if dev_name:
        final_name = f"{brand}{ver_str} - {dev_name}"
        final_desc = f"صورة نظام {brand}{ver_str} الرسمية لجهاز {dev_name}{install_type}"
    else:
        clean_base = clean_filename(fn)
        final_name = f"{brand}{ver_str} - {clean_base}"
        final_desc = f"صورة نظام {brand}{ver_str} لأجهزة الإنيجما 2{install_type}"

    return final_name, final_desc


def get_smart_name_and_desc(fn, clean_name, release_body="", default_desc="", is_skin=False, is_sys_img=False, disp_folder=""):
    clean_k = get_file_basename(fn)
    
    # 1. التعديل اليدوي المحفوظ
    if clean_k in metadata_store:
        u_name = metadata_store[clean_k].get("name", "").strip()
        u_desc = metadata_store[clean_k].get("description", "").strip()
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

    if "morph883" in fn_l or "morph" in fn_l:
        sat = "Hotbird 13E" if "13" in fn_l else ""
        return f"Channels {sat} (Morph883)".strip(), "ملف قنوات ومفضلات مرتب وشامل من إعداد Morph883"

    if "mnasr" in fn_l:
        return "Channels Setting (MNASR)", "ملف قنوات محدث مرتب بعناية لجميع الأقمار والمفضلات العربية"
        
    if "openatv" in fn_l and ("channel" in fn_l or "setting" in fn_l):
        return "OpenATV Channels Backup", "نسخة احتياطية لقائمة القنوات والمفضلات الرياضية والعامة"

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
            return "Picons Nilesat (7.0W / 8.0W)", "شعارات ولوجوهات قنوات نايل سات بجودة عالية وشفافة"
        elif "13e" in fn_l or "hotbird" in fn_l:
            return "Picons Hotbird (13.0E)", "شعارات وقنوات القمر الأوروبي هوتبيرد 13 شرق"
        elif "16.0e" in fn_l or "16e" in fn_l:
            return "Picons Eutelsat (16.0E)", "شعارات قنوات قمر يوتلسات 16 شرق بدقة عالية"
        elif "26" in fn_l or "badr" in fn_l:
            return "Picons Badr / Arabsat (26.0E)", "شعارات وقنوات قمر عربسات بدر 26 شرق"
        elif "39e" in fn_l or "hellas" in fn_l:
            return "Picons Hellas Sat (39.0E)", "شعارات وقنوات قمر هيلاسات 39 شرق الرياضي"
        elif "all" in fn_l:
            return "Picons Full Package (All Sats)", "مجموعة شعارات القنوات الشاملة لمعظم الأقمار الفضائية"

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
                    return f"{BASE_URL}/{folder}/{quote(file)}"
    return ""


def normalize_text(text):
    return re.sub(r'[^a-z0-9]', '', str(text).lower())


# جلب ملفات الـ Releases
release_assets_pool = []
github_token = os.environ.get("GITHUB_TOKEN", "")

headers = {"User-Agent": "MohamedStore-Feed", "Accept": "application/vnd.github+json"}
if github_token:
    headers["Authorization"] = f"token {github_token}"

page = 1
while True:
    try:
        api_rel = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/releases?per_page=100&page={page}"
        req = urllib.request.Request(api_rel, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            releases = json.loads(response.read().decode("utf-8"))

        if not releases or not isinstance(releases, list):
            break

        for release in releases:
            rel_body = release.get("body", "") or release.get("name", "")
            for asset in release.get("assets", []):
                filename = asset.get("name", "")
                if filename.lower() not in IGNORED_FILES:
                    release_assets_pool.append({
                        "filename": filename,
                        "url": asset.get("browser_download_url", ""),
                        "body": rel_body
                    })

        if len(releases) < 100:
            break
        page += 1
    except Exception as e:
        print("Releases notice:", e)
        break

assigned_releases = set()
globally_seen = set()

# 1. System Images
sys_folders = {}

if os.path.isdir("system_images"):
    for folder in sorted(os.listdir("system_images")):
        fpath = os.path.join("system_images", folder)
        if not os.path.isdir(fpath):
            continue
        norm = normalize_text(folder)
        disp = "All" if norm == "all" else folder
        sys_folders[norm] = {"display_name": disp, "items": [], "seen": set()}

        for fn in sorted(os.listdir(fpath)):
            if fn.lower() in IGNORED_FILES or fn.startswith("."):
                continue
            # التأكد أن الملف له امتداد صورة حقيقي
            if not any(fn.lower().endswith(ext) for ext in VALID_SYS_IMAGE_EXTS):
                continue

            norm_fn = normalize_text(fn)
            sys_folders[norm]["seen"].add(norm_fn)
            globally_seen.add(norm_fn)
            
            clean = clean_filename(fn)
            f_url = f"{BASE_URL}/system_images/{quote(folder)}/{quote(fn)}"
            body_desc = ""
            for asset in release_assets_pool:
                if normalize_text(asset["filename"]) == norm_fn:
                    f_url = asset["url"]
                    body_desc = asset.get("body", "")
                    assigned_releases.add(normalize_text(asset["filename"]))
                    break

            final_name, final_desc = get_smart_name_and_desc(fn, clean, body_desc, f"{disp} Image", is_skin=False, is_sys_img=True, disp_folder=disp)

            sys_folders[norm]["items"].append({
                "name": final_name,
                "description": final_desc,
                "file": f_url,
                "image": image_url(clean.split("_")[0]) or image_url(disp) or image_url("system_images")
            })

# شرط صور النظام في الـ Releases: (اسم الصورة + موديل الجهاز)
for asset in release_assets_pool:
    fn = asset["filename"]
    fn_lower = fn.lower()
    fn_norm = normalize_text(fn)

    is_sys_img = False
    has_brand = any(b in fn_lower for b in ["openatv", "egami", "pure2", "openbh", "blackhole", "openpli", "openspa", "openvix", "opendroid", "openhdf", "systemimage"])
    if not has_brand and re.search(r'(^|[^a-z])vti([^a-z]|$)', fn_lower):
        has_brand = True

    has_model = any(k in fn_norm for k, d in DEVICE_MAP) or any(ext in fn_lower for ext in ["usb.zip", "emmc.zip", "mmc.zip", "recovery.zip", "rootfs.tar.bz2", ".nfi", ".img"])

    if has_brand and has_model:
        if not any(k in fn_norm for k in ["plugin", "skin", "picon", "channel", "ncam", "oscam"]):
            is_sys_img = True

    if is_sys_img and fn_norm not in assigned_releases and fn_norm not in globally_seen:
        assigned_releases.add(fn_norm)
        globally_seen.add(fn_norm)
        
        detected_brand = detect_brand_from_filename(fn_lower)
        matched_key = normalize_text(detected_brand)
        
        if matched_key not in sys_folders:
            sys_folders[matched_key] = {"display_name": detected_brand, "items": [], "seen": set()}

        clean = clean_filename(fn)
        disp = sys_folders[matched_key]["display_name"]
        final_name, final_desc = get_smart_name_and_desc(fn, clean, asset.get("body", ""), f"{disp} Image", is_skin=False, is_sys_img=True, disp_folder=disp)

        sys_folders[matched_key]["items"].append({
            "name": final_name,
            "description": final_desc,
            "file": asset["url"],
            "image": image_url(clean.split("_")[0]) or image_url(disp) or image_url("system_images")
        })

for norm_k, f_data in sorted(sys_folders.items()):
    data["categories"]["system_images"].append({
        "name": f_data["display_name"],
        "items": f_data["items"]
    })

# 2. Skins
skin_folders = {}
if os.path.isdir("skins"):
    for folder in sorted(os.listdir("skins")):
        fpath = os.path.join("skins", folder)
        if not os.path.isdir(fpath):
            continue
        norm = normalize_text(folder)
        disp = "All" if norm == "all" else folder
        skin_folders[norm] = {"display_name": disp, "items": [], "seen": set()}

        for fn in sorted(os.listdir(fpath)):
            if fn.lower() in IGNORED_FILES or fn.startswith("."):
                continue
            norm_fn = normalize_text(fn)
            skin_folders[norm]["seen"].add(norm_fn)
            globally_seen.add(norm_fn)
            
            clean = clean_filename(fn)
            disp_skin = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
            f_url = f"{BASE_URL}/skins/{quote(folder)}/{quote(fn)}"
            body_desc = ""
            for asset in release_assets_pool:
                if normalize_text(asset["filename"]) == norm_fn:
                    f_url = asset["url"]
                    body_desc = asset.get("body", "")
                    assigned_releases.add(normalize_text(asset["filename"]))
                    break

            final_name, final_desc = get_smart_name_and_desc(fn, clean, body_desc, f"{disp} Skin", is_skin=True, is_sys_img=False)

            skin_folders[norm]["items"].append({
                "name": final_name,
                "description": final_desc,
                "file": f_url,
                "image": image_url(disp_skin.split("_")[0]) or image_url("skins")
            })

for asset in release_assets_pool:
    fn = asset["filename"]
    fn_norm = normalize_text(fn)

    if "skin" in fn_norm and fn_norm not in assigned_releases and fn_norm not in globally_seen:
        assigned_releases.add(fn_norm)
        globally_seen.add(fn_norm)
        
        matched = "all"
        for norm_k in skin_folders.keys():
            if norm_k != "all" and norm_k in fn_norm:
                matched = norm_k
                break

        if matched not in skin_folders:
            skin_folders[matched] = {"display_name": "All", "items": [], "seen": set()}

        clean = clean_filename(fn)
        disp_skin = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
        disp = skin_folders[matched]["display_name"]
        final_name, final_desc = get_smart_name_and_desc(fn, clean, asset.get("body", ""), f"{disp} Skin", is_skin=True, is_sys_img=False)

        skin_folders[matched]["items"].append({
            "name": final_name,
            "description": final_desc,
            "file": asset["url"],
            "image": image_url(disp_skin.split("_")[0]) or image_url("skins")
        })

for norm_k, f_data in sorted(skin_folders.items()):
    data["categories"]["skins"].append({
        "name": f_data["display_name"],
        "items": f_data["items"]
    })

# 3. باقي الأقسام
def handle_category_without_restrictions(cat_key, release_matcher, default_desc):
    items = []
    seen_in_cat = set()

    if os.path.isdir(cat_key):
        for root, dirs, files in os.walk(cat_key):
            for fn in sorted(files):
                if fn.lower() in IGNORED_FILES or fn.startswith("."):
                    continue
                norm_fn = normalize_text(fn)
                if norm_fn in seen_in_cat:
                    continue
                seen_in_cat.add(norm_fn)
                globally_seen.add(norm_fn)
                
                clean = clean_filename(fn)
                disp_name = clean.replace("enigma2-plugin-extensions-", "").replace("enigma2-plugin-", "")
                rel_path = os.path.relpath(os.path.join(root, fn), cat_key).replace("\\", "/")
                
                parts = rel_path.split("/")
                quoted_rel_path = "/".join([quote(p) for p in parts])
                f_url = f"{BASE_URL}/{cat_key}/{quoted_rel_path}"
                body_desc = ""
                for asset in release_assets_pool:
                    if normalize_text(asset["filename"]) == norm_fn:
                        f_url = asset["url"]
                        body_desc = asset.get("body", "")
                        assigned_releases.add(normalize_text(asset["filename"]))
                        break

                final_name, final_desc = get_smart_name_and_desc(fn, clean, body_desc, default_desc, is_skin=False, is_sys_img=False)

                items.append({
                    "name": final_name,
                    "description": final_desc,
                    "file": f_url,
                    "image": image_url(disp_name.split("_")[0]) or image_url(cat_key)
                })

    for asset in release_assets_pool:
        fn = asset["filename"]
        fn_norm = normalize_text(fn)
        if fn_norm in assigned_releases or fn_norm in globally_seen or fn_norm in seen_in_cat:
            continue

        if release_matcher(fn_norm, fn.lower()):
            assigned_releases.add(fn_norm)
            globally_seen.add(fn_norm)
            seen_in_cat.add(fn_norm)
            
            clean = clean_filename(fn)
            disp_name = clean.replace("enigma2-plugin-extensions-", "").replace("enigma2-plugin-", "")
            final_name, final_desc = get_smart_name_and_desc(fn, clean, asset.get("body", ""), default_desc, is_skin=False, is_sys_img=False)

            items.append({
                "name": final_name,
                "description": final_desc,
                "file": asset["url"],
                "image": image_url(disp_name.split("_")[0]) or image_url(cat_key)
            })

    data["categories"][cat_key] = items


handle_category_without_restrictions("novaler", lambda n, l: ("novaler" in n or "novacam" in n or "noflayer" in n) and "skin" not in n, "Novaler Package")
handle_category_without_restrictions("picons", lambda n, l: ("picon" in n or "snp" in n or "srp" in n) and "skin" not in n, "Picons Package")
handle_category_without_restrictions("channels", lambda n, l: (any(k in n for k in ["channel", "setting", "bouquet", "satellites", "fav", "mnasr", "morph"]) or l.endswith(".tv")) and "plugin" not in n, "Channels Settings")
handle_category_without_restrictions("tools", lambda n, l: any(k in n for k in ["ncam", "oscam", "softcam", "emu", "script", "clean", "backup", "restart", "network"]), "Tool Package")
handle_category_without_restrictions("plugins", lambda n, l: ("plugin" in n or "extension" in n) and "skin" not in n, "Plugin Extension")

os.makedirs("feed", exist_ok=True)
with open(INDEX_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

with open(META_STORE_FILE, "w", encoding="utf-8") as f:
    json.dump(metadata_store, f, indent=4, ensure_ascii=False)

print("🎉 Successfully generated feed/index.json: Clean UI & No Mixed Text Glitches!")
