import os
import json
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

# -------- Preserve old descriptions --------
old_descriptions = {}

try:
    if os.path.exists("feed/index.json"):
        with open("feed/index.json", "r", encoding="utf-8") as f:
            old = json.load(f)

        for cat, items in old.get("categories", {}).items():
            if isinstance(items, list):
                for folder_or_item in items:
                    if isinstance(folder_or_item, dict):
                        if "items" in folder_or_item:
                            for it in folder_or_item.get("items", []):
                                old_descriptions[it.get("name", "")] = it.get("description", "")
                        else:
                            old_descriptions[folder_or_item.get("name", "")] = folder_or_item.get("description", "")
except Exception:
    pass


def image_url(prefix):
    prefix = prefix.lower()
    if os.path.isdir("Icons"):
        for file in sorted(os.listdir("Icons")):
            if file.lower().startswith(prefix) and file.lower().endswith(".png"):
                return f"{BASE_URL}/Icons/{file}"
    if os.path.isdir("images"):
        for file in sorted(os.listdir("images")):
            if file.lower().startswith(prefix) and file.lower().endswith(".png"):
                return f"{BASE_URL}/images/{file}"
    return ""


# صيغ ملفات التثبيت والصور العامة
EXTENSIONS = (".ipk", ".sh", ".deb", ".zip", ".tar.gz", ".tgz", ".tar", ".py", ".tv", ".img", ".nfi", ".tar.xz", ".bin")

# قاموس روابط التحميل السريعة من الـ Releases إن وجدت
release_urls = {}
try:
    api_rel = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/releases"
    req = urllib.request.Request(
        api_rel,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        releases = json.loads(response.read().decode("utf-8"))
        for release in releases:
            for asset in release.get("assets", []):
                filename = asset["name"]
                if filename.endswith(EXTENSIONS):
                    release_urls[filename] = asset["browser_download_url"]
except Exception:
    pass


# جلب شجرة ملفات ومجلدات المستودع من GitHub لضمان قراءة ما تم رفعه على الموقع مباشرة
github_files = []
try:
    api_tree = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/git/trees/main?recursive=1"
    req = urllib.request.Request(
        api_tree,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        tree_data = json.loads(response.read().decode("utf-8"))
        for item in tree_data.get("tree", []):
            if item.get("type") == "blob":
                github_files.append(item.get("path", ""))
except Exception:
    pass


def clean_filename(filename):
    if filename.endswith(".tar.gz"):
        return filename[:-7]
    elif filename.endswith(".tar.xz"):
        return filename[:-7]
    else:
        return os.path.splitext(filename)[0]


def get_file_url(relative_path, filename):
    if filename in release_urls:
        return release_urls[filename]
    return f"{BASE_URL}/{relative_path}"


# -------------------------------------------------
# 1. System Images (صور النظام - كل ملف في حافظته بدقة تامة)
# -------------------------------------------------
sys_folders = set()
if os.path.isdir("system_images"):
    for f in os.listdir("system_images"):
        if os.path.isdir(os.path.join("system_images", f)):
            sys_folders.add(f)

for p in github_files:
    if p.startswith("system_images/"):
        parts = p.split("/")
        if len(parts) >= 3:
            sys_folders.add(parts[1])

for folder in sorted(sys_folders):
    folder_items = []
    seen_files = set()
    folder_path = os.path.join("system_images", folder)

    # 1. من المجلد المحلي
    if os.path.isdir(folder_path):
        for filename in sorted(os.listdir(folder_path)):
            if filename.endswith(EXTENSIONS) and filename not in seen_files:
                seen_files.add(filename)
                clean = clean_filename(filename)
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                image_name = clean.split("_")[0]
                img = image_url(image_name) or image_url(folder) or image_url("system_images")

                folder_items.append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, f"{folder} Firmware Image"),
                    "file": get_file_url(f"system_images/{folder}/{filename}", filename),
                    "image": img
                })

    # 2. من GitHub مباشرة
    prefix = f"system_images/{folder}/"
    for p in github_files:
        if p.startswith(prefix):
            filename = os.path.basename(p)
            if filename.endswith(EXTENSIONS) and filename not in seen_files:
                seen_files.add(filename)
                clean = clean_filename(filename)
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                image_name = clean.split("_")[0]
                img = image_url(image_name) or image_url(folder) or image_url("system_images")

                folder_items.append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, f"{folder} Firmware Image"),
                    "file": get_file_url(p, filename),
                    "image": img
                })

    data["categories"]["system_images"].append({
        "name": folder.replace("_", " "),
        "items": folder_items
    })


# -------------------------------------------------
# 2. Skins (السكينات - كل سكين في حافظته بدقة تامة)
# -------------------------------------------------
skin_folders = set()
if os.path.isdir("skins"):
    for f in os.listdir("skins"):
        if os.path.isdir(os.path.join("skins", f)):
            skin_folders.add(f)

for p in github_files:
    if p.startswith("skins/"):
        parts = p.split("/")
        if len(parts) >= 3:
            skin_folders.add(parts[1])

for folder in sorted(skin_folders):
    items = []
    seen_files = set()
    folder_path = os.path.join("skins", folder)

    # 1. محلياً
    if os.path.isdir(folder_path):
        for filename in sorted(os.listdir(folder_path)):
            if filename.endswith(EXTENSIONS) and filename not in seen_files:
                seen_files.add(filename)
                clean = clean_filename(filename)
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                display = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
                image_name = display.split("_")[0]
                img = image_url(image_name) or image_url(clean.split("_")[0]) or image_url("skins")

                items.append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, folder + " Skin"),
                    "file": get_file_url(f"skins/{folder}/{filename}", filename),
                    "image": img
                })

    # 2. من GitHub
    prefix = f"skins/{folder}/"
    for p in github_files:
        if p.startswith(prefix):
            filename = os.path.basename(p)
            if filename.endswith(EXTENSIONS) and filename not in seen_files:
                seen_files.add(filename)
                clean = clean_filename(filename)
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                display = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
                image_name = display.split("_")[0]
                img = image_url(image_name) or image_url(clean.split("_")[0]) or image_url("skins")

                items.append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, folder + " Skin"),
                    "file": get_file_url(p, filename),
                    "image": img
                })

    data["categories"]["skins"].append({
        "name": folder.replace("_", " "),
        "items": items
    })


# -------------------------------------------------
# 3. Picons (البيكونات حصراً من مجلد picons/)
# -------------------------------------------------
picon_files = set()
if os.path.isdir("picons"):
    for f in os.listdir("picons"):
        if f.endswith(EXTENSIONS):
            picon_files.add(f)

for p in github_files:
    if p.startswith("picons/"):
        fname = os.path.basename(p)
        if fname.endswith(EXTENSIONS):
            picon_files.add(fname)

for filename in sorted(picon_files):
    clean = clean_filename(filename)
    data["categories"]["picons"].append({
        "name": clean,
        "version": "1.0",
        "description": old_descriptions.get(clean, "Picon Pack"),
        "file": get_file_url(f"picons/{filename}", filename),
        "image": image_url(clean.split("_")[0]) or image_url("picons")
    })


# -------------------------------------------------
# 4. Channels & Settings (القنوات حصراً من channels/)
# -------------------------------------------------
channel_files = set()
if os.path.isdir("channels"):
    for f in os.listdir("channels"):
        if f.endswith(EXTENSIONS):
            channel_files.add(f)

for p in github_files:
    if p.startswith("channels/"):
        fname = os.path.basename(p)
        if fname.endswith(EXTENSIONS):
            channel_files.add(fname)

for filename in sorted(channel_files):
    clean = clean_filename(filename)
    data["categories"]["channels"].append({
        "name": clean,
        "version": "1.0",
        "description": old_descriptions.get(clean, "Channel Settings"),
        "file": get_file_url(f"channels/{filename}", filename),
        "image": image_url(clean.split("_")[0]) or image_url("channels")
    })


# -------------------------------------------------
# 5. Tools (الأدوات حصراً من tools/)
# -------------------------------------------------
tool_files = set()
if os.path.isdir("tools"):
    for f in os.listdir("tools"):
        if f.endswith(EXTENSIONS):
            tool_files.add(f)

for p in github_files:
    if p.startswith("tools/"):
        fname = os.path.basename(p)
        if fname.endswith(EXTENSIONS):
            tool_files.add(fname)

for filename in sorted(tool_files):
    clean = clean_filename(filename)
    version = clean.split("_")[-2] if "_" in clean else "1.0"
    image_name = clean.split("_")[0]

    data["categories"]["tools"].append({
        "name": clean,
        "version": version,
        "description": old_descriptions.get(clean, "System Tool"),
        "file": get_file_url(f"tools/{filename}", filename),
        "image": image_url(image_name) or image_url("tools")
    })


# -------------------------------------------------
# 6. Plugins (الإضافات حصراً من plugins/)
# -------------------------------------------------
plugin_files = set()
if os.path.isdir("plugins"):
    for f in os.listdir("plugins"):
        if f.endswith(EXTENSIONS):
            plugin_files.add(f)

for p in github_files:
    if p.startswith("plugins/"):
        fname = os.path.basename(p)
        if fname.endswith(EXTENSIONS):
            plugin_files.add(fname)

for filename in sorted(plugin_files):
    clean = clean_filename(filename)
    version = clean.split("_")[-2] if "_" in clean else "1.0"
    display = clean.replace("enigma2-plugin-", "")

    data["categories"]["plugins"].append({
        "name": display,
        "version": version,
        "description": old_descriptions.get(display, "Plugin Extension"),
        "file": get_file_url(f"plugins/{filename}", filename),
        "image": image_url(
            display.split("_")[0]
            .replace("extensions-", "")
            .replace("skins-", "")
            .replace("plugin-", "")
        ) or image_url("plugins")
    })


# -------------------------------------------------
# 7. Novaler (قسم نوفالير حصراً من novaler/ أو Novaler/ أو Noflayer/)
# -------------------------------------------------
novaler_files = set()
novaler_dir_name = "novaler"

for check_dir in ["novaler", "Novaler", "Noflayer", "noflayer"]:
    if os.path.isdir(check_dir):
        novaler_dir_name = check_dir
        for f in os.listdir(check_dir):
            if f.endswith(EXTENSIONS):
                novaler_files.add((check_dir, f))

for p in github_files:
    for check_dir in ["novaler/", "Novaler/", "Noflayer/", "noflayer/"]:
        if p.startswith(check_dir):
            fname = os.path.basename(p)
            if fname.endswith(EXTENSIONS):
                novaler_files.add((check_dir.rstrip("/"), fname))

for dir_used, filename in sorted(novaler_files):
    clean = clean_filename(filename)
    version = clean.split("_")[-2] if "_" in clean else "1.0"
    display = (
        clean.replace("enigma2-plugin-extensions-", "")
        .replace("enigma2-plugin-", "")
        .replace("extensions-", "")
    )
    image_name = display.split("_")[0]
    img = image_url("novaler") or image_url("noflayer") or image_url(image_name)

    data["categories"]["novaler"].append({
        "name": clean,
        "version": version,
        "description": old_descriptions.get(clean, "Novaler Pack"),
        "file": get_file_url(f"{dir_used}/{filename}", filename),
        "image": img
    })


# -------------------------------------------------
# Save JSON
# -------------------------------------------------
os.makedirs("feed", exist_ok=True)

with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("feed/index.json generated successfully. 100% Strict folder separation with zero mixing.")
