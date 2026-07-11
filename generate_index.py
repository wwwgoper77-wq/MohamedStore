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
    if not os.path.isdir("images"):
        return ""

    prefix = prefix.lower()

    for file in sorted(os.listdir("images")):
        if file.lower().startswith(prefix) and file.lower().endswith(".png"):
            return f"{BASE_URL}/images/{file}"

    return ""


# صيغ ملفات التثبيت المدعومة بالكامل
EXTENSIONS = (".ipk", ".sh", ".deb", ".zip", ".tar.gz", ".tgz", ".tar", ".py", ".tv")

# Intermediate dictionaries to combine API and Local items before building the final JSON
plugins_dict = {}
tools_dict = {}
system_images_dict = {}
picons_dict = {}
channels_dict = {}
skins_dict = {} # Structure: { "FolderName": { "filename": {item_data} } }

# -------------------------------------------------
# 1- Read from GitHub Releases API (All Categories)
# -------------------------------------------------
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

            if not filename.endswith(EXTENSIONS):
                continue

            lower_filename = filename.lower()

            # --- Route to Picons ---
            if "picon" in lower_filename:
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

            # --- Route to Skins (Dynamic Folder via Filename Naming Convention: FolderName--filename.ext) ---
            elif "skin" in lower_filename:
                # Detect folder name using '--' separator, fallback to 'بقية الصور' if not provided
                if "--" in filename:
                    folder_name, actual_filename = filename.split("--", 1)
                else:
                    folder_name, actual_filename = "بقية الصور", filename

                if actual_filename.endswith(".tar.gz"):
                    clean = actual_filename[:-7]
                else:
                    clean = os.path.splitext(actual_filename)[0]

                version = clean.split("_")[-2] if "_" in clean else "1.0"
                image_name = clean.replace("enigma2-plugin-skins-", "").split("_")[0]

                if folder_name not in skins_dict:
                    skins_dict[folder_name] = {}

                skins_dict[folder_name][filename] = {
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, folder_name + " Skin"),
                    "file": asset["browser_download_url"],
                    "image": image_url(image_name)
                }

            # --- Route to Tools ---
            elif "tool" in lower_filename:
                if filename.endswith(".tar.gz"):
                    clean = filename[:-7]
                else:
                    clean = os.path.splitext(filename)[0]

                version = clean.split("_")[-2] if "_" in clean else "1.0"
                image_name = clean.split("_")[0]

                tools_dict[filename] = {
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean,""),
                    "file": asset["browser_download_url"],
                    "image": image_url(image_name)
                }

            # --- Route to System Images ---
            elif any(ext in lower_filename for ext in [".img", "system"]):
                if not (filename.endswith(".zip") or filename.endswith(".tar.gz") or filename.endswith(".img")):
                    continue
                if filename.endswith(".tar.gz"):
                    clean = filename[:-7]
                else:
                    clean = os.path.splitext(filename)[0]

                version = clean.split("_")[-2] if "_" in clean else "1.0"
                image_name = clean.split("_")[0]

                system_images_dict[filename] = {
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean,""),
                    "file": asset["browser_download_url"],
                    "image": image_url(image_name)
                }

            # --- Route to Channels ---
            elif "channel" in lower_filename:
                if filename.endswith(".tar.gz"):
                    clean = filename[:-7]
                else:
                    clean = os.path.splitext(filename)[0]

                channels_dict[filename] = {
                    "name": clean,
                    "version": "1.0",
                    "description": old_descriptions.get(clean,""),
                    "file": asset["browser_download_url"],
                    "image": image_url(clean.split("_")[0])
                }

            # --- Default Fallback: Route to Plugins ---
            else:
                if filename.endswith(".tar.gz"):
                    clean = filename[:-7]
                else:
                    clean = os.path.splitext(filename)[0]

                version = clean.split("_")[-2] if "_" in clean else "1.0"
                display = clean.replace("enigma2-plugin-", "")

                image_name = display.replace("extensions-", "").replace("skins-", "").split("_")[0]

                plugins_dict[filename] = {
                    "name": display,
                    "version": version,
                    "description": old_descriptions.get(display, ""),
                    "file": asset["browser_download_url"],
                    "image": image_url(display.split("_")[0].replace("extensions-", "").replace("skins-", "").replace("plugin-", ""))
                }

except Exception as e:
    print("GitHub Releases Error:", e)


# -------------------------------------------------
# 2- Read Local Folders & Merge
# -------------------------------------------------

# Plugins Local
if os.path.isdir("plugins"):
    for filename in sorted(os.listdir("plugins")):
        if not filename.endswith(EXTENSIONS): continue
        clean = filename[:-7] if filename.endswith(".tar.gz") else os.path.splitext(filename)[0]
        version = clean.split("_")[-2] if "_" in clean else "1.0"
        display = clean.replace("enigma2-plugin-", "")

        if filename not in plugins_dict:
            plugins_dict[filename] = {
                "name": display,
                "version": version,
                "description": old_descriptions.get(display, ""),
                "file": f"{BASE_URL}/plugins/{filename}",
                "image": image_url(display.split("_")[0].replace("extensions-", "").replace("skins-", "").replace("plugin-", ""))
            }

# Skins Local
if os.path.isdir("skins"):
    for folder in sorted(os.listdir("skins")):
        folder_path = os.path.join("skins", folder)
        if not os.path.isdir(folder_path): continue
        
        if folder not in skins_dict:
            skins_dict[folder] = {}

        for filename in sorted(os.listdir(folder_path)):
            if not filename.endswith(EXTENSIONS): continue
            clean = filename[:-7] if filename.endswith(".tar.gz") else os.path.splitext(filename)[0]
            version = clean.split("_")[-2] if "_" in clean else "1.0"
            image_name = clean.replace("enigma2-plugin-skins-", "").split("_")[0]

            if filename not in skins_dict[folder]:
                skins_dict[folder][filename] = {
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, folder + " Skin"),
                    "file": f"{BASE_URL}/skins/{folder}/{filename}",
                    "image": image_url(image_name)
                }

# Tools Local
if os.path.isdir("tools"):
    for filename in sorted(os.listdir("tools")):
        if not filename.endswith(EXTENSIONS): continue
        clean = filename[:-7] if filename.endswith(".tar.gz") else os.path.splitext(filename)[0]
        version = clean.split("_")[-2] if "_" in clean else "1.0"
        image_name = clean.split("_")[0]

        if filename not in tools_dict:
            tools_dict[filename] = {
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean,""),
                "file": f"{BASE_URL}/tools/{filename}",
                "image": image_url(image_name)
            }

# System Images Local
if os.path.isdir("system_images"):
    for filename in sorted(os.listdir("system_images")):
        if not (filename.endswith(".zip") or filename.endswith(".tar.gz") or filename.endswith(".img")): continue
        clean = filename[:-7] if filename.endswith(".tar.gz") else os.path.splitext(filename)[0]
        version = clean.split("_")[-2] if "_" in clean else "1.0"
        image_name = clean.split("_")[0]

        if filename not in system_images_dict:
            system_images_dict[filename] = {
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean,""),
                "file": f"{BASE_URL}/system_images/{filename}",
                "image": image_url(image_name)
            }

# Picons Local
if os.path.isdir("picons"):
    for filename in sorted(os.listdir("picons")):
        if not filename.endswith(EXTENSIONS): continue
        clean = filename[:-7] if filename.endswith(".tar.gz") else os.path.splitext(filename)[0]

        if filename not in picons_dict:
            picons_dict[filename] = {
                "name": clean,
                "version": "1.0",
                "description": old_descriptions.get(clean, ""),
                "file": f"{BASE_URL}/picons/{filename}",
                "image": image_url(clean.split("_")[0])
            }

# Channels Local
if os.path.isdir("channels"):
    for filename in sorted(os.listdir("channels")):
        if not filename.endswith(EXTENSIONS): continue
        clean = filename[:-7] if filename.endswith(".tar.gz") else os.path.splitext(filename)[0]

        if filename not in channels_dict:
            channels_dict[filename] = {
                "name": clean,
                "version": "1.0",
                "description": old_descriptions.get(clean,""),
                "file": f"{BASE_URL}/channels/{filename}",
                "image": image_url(clean.split("_")[0])
            }


# -------------------------------------------------
# 3- Compile data into JSON Structure
# -------------------------------------------------

for filename in sorted(plugins_dict):
    data["categories"]["plugins"].append(plugins_dict[filename])

for filename in sorted(tools_dict):
    data["categories"]["tools"].append(tools_dict[filename])

for filename in sorted(system_images_dict):
    data["categories"]["system_images"].append(system_images_dict[filename])

for filename in sorted(picons_dict):
    data["categories"]["picons"].append(picons_dict[filename])

for filename in sorted(channels_dict):
    data["categories"]["channels"].append(channels_dict[filename])

# Build grouped skins
for folder in sorted(skins_dict):
    folder_items = []
    for filename in sorted(skins_dict[folder]):
        folder_items.append(skins_dict[folder][filename])
    
    if folder_items:
        data["categories"]["skins"].append({
            "name": folder,
            "items": folder_items
        })

# -------------------------------------------------
# Save JSON
# -------------------------------------------------
os.makedirs("feed", exist_ok=True)

with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("feed/index.json generated successfully.")
