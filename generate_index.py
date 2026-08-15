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
        with open("feed/index.json","r",encoding="utf-8") as f:
            old = json.load(f)

        for cat, items in old.get("categories", {}).items():
            if cat == "skins":
                for folder in items:
                    for it in folder.get("items", []):
                        old_descriptions[it.get("name","")] = it.get("description","")
            else:
                for it in items:
                    old_descriptions[it.get("name","")] = it.get("description","")
except:
    pass


def image_url(prefix):
    if not os.path.isdir("images"):
        return ""
    prefix = prefix.lower()
    for file in sorted(os.listdir("images")):
        if file.lower().startswith(prefix) and file.lower().endswith(".png"):
            return f"{BASE_URL}/images/{file}"
    return ""


# صيغ ملفات التثبيت العامة
EXTENSIONS = (".ipk", ".sh", ".deb", ".zip", ".tar.gz", ".tgz", ".tar", ".py", ".tv", ".img", ".nfi", ".tar.xz")


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
# 1. System Images (صور النظام حصراً)
# -------------------------------------------------
sys_list = []
if os.path.isdir("system_images"):
    for filename in sorted(os.listdir("system_images")):
        if filename.endswith((".zip", ".tar.gz", ".img", ".nfi", ".tar.xz")):
            sys_list.append(filename)

for asset in release_assets_pool:
    fname = asset["filename"]
    lower_f = fname.lower()
    # استبعاد أي شيء ليس صورة نظام
    if any(k in lower_f for k in ["skin", "picon", "plugin", "tool", "channel", "settings", "backup", "ncam", "oscam", "softcam", "script"]):
        continue
    # قبول ملفات الصور
    if any(img_kw in lower_f for img_kw in ["egami", "openatv", "blackhole", "vti", "pure2", "openpli", "openblack", "vu+", "image", "firmware", "rootfs"]):
        if fname not in sys_list:
            sys_list.append(fname)

for filename in sorted(sys_list):
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
        "description": old_descriptions.get(clean,""),
        "file": file_path_url,
        "image": image_url(image_name)
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
            image_name = clean.replace("enigma2-plugin-skins-", "").split("_")[0]

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
        "description": old_descriptions.get(clean,""),
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
        "description": old_descriptions.get(clean,""),
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
    # استبعاد أي شيء ينتمي للأقسام المذكورة أعلاه بصرامة
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
    image_name = clean.split("_")[0]

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
        "image": image_url(image_name)
    })


# -------------------------------------------------
# Save JSON
# -------------------------------------------------
os.makedirs("feed", exist_ok=True)

with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("feed/index.json generated successfully.")
