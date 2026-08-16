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
    # 1. البحث في مجلد Icons أولاً
    if os.path.isdir("Icons"):
        for file in sorted(os.listdir("Icons")):
            if file.lower().startswith(prefix) and file.lower().endswith(".png"):
                return f"{BASE_URL}/Icons/{file}"
    # 2. البحث في مجلد images ثانياً إذا لم توجد في Icons
    if os.path.isdir("images"):
        for file in sorted(os.listdir("images")):
            if file.lower().startswith(prefix) and file.lower().endswith(".png"):
                return f"{BASE_URL}/images/{file}"
    return ""


# صيغ ملفات التثبيت والصور العامة
EXTENSIONS = (".ipk", ".sh", ".deb", ".zip", ".tar.gz", ".tgz", ".tar", ".py", ".tv", ".img", ".nfi", ".tar.xz", ".bin")


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


# دالة مساعدة لتنظيف اسم الملف وإزالة الامتدادات المركبة
def clean_filename(filename):
    if filename.endswith(".tar.gz"):
        return filename[:-7]
    elif filename.endswith(".tar.xz"):
        return filename[:-7]
    else:
        return os.path.splitext(filename)[0]


# -------------------------------------------------
# 1. System Images (صور النظام - حسب المجلد الحقيقي 100%)
# -------------------------------------------------
if os.path.isdir("system_images"):
    for folder in sorted(os.listdir("system_images")):
        folder_path = os.path.join("system_images", folder)
        
        # إذا كان مجلداً (مثل OpenDroid, Egami, OpenATV ...)
        if os.path.isdir(folder_path):
            folder_items = []
            
            # قراءة الملفات من المجلد المحلي
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

            # فحص إذا كان هناك ملفات في Releases تخص هذا المجلد
            folder_lower = folder.lower().replace("_", "").replace(" ", "")
            for asset in release_assets_pool:
                fname = asset["filename"]
                fname_lower = fname.lower()
                if any(k in fname_lower for k in ["skin", "picon", "plugin", "tool", "channel", "settings", "backup"]):
                    continue
                if folder_lower in fname_lower:
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
            
            # إذا كان المجلد فارغاً نعرض Coming Soon
            if not folder_items:
                folder_items.append({
                    "name": f"{folder.replace('_', ' ')} (Coming Soon)",
                    "version": "1.0",
                    "description": f"No firmware images uploaded yet for {folder.replace('_', ' ')}.",
                    "file": "",
                    "image": image_url(folder) or image_url("system_images")
                })

            data["categories"]["system_images"].append({
                "name": folder.replace("_", " "),
                "items": folder_items
            })
        
        # إذا كان ملف صورة موضوع مباشرة في الجذر
        elif folder.endswith(EXTENSIONS):
            filename = folder
            clean = clean_filename(filename)
            version = clean.split("_")[-2] if "_" in clean else "1.0"
            image_name = clean.split("_")[0]

            file_path_url = f"{BASE_URL}/system_images/{filename}"
            for asset in release_assets_pool:
                if asset["filename"] == filename:
                    file_path_url = asset["url"]
                    break

            data["categories"]["system_images"].append({
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, "Enigma2 Firmware Image"),
                "file": file_path_url,
                "image": image_url(image_name) or image_url("system_images")
            })


# -------------------------------------------------
# 2. Skins (السكينات)
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

        if not items:
            items.append({
                "name": f"{folder.replace('_', ' ')} (Coming Soon)",
                "version": "1.0",
                "description": f"No skins uploaded yet for {folder.replace('_', ' ')}.",
                "file": "",
                "image": image_url(folder) or image_url("skins")
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
# 4. Channels & Settings (القنوات والملفات المفضلة)
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
# 5. Tools (الأدوات والايميو والسكربتات)
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
# 6. Plugins (الإضافات العامة)
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

print("feed/index.json generated successfully. Pure folder-based mapping active (no other images).")
