import os
import json

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


# -------------------------------------------------
# Plugins
# -------------------------------------------------

if os.path.isdir("plugins"):

    for filename in sorted(os.listdir("plugins")):

        if not filename.endswith(EXTENSIONS):
            continue

        if filename.endswith(".tar.gz"):
            clean = filename[:-7]
        else:
            clean = os.path.splitext(filename)[0]

        version = clean.split("_")[-2] if "_" in clean else "1.0"

        display = clean.replace("enigma2-plugin-", "")

        image_name = display
        image_name = image_name.replace("extensions-", "")
        image_name = image_name.replace("skins-", "")
        image_name = image_name.split("_")[0]

        data["categories"]["plugins"].append({
            "name": display,
            "version": version,
            "description": old_descriptions.get(display, ""),
            "file": f"{BASE_URL}/plugins/{filename}",
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

if os.path.isdir("tools"):

    for filename in sorted(os.listdir("tools")):

        if not filename.endswith(EXTENSIONS):
            continue

        if filename.endswith(".tar.gz"):
            clean = filename[:-7]
        else:
            clean = os.path.splitext(filename)[0]

        version = clean.split("_")[-2] if "_" in clean else "1.0"

        image_name = clean.split("_")[0]

        data["categories"]["tools"].append({
            "name": clean,
            "version": version,
            "description": old_descriptions.get(clean,""),
            "file": f"{BASE_URL}/tools/{filename}",
            "image": image_url(image_name)
        })


# -------------------------------------------------
# System Images
# -------------------------------------------------

if os.path.isdir("system_images"):

    for filename in sorted(os.listdir("system_images")):

        if not (
            filename.endswith(".zip")
            or filename.endswith(".tar.gz")
            or filename.endswith(".img")
        ):
            continue

        if filename.endswith(".tar.gz"):
            clean = filename[:-7]
        else:
            clean = os.path.splitext(filename)[0]

        version = clean.split("_")[-2] if "_" in clean else "1.0"

        image_name = clean.split("_")[0]

        data["categories"]["system_images"].append({
            "name": clean,
            "version": version,
            "description": old_descriptions.get(clean,""),
            "file": f"{BASE_URL}/system_images/{filename}",
            "image": image_url(image_name)
        })


# Picons
picons_dict = {}

# 1. Read Picons from GitHub Releases
try:
    import urllib.request
    import json
    
    headers = {"User-Agent": "Mozilla/5.0"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("INPUT_GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
        
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/releases",
        headers=headers
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        releases = json.loads(response.read().decode())
        
    for release in releases:
        for asset in release.get("assets", []):
            filename = asset.get("name")
            if filename and filename.endswith(EXTENSIONS):
                if filename.endswith(".tar.gz"):
                    clean = filename[:-7]
                else:
                    clean = os.path.splitext(filename)[0]
                
                # Store or overwrite picons info with GitHub Releases data
                picons_dict[filename] = {
                    "name": clean,
                    "version": "1.0",
                    "description": old_descriptions.get(clean, ""),
                    "file": asset.get("browser_download_url"),
                    "image": image_url(clean.split("_")[0])
                }
except Exception as e:
    print(f"Warning: Could not fetch Picons from GitHub Releases: {e}")

# 2. Read Picons from local picons folder
if os.path.isdir("picons"):
    for filename in sorted(os.listdir("picons")):
        if filename.endswith(EXTENSIONS):
            if filename.endswith(".tar.gz"):
                clean = filename[:-7]
            else:
                clean = os.path.splitext(filename)[0]
                
            # If the file exists in both places, prefer the GitHub Releases download URL.
            if filename not in picons_dict:
                picons_dict[filename] = {
                    "name": clean,
                    "version": "1.0",
                    "description": old_descriptions.get(clean, ""),
                    "file": f"{BASE_URL}/picons/{filename}",
                    "image": image_url(clean.split("_")[0])
                }

# Add all picons sorted by filename
for filename in sorted(picons_dict.keys()):
    data["categories"]["picons"].append(picons_dict[filename])


# Channels
if os.path.isdir("channels"):
    for filename in sorted(os.listdir("channels")):
        if filename.endswith(EXTENSIONS):
            if filename.endswith(".tar.gz"):
                clean = filename[:-7]
            else:
                clean = os.path.splitext(filename)[0]
            data["categories"]["channels"].append({
                "name":clean,
                "version":"1.0",
                "description":old_descriptions.get(clean,""),
                "file":f"{BASE_URL}/channels/{filename}",
                "image":image_url(clean.split("_")[0])
            })

# -------------------------------------------------
# Save JSON
# -------------------------------------------------

os.makedirs("feed", exist_ok=True)

with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("feed/index.json generated successfully.")
