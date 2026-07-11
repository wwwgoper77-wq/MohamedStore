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
    Example:
    ipaudiopro.png
    ipaudiopro-icon.png
    ipaudiopro_v2.png
    """
    if not os.path.isdir("images"):
        return ""

    prefix = prefix.lower()

    for file in sorted(os.listdir("images")):
        if file.lower().startswith(prefix) and file.lower().endswith(".png"):
            return f"{BASE_URL}/images/{file}"

    return ""


# صيغ ملفات التثبيت المدعومة بالكامل
EXTENSIONS = (".ipk", ".sh", ".deb", ".zip", ".tar.gz", ".tgz", ".tar", ".py", ".tv")


# -------- Fetch GitHub Releases once --------
releases = []
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
except Exception as e:
    print("GitHub Releases Fetch Error:", e)

# Map asset names to their download URLs
release_assets = {}
try:
    for release in releases:
        for asset in release.get("assets", []):
            filename = asset["name"]
            release_assets[filename] = asset["browser_download_url"]
except Exception as e:
    print("Error mapping releases:", e)


# -------- Map local files to categories for Release Asset Classification --------
local_filename_category = {}

if os.path.isdir("plugins"):
    for fn in os.listdir("plugins"):
        local_filename_category[fn] = "plugins"

if os.path.isdir("skins"):
    for folder in os.listdir("skins"):
        folder_path = os.path.join("skins", folder)
        if os.path.isdir(folder_path):
            for fn in os.listdir(folder_path):
                local_filename_category[fn] = "skins"

if os.path.isdir("tools"):
    for fn in os.listdir("tools"):
        local_filename_category[fn] = "tools"

if os.path.isdir("system_images"):
    for fn in os.listdir("system_images"):
        local_filename_category[fn] = "system_images"

if os.path.isdir("picons"):
    for fn in os.listdir("picons"):
        local_filename_category[fn] = "picons"

if os.path.isdir("channels"):
    for fn in os.listdir("channels"):
        local_filename_category[fn] = "channels"


def classify_release_asset(filename):
    """
    Returns the category name based on the filename characteristics or local folders mapping.
    """
    # First, check if mapped to a category via local folders
    if filename in local_filename_category:
        return local_filename_category[filename]

    fn_lower = filename.lower()

    # 1. Picons
    if "picon" in fn_lower or "220x132" in fn_lower or "100x60" in fn_lower or "400x240" in fn_lower:
        return "picons"

    # 2. Skins
    if "skin" in fn_lower:
        return "skins"

    # 3. Channels
    if any(x in fn_lower for x in ["channel", "setting", "sat", "bouq", "transponder"]):
        return "channels"

    # 4. Plugins
    if "plugin" in fn_lower:
        return "plugins"

    # 5. System Images
    if any(x in fn_lower for x in ["image", "system", "backup", "flash"]) or fn_lower.endswith(".img"):
        return "system_images"

    # Fallback to tools
    return "tools"


# -------------------------------------------------
# Plugins
# -------------------------------------------------

plugin_filenames = set()
if os.path.isdir("plugins"):
    for filename in os.listdir("plugins"):
        if filename.endswith(EXTENSIONS):
            plugin_filenames.add(filename)

# Add Release assets that classify as plugins
for filename in release_assets:
    if filename.endswith(EXTENSIONS):
        if classify_release_asset(filename) == "plugins":
            plugin_filenames.add(filename)

for filename in sorted(plugin_filenames):
    if filename.endswith(".tar.gz"):
        clean = filename[:-7]
    else:
        clean = os.path.splitext(filename)[0]

    version = clean.split("_")[-2] if "_" in clean else "1.0"

    display = clean.replace("enigma2-plugin-", "")

    # Dual-source lookup
    if filename in release_assets:
        file_url = release_assets[filename]
    else:
        file_url = f"{BASE_URL}/plugins/{filename}"

    data["categories"]["plugins"].append({
        "name": display,
        "version": version,
        "description": old_descriptions.get(display, ""),
        "file": file_url,
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

local_skin_folders = {}
if os.path.isdir("skins"):
    for folder in os.listdir("skins"):
        folder_path = os.path.join("skins", folder)
        if os.path.isdir(folder_path):
            for filename in os.listdir(folder_path):
                if filename.endswith(EXTENSIONS):
                    local_skin_folders[filename] = folder

skin_tuples = set()

# 1. From local folders
for filename, folder in local_skin_folders.items():
    skin_tuples.add((folder, filename))

# 2. From Release assets
for filename in release_assets:
    if filename.endswith(EXTENSIONS):
        if classify_release_asset(filename) == "skins":
            if filename in local_skin_folders:
                folder = local_skin_folders[filename]
            else:
                clean_skin_name = filename.replace("enigma2-plugin-skins-", "")
                if "_" in clean_skin_name:
                    folder_name = clean_skin_name.split("_")[0]
                else:
                    if filename.endswith(".tar.gz"):
                        folder_name = clean_skin_name[:-7]
                    else:
                        folder_name = os.path.splitext(clean_skin_name)[0]
                folder = folder_name.capitalize()
            skin_tuples.add((folder, filename))

skins_grouped = {}
for folder, filename in sorted(skin_tuples):
    if folder not in skins_grouped:
        skins_grouped[folder] = []

    if filename.endswith(".tar.gz"):
        clean = filename[:-7]
    else:
        clean = os.path.splitext(filename)[0]

    version = clean.split("_")[-2] if "_" in clean else "1.0"

    image_name = clean.replace("enigma2-plugin-skins-", "")
    image_name = image_name.split("_")[0]

    if filename in release_assets:
        file_url = release_assets[filename]
    else:
        file_url = f"{BASE_URL}/skins/{folder}/{filename}"

    skins_grouped[folder].append({
        "name": clean,
        "version": version,
        "description": old_descriptions.get(clean, folder + " Skin"),
        "file": file_url,
        "image": image_url(image_name)
    })

for folder in sorted(skins_grouped.keys()):
    data["categories"]["skins"].append({
        "name": folder,
        "items": sorted(skins_grouped[folder], key=lambda x: x["name"])
    })


# -------------------------------------------------
# Tools
# -------------------------------------------------

tool_filenames = set()
if os.path.isdir("tools"):
    for filename in os.listdir("tools"):
        if filename.endswith(EXTENSIONS):
            tool_filenames.add(filename)

for filename in release_assets:
    if filename.endswith(EXTENSIONS):
        if classify_release_asset(filename) == "tools":
            tool_filenames.add(filename)

for filename in sorted(tool_filenames):
    if filename.endswith(".tar.gz"):
        clean = filename[:-7]
    else:
        clean = os.path.splitext(filename)[0]

    version = clean.split("_")[-2] if "_" in clean else "1.0"

    image_name = clean.split("_")[0]

    # Dual-source lookup
    if filename in release_assets:
        file_url = release_assets[filename]
    else:
        file_url = f"{BASE_URL}/tools/{filename}"

    data["categories"]["tools"].append({
        "name": clean,
        "version": version,
        "description": old_descriptions.get(clean,""),
        "file": file_url,
        "image": image_url(image_name)
    })


# -------------------------------------------------
# System Images
# -------------------------------------------------

system_image_filenames = set()
if os.path.isdir("system_images"):
    for filename in os.listdir("system_images"):
        if filename.endswith((".zip", ".tar.gz", ".img")):
            system_image_filenames.add(filename)

for filename in release_assets:
    if filename.endswith((".zip", ".tar.gz", ".img")):
        if classify_release_asset(filename) == "system_images":
            system_image_filenames.add(filename)

for filename in sorted(system_image_filenames):
    if filename.endswith(".tar.gz"):
        clean = filename[:-7]
    else:
        clean = os.path.splitext(filename)[0]

    version = clean.split("_")[-2] if "_" in clean else "1.0"

    image_name = clean.split("_")[0]

    # Dual-source lookup
    if filename in release_assets:
        file_url = release_assets[filename]
    else:
        file_url = f"{BASE_URL}/system_images/{filename}"

    data["categories"]["system_images"].append({
        "name": clean,
        "version": version,
        "description": old_descriptions.get(clean,""),
        "file": file_url,
        "image": image_url(image_name)
    })


# -------------------------------------------------
# Picons
# -------------------------------------------------

picon_filenames = set()
if os.path.isdir("picons"):
    for filename in os.listdir("picons"):
        if filename.endswith(EXTENSIONS):
            picon_filenames.add(filename)

for filename in release_assets:
    if filename.endswith(EXTENSIONS):
        if classify_release_asset(filename) == "picons":
            picon_filenames.add(filename)

for filename in sorted(picon_filenames):
    if filename.endswith(".tar.gz"):
        clean = filename[:-7]
    else:
        clean = os.path.splitext(filename)[0]

    # Dual-source lookup
    if filename in release_assets:
        file_url = release_assets[filename]
    else:
        file_url = f"{BASE_URL}/picons/{filename}"

    data["categories"]["picons"].append({
        "name": clean,
        "version": "1.0",
        "description": old_descriptions.get(clean, ""),
        "file": file_url,
        "image": image_url(clean.split("_")[0])
    })


# -------------------------------------------------
# Channels
# -------------------------------------------------

channel_filenames = set()
if os.path.isdir("channels"):
    for filename in os.listdir("channels"):
        if filename.endswith(EXTENSIONS):
            channel_filenames.add(filename)

for filename in release_assets:
    if filename.endswith(EXTENSIONS):
        if classify_release_asset(filename) == "channels":
            channel_filenames.add(filename)

for filename in sorted(channel_filenames):
    if filename.endswith(".tar.gz"):
        clean = filename[:-7]
    else:
        clean = os.path.splitext(filename)[0]

    # Dual-source lookup
    if filename in release_assets:
        file_url = release_assets[filename]
    else:
        file_url = f"{BASE_URL}/channels/{filename}"

    data["categories"]["channels"].append({
        "name": clean,
        "version": "1.0",
        "description": old_descriptions.get(clean,""),
        "file": file_url,
        "image": image_url(clean.split("_")[0])
    })


# -------------------------------------------------
# Save JSON
# -------------------------------------------------

os.makedirs("feed", exist_ok=True)

with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("feed/index.json generated successfully.")
