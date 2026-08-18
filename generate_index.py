import os
import json
import re
import urllib.request
import urllib.error

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
# 2. جلب جميع ملفات Releases من GitHub API مع دعم Pagination & Token
# -------------------------------------------------
release_assets_pool = []
github_token = os.environ.get("GITHUB_TOKEN", "")

headers = {
    "User-Agent": "MohamedStore-Feed-Generator",
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
        print(f"GitHub Releases Fetch Notice on page {page}:", e)
        break

print(f"✅ Total Release Assets loaded: {len(release_assets_pool)}")


# -------------------------------------------------
# 3. معالجة الأقسام ذات الحافظات الفرعية (System Images & Skins)
# -------------------------------------------------
def process_nested_category(cat_key, default_label):
    folders_map = {}

    # أولاً: قراءة المجلدات الحقيقية في المستودع (بما فيها الفارغة)
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

            # قراءة الملفات المحلية إن وجدت
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

    # ثانياً: فحص وتوزيع ملفات Releases على الحافظات
    for asset in release_assets_pool:
        fname = asset["filename"]
        fname_norm = normalize_text(fname)

        is_this_cat = False
        if cat_key == "system_images":
            if any(k in fname_norm for k in [
                "systemimage", "systemimages", "openpli", "openatv", "openbh", "blackhole",
                "egami", "pure2", "openspa", "openvix", "octagon", "vuplus", "vuzero", "vuduo",
                "sf8008", "multibox", "py3", "emmc", "mmc", "recovery", "rootfs", "kernel"
            ]):
                # استبعاد البلجنات والسكينات
                if not any(k in fname_norm for k in ["plugin", "skin", "picon", "channel", "ncam", "oscam"]):
                    is_this_cat = True

        elif cat_key == "skins":
            if "skin" in fname_norm:
                is_this_cat = True

        if not is_this_cat:
            continue

        # مطابقة اسم الحافظة
        matched_folder = None
        for f_norm, f_data in folders_map.items():
            if f_norm != "all" and f_norm in fname_norm:
                matched_folder = f_norm
                break

        # مطابقة خاصة لصور النظام المشهورة إن لم يكن المجلد موجوداً بعد
        if not matched_folder and cat_key == "system_images":
            if "openpli" in fname_norm or "open.pli" in fname.lower():
                matched_folder = "openpli"
                if matched_folder not in folders_map:
                    folders_map[matched_folder] = {"display_name": "OpenPLi", "items": [], "seen_files": set()}
            elif "openatv" in fname_norm or "atv" in fname_norm:
                matched_folder = "openatv"
                if matched_folder not in folders_map:
                    folders_map[matched_folder] = {"display_name": "OpenATV", "items": [], "seen_files": set()}
            elif "openbh" in fname_norm or "blackhole" in fname_norm:
                matched_folder = "openbh"
                if matched_folder not in folders_map:
                    folders_map[matched_folder] = {"display_name": "OpenBH", "items": [], "seen_files": set()}
            elif "egami" in fname_norm:
                matched_folder = "egami"
                if matched_folder not in folders_map:
                    folders_map[matched_folder] = {"display_name": "EGAMI", "items": [], "seen_files": set()}

        if not matched_folder:
            if "all" in folders_map:
                matched_folder = "all"
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

    # حفظ الحافظات بما فيها الفارغة
    for f_norm, f_data in sorted(folders_map.items()):
        data["categories"][cat_key].append({
            "name": f_data["display_name"],
            "items": f_data["items"]
        })


# تشغيل الأقسام المزدوجة
process_nested_category("system_images", "Image")
process_nested_category("skins", "Skin")


# -------------------------------------------------
# 4. معالجة الأقسام المفردة (Plugins, Tools, Picons, Channels, Novaler)
# -------------------------------------------------
def process_flat_category(cat_key, keywords, exclude_keywords):
    items_list = []
    seen_files = set()

    # 1. قراءة الملفات المحلية
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

    # 2. سحب ملفات Releases الخاصة بهذا القسم بدقة
    for asset in release_assets_pool:
        fname = asset["filename"]
        fname_norm = normalize_text(fname)

        if fname in seen_files:
            continue

        # استبعاد الكلمات التابعة لأقسام أخرى
        if any(ex in fname_norm for ex in exclude_keywords):
            continue

        # مطابقة كلمات هذا القسم
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


# تصنيف دقيق ومنظم للأقسام الفردية
process_flat_category(
    "plugins",
    ["plugin", "extension", "panel", "weather", "tmdb", "subs", "e2player", "multiepg", "ipa", "audi"],
    ["skin", "systemimage", "openpli", "openatv", "openbh", "egami", "picon", "satellites", "ncam", "oscam"]
)

process_flat_category(
    "tools",
    ["tool", "ncam", "oscam", "softcam", "emu", "script", "tweak", "extnumber", "powershell"],
    ["skin", "systemimage", "openpli", "openatv", "picon", "satellites"]
)

process_flat_category(
    "picons",
    ["picon", "logos", "snp", "srp", "zzpicon"],
    ["skin", "systemimage", "plugin"]
)

process_flat_category(
    "channels",
    ["channel", "setting", "bouquet", "satellites", "fav", "m3u"],
    ["skin", "systemimage", "plugin", "picon"]
)

process_flat_category(
    "novaler",
    ["novaler", "noflayer"],
    ["skin", "systemimage", "openpli", "openatv", "openbh", "egami"]
)


# -------------------------------------------------
# 5. حفظ الفهرس في feed/index.json
# -------------------------------------------------
os.makedirs("feed", exist_ok=True)
output_path = "feed/index.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print(f"🎉 Successfully generated {output_path} with all Release assets, preserved folders & descriptions!")
