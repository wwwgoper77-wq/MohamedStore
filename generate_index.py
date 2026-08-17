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


# دالة دقيقة لتحديد مطابقة ملف الـ Release لحافظة صور النظام
def match_release_to_system_image_folder(fname_lower, folder_name):
    f_lower = folder_name.lower().replace("_", "").replace(" ", "")

    if any(k in fname_lower for k in ["openbh", "open-bh", "obh", "blackhole", "black_hole"]):
        return f_lower in ["openbh", "blackhole"]
    if "egami" in fname_lower:
        return f_lower == "egami"
    if "openatv" in fname_lower or "atv" in fname_lower:
        return f_lower == "openatv"
    if "pure2" in fname_lower or "pur2" in fname_lower:
        return f_lower == "pure2"
    if "openpli" in fname_lower or "pli" in fname_lower:
        return f_lower == "openpli"
    if "opendroid" in fname_lower or "droid" in fname_lower:
        return f_lower == "opendroid"
    if "openspa" in fname_lower:
        return f_lower == "openspa"
    if "vti" in fname_lower:
        return f_lower == "vti"
    if any(k in fname_lower for k in ["octagon", "sf8008", "sx88", "sf4008"]):
        return f_lower == "octagon"
    if any(k in fname_lower for k in ["vuplus", "vuduo", "vuuno", "vuzero", "vuultimo", "vusolo"]):
        return f_lower == "vuplus"
    if "novaler" in fname_lower or "noflayer" in fname_lower:
        return f_lower in ["novaler", "noflayer"]

    return f_lower in fname_lower


# -------------------------------------------------
# 1. System Images (دمج ومنع تكرار الحافظات)
# -------------------------------------------------
sys_folders_map = {} # لدمج أي حافظات متطابقة بالاسم

if os.path.isdir("system_images"):
    for entry in sorted(os.listdir("system_images")):
        entry_path = os.path.join("system_images", entry)

        if os.path.isdir(entry_path):
            canonical_name = entry
            # التحقق إذا كان الاسم موجوداً بحالة أحرف مختلفة لدمجه
            for existing in sys_folders_map.keys():
                if existing.lower() == entry.lower():
                    canonical_name = existing
                    break

            if canonical_name not in sys_folders_map:
                sys_folders_map[canonical_name] = {"items": [], "seen_files": set()}

            # 1. الملفات من المجلد المحلي
            for filename in sorted(os.listdir(entry_path)):
                if not filename.endswith(EXTENSIONS):
                    continue
                if filename not in sys_folders_map[canonical_name]["seen_files"]:
                    sys_folders_map[canonical_name]["seen_files"].add(filename)
                    clean = clean_filename(filename)
                    version = clean.split("_")[-2] if "_" in clean else "1.0"
                    image_name = clean.split("_")[0]

                    file_path_url = f"{BASE_URL}/system_images/{entry}/{filename}"
                    for asset in release_assets_pool:
                        if asset["filename"] == filename:
                            file_path_url = asset["url"]
                            break

                    sys_folders_map[canonical_name]["items"].append({
                        "name": clean,
                        "version": version,
                        "description": old_descriptions.get(clean, f"{canonical_name} Image"),
                        "file": file_path_url,
                        "image": image_url(image_name) or image_url(canonical_name) or image_url("system_images")
                    })

            # 2. ملفات Releases
            for asset in release_assets_pool:
                fname = asset["filename"]
                fname_lower = fname.lower()
                if any(k in fname_lower for k in ["skin", "picon", "plugin", "tool", "channel", "settings", "ncam", "oscam"]):
                    continue

                if match_release_to_system_image_folder(fname_lower, canonical_name):
                    if fname not in sys_folders_map[canonical_name]["seen_files"]:
                        sys_folders_map[canonical_name]["seen_files"].add(fname)
                        clean = clean_filename(fname)
                        version = clean.split("_")[-2] if "_" in clean else "1.0"
                        sys_folders_map[canonical_name]["items"].append({
                            "name": clean,
                            "version": version,
                            "description": old_descriptions.get(clean, f"{canonical_name} Image"),
                            "file": asset["url"],
                            "image": image_url(clean.split("_")[0]) or image_url(canonical_name) or image_url("system_images")
                        })

for f_name, f_data in sorted(sys_folders_map.items()):
    data["categories"]["system_images"].append({
        "name": f_name,
        "items": f_data["items"]
    })


# -------------------------------------------------
# 2. Skins (دمج ومنع تكرار حافظة All أو أي حافظة أخرى)
# -------------------------------------------------
skin_folders_map = {}

if os.path.isdir("skins"):
    for folder in sorted(os.listdir("skins")):
        folder_path = os.path.join("skins", folder)
        if not os.path.isdir(folder_path):
            continue

        canonical_name = folder
        # دمج All مع all أو أي حالة أحرف مكررة
        for existing in skin_folders_map.keys():
            if existing.lower() == folder.lower():
                canonical_name = existing
                break

        if canonical_name not in skin_folders_map:
            skin_folders_map[canonical_name] = {"items": [], "seen_files": set()}

        # 1. الملفات من داخل المجلد
        for filename in sorted(os.listdir(folder_path)):
            if not filename.endswith(EXTENSIONS):
                continue
            if filename not in skin_folders_map[canonical_name]["seen_files"]:
                skin_folders_map[canonical_name]["seen_files"].add(filename)
                clean = clean_filename(filename)
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                display = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
                image_name = display.split("_")[0]

                file_path_url = f"{BASE_URL}/skins/{folder}/{filename}"
                for asset in release_assets_pool:
                    if asset["filename"] == filename:
                        file_path_url = asset["url"]
                        break

                skin_folders_map[canonical_name]["items"].append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, canonical_name + " Skin"),
                    "file": file_path_url,
                    "image": image_url(image_name) or image_url("skins")
                })

        # 2. الملفات من Releases
        folder_lower = canonical_name.lower().replace("_", "").replace(" ", "")
        for asset in release_assets_pool:
            fname = asset["filename"]
            fname_lower = fname.lower()
            if "skin" in fname_lower and (folder_lower in fname_lower or folder_lower == "all"):
                if fname not in skin_folders_map[canonical_name]["seen_files"]:
                    skin_folders_map[canonical_name]["seen_files"].add(fname)
                    clean = clean_filename(fname)
                    version = clean.split("_")[-2] if "_" in clean else "1.0"
                    display = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
                    image_name = display.split("_")[0]

                    skin_folders_map[canonical_name]["items"].append({
                        "name": clean,
                        "version": version,
                        "description": old_descriptions.get(clean, canonical_name + " Skin"),
                        "file": asset["url"],
                        "image": image_url(image_name) or image_url("skins")
                    })

for f_name, f_data in sorted(skin_folders_map.items()):
    data["categories"]["skins"].append({
        "name": f_name,
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

print("feed/index.json generated successfully. Zero duplicated folders guaranteed.")
