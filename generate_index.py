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
            if cat in ["skins", "system_images"]:
                for folder in items:
                    if isinstance(folder, dict) and "items" in folder:
                        for it in folder.get("items", []):
                            old_descriptions[it.get("name", "")] = it.get("description", "")
                    elif isinstance(folder, dict):
                        old_descriptions[folder.get("name", "")] = folder.get("description", "")
            else:
                for it in items:
                    old_descriptions[it.get("name", "")] = it.get("description", "")
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


# صيغ ملفات التثبيت العامة
EXTENSIONS = (".ipk", ".sh", ".deb", ".zip", ".tar.gz", ".tgz", ".tar", ".py", ".tv", ".img", ".nfi", ".tar.xz", ".bin")


# -------------------------------------------------
# جلب ملفات Releases
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
except Exception as e:
    print("GitHub Releases Fetch Error:", e)


def clean_filename(filename):
    if filename.endswith(".tar.gz"):
        return filename[:-7]
    elif filename.endswith(".tar.xz"):
        return filename[:-7]
    else:
        return os.path.splitext(filename)[0]


# -------------------------------------------------
# 1. System Images
# -------------------------------------------------
sys_folders_map = {}

if os.path.isdir("system_images"):
    for entry in sorted(os.listdir("system_images")):
        entry_path = os.path.join("system_images", entry)

        if os.path.isdir(entry_path):
            key = entry.lower()
            if key not in sys_folders_map:
                sys_folders_map[key] = {
                    "display_name": entry,
                    "items": [],
                    "seen_files": set()
                }

            # الملفات المحلية
            for filename in sorted(os.listdir(entry_path)):
                if not filename.endswith(EXTENSIONS):
                    continue
                if filename not in sys_folders_map[key]["seen_files"]:
                    sys_folders_map[key]["seen_files"].add(filename)
                    clean = clean_filename(filename)
                    version = clean.split("_")[-2] if "_" in clean else "1.0"
                    image_name = clean.split("_")[0]

                    file_path_url = f"{BASE_URL}/system_images/{entry}/{filename}"
                    for asset in release_assets_pool:
                        if asset["filename"] == filename:
                            file_path_url = asset["url"]
                            break

                    sys_folders_map[key]["items"].append({
                        "name": clean,
                        "version": version,
                        "description": old_descriptions.get(clean, f"{sys_folders_map[key]['display_name']} Image"),
                        "file": file_path_url,
                        "image": image_url(image_name) or image_url(sys_folders_map[key]["display_name"]) or image_url("system_images")
                    })

for key, f_data in sorted(sys_folders_map.items()):
    data["categories"]["system_images"].append({
        "name": f_data["display_name"],
        "items": f_data["items"]
    })


# -------------------------------------------------
# 2. Skins (دمج قاطع لأي مجلدات متشابهة مثل All و all)
# -------------------------------------------------
skin_folders_map = {}

if os.path.isdir("skins"):
    for folder in sorted(os.listdir("skins")):
        folder_path = os.path.join("skins", folder)
        if not os.path.isdir(folder_path):
            continue

        # توحيد المفتاح ليكون بالأحرف الصغيرة (all = All)
        key = folder.lower()

        if key not in skin_folders_map:
            skin_folders_map[key] = {
                "display_name": "All" if key == "all" else folder,
                "items": [],
                "seen_files": set()
            }

        # 1. الملفات من داخل المجلد
        for filename in sorted(os.listdir(folder_path)):
            if not filename.endswith(EXTENSIONS):
                continue
            if filename not in skin_folders_map[key]["seen_files"]:
                skin_folders_map[key]["seen_files"].add(filename)
                clean = clean_filename(filename)
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                display = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
                image_name = display.split("_")[0]

                file_path_url = f"{BASE_URL}/skins/{folder}/{filename}"
                for asset in release_assets_pool:
                    if asset["filename"] == filename:
                        file_path_url = asset["url"]
                        break

                skin_folders_map[key]["items"].append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, skin_folders_map[key]["display_name"] + " Skin"),
                    "file": file_path_url,
                    "image": image_url(image_name) or image_url("skins")
                })

        # 2. ملفات Releases
        for asset in release_assets_pool:
            fname = asset["filename"]
            fname_lower = fname.lower()
            if "skin" in fname_lower and (key in fname_lower or key == "all"):
                if fname not in skin_folders_map[key]["seen_files"]:
                    skin_folders_map[key]["seen_files"].add(fname)
                    clean = clean_filename(fname)
                    version = clean.split("_")[-2] if "_" in clean else "1.0"
                    display = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
                    image_name = display.split("_")[0]

                    skin_folders_map[key]["items"].append({
                        "name": clean,
                        "version": version,
                        "description": old_descriptions.get(clean, skin_folders_map[key]["display_name"] + " Skin"),
                        "file": asset["url"],
                        "image": image_url(image_name) or image_url("skins")
                    })

for key, f_data in sorted(skin_folders_map.items()):
    data["categories"]["skins"].append({
        "name": f_data["display_name"],
        "items": f_data["items"]
    })


# -------------------------------------------------
# 3. Picons (البيكونات)
# -------------------------------------------------
picons_list = []
seen_picons = set()

if os.path.isdir("picons"):
    for filename in sorted(os.listdir("picons")):
        if filename.endswith(EXTENSIONS):
            seen_picons.add(filename)
            clean = clean_filename(filename)
            file_url = f"{BASE_URL}/picons/{filename}"
            for asset in release_assets_pool:
                if asset["filename"] == filename:
                    file_url = asset["url"]
                    break
            picons_list.append({
                "name": clean,
                "version": "1.0",
                "description": old_descriptions.get(clean, ""),
                "file": file_url,
                "image": image_url(clean.split("_")[0]) or image_url("picons")
            })

for asset in release_assets_pool:
    fname = asset["filename"]
    if "picon" in fname.lower() and fname not in seen_picons:
        seen_picons.add(fname)
        clean = clean_filename(fname)
        picons_list.append({
            "name": clean,
            "version": "1.0",
            "description": old_descriptions.get(clean, ""),
            "file": asset["url"],
            "image": image_url(clean.split("_")[0]) or image_url("picons")
        })

data["categories"]["picons"] = picons_list


# -------------------------------------------------
# 4. Channels & Settings (القنوات)
# -------------------------------------------------
channels_list = []
seen_channels = set()

if os.path.isdir("channels"):
    for filename in sorted(os.listdir("channels")):
        if filename.endswith(EXTENSIONS):
            seen_channels.add(filename)
            clean = clean_filename(filename)
            file_url = f"{BASE_URL}/channels/{filename}"
            for asset in release_assets_pool:
                if asset["filename"] == filename:
                    file_url = asset["url"]
                    break
            channels_list.append({
                "name": clean,
                "version": "1.0",
                "description": old_descriptions.get(clean, ""),
                "file": file_url,
                "image": image_url(clean.split("_")[0]) or image_url("channels")
            })

for asset in release_assets_pool:
    fname = asset["filename"]
    fname_lower = fname.lower()
    if any(k in fname_lower for k in ["skin", "picon", "plugin", "image", "egami", "openatv", "sf8008", "openbh", "vu"]):
        continue
    if any(k in fname_lower for k in ["channel", "setting", "bouquet", "satellites"]) and fname not in seen_channels:
        seen_channels.add(fname)
        clean = clean_filename(fname)
        channels_list.append({
            "name": clean,
            "version": "1.0",
            "description": old_descriptions.get(clean, ""),
            "file": asset["url"],
            "image": image_url(clean.split("_")[0]) or image_url("channels")
        })

data["categories"]["channels"] = channels_list


# -------------------------------------------------
# 5. Tools (الأدوات)
# -------------------------------------------------
tools_list = []
seen_tools = set()

if os.path.isdir("tools"):
    for filename in sorted(os.listdir("tools")):
        if filename.endswith(EXTENSIONS):
            seen_tools.add(filename)
            clean = clean_filename(filename)
            version = clean.split("_")[-2] if "_" in clean else "1.0"
            image_name = clean.split("_")[0]
            file_url = f"{BASE_URL}/tools/{filename}"
            for asset in release_assets_pool:
                if asset["filename"] == filename:
                    file_url = asset["url"]
                    break
            tools_list.append({
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, ""),
                "file": file_url,
                "image": image_url(image_name) or image_url("tools")
            })

for asset in release_assets_pool:
    fname = asset["filename"]
    fname_lower = fname.lower()
    if any(k in fname_lower for k in ["skin", "picon", "channel", "image", "settings", "backup", "sf8008", "openbh", "egami", "vu"]):
        continue
    if any(k in fname_lower for k in ["ncam", "oscam", "tool", "script", "softcam", "emu", "tweaks", "extnumber"]) and fname not in seen_tools:
        seen_tools.add(fname)
        clean = clean_filename(fname)
        version = clean.split("_")[-2] if "_" in clean else "1.0"
        image_name = clean.split("_")[0]
        tools_list.append({
            "name": clean,
            "version": version,
            "description": old_descriptions.get(clean, ""),
            "file": asset["url"],
            "image": image_url(image_name) or image_url("tools")
        })

data["categories"]["tools"] = tools_list


# -------------------------------------------------
# 6. Plugins (الإضافات)
# -------------------------------------------------
plugins_list = []
seen_plugins = set()

if os.path.isdir("plugins"):
    for filename in sorted(os.listdir("plugins")):
        if filename.endswith(EXTENSIONS):
            seen_plugins.add(filename)
            clean = clean_filename(filename)
            version = clean.split("_")[-2] if "_" in clean else "1.0"
            display = clean.replace("enigma2-plugin-", "")
            file_url = f"{BASE_URL}/plugins/{filename}"
            for asset in release_assets_pool:
                if asset["filename"] == filename:
                    file_url = asset["url"]
                    break
            plugins_list.append({
                "name": display,
                "version": version,
                "description": old_descriptions.get(display, ""),
                "file": file_url,
                "image": image_url(
                    display.split("_")[0]
                    .replace("extensions-", "")
                    .replace("skins-", "")
                    .replace("plugin-", "")
                ) or image_url("plugins")
            })

for asset in release_assets_pool:
    fname = asset["filename"]
    fname_lower = fname.lower()
    if any(k in fname_lower for k in ["skin", "picon", "channel", "image", "settings", "backup", "ncam", "oscam", "softcam", "script", "egami", "openatv", "sf8008", "openbh", "vu"]):
        continue
    if any(k in fname_lower for k in ["plugin", "ipa", "timeshift", "audi", "panel", "weather", "tmdb", "subs", "e2player", "multiepg"]) and fname not in seen_plugins:
        seen_plugins.add(fname)
        clean = clean_filename(fname)
        version = clean.split("_")[-2] if "_" in clean else "1.0"
        display = clean.replace("enigma2-plugin-", "")
        plugins_list.append({
            "name": display,
            "version": version,
            "description": old_descriptions.get(display, ""),
            "file": asset["url"],
            "image": image_url(
                display.split("_")[0]
                .replace("extensions-", "")
                .replace("skins-", "")
                .replace("plugin-", "")
            ) or image_url("plugins")
        })

data["categories"]["plugins"] = plugins_list


# -------------------------------------------------
# 7. Novaler (قسم نوفالير)
# -------------------------------------------------
novaler_list = []
seen_novaler = set()
novaler_folder = "novaler" if os.path.isdir("novaler") else "Novaler" if os.path.isdir("Novaler") else "Noflayer" if os.path.isdir("Noflayer") else "noflayer"

if os.path.isdir(novaler_folder):
    for filename in sorted(os.listdir(novaler_folder)):
        if filename.endswith(EXTENSIONS):
            seen_novaler.add(filename)
            clean = clean_filename(filename)
            version = clean.split("_")[-2] if "_" in clean else "1.0"
            display = (
                clean.replace("enigma2-plugin-extensions-", "")
                .replace("enigma2-plugin-", "")
                .replace("extensions-", "")
            )
            image_name = display.split("_")[0]
            img = image_url("novaler") or image_url("noflayer") or image_url(image_name)

            file_url = f"{BASE_URL}/{novaler_folder}/{filename}"
            for asset in release_assets_pool:
                if asset["filename"] == filename:
                    file_url = asset["url"]
                    break

            novaler_list.append({
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, ""),
                "file": file_url,
                "image": img
            })

for asset in release_assets_pool:
    fname = asset["filename"]
    fname_lower = fname.lower()
    if any(k in fname_lower for k in ["skin", "picon", "channel", "settings", "backup", "openbh", "blackhole", "egami", "openatv", "pure2", "openpli", "vu"]):
        continue
    if ("novaler" in fname_lower or "noflayer" in fname_lower) and fname not in seen_novaler:
        seen_novaler.add(fname)
        clean = clean_filename(fname)
        version = clean.split("_")[-2] if "_" in clean else "1.0"
        display = (
            clean.replace("enigma2-plugin-extensions-", "")
            .replace("enigma2-plugin-", "")
            .replace("extensions-", "")
        )
        image_name = display.split("_")[0]
        img = image_url("novaler") or image_url("noflayer") or image_url(image_name)
        novaler_list.append({
            "name": clean,
            "version": version,
            "description": old_descriptions.get(clean, ""),
            "file": asset["url"],
            "image": img
        })

data["categories"]["novaler"] = novaler_list


# -------------------------------------------------
# Save JSON
# -------------------------------------------------
os.makedirs("feed", exist_ok=True)

with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("feed/index.json generated successfully. All duplicate skins merged into single 'All' folder.")
