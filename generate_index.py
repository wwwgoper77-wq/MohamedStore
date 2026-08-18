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
# 1. حفظ واسترجاع الأوصاف القديمة
# -------------------------------------------------
old_descriptions = {}
try:
    if os.path.exists("feed/index.json"):
        with open("feed/index.json", "r", encoding="utf-8") as f:
            old = json.load(f)

        for cat, items in old.get("categories", {}).items():
            if cat in ["skins", "system_images"]:
                for folder in items:
                    if isinstance(folder, dict) and "items" in folder:
                        for it in folder.get("items", []):
                            if it.get("name") and it.get("description"):
                                old_descriptions[it["name"]] = it["description"]
                    elif isinstance(folder, dict):
                        if folder.get("name") and folder.get("description"):
                            old_descriptions[folder["name"]] = folder["description"]
            else:
                for it in items:
                    if it.get("name") and it.get("description"):
                        old_descriptions[it["name"]] = it["description"]
except Exception as e:
    print("Notice: No previous descriptions loaded:", e)


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
    """توحيد النص لإلغاء الفروق بين الحروف الكبيرة والصغيرة والنقاط والشرطات"""
    return re.sub(r'[^a-z0-9]', '', text.lower())


# -------------------------------------------------
# 2. جلب جميع ملفات Releases من GitHub API
# -------------------------------------------------
release_assets_pool = []
try:
    api_rel = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/releases"
    req = urllib.request.Request(
        api_rel,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.github+json"
        }
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        releases = json.loads(response.read().decode("utf-8"))

    for release in releases:
        for asset in release.get("assets", []):
            filename = asset.get("name", "")
            if filename.endswith(EXTENSIONS):
                release_assets_pool.append({
                    "filename": filename,
                    "url": asset.get("browser_download_url", "")
                })
    print(f"✅ Loaded {len(release_assets_pool)} assets from Releases.")
except Exception as e:
    print("⚠️ GitHub Releases Fetch Error:", e)


# -------------------------------------------------
# 3. معالجة الأقسام ذات الحافظات الفرعية (System Images & Skins)
# -------------------------------------------------
def process_nested_category(cat_key, default_label):
    folders_map = {}

    # أولاً: قراءة المجلدات الحقيقية في المستودع
    if os.path.isdir(cat_key):
        for folder in sorted(os.listdir(cat_key)):
            folder_path = os.path.join(cat_key, folder)
            if not os.path.isdir(folder_path):
                continue

            folder_norm = normalize_text(folder)
            display_name = "All" if folder_norm == "all" else folder

            if folder_norm not in folders_map:
                folders_map[folder_norm] = {
                    "display_name": display_name,
                    "items": [],
                    "seen_files": set()
                }

            # قراءة الملفات المحلية
            for filename in sorted(os.listdir(folder_path)):
                if not filename.endswith(EXTENSIONS):
                    continue
                if filename not in folders_map[folder_norm]["seen_files"]:
                    folders_map[folder_norm]["seen_files"].add(filename)
                    clean = clean_filename(filename)
                    version = clean.split("_")[-2] if "_" in clean else "1.0"

                    file_url = f"{BASE_URL}/{cat_key}/{folder}/{filename}"
                    for asset in release_assets_pool:
                        if asset["filename"] == filename:
                            file_url = asset["url"]
                            break

                    folders_map[folder_norm]["items"].append({
                        "name": clean,
                        "version": version,
                        "description": old_descriptions.get(clean, f"{display_name} {default_label}"),
                        "file": file_url,
                        "image": image_url(clean.split("_")[0]) or image_url(display_name) or image_url(cat_key)
                    })

    # ثانياً: فحص ملفات الـ Releases بحسب القسم أولاً ثم المجلد
    for asset in release_assets_pool:
        fname = asset["filename"]
        fname_norm = normalize_text(fname)

        # التحقق من مطابقة القسم (مثلاً: system_images أو skins)
        is_this_cat = False
        if cat_key == "system_images" and any(k in fname_norm for k in ["systemimage", "systemimages", "image", "img", "py3", "emmc", "mmc", "recovery", "usb"]):
            is_this_cat = True
        elif cat_key == "skins" and "skin" in fname_norm:
            is_this_cat = True

        if not is_this_cat:
            continue

        # تحديد المجلد الهدف المناسب بناءً على الاسم
        matched_folder = None
        for f_norm, f_data in folders_map.items():
            if f_norm != "all" and f_norm in fname_norm:
                matched_folder = f_norm
                break

        # إذا لم يتطابق مع مجلد معين، يوضع في All أو ينشئ مجلداً باسم الفريق
        if not matched_folder:
            if "all" in folders_map:
                matched_folder = "all"
            else:
                # إنشاء مجلد تلقائي مثل openpli
                if "openpli" in fname_norm or "open.pli" in fname.lower():
                    matched_folder = "openpli"
                    if matched_folder not in folders_map:
                        folders_map[matched_folder] = {"display_name": "OpenPLi", "items": [], "seen_files": set()}
                else:
                    matched_folder = "all"
                    if matched_folder not in folders_map:
                        folders_map[matched_folder] = {"display_name": "All", "items": [], "seen_files": set()}

        if fname not in folders_map[matched_folder]["seen_files"]:
            folders_map[matched_folder]["seen_files"].add(fname)
            clean = clean_filename(fname)
            version = clean.split("_")[-2] if "_" in clean else "1.0"
            display_name = folders_map[matched_folder]["display_name"]

            folders_map[matched_folder]["items"].append({
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, f"{display_name} {default_label}"),
                "file": asset["url"],
                "image": image_url(clean.split("_")[0]) or image_url(display_name) or image_url(cat_key)
            })

    # تجهيز القائمة النهائية
    for f_norm, f_data in sorted(folders_map.items()):
        if f_data["items"]:
            data["categories"][cat_key].append({
                "name": f_data["display_name"],
                "items": f_data["items"]
            })


# تشغيل صور النظام والسكينات
process_nested_category("system_images", "Image")
process_nested_category("skins", "Skin")


# -------------------------------------------------
# 4. معالجة الأقسام المفردة (Plugins, Tools, Picons, Channels, Novaler)
# -------------------------------------------------
def process_flat_category(cat_key, keywords):
    items_list = []
    seen_files = set()

    # الملفات المحلية
    if os.path.isdir(cat_key):
        for filename in sorted(os.listdir(cat_key)):
            if not filename.endswith(EXTENSIONS):
                continue
            seen_files.add(filename)
            clean = clean_filename(filename)
            version = clean.split("_")[-2] if "_" in clean else "1.0"

            file_url = f"{BASE_URL}/{cat_key}/{filename}"
            for asset in release_assets_pool:
                if asset["filename"] == filename:
                    file_url = asset["url"]
                    break

            items_list.append({
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, f"{cat_key.capitalize()} Package"),
                "file": file_url,
                "image": image_url(clean.split("_")[0]) or image_url(cat_key)
            })

    # ملفات Releases
    for asset in release_assets_pool:
        fname = asset["filename"]
        fname_norm = normalize_text(fname)

        if fname in seen_files:
            continue

        # استبعاد الأقسام الأخرى
        if any(k in fname_norm for k in ["systemimage", "skin", "openpli", "openatv", "openbh", "egami"]):
            continue

        if any(k in fname_norm for k in keywords):
            seen_files.add(fname)
            clean = clean_filename(fname)
            version = clean.split("_")[-2] if "_" in clean else "1.0"

            items_list.append({
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, f"{cat_key.capitalize()} Package"),
                "file": asset["url"],
                "image": image_url(clean.split("_")[0]) or image_url(cat_key)
            })

    data["categories"][cat_key] = items_list


process_flat_category("plugins", ["plugin", "extension", "panel", "weather", "tmdb", "subs", "e2player", "multiepg"])
process_flat_category("tools", ["tool", "ncam", "oscam", "softcam", "emu", "script", "tweak"])
process_flat_category("picons", ["picon", "logos", "snp", "srp"])
process_flat_category("channels", ["channel", "setting", "bouquet", "satellites"])
process_flat_category("novaler", ["novaler", "noflayer"])


# -------------------------------------------------
# 5. حفظ الفهرس في feed/index.json
# -------------------------------------------------
os.makedirs("feed", exist_ok=True)
output_path = "feed/index.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print(f"🎉 Successfully generated {output_path} with all categories, releases, and preserved descriptions!")
