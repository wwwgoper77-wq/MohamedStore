import os
import json

GITHUB_USER = "wwwgoper77-wq"
REPO_NAME = "MohamedStore"

BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main"

folders = ["plugins", "skins", "tools", "system_images"]

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


def add_files(folder):
    if not os.path.isdir(folder):
        return

    for filename in sorted(os.listdir(folder)):
        if not (
            filename.endswith(".ipk")
            or filename.endswith(".zip")
            or filename.endswith(".tar.gz")
        ):
            continue

        if filename.endswith(".tar.gz"):
            clean = filename[:-7]
        else:
            clean = os.path.splitext(filename)[0]

        parts = clean.split("_")
        version = parts[-2] if len(parts) >= 2 else "1.0"

        display_name = clean

        if folder == "plugins":
            display_name = (
                clean.replace("enigma2-plugin-extensions-", "")
                .replace("enigma2-plugin-skins-", "")
                .replace("enigma2-plugin-", "")
            )

        item = {
            "name": display_name,
            "version": version,
            "description": "",
            "file": f"{BASE_URL}/{folder}/{filename}",
            "image": f"{BASE_URL}/images/{display_name}.png"
        }

        data["categories"][folder].append(item)


for folder in folders:
    add_files(folder)

with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("index.json generated successfully.")
