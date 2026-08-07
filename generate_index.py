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
        "channels": []
    }
}

# -------- Preserve old descriptions --------
old_descriptions = {}

try:
    if os.path.exists("feed/index.json"):
        with open("feed/index.json","r",encoding="utf-8") as f:
            old = json.load(f)

        for cat, items in old.get("categories", {}).items():
            if isinstance(items, list):
                for entry in items:
                    if isinstance(entry, dict) and "items" in entry and isinstance(entry["items"], list):
                        for it in entry["items"]:
                            if isinstance(it, dict):
                                old_descriptions[it.get("name","")] = it.get("description","")
                    elif isinstance(entry, dict):
                        old_descriptions[entry.get("name","")] = entry.get("description","")
except:
    pass


def image_url(prefix):
    """
    Search automatically for an image beginning with prefix.
    """
    if not os.path.isdir("images"):
        return ""

    prefix = prefix.lower()

    for file in sorted(os.listdir("images")):
        if file.lower().startswith(prefix) and file.lower().endswith(".png"):
            return f"{BASE_URL}/images/{file}"

    return ""


# صيغ ملفات التثبيت المدعومة بالكامل
EXTENSIONS = (".ipk", ".sh", ".deb", ".zip", ".tar.gz", ".tgz", ".tar", ".py", ".tv", ".img", ".nfi")


# -------------------------------------------------
# Global Release Assets Fetcher
# -------------------------------------------------

release_assets_pool = []
try:
    api = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/releases"
    req = urllib.request.Request(
        api,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.github+json"
        }
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
    print("GitHub Releases Fetch Error:", e)


# -------------------------------------------------
# Plugins
# -------------------------------------------------

plugins_list = []
if os.path.isdir("plugins"):
    for filename in sorted(os.listdir("plugins")):
        if filename.endswith(EXTENSIONS):
            plugins_list.append(filename)

for asset in release_assets_pool:
    fname = asset["filename"]
    lower_f = fname.lower()
    # استبعاد السكينات والصور من البلجِنات
    if "skin" in lower_f or "picon" in lower_f or "channel" in lower_f:
        continue
    if "plugin" in lower_f or "ipa" in lower_f or "timeshift" in lower_f or "audi" in lower_f or "panel" in lower_f:
        if fname not in plugins_list:
            plugins_list.append(fname)

for filename in sorted(plugins_list):
    if filename.endswith(".tar.gz"):
        clean = filename[:-7]
    else:
        clean = os.path.splitext(filename)[0]

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
# Skins
# -------------------------------------------------

if os.path.isdir("skins"):
    for folder in sorted(os.listdir("skins")):
        folder_path = os.path.join("skins", folder)
        if not os.path.isdir(folder_path):
            continue

        items = []
        for filename in sorted(os.listdir(folder_path)):
            if not filename.endswith(EXTENSIONS):
                continue

            if filename.endswith(".tar.gz"):
                clean = filename[:-7]
            else:
                clean = os.path.splitext(filename)[0]

            version = clean.split("_")[-2] if "_" in clean else "1.0"
            image_name = clean.replace("enigma2-plugin-skins-", "")
            image_name = image_name.split("_")[0]

            items.append({
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, folder + " Skin"),
                "file": f"{BASE_URL}/skins/{folder}/{filename}",
                "image": image_url(image_name)
            })

        data["categories"]["skins"].append({
            "name": folder,
            "items": items
        })


# -------------------------------------------------
# Tools
# -------------------------------------------------

tools_list = []
if os.path.isdir("tools"):
    for filename in sorted(os.listdir("tools")):
        if filename.endswith(EXTENSIONS):
            tools_list.append(filename)

for asset in release_assets_pool:
    fname = asset["filename"]
    lower_f = fname.lower()
    if "skin" in lower_f or "picon" in lower_f or "channel" in lower_f or "image" in lower_f:
        continue
    if "ncam" in lower_f or "oscam" in lower_f or "tool" in lower_f or "script" in lower_f or "softcam" in lower_f:
        if fname not in tools_list:
            tools_list.append(fname)

for filename in sorted(tools_list):
    if filename.endswith(".tar.gz"):
        clean = filename[:-7]
    else:
        clean = os.path.splitext(filename)[0]

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
        "description": old_descriptions.get(clean,""),
        "file": file_path_url,
        "image": image_url(image_name)
    })


# -------------------------------------------------
# System Images (دعم المجلدات الفرعية للأجهزة والصور مثل OpenATV, EGAMI, إلخ)
# -------------------------------------------------

sys_folders = {}
flat_sys_items = []

if os.path.isdir("system_images"):
    # 1. فحص المجلدات الفرعية داخل system_images
    for entry in sorted(os.listdir("system_images")):
        entry_path = os.path.join("system_images", entry)
        if os.path.isdir(entry_path):
            folder = entry
            items = []
            for filename in sorted(os.listdir(entry_path)):
                if filename.endswith((".zip", ".tar.gz", ".img", ".nfi")):
                    if filename.endswith(".tar.gz"):
                        clean = filename[:-7]
                    else:
                        clean = os.path.splitext(filename)[0]

                    version = clean.split("_")[-2] if "_" in clean else "1.0"
                    image_name = clean.split("_")[0]

                    file_path_url = f"{BASE_URL}/system_images/{folder}/{filename}"
                    for asset in release_assets_pool:
                        if asset["filename"] == filename:
                            file_path_url = asset["url"]
                            break

                    items.append({
                        "name": clean,
                        "version": version,
                        "description": old_descriptions.get(clean, f"{folder} System Image"),
                        "file": file_path_url,
                        "image": image_url(image_name)
                    })

            sys_folders[folder] = items

        elif os.path.isfile(entry_path) and entry.endswith((".zip", ".tar.gz", ".img", ".nfi")):
            filename = entry
            if filename.endswith(".tar.gz"):
                clean = filename[:-7]
            else:
                clean = os.path.splitext(filename)[0]

            version = clean.split("_")[-2] if "_" in clean else "1.0"
            image_name = clean.split("_")[0]

            file_path_url = f"{BASE_URL}/system_images/{filename}"
            for asset in release_assets_pool:
                if asset["filename"] == filename:
                    file_path_url = asset["url"]
                    break

            flat_sys_items.append({
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, ""),
                "file": file_path_url,
                "image": image_url(image_name)
            })

# 2. فحص GitHub Releases المتاحة وصورة النظام
for asset in release_assets_pool:
    fname = asset["filename"]
    lower_f = fname.lower()
    if "skin" in lower_f or "picon" in lower_f or "plugin" in lower_f or "tool" in lower_f:
        continue
    
    if any(img_kw in lower_f for img_kw in ["egami", "openatv", "blackhole", "vti", "pure2", "openpli", "openblack", "vu+"]):
        if fname.endswith((".zip", ".tar.gz", ".img", ".nfi")):
            if fname.endswith(".tar.gz"):
                clean = fname[:-7]
            else:
                clean = os.path.splitext(fname)[0]

            added = False
            for folder, f_items in sys_folders.items():
                if any(it["name"] == clean for it in f_items):
                    added = True
                    break
            if not added and any(it["name"] == clean for it in flat_sys_items):
                added = True

            if not added:
                target_folder = None
                for folder in sys_folders:
                    if folder.lower() in lower_f:
                        target_folder = folder
                        break
                
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                image_name = clean.split("_")[0]
                item_obj = {
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, ""),
                    "file": asset["url"],
                    "image": image_url(image_name)
                }

                if target_folder:
                    sys_folders[target_folder].append(item_obj)
                else:
                    flat_sys_items.append(item_obj)

for folder in sorted(sys_folders.keys()):
    if sys_folders[folder]:
        data["categories"]["system_images"].append({
            "name": folder,
            "items": sys_folders[folder]
        })

for item in flat_sys_items:
    data["categories"]["system_images"].append(item)


# -------------------------------------------------
# Picons
# -------------------------------------------------

picons_dict = {}

for asset in release_assets_pool:
    filename = asset["filename"]
    if "picon" not in filename.lower():
        continue

    if filename.endswith(".tar.gz"):
        clean = filename[:-7]
    else:
        clean = os.path.splitext(filename)[0]

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

        if filename.endswith(".tar.gz"):
            clean = filename[:-7]
        else:
            clean = os.path.splitext(filename)[0]

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
# Channels
# -------------------------------------------------

channels_list = []
if os.path.isdir("channels"):
    for filename in sorted(os.listdir("channels")):
        if filename.endswith(EXTENSIONS):
            channels_list.append(filename)

for asset in release_assets_pool:
    fname = asset["filename"]
    lower_f = fname.lower()
    if "skin" in lower_f or "picon" in lower_f or "plugin" in lower_f:
        continue
    if "channel" in lower_f or "backup" in lower_f or "settings" in lower_f:
        if fname not in channels_list:
            channels_list.append(fname)

for filename in sorted(channels_list):
    if filename.endswith(".tar.gz"):
        clean = filename[:-7]
    else:
        clean = os.path.splitext(filename)[0]

    file_path_url = f"{BASE_URL}/channels/{filename}"
    for asset in release_assets_pool:
        if asset["filename"] == filename:
            file_path_url = asset["url"]
            break

    data["categories"]["channels"].append({
        "name": clean,
        "version": "1.0",
        "description": old_descriptions.get(clean,""),
        "file": file_path_url,
        "image": image_url(clean.split("_")[0])
    })


# -------------------------------------------------
# Save JSON
# -------------------------------------------------

os.makedirs("feed", exist_ok=True)

with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("feed/index.json generated successfully.")
