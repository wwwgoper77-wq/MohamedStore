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
except:
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


# -------------------------------------------------
# 1. جلب شجرة المستودع بالكامل من GitHub ديناميكياً
# -------------------------------------------------
github_tree_paths = []
try:
    api_tree = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/git/trees/main?recursive=1"
    req = urllib.request.Request(
        api_tree,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        tree_data = json.loads(response.read().decode("utf-8"))
        for item in tree_data.get("tree", []):
            github_tree_paths.append(item.get("path", ""))
except Exception as e:
    print("GitHub Tree Fetch Info:", e)


# -------------------------------------------------
# 2. جلب ملفات الـ Releases
# -------------------------------------------------
release_assets_pool = []
try:
    api_rel = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/releases"
    req = urllib.request.Request(
        api_rel,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        releases = json.loads(response.read().decode("utf-8"))
        for release in releases:
            for asset in release.get("assets", []):
                filename = asset["name"]
                if filename.endswith(EXTENSIONS):
                    release_assets_pool.append({
                        "filename": filename,
                        "url": asset["browser_download_url"]
                    })
except Exception as e:
    print("GitHub Releases Fetch Info:", e)


def clean_filename(filename):
    if filename.endswith(".tar.gz"):
        return filename[:-7]
    elif filename.endswith(".tar.xz"):
        return filename[:-7]
    else:
        return os.path.splitext(filename)[0]


# دالة ذكية لاكتشاف كافة المجلدات التابعة لأي قسم تلقائياً
def discover_category_folders(section_name):
    folders = set()
    
    # من المجلد المحلي
    if os.path.isdir(section_name):
        for f in os.listdir(section_name):
            if os.path.isdir(os.path.join(section_name, f)):
                folders.add(f)
                
    # من شجرة GitHub
    prefix = f"{section_name}/"
    for p in github_tree_paths:
        if p.startswith(prefix):
            parts = p[len(prefix):].split("/")
            if len(parts) >= 1 and parts[0]:
                # إذا كان مجلداً فرعياً
                if len(parts) > 1 or not any(parts[0].endswith(ext) for ext in EXTENSIONS):
                    folders.add(parts[0])
                    
    return sorted(list(folders))


# -------------------------------------------------
# 1. System Images (ديناميكي 100% لأي مجلد جديد)
# -------------------------------------------------
sys_folders = discover_category_folders("system_images")

for folder in sys_folders:
    folder_path = os.path.join("system_images", folder)
    folder_items = []
    
    # 1. الملفات من المجلد المحلي
    if os.path.isdir(folder_path):
        for filename in sorted(os.listdir(folder_path)):
            if not filename.endswith(EXTENSIONS):
                continue
            clean = clean_filename(filename)
            version = clean.split("_")[-2] if "_" in clean else "1.0"
            image_name = clean.split("_")[0]
            img = image_url(image_name) or image_url(folder) or image_url("system_images")

            file_path_url = f"{BASE_URL}/system_images/{folder}/{filename}"
            for asset in release_assets_pool:
                if asset["filename"] == filename:
                    file_path_url = asset["url"]
                    break

            folder_items.append({
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, f"{folder} Firmware Image"),
                "file": file_path_url,
                "image": img
            })

    # 2. الملفات من GitHub Tree (إذا رُفعت على GitHub مباشرة)
    folder_prefix = f"system_images/{folder}/"
    for p in github_tree_paths:
        if p.startswith(folder_prefix):
            filename = os.path.basename(p)
            if filename.endswith(EXTENSIONS) and not any(it["name"] == clean_filename(filename) for it in folder_items):
                clean = clean_filename(filename)
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                image_name = clean.split("_")[0]
                img = image_url(image_name) or image_url(folder) or image_url("system_images")
                folder_items.append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, f"{folder} Firmware Image"),
                    "file": f"{BASE_URL}/{p}",
                    "image": img
                })

    # 3. ربط ملفات Releases بالمجلد تلقائياً بحسب اسم الحافظة
    folder_kw = folder.lower().replace("_", "").replace(" ", "")
    extra_kws = [folder_kw]
    if "octagon" in folder_kw:
        extra_kws.extend(["sf8008", "sx88", "sf4008"])
    elif "novaler" in folder_kw:
        extra_kws.extend(["multibox", "4kpro", "4kse"])
    elif "vu" in folder_kw:
        extra_kws.extend(["vuplus", "vuzero", "uno4k", "duo4k", "zero4k"])

    for asset in release_assets_pool:
        fname = asset["filename"]
        fname_lower = fname.lower()
        if any(k in fname_lower for k in ["skin", "picon", "plugin", "tool", "channel", "settings", "backup"]):
            continue
        if any(kw in fname_lower for kw in extra_kws):
            if not any(it["file"] == asset["url"] for it in folder_items):
                clean = clean_filename(fname)
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                folder_items.append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, f"{folder} Firmware Image"),
                    "file": asset["url"],
                    "image": image_url(clean.split("_")[0]) or image_url(folder) or image_url("system_images")
                })

    data["categories"]["system_images"].append({
        "name": folder.replace("_", " "),
        "items": folder_items
    })


# -------------------------------------------------
# 2. Skins (ديناميكي 100% لأي مجلد جديد)
# -------------------------------------------------
skin_folders = discover_category_folders("skins")

for folder in skin_folders:
    folder_path = os.path.join("skins", folder)
    items = []
    
    # 1. محلياً
    if os.path.isdir(folder_path):
        for filename in sorted(os.listdir(folder_path)):
            if not filename.endswith(EXTENSIONS):
                continue
            clean = clean_filename(filename)
            version = clean.split("_")[-2] if "_" in clean else "1.0"
            display = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
            image_name = display.split("_")[0]

            img = image_url(image_name) or image_url(clean.split("_")[0]) or image_url("skins")

            items.append({
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, folder + " Skin"),
                "file": f"{BASE_URL}/skins/{folder}/{filename}",
                "image": img
            })

    # 2. من GitHub Tree
    folder_prefix = f"skins/{folder}/"
    for p in github_tree_paths:
        if p.startswith(folder_prefix):
            filename = os.path.basename(p)
            if filename.endswith(EXTENSIONS) and not any(it["name"] == clean_filename(filename) for it in items):
                clean = clean_filename(filename)
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                display = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
                image_name = display.split("_")[0]
                img = image_url(image_name) or image_url(clean.split("_")[0]) or image_url("skins")
                items.append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, folder + " Skin"),
                    "file": f"{BASE_URL}/{p}",
                    "image": img
                })

    data["categories"]["skins"].append({
        "name": folder.replace("_", " "),
        "items": items
    })


# -------------------------------------------------
# 3. Picons (البيكونات)
# -------------------------------------------------
picons_dict = {}

for asset in release_assets_pool:
    filename = asset["filename"]
    if "picon" not in filename.lower():
        continue
    clean = clean_filename(filename)
    picons_dict[filename] = {
        "name": clean,
        "version": "1.0",
        "description": old_descriptions.get(clean, ""),
        "file": asset["url"],
        "image": image_url(clean.split("_")[0])
    }

if os.path.isdir("picons"):
    for filename in sorted(os.listdir("picons")):
        if not filename.endswith(EXTENSIONS):
            continue
        clean = clean_filename(filename)
        if filename not in picons_dict:
            picons_dict[filename] = {
                "name": clean,
                "version": "1.0",
                "description": old_descriptions.get(clean, ""),
                "file": f"{BASE_URL}/picons/{filename}",
                "image": image_url(clean.split("_")[0])
            }

for filename in sorted(picons_dict):
    data["categories"]["picons"].append(picons_dict[filename])


# -------------------------------------------------
# 4. Channels & Settings (القنوات)
# -------------------------------------------------
channels_list = []
if os.path.isdir("channels"):
    for filename in sorted(os.listdir("channels")):
        if filename.endswith(EXTENSIONS):
            channels_list.append(filename)

for asset in release_assets_pool:
    fname = asset["filename"]
    lower_f = fname.lower()
    if any(k in lower_f for k in ["skin", "picon", "plugin", "image", "egami", "openatv"]):
        continue
    if any(k in lower_f for k in ["channel", "backup", "settings", "setting", "bouquets", "satellites"]):
        if fname not in channels_list:
            channels_list.append(fname)

for filename in sorted(channels_list):
    clean = clean_filename(filename)
    file_path_url = f"{BASE_URL}/channels/{filename}"
    for asset in release_assets_pool:
        if asset["filename"] == filename:
            file_path_url = asset["url"]
            break

    data["categories"]["channels"].append({
        "name": clean,
        "version": "1.0",
        "description": old_descriptions.get(clean, ""),
        "file": file_path_url,
        "image": image_url(clean.split("_")[0])
    })


# -------------------------------------------------
# 5. Tools (الأدوات)
# -------------------------------------------------
tools_list = []
if os.path.isdir("tools"):
    for filename in sorted(os.listdir("tools")):
        if filename.endswith(EXTENSIONS):
            tools_list.append(filename)

for asset in release_assets_pool:
    fname = asset["filename"]
    lower_f = fname.lower()
    if any(k in lower_f for k in ["skin", "picon", "channel", "image", "settings", "backup"]):
        continue
    if any(k in lower_f for k in ["ncam", "oscam", "tool", "script", "softcam", "emu", "tweaks", "extnumber"]):
        if fname not in tools_list:
            tools_list.append(fname)

for filename in sorted(tools_list):
    clean = clean_filename(filename)
    version = clean.split("_")[-2] if "_" in clean else "1.0"
    image_name = clean.split("_")[0]

    file_path_url = f"{BASE_URL}/tools/{filename}"
    for asset in release_assets_pool:
        if asset["filename"] == filename:
            file_path_url = asset["url"]
            break

    data["categories"]["tools"].append({
        "name": clean,
        "version": version,
        "description": old_descriptions.get(clean, ""),
        "file": file_path_url,
        "image": image_url(image_name)
    })


# -------------------------------------------------
# 6. Plugins (الإضافات)
# -------------------------------------------------
plugins_list = []
if os.path.isdir("plugins"):
    for filename in sorted(os.listdir("plugins")):
        if filename.endswith(EXTENSIONS):
            plugins_list.append(filename)

for asset in release_assets_pool:
    fname = asset["filename"]
    lower_f = fname.lower()
    if any(k in lower_f for k in ["skin", "picon", "channel", "image", "settings", "backup", "ncam", "oscam", "softcam", "script", "egami", "openatv"]):
        continue
    
    if any(k in lower_f for k in ["plugin", "ipa", "timeshift", "audi", "panel", "weather", "tmdb", "subs", "e2player", "multiepg"]):
        if fname not in plugins_list:
            plugins_list.append(fname)

for filename in sorted(plugins_list):
    clean = clean_filename(filename)
    version = clean.split("_")[-2] if "_" in clean else "1.0"
    display = clean.replace("enigma2-plugin-", "")

    file_path_url = f"{BASE_URL}/plugins/{filename}"
    for asset in release_assets_pool:
        if asset["filename"] == filename:
            file_path_url = asset["url"]
            break

    data["categories"]["plugins"].append({
        "name": display,
        "version": version,
        "description": old_descriptions.get(display, ""),
        "file": file_path_url,
        "image": image_url(
            display.split("_")[0]
            .replace("extensions-", "")
            .replace("skins-", "")
            .replace("plugin-", "")
        )
    })


# -------------------------------------------------
# 7. Novaler (قسم نوفالير)
# -------------------------------------------------
novaler_list = []
novaler_folder = "novaler" if os.path.isdir("novaler") else "Novaler" if os.path.isdir("Novaler") else "novaler"

if os.path.isdir("novaler"):
    for filename in sorted(os.listdir("novaler")):
        if filename.endswith(EXTENSIONS):
            novaler_list.append(filename)
elif os.path.isdir("Novaler"):
    for filename in sorted(os.listdir("Novaler")):
        if filename.endswith(EXTENSIONS):
            novaler_list.append(filename)

for asset in release_assets_pool:
    fname = asset["filename"]
    lower_f = fname.lower()
    if any(k in lower_f for k in ["skin", "picon", "channel", "image", "settings", "backup"]):
        continue
    if "novaler" in lower_f or "noflayer" in lower_f:
        if fname not in novaler_list:
            novaler_list.append(fname)

for filename in sorted(novaler_list):
    clean = clean_filename(filename)
    version = clean.split("_")[-2] if "_" in clean else "1.0"
    display = (
        clean.replace("enigma2-plugin-extensions-", "")
        .replace("enigma2-plugin-", "")
        .replace("extensions-", "")
    )
    image_name = display.split("_")[0]

    img = image_url("novaler") or image_url("noflayer") or image_url(image_name)

    file_path_url = f"{BASE_URL}/{novaler_folder}/{filename}"
    for asset in release_assets_pool:
        if asset["filename"] == filename:
            file_path_url = asset["url"]
            break

    data["categories"]["novaler"].append({
        "name": clean,
        "version": version,
        "description": old_descriptions.get(clean, ""),
        "file": file_path_url,
        "image": img
    })


# -------------------------------------------------
# Save JSON
# -------------------------------------------------
os.makedirs("feed", exist_ok=True)

with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("feed/index.json generated successfully. 100% Dynamic - Any new folder will appear automatically.")
