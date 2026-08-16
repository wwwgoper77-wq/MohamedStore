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
        "channels": [],
        "novaler": []
    }
}

# -------- Preserve old descriptions (نفس طريقتك الأصلية بالضبط) --------
old_descriptions = {}

try:
    if os.path.exists("feed/index.json"):
        with open("feed/index.json", "r", encoding="utf-8") as f:
            old = json.load(f)

        for cat, items in old.get("categories", {}).items():
            if cat in ["skins", "system_images"]:
                for folder in items:
                    if isinstance(folder, dict) and "items" in folder:
                        for it in folder.get("items", []):
                            old_descriptions[it.get("name", "")] = it.get("description", "")
                    elif isinstance(folder, dict):
                        old_descriptions[folder.get("name", "")] = folder.get("description", "")
            else:
                for it in items:
                    old_descriptions[it.get("name", "")] = it.get("description", "")
except:
    pass


def image_url(prefix):
    prefix = prefix.lower()
    # 1. البحث في مجلد Icons أولاً
    if os.path.isdir("Icons"):
        for file in sorted(os.listdir("Icons")):
            if file.lower().startswith(prefix) and file.lower().endswith(".png"):
                return f"{BASE_URL}/Icons/{file}"
    # 2. البحث في مجلد images ثانياً إذا لم توجد في Icons
    if os.path.isdir("images"):
        for file in sorted(os.listdir("images")):
            if file.lower().startswith(prefix) and file.lower().endswith(".png"):
                return f"{BASE_URL}/images/{file}"
    return ""


# صيغ ملفات التثبيت العامة
EXTENSIONS = (".ipk", ".sh", ".deb", ".zip", ".tar.gz", ".tgz", ".tar", ".py", ".tv", ".img", ".nfi", ".tar.xz", ".bin")


# -------------------------------------------------
# Global Release Assets Fetcher (لتحويل الروابط فقط للملفات الكبيرة)
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


# دالة مساعدة لتنظيف اسم الملف وإزالة الامتدادات المركبة
def clean_filename(filename):
    if filename.endswith(".tar.gz"):
        return filename[:-7]
    elif filename.endswith(".tar.xz"):
        return filename[:-7]
    else:
        return os.path.splitext(filename)[0]


# -------------------------------------------------
# 1. System Images (فقط المجلدات والملفات التي وضعتها أنت)
# -------------------------------------------------
if os.path.isdir("system_images"):
    for entry in sorted(os.listdir("system_images")):
        entry_path = os.path.join("system_images", entry)

        # إذا كان مجلداً أنشأته أنت
        if os.path.isdir(entry_path):
            items = []
            for filename in sorted(os.listdir(entry_path)):
                if not filename.endswith(EXTENSIONS):
                    continue
                clean = clean_filename(filename)
                version = clean.split("_")[-2] if "_" in clean else "1.0"
                image_name = clean.split("_")[0]

                file_path_url = f"{BASE_URL}/system_images/{entry}/{filename}"
                for asset in release_assets_pool:
                    if asset["filename"] == filename:
                        file_path_url = asset["url"]
                        break

                items.append({
                    "name": clean,
                    "version": version,
                    "description": old_descriptions.get(clean, ""),
                    "file": file_path_url,
                    "image": image_url(image_name) or image_url("system_images")
                })

            data["categories"]["system_images"].append({
                "name": entry,
                "items": items
            })

        # إذا كان ملف صورة مباشر
        elif entry.endswith(EXTENSIONS):
            clean = clean_filename(entry)
            version = clean.split("_")[-2] if "_" in clean else "1.0"
            image_name = clean.split("_")[0]

            file_path_url = f"{BASE_URL}/system_images/{entry}"
            for asset in release_assets_pool:
                if asset["filename"] == entry:
                    file_path_url = asset["url"]
                    break

            data["categories"]["system_images"].append({
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, ""),
                "file": file_path_url,
                "image": image_url(image_name) or image_url("system_images")
            })


# -------------------------------------------------
# 2. Skins (السكينات - المجلدات التي أنشأتها أنت فقط)
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
            clean = clean_filename(filename)
            version = clean.split("_")[-2] if "_" in clean else "1.0"
            image_name = clean.replace("enigma2-plugin-skins-", "").split("_")[0]

            file_path_url = f"{BASE_URL}/skins/{folder}/{filename}"
            for asset in release_assets_pool:
                if asset["filename"] == filename:
                    file_path_url = asset["url"]
                    break

            items.append({
                "name": clean,
                "version": version,
                "description": old_descriptions.get(clean, folder + " Skin"),
                "file": file_path_url,
                "image": image_url(image_name) or image_url("skins")
            })

        data["categories"]["skins"].append({
            "name": folder,
            "items": items
        })


# -------------------------------------------------
# 3. Picons (البيكونات من مجلد picons)
# -------------------------------------------------
if os.path.isdir("picons"):
    for filename in sorted(os.listdir("picons")):
        if not filename.endswith(EXTENSIONS):
            continue
        clean = clean_filename(filename)
        file_path_url = f"{BASE_URL}/picons/{filename}"
        for asset in release_assets_pool:
            if asset["filename"] == filename:
                file_path_url = asset["url"]
                break

        data["categories"]["picons"].append({
            "name": clean,
            "version": "1.0",
            "description": old_descriptions.get(clean, ""),
            "file": file_path_url,
            "image": image_url(clean.split("_")[0]) or image_url("picons")
        })


# -------------------------------------------------
# 4. Channels & Settings (القنوات من مجلد channels)
# -------------------------------------------------
if os.path.isdir("channels"):
    for filename in sorted(os.listdir("channels")):
        if not filename.endswith(EXTENSIONS):
            continue
        clean = clean_filename(filename)
        file_path_url = f"{BASE_URL}/channels/{filename}"
        for asset in release_assets_pool:
            if asset["filename"] == filename:
                file_path_url = asset["url"]
                break

        data["categories"]["channels"].append({
            "name": clean,
            "version": "1.0",
            "description": old_descriptions.get(clean, ""),
            "file": file_path_url,
            "image": image_url(clean.split("_")[0]) or image_url("channels")
        })


# -------------------------------------------------
# 5. Tools (الأدوات من مجلد tools)
# -------------------------------------------------
if os.path.isdir("tools"):
    for filename in sorted(os.listdir("tools")):
        if not filename.endswith(EXTENSIONS):
            continue
        clean = clean_filename(filename)
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
            "description": old_descriptions.get(clean, ""),
            "file": file_path_url,
            "image": image_url(image_name) or image_url("tools")
        })


# -------------------------------------------------
# 6. Plugins (الإضافات من مجلد plugins)
# -------------------------------------------------
if os.path.isdir("plugins"):
    for filename in sorted(os.listdir("plugins")):
        if not filename.endswith(EXTENSIONS):
            continue
        clean = clean_filename(filename)
        version = clean.split("_")[-2] if "_" in clean else "1.0"
        display = clean.replace("enigma2-plugin-", "")

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
            ) or image_url("plugins")
        })


# -------------------------------------------------
# 7. Novaler (قسم نوفالير)
# -------------------------------------------------
novaler_folder = "novaler" if os.path.isdir("novaler") else "Novaler" if os.path.isdir("Novaler") else "Noflayer" if os.path.isdir("Noflayer") else "noflayer"

if os.path.isdir(novaler_folder):
    for filename in sorted(os.listdir(novaler_folder)):
        if not filename.endswith(EXTENSIONS):
            continue
        clean = clean_filename(filename)
        version = clean.split("_")[-2] if "_" in clean else "1.0"
        display = (
            clean.replace("enigma2-plugin-extensions-", "")
            .replace("enigma2-plugin-", "")
            .replace("extensions-", "")
        )
        image_name = display.split("_")[0]
        img = image_url("novaler") or image_url("noflayer") or image_url(image_name)

        file_path_url = f"{BASE_URL}/{novaler_folder}/{filename}"
        for asset in release_assets_pool:
            if asset["filename"] == filename:
                file_path_url = asset["url"]
                break

        data["categories"]["novaler"].append({
            "name": clean,
            "version": version,
            "description": old_descriptions.get(clean, ""),
            "file": file_path_url,
            "image": img
        })


# -------------------------------------------------
# Save JSON
# -------------------------------------------------
os.makedirs("feed", exist_ok=True)

with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("feed/index.json generated successfully.")
