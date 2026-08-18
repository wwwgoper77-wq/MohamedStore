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

# -------------------------------------------------
# 1. حفظ الأوصاف القديمة
# -------------------------------------------------
old_descriptions = {}
try:
    if os.path.exists("feed/index.json"):
        with open("feed/index.json", "r", encoding="utf-8") as f:
            old = json.load(f)

        for cat, items in old.get("categories", {}).items():
            if isinstance(items, list):
                for el in items:
                    if isinstance(el, dict) and "items" in el:
                        for it in el.get("items", []):
                            if it.get("name") and it.get("description"):
                                old_descriptions[it["name"]] = it["description"]
                    elif isinstance(el, dict):
                        if el.get("name") and el.get("description"):
                            old_descriptions[el["name"]] = el["description"]
except Exception:
    pass


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


# الامتدادات المدعومة
EXTENSIONS = (".ipk", ".sh", ".deb", ".zip", ".tar.gz", ".tgz", ".tar", ".py", ".tv", ".img", ".nfi", ".tar.xz", ".bin")


def clean_filename(filename):
    if filename.endswith(".tar.gz") or filename.endswith(".tar.xz"):
        return filename[:-7]
    return os.path.splitext(filename)[0]


def normalize_text(text):
    return re.sub(r'[^a-z0-9]', '', str(text).lower())


# -------------------------------------------------
# 2. جلب جميع ملفات Releases كاملة بدون نقصان
# -------------------------------------------------
release_assets_pool = []
github_token = os.environ.get("GITHUB_TOKEN", "")

headers = {
    "User-Agent": "MohamedStore-Feed",
    "Accept": "application/vnd.github+json"
}
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
            for asset in release.get("assets", []):
                filename = asset.get("name", "")
                if filename.endswith(EXTENSIONS):
                    release_assets_pool.append({
                        "filename": filename,
                        "url": asset.get("browser_download_url", "")
                    })

        if len(releases) < 100:
            break
        page += 1
    except Exception as e:
        print("Releases Fetch Status:", e)
        break

print(f"✅ Loaded {len(release_assets_pool)} files from Releases.")


# -------------------------------------------------
# 3. معالجة الأقسام ذات المجلدات (system_images و skins)
# -------------------------------------------------
def process_nested(cat_key, default_label):
    folders_map = {}

    # قراءة كل المجلدات الموجودة في المستودع
    if os.path.isdir(cat_key):
        for folder in sorted(os.listdir(cat_key)):
            f_path = os.path.join(cat_key, folder)
            if not os.path.isdir(f_path):
                continue

            norm_key = normalize_text(folder)
            display_name = "All" if norm_key == "all" else folder

            if norm_key not in folders_map:
                folders_map[norm_key] = {
                    "display_name": display_name,
                    "items": [],
                    "seen": set()
                }

            # جلب كل الملفات المحلية في المجلد
            for fn in sorted(os.listdir(f_path)):
                if not fn.endswith(EXTENSIONS):
                    continue
                folders_map[norm_key]["seen"].add(fn)
                clean = clean_filename(fn)
                ver = clean.split("_")[-2] if "_" in clean else "1.0"

                file_url = f"{BASE_URL}/{cat_key}/{folder}/{fn}"
                for asset in release_assets_pool:
                    if asset["filename"] == fn:
                        file_url = asset["url"]
                        break

                folders_map[norm_key]["items"].append({
                    "name": clean,
                    "version": ver,
                    "description": old_descriptions.get(clean, f"{display_name} {default_label}"),
                    "file": file_url,
                    "image": image_url(clean.split("_")[0]) or image_url(display_name) or image_url(cat_key)
                })

    # ربط ملفات الـ Releases بالمجلد الذي يطابق اسمها فوراً (بدون شروط أجهزة)
    for asset in release_assets_pool:
        fn = asset["filename"]
        fn_norm = normalize_text(fn)

        matched_folder = None

        # 1. إذا كان اسم المجلد موجوداً في اسم الملف
        for norm_k in folders_map.keys():
            if norm_k != "all" and norm_k in fn_norm:
                matched_folder = norm_k
                break

        # 2. إذا لم يطابق مجلداً فرعياً، وكان الملف ينتمي لهذا القسم
        if not matched_folder:
            if cat_key == "system_images" and any(k in fn_norm for k in ["image", "img", "py3", "emmc", "mmc", "usb", "recovery", "rootfs"]):
                matched_folder = "all" if "all" in folders_map else None
            elif cat_key == "skins" and "skin" in fn_norm:
                matched_folder = "all" if "all" in folders_map else None

        # وضع الملف في المجلد المطابق
        if matched_folder and matched_folder in folders_map:
            if fn not in folders_map[matched_folder]["seen"]:
                folders_map[matched_folder]["seen"].add(fn)
                clean = clean_filename(fn)
                ver = clean.split("_")[-2] if "_" in clean else "1.0"
                disp = folders_map[matched_folder]["display_name"]

                folders_map[matched_folder]["items"].append({
                    "name": clean,
                    "version": ver,
                    "description": old_descriptions.get(clean, f"{disp} {default_label}"),
                    "file": asset["url"],
                    "image": image_url(clean.split("_")[0]) or image_url(disp) or image_url(cat_key)
                })

    # حفظ كافة المجلدات بما فيها الفارغة
    for norm_k, f_data in sorted(folders_map.items()):
        data["categories"][cat_key].append({
            "name": f_data["display_name"],
            "items": f_data["items"]
        })


process_nested("system_images", "Image")
process_nested("skins", "Skin")


# -------------------------------------------------
# 4. معالجة الأقسام العادية (Plugins, Tools, Picons, Channels, Novaler)
# -------------------------------------------------
def process_flat(cat_key):
    items = []
    seen = set()

    # 1. الملفات من داخل المجلد المحلي
    if os.path.isdir(cat_key):
        for fn in sorted(os.listdir(cat_key)):
            if not fn.endswith(EXTENSIONS):
                continue
            seen.add(fn)
            clean = clean_filename(fn)
            ver = clean.split("_")[-2] if "_" in clean else "1.0"

            file_url = f"{BASE_URL}/{cat_key}/{fn}"
            for asset in release_assets_pool:
                if asset["filename"] == fn:
                    file_url = asset["url"]
                    break

            items.append({
                "name": clean,
                "version": ver,
                "description": old_descriptions.get(clean, f"{cat_key.capitalize()} Package"),
                "file": file_url,
                "image": image_url(clean.split("_")[0]) or image_url(cat_key)
            })

    # 2. ملفات الـ Releases التي تحتوي على اسم القسم
    cat_norm = normalize_text(cat_key)
    for asset in release_assets_pool:
        fn = asset["filename"]
        fn_norm = normalize_text(fn)

        if fn in seen:
            continue

        # إذا كان اسم القسم موجوداً في اسم الملف
        if cat_norm in fn_norm:
            seen.add(fn)
            clean = clean_filename(fn)
            ver = clean.split("_")[-2] if "_" in clean else "1.0"

            items.append({
                "name": clean,
                "version": ver,
                "description": old_descriptions.get(clean, f"{cat_key.capitalize()} Package"),
                "file": asset["url"],
                "image": image_url(clean.split("_")[0]) or image_url(cat_key)
            })

    data["categories"][cat_key] = items


# معالجة كل الأقسام فوراً
process_flat("plugins")
process_flat("tools")
process_flat("picons")
process_flat("channels")
process_flat("novaler")


# -------------------------------------------------
# 5. حفظ الفهرس في feed/index.json
# -------------------------------------------------
os.makedirs("feed", exist_ok=True)
with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("🎉 Feed index generated successfully without any restrictions or hardcoded device checks!")
