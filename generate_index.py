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
# Global Release Assets Fetcher (لجلب ملفات الـ Release وتوزيعها تلقائياً)
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

# إضافة ملفات البلجِن من الـ Release إن وجدت
for asset in release_assets_pool:
    fname = asset["filename"]
    if "plugin" in fname.lower() or "ipa" in fname.lower() or "timeshift" in fname.lower() or "audi" in fname.lower():
        if fname not in plugins_list:
            plugins_list.append(fname)

for filename in sorted(plugins_list):
    if filename.endswith(".tar.gz"):
        clean = filename[:-7]
    else:
        clean = os.path.splitext(filename)[0]

    version = clean.split("_")[-2] if "_" in clean else "1.0"
    display = clean.replace("enigma2-plugin-", "")

    # التحقق هل الملف محلي أم من الـ Release
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
    if "ncam" in fname.lower() or "oscam" in fname.lower() or "tool" in fname.lower() or "script" in fname.lower():
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
# System Images
# -------------------------------------------------

sys_list = []
if os.path.isdir("system_images"):
    for filename in sorted(os.listdir("system_images")):
        if filename.endswith((".zip", ".tar.gz", ".img", ".nfi")):
            sys_list.append(filename)

for asset in release_assets_pool:
    fname = asset["filename"]
    if any(img_kw in fname.lower() for img_kw in ["egami", "openatv", "blackhole", "vti", "pure2", "image", "vu+"]):
        if fname not in sys_list:
            sys_list.append(fname)

for filename in sorted(sys_list):
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

    data["categories"]["system_images"].append({
        "name": clean,
        "version": version,
        "description": old_descriptions.get(clean,""),
        "file": file_path_url,
        "image": image_url(image_name)
    })


# -------------------------------------------------
# Picons
# -------------------------------------------------

picons_dict = {}

# 1- Read from GitHub Releases Assets Pool
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

# 2- Read local picons folder
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
    if "channel" in fname.lower() or "backup" in fname.lower():
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
