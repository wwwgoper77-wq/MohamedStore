import json
import os

INDEX_FILE = "feed/index.json"
META_FILE = "feed/metadata_store.json"

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

def clean_item(it, existing_custom):
    fn = it.get("file", "").split("/")[-1]
    name = it.get("name", "")
    desc = it.get("description", "")

    # إذا كان للملف اسم ووصف خاص قمت بتعديله بيدك، اتركه ولا تغيره!
    if fn in existing_custom:
        saved = existing_custom[fn]
        if saved.get("name") and saved["name"] != fn:
            it["name"] = saved["name"]
        if saved.get("description") and saved["description"] not in ["Plugin Extension", "Tool Package", "All Skin", "e"]:
            it["description"] = saved["description"]
            return

    # غير ذلك يطبق التنسيق التلقائي
    if "ipaudiopro" in fn.lower() or "ipa udio" in fn.lower():
        if "py2.7" in fn: it["name"] = "IPAudio Pro v1.7 (Py2.7)"
        elif "py3.11" in fn: it["name"] = "IPAudio Pro v1.7 (Py3.11)"
        elif "py3.12" in fn: it["name"] = "IPAudio Pro v1.9 (Py3.12)"
        elif "py3.13" in fn and "ff8.0" in fn: it["name"] = "IPAudio Pro v1.9 (Py3.13 - FF8.0)"
        elif "py3.13" in fn: it["name"] = "IPAudio Pro v1.9 (Py3.13)"
        elif "py3.14" in fn: it["name"] = "IPAudio Pro v1.9 (Py3.14)"
        elif "py3.9" in fn: it["name"] = "IPAudio Pro v1.7 (Py3.9)"
        else: it["name"] = "IPAudio Pro All"
        it["description"] = "تشغيل الصوتيات والقنوات الصوتية لمطابقة التعليق العربي"
        return

    if "beengo" in fn.lower():
        ver = fn.split("beengo-")[-1].split("_")[0]
        it["name"] = f"Beengo IPTV ({ver})"
        it["description"] = "مشغل الوسائط والبث المباشر لخدمة بينجو"
        return

    if "novacam-supreme" in fn.lower():
        ver = fn.split("novacam-supreme-")[-1].split("_")[0]
        it["name"] = f"Novacam Supreme ({ver})"
        it["description"] = "سيرفر ومحاكي نوفاكام سوبريم المطور للقنوات المشفرة"
        return
    if "novacampro" in fn.lower():
        ver = fn.split("novacampro-")[-1].split("_")[0]
        it["name"] = f"Novacam Pro ({ver})"
        it["description"] = "محاكي وسيرفر نوفاكام برو لأجهزة نوفالير"
        return
    if "novalerstore" in fn.lower():
        ver = fn.split("novalerstore-")[-1].split("_")[0]
        it["name"] = f"Novaler Store ({ver})"
        it["description"] = "متجر وبنل نوفالير الرسمي لتثبيت وتحديث الإضافات"
        return
    if "suptv" in fn.lower():
        ver = fn.split("suptv-")[-1].split("_")[0]
        it["name"] = f"SupTV ({ver})"
        it["description"] = "تطبيق وسيرفر سوب تيفي الشهير للشيرنج و IPTV"
        return

    if "oscam" in fn.lower():
        if "levi45" in fn:
            it["name"] = "Oscam Emu Levi45 v11965"
            it["description"] = "محاكي أوسكام إيمو محدث بآخر الشفرات وكسر التشفير"
        elif "11878" in fn:
            it["name"] = "Oscam Emu r802 v11878"
            it["description"] = "محاكي أوسكام إيمو مستقر وسريع في كسر التشفير"
        elif "11886" in fn:
            it["name"] = "Oscam Emu r803 v11886"
            it["description"] = "محاكي أوسكام إيمو محدث لفتح القنوات الفضائية"
        elif "oscamicam" in fn:
            it["name"] = "Oscam ICam v11725"
            it["description"] = "محاكي أوسكام آيكام لتشغيل باقات وقنوات ICam"
        elif "798" in fn:
            it["name"] = "Oscam All Images r798 (ARM+MIPS)"
            it["description"] = "محاكي أوسكام الشامل لجميع الصور ومعالجات ARM و MIPS"
        elif "801" in fn:
            it["name"] = "Oscam All Images r801 (ARM+MIPS)"
            it["description"] = "أحدث إصدار من أوسكام الشامل المتوافق مع كافة الصور"
        return

    if "picon" in fn.lower() or "picons" in fn.lower():
        if "7.0w" in fn.lower() or "7.ow" in fn.lower() or "8.0w" in fn.lower():
            it["name"] = "بيكونات قمر نايل سات (Nilesat 7W / 8W)"
            it["description"] = "شعارات ولوجوهات قنوات نايل سات بجودة عالية وشفافة"
        elif "13e" in fn.lower():
            it["name"] = "بيكونات قمر هوتبيرد (Hotbird 13E)"
            it["description"] = "شعارات وقنوات القمر الأوروبي هوتبيرد 13 شرق"
        elif "16.0e" in fn.lower():
            it["name"] = "بيكونات قمر يوتلسات (Eutelsat 16E)"
            it["description"] = "شعارات قنوات قمر يوتلسات 16 شرق بدقة عالية"
        elif "26" in fn.lower():
            it["name"] = "بيكونات قمر عربسات بدر (Badr 26E)"
            it["description"] = "شعارات وقنوات قمر عربسات بدر 26 شرق"
        elif "39e" in fn.lower():
            it["name"] = "بيكونات قمر هيلاسات (Hellas Sat 39E)"
            it["description"] = "شعارات وقنوات قمر هيلاسات 39 شرق الرياضي"
        elif "all" in fn.lower():
            it["name"] = "حزمة البيكونات الشاملة (جميع الأقمار)"
            it["description"] = "مجموعة شعارات القنوات الشاملة لمعظم الأقمار الفضائية"
        return

    if "channels" in fn.lower():
        if "mnasr" in fn.lower():
            it["name"] = "ملف قنوات ومفضلات مرتب (MNASR)"
            it["description"] = "ملف قنوات محدث مرتب بعناية لجميع الأقمار والمفضلات العربية"
        elif "openatv" in fn.lower():
            it["name"] = "ملف قنوات ومفضلات صورة OpenATV"
            it["description"] = "نسخة احتياطية لقائمة القنوات والمفضلات الرياضية والعامة"
        return

    for brand in ["egami", "openatv", "openbh", "opendroid", "openhdf", "openpli", "openvix", "pure2", "vti"]:
        if brand in fn.lower():
            dev = "الجهاز"
            for d in ["vuzero4k", "vuduo4kse", "vuduo4k", "vusolo4k", "vuultimo4k", "vuuno4kse", "vuuno4k", "vuzero", "vusolo2", "vuduo2", "novaler4kpro", "novaler4kse", "novaler4k", "sf8008", "sf4008", "sf3038", "sx88v2", "sx988", "sfx6008", "dm900", "dm920", "gbquad4k", "gbtrio4kpro", "gbtrio4k", "zgemmah17combo", "zgemmah82h"]:
                if d in fn.lower().replace(".", "").replace("-", "").replace("_", ""):
                    dev = d.upper()
                    break
            it["name"] = f"صورة {brand.upper()} لجهاز {dev}"
            it["description"] = f"صورة نظام {brand.upper()} الرسمية المحدثة لجهاز {dev}"
            return

    if "skin" in fn.lower():
        s_name = fn.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("enigma2-skin-", "").replace("skin-", "").split(".")[0]
        it["name"] = f"سكين {s_name}"
        it["description"] = f"سكين {s_name} عالي الدقة FHD بتصميم أنيق وخفيف"
        return

    for k, (n, d) in CUSTOM_MAP.items():
        if k.lower() in fn.lower() or k.lower() in name.lower():
            it["name"] = n
            it["description"] = d
            return

if os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    existing_custom = {}
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, "r", encoding="utf-8") as f:
                existing_custom = json.load(f)
        except Exception:
            existing_custom = {}

    meta_store = {}
    for cat, items in data.get("categories", {}).items():
        if isinstance(items, list):
            for el in items:
                if isinstance(el, dict) and "items" in el:
                    for it in el.get("items", []):
                        clean_item(it, existing_custom)
                        fn = it.get("file", "").split("/")[-1]
                        if fn: meta_store[fn] = {"name": it["name"], "description": it["description"]}
                elif isinstance(el, dict):
                    clean_item(el, existing_custom)
                    fn = el.get("file", "").split("/")[-1]
                    if fn: meta_store[fn] = {"name": el["name"], "description": el["description"]}

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta_store, f, indent=4, ensure_ascii=False)

    print("🎉 تم التنسيق بنجاح مع الحفاظ الكامل على أي تعديل يدوي قمت به!")
