import os
import json

plugins_dir = "plugins"
data = {
    "store": "Enigma2 Store",
    "plugins": []
}

if os.path.exists(plugins_dir):
    for f in os.listdir(plugins_dir):
        if f.endswith(".ipk") or f.endswith(".tar.gz") or f.endswith(".zip"):
            name = f.split("_")[0]
            data["plugins"].append({
                "name": name,
                "file": f"plugins/{f}",
                "image": f"images/{name}.png",
                "version": 1.0
            })

with open("index.json", "w") as x:
    json.dump(data, x, indent=4)
