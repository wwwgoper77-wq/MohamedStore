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

# -------------------------------------------------
# 1. جلب الملفات الكبيرة من GitHub Releases
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
                filename = asset.get("name", "")
                if filename.endswith(EXTENSIONS):
                    release_assets_pool.append({
                        "filename": filename,
                        "url": asset.get("browser_download_url", "")
                    })
    print(f"📦 Successfully fetched {len(release_assets_pool)} large assets from GitHub Releases.")
except Exception as e:
    print("⚠️ GitHub Releases Fetch Error:", e)


# جلب شجرة ملفات المستودع لضمان قراءة المجلدات والملفات الخفيفة المرفوعة على الموقع
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


# -------------------------------------------------
# 1. System Images (صور النظام: خفيفة من المجلدات + كبيرة من Releases)
# -------------------------------------------------
SYSTEM_IMAGE_FOLDERS = {
    "Octagon": ["octagon", "sf8008", "sf8008m", "sf8008plus", "sx88", "sf4008"],
    "OpenDroid": ["opendroid", "droid"],
    "Egami": ["egami"],
    "OpenATV": ["openatv", "atv"],
    "Pure2": ["pure2", "pur2"],
    "OpenBH": ["openbh", "blackhole"],
    "OpenPLi": ["openpli", "pli"],
    "OpenSPA": ["openspa"],
    "VTI": ["vti"],
    "Novaler": ["novaler", "noflayer", "multibox", "4kpro", "4kse"],
    "OpenEight": ["openeight"],
    "OpenHDF": ["openhdf"],
    "OpenVision": ["openvision"],
    "OpenViX": ["openvix", "vix"],
    "VuPlus": ["vuplus", "vuzero", "uno4k", "duo4k", "zero4k", "solo4k"],
    "Zgemma": ["zgemma", "h9", "h7", "h11"],
    "Backups": ["backup", "fullbackup"]
}

sys_folders = set(SYSTEM_IMAGE_FOLDERS.keys())
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

    # 1. الملفات الخفيفة من المجلد المحلي
    if os.path.isdir(folder_path):
        for filename in sorted(os.listdir(folder_path)):
            if filename.endswith(EXTENSIONS) and filename not in seen_files:
                seen_files.add(filename)
                clean = clean_filename(filename)
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                image_name = clean.split("_")[0]
                img = image_url(image_name) or image_url(folder) or image_url("system_images")

                file_url = f"{BASE_URL}/system_images/{folder}/{filename}"
                for r in release_assets_pool:
                    if r["filename"] == filename:
                        file_url = r["url"]
                        break

                folder_items.append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, f"{folder} Firmware Image"),
                    "file": file_url,
                    "image": img
                })

    # 2. الملفات الخفيفة من شجرة GitHub
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

                file_url = f"{BASE_URL}/{p}"
                for r in release_assets_pool:
                    if r["filename"] == filename:
                        file_url = r["url"]
                        break

                folder_items.append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, f"{folder} Firmware Image"),
                    "file": file_url,
                    "image": img
                })

    # 3. الملفات الكبيرة من Releases
    keywords = SYSTEM_IMAGE_FOLDERS.get(folder, [folder.lower().replace("_", "").replace(" ", "")])
    for asset in release_assets_pool:
        fname = asset["filename"]
        fname_lower = fname.lower()
        if any(k in fname_lower for k in ["skin", "picon", "plugin", "tool", "channel", "settings", "ncam", "oscam"]):
            continue
        if any(kw in fname_lower for kw in keywords):
            if fname not in seen_files:
                seen_files.add(fname)
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
# 2. Skins (السكينات: خفيفة من المجلدات + كبيرة من Releases)
# -------------------------------------------------
SKIN_IMAGE_FOLDERS = {
    "Egami": ["egami"],
    "OpenATV": ["openatv", "atv"],
    "Pure2": ["pure2"],
    "OpenBH": ["openbh", "blackhole"],
    "OpenPLi": ["openpli", "pli"],
    "OpenSPA": ["openspa"],
    "VTI": ["vti"],
    "Novaler": ["novaler"],
    "FHD_Skins": ["fhd", "1080"]
}

skin_folders = set(SKIN_IMAGE_FOLDERS.keys())
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

                file_url = f"{BASE_URL}/skins/{folder}/{filename}"
                for r in release_assets_pool:
                    if r["filename"] == filename:
                        file_url = r["url"]
                        break

                items.append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, folder + " Skin"),
                    "file": file_url,
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

                file_url = f"{BASE_URL}/{p}"
                for r in release_assets_pool:
                    if r["filename"] == filename:
                        file_url = r["url"]
                        break

                items.append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, folder + " Skin"),
                    "file": file_url,
                    "image": img
                })

    # 3. من Releases
    keywords = SKIN_IMAGE_FOLDERS.get(folder, [folder.lower()])
    for asset in release_assets_pool:
        fname = asset["filename"]
        fname_lower = fname.lower()
        if "skin" in fname_lower and any(kw in fname_lower for kw in keywords):
            if fname not in seen_files:
                seen_files.add(fname)
                clean = clean_filename(fname)
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                display = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
                image_name = display.split("_")[0]
                items.append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, folder + " Skin"),
                    "file": asset["url"],
                    "image": image_url(image_name) or image_url(clean.split("_")[0]) or image_url("skins")
                })

    data["categories"]["skins"].append({
        "name": folder.replace("_", " "),
        "items": items
    })


# -------------------------------------------------
# 3. Picons (البيكونات: خفيفة من المجلد + كبيرة من Releases)
# -------------------------------------------------
picons_dict = {}

for asset in release_assets_pool:
    filename = asset["filename"]
    if "picon" in filename.lower():
        clean = clean_filename(filename)
        picons_dict[filename] = {
            "name": clean,
            "version": "1.0",
            "description": old_descriptions.get(clean, "Picon Pack"),
            "file": asset["url"],
            "image": image_url(clean.split("_")[0]) or image_url("picons")
        }

if os.path.isdir("picons"):
    for filename in os.listdir("picons"):
        if filename.endswith(EXTENSIONS) and filename not in picons_dict:
            clean = clean_filename(filename)
            picons_dict[filename] = {
                "name": clean,
                "version": "1.0",
                "description": old_descriptions.get(clean, "Picon Pack"),
                "file": f"{BASE_URL}/picons/{filename}",
                "image": image_url(clean.split("_")[0]) or image_url("picons")
            }

for filename in sorted(picons_dict.keys()):
    data["categories"]["picons"].append(picons_dict[filename])


# -------------------------------------------------
# 4. Channels & Settings (القنوات)
# -------------------------------------------------
channels_dict = {}

for asset in release_assets_pool:
    fname = asset["filename"]
    lower_f = fname.lower()
    if any(k in lower_f for k in ["skin", "picon", "plugin", "image", "egami", "openatv", "sf8008"]):
        continue
    if any(k in lower_f for k in ["channel", "setting", "bouquet", "satellites"]):
        clean = clean_filename(fname)
        channels_dict[fname] = {
            "name": clean,
            "version": "1.0",
            "description": old_descriptions.get(clean, "Channel Settings"),
            "file": asset["url"],
            "image": image_url(clean.split("_")[0]) or image_url("channels")
        }

if os.path.isdir("channels"):
    for filename in os.listdir("channels"):
        if filename.endswith(EXTENSIONS) and filename not in channels_dict:
            clean = clean_filename(filename)
            channels_dict[filename] = {
                "name": clean,
                "version": "1.0",
                "description": old_descriptions.get(clean, "Channel Settings"),
                "file": f"{BASE_URL}/channels/{filename}",
                "image": image_url(clean.split("_")[0]) or image_url("channels")
            }

for filename in sorted(channels_dict.keys()):
    data["categories"]["channels"].append(channels_dict[filename])


# -------------------------------------------------
# 5. Tools (الأدوات: خفيفة من tools/ + كبيرة من Releases)
# -------------------------------------------------
tools_dict = {}

for asset in release_assets_pool:
    fname = asset["filename"]
    lower_f = fname.lower()
    if any(k in lower_f for k in ["skin", "picon", "channel", "image", "settings", "backup", "sf8008"]):
        continue
    if any(k in lower_f for k in ["ncam", "oscam", "tool", "script", "softcam", "emu", "tweaks", "extnumber"]):
        clean = clean_filename(fname)
        version = clean.split("_")[-2] if "_" in clean else "1.0"
        image_name = clean.split("_")[0]
        tools_dict[fname] = {
            "name": clean,
            "version": version,
            "description": old_descriptions.get(clean, "System Tool"),
            "file": asset["url"],
            "image": image_url(image_name) or image_url("tools")
        }

if os.path.isdir("tools"):
    for filename in os.listdir("tools"):
        if filename.endswith(EXTENSIONS) and filename not in tools_dict:
            clean = clean_filename(filename)
            version = clean.split("_")[-2] if "_" in clean else "1.0"
            image_name = clean.split("_")[0]
            tools_dict[filename] = {
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, "System Tool"),
                "file": f"{BASE_URL}/tools/{filename}",
                "image": image_url(image_name) or image_url("tools")
            }

for filename in sorted(tools_dict.keys()):
    data["categories"]["tools"].append(tools_dict[filename])


# -------------------------------------------------
# 6. Plugins (الإضافات: خفيفة من plugins/ + كبيرة من Releases)
# -------------------------------------------------
plugins_dict = {}

for asset in release_assets_pool:
    fname = asset["filename"]
    lower_f = fname.lower()
    if any(k in lower_f for k in ["skin", "picon", "channel", "image", "settings", "backup", "ncam", "oscam", "softcam", "script", "egami", "openatv", "sf8008"]):
        continue
    if any(k in lower_f for k in ["plugin", "ipa", "timeshift", "audi", "panel", "weather", "tmdb", "subs", "e2player", "multiepg"]):
        clean = clean_filename(fname)
        version = clean.split("_")[-2] if "_" in clean else "1.0"
        display = clean.replace("enigma2-plugin-", "")
        plugins_dict[fname] = {
            "name": display,
            "version": version,
            "description": old_descriptions.get(display, "Plugin Extension"),
            "file": asset["url"],
            "image": image_url(
                display.split("_")[0]
                .replace("extensions-", "")
                .replace("skins-", "")
                .replace("plugin-", "")
            ) or image_url("plugins")
        }

if os.path.isdir("plugins"):
    for filename in os.listdir("plugins"):
        if filename.endswith(EXTENSIONS) and filename not in plugins_dict:
            clean = clean_filename(filename)
            version = clean.split("_")[-2] if "_" in clean else "1.0"
            display = clean.replace("enigma2-plugin-", "")
            plugins_dict[filename] = {
                "name": display,
                "version": version,
                "description": old_descriptions.get(display, "Plugin Extension"),
                "file": f"{BASE_URL}/plugins/{filename}",
                "image": image_url(
                    display.split("_")[0]
                    .replace("extensions-", "")
                    .replace("skins-", "")
                    .replace("plugin-", "")
                ) or image_url("plugins")
            }

for filename in sorted(plugins_dict.keys()):
    data["categories"]["plugins"].append(plugins_dict[filename])


# -------------------------------------------------
# 7. Novaler (قسم نوفالير)
# -------------------------------------------------
novaler_dict = {}

for asset in release_assets_pool:
    fname = asset["filename"]
    lower_f = fname.lower()
    if any(k in lower_f for k in ["skin", "picon", "channel", "image", "settings", "backup"]):
        continue
    if "novaler" in lower_f or "noflayer" in lower_f:
        clean = clean_filename(fname)
        version = clean.split("_")[-2] if "_" in clean else "1.0"
        display = (
            clean.replace("enigma2-plugin-extensions-", "")
            .replace("enigma2-plugin-", "")
            .replace("extensions-", "")
        )
        image_name = display.split("_")[0]
        img = image_url("novaler") or image_url("noflayer") or image_url(image_name)

        novaler_dict[fname] = {
            "name": clean,
            "version": version,
            "description": old_descriptions.get(clean, "Novaler Pack"),
            "file": asset["url"],
            "image": img
        }

for check_dir in ["novaler", "Novaler", "Noflayer", "noflayer"]:
    if os.path.isdir(check_dir):
        for filename in os.listdir(check_dir):
            if filename.endswith(EXTENSIONS) and filename not in novaler_dict:
                clean = clean_filename(filename)
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                display = (
                    clean.replace("enigma2-plugin-extensions-", "")
                    .replace("enigma2-plugin-", "")
                    .replace("extensions-", "")
                )
                image_name = display.split("_")[0]
                img = image_url("novaler") or image_url("noflayer") or image_url(image_name)

                novaler_dict[filename] = {
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, "Novaler Pack"),
                    "file": f"{BASE_URL}/{check_dir}/{filename}",
                    "image": img
                }

for filename in sorted(novaler_dict.keys()):
    data["categories"]["novaler"].append(novaler_dict[filename])


# -------------------------------------------------
# Save JSON
# -------------------------------------------------
os.makedirs("feed", exist_ok=True)

with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

total_items = (
    sum(len(f.get("items", [])) for f in data["categories"]["system_images"]) +
    sum(len(f.get("items", [])) for f in data["categories"]["skins"]) +
    len(data["categories"]["plugins"]) +
    len(data["categories"]["tools"]) +
    len(data["categories"]["picons"]) +
    len(data["categories"]["channels"]) +
    len(data["categories"]["novaler"])
)

print(f"✅ feed/index.json generated successfully!")
print(f"   - Total Packages (Folders + Releases): {total_items}")
