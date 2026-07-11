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

            # Dual-source lookup
            if filename in release_assets:
                file_url = release_assets[filename]
            else:
                file_url = f"{BASE_URL}/skins/{folder}/{filename}"

            items.append({
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, folder + " Skin"),
                "file": file_url,
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

picons_dict = {}

# 1- Process already fetched releases for Picons
try:
    for release in releases:
        for asset in release.get("assets", []):

            filename = asset["name"]

            # فلترة ذكية: التأكد من وجود كلمة picon في اسم الملف لمنع تداخل الإضافات والقنوات الأخرى
            if "picon" not in filename.lower():
                continue

            if not filename.endswith(EXTENSIONS):
                continue

            if filename.endswith(".tar.gz"):
                clean = filename[:-7]
            else:
                clean = os.path.splitext(filename)[0]

            picons_dict[filename] = {
                "name": clean,
                "version": "1.0",
                "description": old_descriptions.get(clean, ""),
                "file": asset["browser_download_url"],
                "image": image_url(clean.split("_")[0])
            }

except Exception as e:
    print("GitHub Releases Picons Error:", e)

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
            # Dual-source lookup
            if filename in release_assets:
                file_url = release_assets[filename]
            else:
                file_url = f"{BASE_URL}/picons/{filename}"

            picons_dict[filename] = {
                "name": clean,
                "version": "1.0",
                "description": old_descriptions.get(clean, ""),
                "file": file_url,
                "image": image_url(clean.split("_")[0])
            }

for filename in sorted(picons_dict):
    data["categories"]["picons"].append(picons_dict[filename])


# -------------------------------------------------
# Channels
# -------------------------------------------------

if os.path.isdir("channels"):
    for filename in sorted(os.listdir("channels")):
        if filename.endswith(EXTENSIONS):
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
