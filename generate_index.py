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

metadata_store = {}

# 1. قراءة الخزنة الحالية
if os.path.exists(META_STORE_FILE):
    try:
        with open(META_STORE_FILE, "r", encoding="utf-8") as f:
            metadata_store = json.load(f)
    except Exception:
        metadata_store = {}

# 2. قراءة أحدث تعديل يدوي قمت بكتابته أنت في index.json وحفظه فوراً في الخزنة
if os.path.exists(INDEX_FILE):
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            old_index = json.load(f)

        def sync_user_edits(item):
            if not isinstance(item, dict):
                return
            fn = item.get("file", "").split("/")[-1]
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


def clean_skin_name(fn):
    """تنظيف اسم السكين ليظهر بالإنجليزية فقط وبدون زوائد"""
    name = fn
    for ext in [".ipk", ".tar.gz", ".tar.xz", ".zip", ".deb"]:
        if name.endswith(ext):
            name = name[:-len(ext)]
            break
    
    # حذف بادئات الانيجما الزائدة
    name = re.sub(r'^(enigma2-plugin-skins?-|enigma2-skin-|skin-)', '', name, flags=re.IGNORECASE)
    # إزالة كلمة _all أو إصدارات البايثون في نهاية اسم الملف
    name = re.sub(r'(_all|_mips|_arm.*)$', '', name, flags=re.IGNORECASE)
    name = name.replace("-", " ").replace("_", " ").strip()
    return name


def get_smart_name_and_desc(fn, clean_name, release_body="", default_desc="", is_skin=False):
    # 1. إذا كان لديك تعديل يدوي محفوظ، هو الأقوى دائماً
    if fn in metadata_store:
        u_name = metadata_store[fn].get("name")
        u_desc = metadata_store[fn].get("description")
        if u_name and u_desc:
            # إذا كان سكين وتوجد كلمة "سكين" عربية بالاسم القديم، نزيلها
            if is_skin and u_name.startswith("سكين "):
                u_name = clean_skin_name(fn)
            return u_name, u_desc
        if u_name:
            if is_skin and u_name.startswith("سكين "):
                u_name = clean_skin_name(fn)
            return u_name, default_desc

    # 2. إذا كان سكين (اسم إنجليزي نظيف فقط)
    if is_skin:
        eng_skin_name = clean_skin_name(fn)
        skin_desc = f"سكين {eng_skin_name} عالي الدقة FHD بتصميم أنيق وخفيف"
        return eng_skin_name, skin_desc

    # 3. التنسيق التلقائي الذكي لبقية الأقسام
    auto_name = clean_name
    auto_desc = default_desc

    if "ipaudiopro" in fn.lower() or "ipa udio" in fn.lower():
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

    if "beengo" in fn.lower():
        ver = fn.split("beengo-")[-1].split("_")[0]
        return f"Beengo IPTV ({ver})", "مشغل الوسائط والبث المباشر لخدمة بينجو"

    if "novacam-supreme" in fn.lower():
        ver = fn.split("novacam-supreme-")[-1].split("_")[0]
        return f"Novacam Supreme ({ver})", "سيرفر ومحاكي نوفاكام سوبريم المطور للقنوات المشفرة"

    if "novacampro" in fn.lower():
        ver = fn.split("novacampro-")[-1].split("_")[0]
        return f"Novacam Pro ({ver})", "محاكي وسيرفر نوفاكام برو لأجهزة نوفالير"

    if "novalerstore" in fn.lower():
        ver = fn.split("novalerstore-")[-1].split("_")[0]
        return f"Novaler Store ({ver})", "متجر وبنل نوفالير الرسمي لتثبيت وتحديث الإضافات"

    if "suptv" in fn.lower():
        ver = fn.split("suptv-")[-1].split("_")[0]
        return f"SupTV ({ver})", "تطبيق وسيرفر سوب تيفي الشهير للشيرنج و IPTV"

    if "oscam" in fn.lower():
        if "levi45" in fn: return "Oscam Emu Levi45 v11965", "محاكي أوسكام إيمو محدث بآخر الشفرات وكسر التشفير"
        elif "11878" in fn: return "Oscam Emu r802 v11878", "محاكي أوسكام إيمو مستقر وسريع في كسر التشفير"
        elif "11886" in fn: return "Oscam Emu r803 v11886", "محاكي أوسكام إيمو محدث لفتح القنوات الفضائية"
        elif "oscamicam" in fn: return "Oscam ICam v11725", "محاكي أوسكام آيكام لتشغيل باقات وقنوات ICam"
        elif "798" in fn: return "Oscam All Images r798 (ARM+MIPS)", "محاكي أوسكام الشامل لجميع الصور ومعالجات ARM و MIPS"
        elif "801" in fn: return "Oscam All Images r801 (ARM+MIPS)", "أحدث إصدار من أوسكام الشامل المتوافق مع كافة الصور"

    if "picon" in fn.lower() or "picons" in fn.lower():
        if "7.0w" in fn.lower() or "7.ow" in fn.lower() or "8.0w" in fn.lower():
            return "بيكونات قمر نايل سات (Nilesat 7W / 8W)", "شعارات ولوجوهات قنوات نايل سات بجودة عالية وشفافة"
        elif "13e" in fn.lower():
            return "بيكونات قمر هوتبيرد (Hotbird 13E)", "شعارات وقنوات القمر الأوروبي هوتبيرد 13 شرق"
        elif "16.0e" in fn.lower():
            return "بيكونات قمر يوتلسات (Eutelsat 16E)", "شعارات قنوات قمر يوتلسات 16 شرق بدقة عالية"
        elif "26" in fn.lower():
            return "بيكونات قمر عربسات بدر (Badr 26E)", "شعارات وقنوات قمر عربسات بدر 26 شرق"
        elif "39e" in fn.lower():
            return "بيكونات قمر هيلاسات (Hellas Sat 39E)", "شعارات وقنوات قمر هيلاسات 39 شرق الرياضي"
        elif "all" in fn.lower():
            return "حزمة البيكونات الشاملة (جميع الأقمار)", "مجموعة شعارات القنوات الشاملة لمعظم الأقمار الفضائية"

    if "channels" in fn.lower():
        if "mnasr" in fn.lower():
            return "ملف قنوات ومفضلات مرتب (MNASR)", "ملف قنوات محدث مرتب بعناية لجميع الأقمار والمفضلات العربية"
        elif "openatv" in fn.lower():
            return "ملف قنوات ومفضلات صورة OpenATV", "نسخة احتياطية لقائمة القنوات والمفضلات الرياضية والعامة"

    for brand in ["egami", "openatv", "openbh", "opendroid", "openhdf", "openpli", "openvix", "pure2", "vti"]:
        if brand in fn.lower():
            dev = "الجهاز"
            for d in ["vuzero4k", "vuduo4kse", "vuduo4k", "vusolo4k", "vuultimo4k", "vuuno4kse", "vuuno4k", "vuzero", "vusolo2", "vuduo2", "novaler4kpro", "novaler4kse", "novaler4k", "sf8008", "sf4008", "sf3038", "sx88v2", "sx988", "sfx6008", "dm900", "dm920", "gbquad4k", "gbtrio4kpro", "gbtrio4k", "zgemmah17combo", "zgemmah82h"]:
                if d in fn.lower().replace(".", "").replace("-", "").replace("_", ""):
                    dev = d.upper()
                    break
            return f"صورة {brand.upper()} لجهاز {dev}", f"صورة نظام {brand.upper()} الرسمية المحدثة لجهاز {dev}"

    for k, (n, d) in CUSTOM_MAP.items():
        if k.lower() in fn.lower() or k.lower() in clean_name.lower():
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


EXTENSIONS = (".ipk", ".sh", ".deb", ".zip", ".tar.gz", ".tgz", ".tar", ".py", ".tv", ".img", ".nfi", ".tar.xz", ".bin")


def clean_filename(filename):
    if filename.endswith(".tar.gz") or filename.endswith(".tar.xz"):
        return filename[:-7]
    return os.path.splitext(filename)[0]


def normalize_text(text):
    return re.sub(r'[^a-z0-9]', '', str(text).lower())


# جلب الـ Releases
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
                if filename.endswith(EXTENSIONS):
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
            if not fn.endswith(EXTENSIONS):
                continue
            sys_folders[norm]["seen"].add(fn)
            clean = clean_filename(fn)
            f_url = f"{BASE_URL}/system_images/{folder}/{fn}"
            body_desc = ""
            for asset in release_assets_pool:
                if asset["filename"] == fn:
                    f_url = asset["url"]
                    body_desc = asset.get("body", "")
                    break

            final_name, final_desc = get_smart_name_and_desc(fn, clean, body_desc, f"{disp} Image", is_skin=False)

            sys_folders[norm]["items"].append({
                "name": final_name,
                "description": final_desc,
                "file": f_url,
                "image": image_url(clean.split("_")[0]) or image_url(disp) or image_url("system_images")
            })

for asset in release_assets_pool:
    fn = asset["filename"]
    fn_lower = fn.lower()
    fn_norm = normalize_text(fn)

    is_sys_img = False
    if any(k in fn_norm for k in ["vti", "openpli", "openatv", "openbh", "blackhole", "egami", "pure2", "openspa", "openvix", "systemimage"]):
        is_sys_img = True
    elif any(ext in fn_lower for ext in ["usb.zip", "emmc.zip", "mmc.zip", "recovery.zip", "rootfs.tar.bz2", ".nfi", ".img"]):
        is_sys_img = True

    if is_sys_img and not any(k in fn_norm for k in ["plugin", "skin", "picon", "channel", "ncam", "oscam"]):
        assigned_releases.add(fn)
        matched = None
        for norm_k in sys_folders.keys():
            if norm_k != "all" and norm_k in fn_norm:
                matched = norm_k
                break

        if not matched:
            matched = "all"
            if matched not in sys_folders:
                sys_folders[matched] = {"display_name": "All", "items": [], "seen": set()}

        if fn not in sys_folders[matched]["seen"]:
            sys_folders[matched]["seen"].add(fn)
            clean = clean_filename(fn)
            disp = sys_folders[matched]["display_name"]
            final_name, final_desc = get_smart_name_and_desc(fn, clean, asset.get("body", ""), f"{disp} Image", is_skin=False)

            sys_folders[matched]["items"].append({
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

# 2. Skins (أسماء إنجليزية نظيفة + أوصاف عربية)
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
            if not fn.endswith(EXTENSIONS):
                continue
            skin_folders[norm]["seen"].add(fn)
            clean = clean_filename(fn)
            disp_skin = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
            f_url = f"{BASE_URL}/skins/{folder}/{fn}"
            body_desc = ""
            for asset in release_assets_pool:
                if asset["filename"] == fn:
                    f_url = asset["url"]
                    body_desc = asset.get("body", "")
                    break

            final_name, final_desc = get_smart_name_and_desc(fn, clean, body_desc, f"{disp} Skin", is_skin=True)

            skin_folders[norm]["items"].append({
                "name": final_name,
                "description": final_desc,
                "file": f_url,
                "image": image_url(disp_skin.split("_")[0]) or image_url("skins")
            })

for asset in release_assets_pool:
    fn = asset["filename"]
    fn_norm = normalize_text(fn)

    if "skin" in fn_norm and fn not in assigned_releases:
        assigned_releases.add(fn)
        matched = None
        for norm_k in skin_folders.keys():
            if norm_k != "all" and norm_k in fn_norm:
                matched = norm_k
                break

        if not matched:
            matched = "all"
            if matched not in skin_folders:
                skin_folders[matched] = {"display_name": "All", "items": [], "seen": set()}

        if fn not in skin_folders[matched]["seen"]:
            skin_folders[matched]["seen"].add(fn)
            clean = clean_filename(fn)
            disp_skin = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
            disp = skin_folders[matched]["display_name"]
            final_name, final_desc = get_smart_name_and_desc(fn, clean, asset.get("body", ""), f"{disp} Skin", is_skin=True)

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

# 3. Flat categories (plugins, tools, novaler, picons, channels)
def handle_flat(cat_key, matcher_func, default_desc):
    items = []
    seen = set()

    if os.path.isdir(cat_key):
        for fn in sorted(os.listdir(cat_key)):
            if not fn.endswith(EXTENSIONS):
                continue
            seen.add(fn)
            clean = clean_filename(fn)
            disp_name = clean.replace("enigma2-plugin-extensions-", "").replace("enigma2-plugin-", "")
            f_url = f"{BASE_URL}/{cat_key}/{fn}"
            body_desc = ""
            for asset in release_assets_pool:
                if asset["filename"] == fn:
                    f_url = asset["url"]
                    body_desc = asset.get("body", "")
                    break

            final_name, final_desc = get_smart_name_and_desc(fn, clean, body_desc, default_desc, is_skin=False)

            items.append({
                "name": final_name,
                "description": final_desc,
                "file": f_url,
                "image": image_url(disp_name.split("_")[0]) or image_url(cat_key)
            })

    for asset in release_assets_pool:
        fn = asset["filename"]
        fn_norm = normalize_text(fn)
        if fn in seen or fn in assigned_releases:
            continue

        if matcher_func(fn_norm):
            assigned_releases.add(fn)
            seen.add(fn)
            clean = clean_filename(fn)
            disp_name = clean.replace("enigma2-plugin-extensions-", "").replace("enigma2-plugin-", "")
            final_name, final_desc = get_smart_name_and_desc(fn, clean, asset.get("body", ""), default_desc, is_skin=False)

            items.append({
                "name": final_name,
                "description": final_desc,
                "file": asset["url"],
                "image": image_url(disp_name.split("_")[0]) or image_url(cat_key)
            })

    data["categories"][cat_key] = items


handle_flat("novaler", lambda n: "novaler" in n or "noflayer" in n, "Novaler Package")
handle_flat("picons", lambda n: "picon" in n or "snp" in n or "srp" in n, "Picons Package")
handle_flat("channels", lambda n: any(k in n for k in ["channel", "setting", "bouquet", "satellites", "fav"]), "Channels Settings")
handle_flat("tools", lambda n: any(k in n for k in ["ncam", "oscam", "softcam", "emu", "tool", "script", "tweak"]), "Tool Package")
handle_flat("plugins", lambda n: True, "Plugin Extension")

# تحديث وتثبيت الخزنة
for cat, items in data["categories"].items():
    if isinstance(items, list):
        for el in items:
            sub = el.get("items", []) if (isinstance(el, dict) and "items" in el) else [el]
            for it in sub:
                if isinstance(it, dict):
                    fn = it.get("file", "").split("/")[-1]
                    if fn:
                        metadata_store[fn] = {
                            "name": it.get("name", ""),
                            "description": it.get("description", "")
                        }

os.makedirs("feed", exist_ok=True)
with open(INDEX_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

with open(META_STORE_FILE, "w", encoding="utf-8") as f:
    json.dump(metadata_store, f, indent=4, ensure_ascii=False)

print("🎉 Successfully generated feed/index.json: English skin names without 'سكين' + Arabic descriptions preserved!")
