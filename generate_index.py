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
        "system_images": []
    }
}


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


# -------------------------------------------------
# Plugins
# -------------------------------------------------

if os.path.isdir("plugins"):

    for filename in sorted(os.listdir("plugins")):

        if not filename.endswith(".ipk"):
            continue

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
            "description": "",
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

            if not filename.endswith(".ipk"):
                continue

            clean = os.path.splitext(filename)[0]

            version = clean.split("_")[-2] if "_" in clean else "1.0"

            image_name = clean.replace("enigma2-plugin-skins-", "")
            image_name = image_name.split("_")[0]

            items.append({
                "name": clean,
                "version": version,
                "description": folder + " Skin",
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

        if not filename.endswith(".ipk"):
            continue

        clean = os.path.splitext(filename)[0]

        version = clean.split("_")[-2] if "_" in clean else "1.0"

        image_name = clean.split("_")[0]

        data["categories"]["tools"].append({
            "name": clean,
            "version": version,
            "description": "",
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
            "description": "",
            "file": f"{BASE_URL}/system_images/{filename}",
            "image": image_url(image_name)
        })


# -------------------------------------------------
# Save JSON
# -------------------------------------------------

os.makedirs("feed", exist_ok=True)

with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("feed/index.json generated successfully.")
