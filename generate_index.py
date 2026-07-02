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

# Plugins
if os.path.isdir("plugins"):
    for filename in sorted(os.listdir("plugins")):
        if filename.endswith(".ipk"):
            clean = os.path.splitext(filename)[0]
            version = clean.split("_")[-2] if "_" in clean else "1.0"

            data["categories"]["plugins"].append({
                "name": clean.replace("enigma2-plugin-", ""),
                "version": version,
                "description": "",
                "file": f"{BASE_URL}/plugins/{filename}",
                "image": ""
            })

# Skins (supports subfolders)
if os.path.isdir("skins"):
    for image_name in sorted(os.listdir("skins")):

        image_path = os.path.join("skins", image_name)

        if not os.path.isdir(image_path):
            continue

        items = []

        for filename in sorted(os.listdir(image_path)):
            if filename.endswith(".ipk"):

                clean = os.path.splitext(filename)[0]
                version = clean.split("_")[-2] if "_" in clean else "1.0"

                items.append({
                    "name": clean,
                    "version": version,
                    "description": image_name + " Skin",
                    "file": f"{BASE_URL}/skins/{image_name}/{filename}",
                    "image": ""
                })

        data["categories"]["skins"].append({
            "name": image_name,
            "items": items
        })

# Tools
if os.path.isdir("tools"):
    for filename in sorted(os.listdir("tools")):
        if filename.endswith(".ipk"):
            clean = os.path.splitext(filename)[0]

            data["categories"]["tools"].append({
                "name": clean,
                "version": "1.0",
                "description": "",
                "file": f"{BASE_URL}/tools/{filename}",
                "image": ""
            })

# Images
if os.path.isdir("system_images"):
    for filename in sorted(os.listdir("system_images")):
        if filename.endswith(".zip"):
            clean = os.path.splitext(filename)[0]

            data["categories"]["system_images"].append({
                "name": clean,
                "version": "1.0",
                "description": "",
                "file": f"{BASE_URL}/system_images/{filename}",
                "image": ""
            })

os.makedirs("feed", exist_ok=True)

with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("Done")
