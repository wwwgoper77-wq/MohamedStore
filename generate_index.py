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

    for f in sorted(os.listdir(folder)):
        if not (
            f.endswith(".ipk")
            or f.endswith(".zip")
            or f.endswith(".tar.gz")
        ):
            continue

        filename = f
        name = (
            filename.replace(".ipk", "")
            .replace(".zip", "")
            .replace(".tar.gz", "")
        )

        parts = name.split("_")
        version = "1.0"

        if len(parts) > 1:
            version = parts[1]

        item = {
            "name": parts[0],
            "version": version,
            "description": "",
            "file": f"{BASE_URL}/{folder}/{filename}",
            "image": f"{BASE_URL}/images/{parts[0]}.png"
        }

        data["categories"][folder].append(item)


for folder in folders:
    add_files(folder)

with open("index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("index.json generated successfully.")
