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

# 2. قراءة التعديلات اليدوية
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


def clean_filename(filename):
    for ext in [".tar.gz", ".tar.xz", ".tar.bz2", ".ipk", ".deb", ".zip", ".sh", ".rar", ".7z", ".tv", ".img", ".nfi"]:
        if filename.lower().endswith(ext):
            return filename[:-len(ext)]
    return os.path.splitext(filename)[0]


def clean_skin_name(fn):
    name = clean_filename(fn)
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
    
    # 1. إذا قمت بتعديله يدوياً
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

    # 4. التسمية الافتراضية
    auto_name = clean_name
    auto_desc = default_desc
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


# جلب الـ Releases لتحديث الروابط إن وجدت
release_assets_map = {}
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
                if filename.lower().endswith(EXTENSIONS):
                    release_assets_map[filename.lower()] = {
                        "url": asset.get("browser_download_url", ""),
                        "body": rel_body,
                        "raw_name": filename
                    }

        if len(releases) < 100:
            break
        page += 1
    except Exception as e:
        print("Releases notice:", e)
        break


# 1. قسم صور النظام System Images (يعتمد 100% على مجلد system_images فقط)
if os.path.isdir("system_images"):
    sys_folders = {}
    for item_name in sorted(os.listdir("system_images")):
        item_path = os.path.join("system_images", item_name)
        if os.path.isdir(item_path):
            disp = item_name
            folder_items = []
            for fn in sorted(os.listdir(item_path)):
                if not fn.lower().endswith(EXTENSIONS):
                    continue
                clean = clean_filename(fn)
                f_url = f"{BASE_URL}/system_images/{item_name}/{fn}"
                body_desc = ""
                if fn.lower() in release_assets_map:
                    f_url = release_assets_map[fn.lower()]["url"]
                    body_desc = release_assets_map[fn.lower()]["body"]
                
                final_name, final_desc = get_smart_name_and_desc(fn, clean, body_desc, f"{disp} Image", is_skin=False, is_sys_img=True, disp_folder=disp)
                folder_items.append({
                    "name": final_name,
                    "description": final_desc,
                    "file": f_url,
                    "image": image_url(clean.split("_")[0]) or image_url(disp) or image_url("system_images")
                })
            if folder_items:
                sys_folders[disp] = folder_items

        elif item_name.lower().endswith(EXTENSIONS):
            disp = "All"
            clean = clean_filename(item_name)
            f_url = f"{BASE_URL}/system_images/{item_name}"
            body_desc = ""
            if item_name.lower() in release_assets_map:
                f_url = release_assets_map[item_name.lower()]["url"]
                body_desc = release_assets_map[item_name.lower()]["body"]
            
            final_name, final_desc = get_smart_name_and_desc(item_name, clean, body_desc, "System Image", is_skin=False, is_sys_img=True, disp_folder=disp)
            if disp not in sys_folders:
                sys_folders[disp] = []
            sys_folders[disp].append({
                "name": final_name,
                "description": final_desc,
                "file": f_url,
                "image": image_url(clean.split("_")[0]) or image_url("system_images")
            })

    for folder_name, items in sys_folders.items():
        data["categories"]["system_images"].append({
            "name": folder_name,
            "items": items
        })


# 2. قسم السكينات Skins (يعتمد 100% على مجلد skins فقط)
if os.path.isdir("skins"):
    skin_folders = {}
    for item_name in sorted(os.listdir("skins")):
        item_path = os.path.join("skins", item_name)
        if os.path.isdir(item_path):
            disp = item_name
            folder_items = []
            for fn in sorted(os.listdir(item_path)):
                if not fn.lower().endswith(EXTENSIONS):
                    continue
                clean = clean_filename(fn)
                disp_skin = clean_skin_name(fn)
                f_url = f"{BASE_URL}/skins/{item_name}/{fn}"
                body_desc = ""
                if fn.lower() in release_assets_map:
                    f_url = release_assets_map[fn.lower()]["url"]
                    body_desc = release_assets_map[fn.lower()]["body"]

                final_name, final_desc = get_smart_name_and_desc(fn, clean, body_desc, f"{disp} Skin", is_skin=True, is_sys_img=False)
                folder_items.append({
                    "name": final_name,
                    "description": final_desc,
                    "file": f_url,
                    "image": image_url(disp_skin.split(" ")[0]) or image_url("skins")
                })
            if folder_items:
                skin_folders[disp] = folder_items

        elif item_name.lower().endswith(EXTENSIONS):
            disp = "All"
            clean = clean_filename(item_name)
            disp_skin = clean_skin_name(item_name)
            f_url = f"{BASE_URL}/skins/{item_name}"
            body_desc = ""
            if item_name.lower() in release_assets_map:
                f_url = release_assets_map[item_name.lower()]["url"]
                body_desc = release_assets_map[item_name.lower()]["body"]

            final_name, final_desc = get_smart_name_and_desc(item_name, clean, body_desc, "Skin", is_skin=True, is_sys_img=False)
            if disp not in skin_folders:
                skin_folders[disp] = []
            skin_folders[disp].append({
                "name": final_name,
                "description": final_desc,
                "file": f_url,
                "image": image_url(disp_skin.split(" ")[0]) or image_url("skins")
            })

    for folder_name, items in skin_folders.items():
        data["categories"]["skins"].append({
            "name": folder_name,
            "items": items
        })


# 3. الأقسام المباشرة الأخرى (تعتمد 100% وبصرامة على مجلداتها فقط)
def process_exact_category(cat_key, default_desc):
    items = []
    if os.path.isdir(cat_key):
        for root, dirs, files in os.walk(cat_key):
            for fn in sorted(files):
                if not fn.lower().endswith(EXTENSIONS):
                    continue
                clean = clean_filename(fn)
                disp_name = clean.replace("enigma2-plugin-extensions-", "").replace("enigma2-plugin-", "")
                rel_path = os.path.relpath(os.path.join(root, fn), cat_key).replace("\\", "/")
                f_url = f"{BASE_URL}/{cat_key}/{rel_path}"
                body_desc = ""
                
                # إذا كان الملف مرفوعاً بالـ Releases، نأخذ رابط التنزيل المباشر
                if fn.lower() in release_assets_map:
                    f_url = release_assets_map[fn.lower()]["url"]
                    body_desc = release_assets_map[fn.lower()]["body"]

                final_name, final_desc = get_smart_name_and_desc(fn, clean, body_desc, default_desc, is_skin=False, is_sys_img=False)
                items.append({
                    "name": final_name,
                    "description": final_desc,
                    "file": f_url,
                    "image": image_url(disp_name.split("_")[0]) or image_url(cat_key)
                })
    data["categories"][cat_key] = items


# كل قسم يأخذ ملفاته فقط من مجلده في المستودع
process_exact_category("novaler", "Novaler Package")
process_exact_category("picons", "Picons Package")
process_exact_category("channels", "Channels Settings")
process_exact_category("tools", "Tool Package")
process_exact_category("plugins", "Plugin Extension")


# حفظ النتائج
os.makedirs("feed", exist_ok=True)
with open(INDEX_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

with open(META_STORE_FILE, "w", encoding="utf-8") as f:
    json.dump(metadata_store, f, indent=4, ensure_ascii=False)

print("🎉 Successfully generated feed/index.json: 100% Folder-driven and zero misplacement!")
