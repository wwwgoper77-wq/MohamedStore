import os
import json
import re
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

# -------------------------------------------------
# 1. حفظ واسترجاع الأوصاف والأسماء المكتوبة باللغة العربية
# -------------------------------------------------
old_descriptions = {}
old_names = {}

try:
    if os.path.exists("feed/index.json"):
        with open("feed/index.json", "r", encoding="utf-8") as f:
            old = json.load(f)

        def save_metadata(item):
            if not isinstance(item, dict):
                return
            fn = item.get("file", "").split("/")[-1]
            c_name = item.get("name", "")
            desc = item.get("description", "")

            if desc:
                if c_name: old_descriptions[c_name] = desc
                if fn: old_descriptions[fn] = desc

            if c_name and fn:
                old_names[fn] = c_name
                old_names[c_name] = c_name

        for cat, items in old.get("categories", {}).items():
            if isinstance(items, list):
                for el in items:
                    if isinstance(el, dict) and "items" in el:
                        for it in el.get("items", []):
                            save_metadata(it)
                    elif isinstance(el, dict):
                        save_metadata(el)

    print(f"✅ Loaded {len(old_descriptions)} descriptions & {len(old_names)} custom names.")
except Exception as e:
    print("Notice loading previous descriptions:", e)


def image_url(prefix):
    if not prefix:
        return ""
    prefix = prefix.lower().strip()
    for folder in ["Icons", "images"]:
        if os.path.isdir(folder):
            for file in sorted(os.listdir(folder)):
                if file.lower().startswith(prefix) and file.lower().endswith(".png"):
                    return f"{BASE_URL}/{folder}/{file}"
    return ""


EXTENSIONS = (".ipk", ".sh", ".deb", ".zip", ".tar.gz", ".tgz", ".tar", ".py", ".tv", ".img", ".nfi", ".tar.xz", ".bin")


def clean_filename(filename):
    if filename.endswith(".tar.gz") or filename.endswith(".tar.xz"):
        return filename[:-7]
    return os.path.splitext(filename)[0]


def normalize_text(text):
    return re.sub(r'[^a-z0-9]', '', str(text).lower())


def get_best_name(filename, default_clean):
    """دالة ذكية لاختيار الاسم العربي وعدم استبداله بالإنجليزي"""
    if filename in old_names and old_names[filename].strip():
        return old_names[filename].strip()
    if default_clean in old_names and old_names[default_clean].strip():
        return old_names[default_clean].strip()
    return default_clean


def get_best_description(clean_name, filename, release_body="", default_desc=""):
    """دالة ذكية لاختيار الوصف العربي وعدم استبداله بالإنجليزي"""
    # 1. إذا كان موجوداً في الأوصاف القديمة المحفوظة
    if clean_name in old_descriptions and old_descriptions[clean_name].strip():
        return old_descriptions[clean_name].strip()
    if filename in old_descriptions and old_descriptions[filename].strip():
        return old_descriptions[filename].strip()

    # 2. إذا كان مكتوباً في تفاصيل الـ Release
    if release_body and release_body.strip():
        # نأخذ أول سطر مفيد من وصف الـ Release
        lines = [l.strip() for l in release_body.split("\n") if l.strip() and not l.strip().startswith("#")]
        if lines:
            return lines[0]

    return default_desc


# -------------------------------------------------
# 2. جلب ملفات الـ Releases وأوصافها العربية
# -------------------------------------------------
release_assets_pool = []
github_token = os.environ.get("GITHUB_TOKEN", "")

headers = {"User-Agent": "MohamedStore-Feed", "Accept": "application/vnd.github+json"}
if github_token:
    headers["Authorization"] = f"token {github_token}"

page = 1
while True:
    try:
        api_rel = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/releases?per_page=100&page={page}"
        req = urllib.request.Request(api_rel, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            releases = json.loads(response.read().decode("utf-8"))

        if not releases or not isinstance(releases, list):
            break

        for release in releases:
            rel_body = release.get("body", "") or release.get("name", "")
            for asset in release.get("assets", []):
                filename = asset.get("name", "")
                if filename.endswith(EXTENSIONS):
                    release_assets_pool.append({
                        "filename": filename,
                        "url": asset.get("browser_download_url", ""),
                        "body": rel_body
                    })

        if len(releases) < 100:
            break
        page += 1
    except Exception as e:
        print("Releases notice:", e)
        break

print(f"✅ Total Release Assets loaded: {len(release_assets_pool)}")

assigned_releases = set()


# -------------------------------------------------
# 3. معالجة صور النظام (System Images)
# -------------------------------------------------
sys_folders = {}
if os.path.isdir("system_images"):
    for folder in sorted(os.listdir("system_images")):
        fpath = os.path.join("system_images", folder)
        if not os.path.isdir(fpath):
            continue
        norm = normalize_text(folder)
        disp = "All" if norm == "all" else folder
        sys_folders[norm] = {"display_name": disp, "items": [], "seen": set()}

        for fn in sorted(os.listdir(fpath)):
            if not fn.endswith(EXTENSIONS):
                continue
            sys_folders[norm]["seen"].add(fn)
            clean = clean_filename(fn)
            ver = clean.split("_")[-2] if "_" in clean else "1.0"
            f_url = f"{BASE_URL}/system_images/{folder}/{fn}"
            body_desc = ""
            for asset in release_assets_pool:
                if asset["filename"] == fn:
                    f_url = asset["url"]
                    body_desc = asset.get("body", "")
                    break

            final_name = get_best_name(fn, clean)
            final_desc = get_best_description(clean, fn, body_desc, f"{disp} Image")

            sys_folders[norm]["items"].append({
                "name": final_name,
                "version": ver,
                "description": final_desc,
                "file": f_url,
                "image": image_url(clean.split("_")[0]) or image_url(disp) or image_url("system_images")
            })

for asset in release_assets_pool:
    fn = asset["filename"]
    fn_lower = fn.lower()
    fn_norm = normalize_text(fn)

    is_sys_img = False
    if any(k in fn_norm for k in ["vti", "openpli", "openatv", "openbh", "blackhole", "egami", "pure2", "openspa", "openvix", "systemimage"]):
        is_sys_img = True
    elif any(ext in fn_lower for ext in ["usb.zip", "emmc.zip", "mmc.zip", "recovery.zip", "rootfs.tar.bz2", ".nfi", ".img"]):
        is_sys_img = True

    if is_sys_img and not any(k in fn_norm for k in ["plugin", "skin", "picon", "channel", "ncam", "oscam"]):
        assigned_releases.add(fn)
        matched = None
        for norm_k in sys_folders.keys():
            if norm_k != "all" and norm_k in fn_norm:
                matched = norm_k
                break

        if not matched:
            matched = "all"
            if matched not in sys_folders:
                sys_folders[matched] = {"display_name": "All", "items": [], "seen": set()}

        if fn not in sys_folders[matched]["seen"]:
            sys_folders[matched]["seen"].add(fn)
            clean = clean_filename(fn)
            ver = clean.split("_")[-2] if "_" in clean else "1.0"
            disp = sys_folders[matched]["display_name"]
            final_name = get_best_name(fn, clean)
            final_desc = get_best_description(clean, fn, asset.get("body", ""), f"{disp} Image")

            sys_folders[matched]["items"].append({
                "name": final_name,
                "version": ver,
                "description": final_desc,
                "file": asset["url"],
                "image": image_url(clean.split("_")[0]) or image_url(disp) or image_url("system_images")
            })

for norm_k, f_data in sorted(sys_folders.items()):
    data["categories"]["system_images"].append({
        "name": f_data["display_name"],
        "items": f_data["items"]
    })


# -------------------------------------------------
# 4. معالجة السكينات (Skins)
# -------------------------------------------------
skin_folders = {}
if os.path.isdir("skins"):
    for folder in sorted(os.listdir("skins")):
        fpath = os.path.join("skins", folder)
        if not os.path.isdir(fpath):
            continue
        norm = normalize_text(folder)
        disp = "All" if norm == "all" else folder
        skin_folders[norm] = {"display_name": disp, "items": [], "seen": set()}

        for fn in sorted(os.listdir(fpath)):
            if not fn.endswith(EXTENSIONS):
                continue
            skin_folders[norm]["seen"].add(fn)
            clean = clean_filename(fn)
            ver = clean.split("_")[-2] if "_" in clean else "1.0"
            disp_skin = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
            f_url = f"{BASE_URL}/skins/{folder}/{fn}"
            body_desc = ""
            for asset in release_assets_pool:
                if asset["filename"] == fn:
                    f_url = asset["url"]
                    body_desc = asset.get("body", "")
                    break

            final_name = get_best_name(fn, clean)
            final_desc = get_best_description(clean, fn, body_desc, f"{disp} Skin")

            skin_folders[norm]["items"].append({
                "name": final_name,
                "version": ver,
                "description": final_desc,
                "file": f_url,
                "image": image_url(disp_skin.split("_")[0]) or image_url("skins")
            })

for asset in release_assets_pool:
    fn = asset["filename"]
    fn_norm = normalize_text(fn)

    if "skin" in fn_norm and fn not in assigned_releases:
        assigned_releases.add(fn)
        matched = None
        for norm_k in skin_folders.keys():
            if norm_k != "all" and norm_k in fn_norm:
                matched = norm_k
                break

        if not matched:
            matched = "all"
            if matched not in skin_folders:
                skin_folders[matched] = {"display_name": "All", "items": [], "seen": set()}

        if fn not in skin_folders[matched]["seen"]:
            skin_folders[matched]["seen"].add(fn)
            clean = clean_filename(fn)
            ver = clean.split("_")[-2] if "_" in clean else "1.0"
            disp_skin = clean.replace("enigma2-plugin-skins-", "").replace("enigma2-plugin-skin-", "").replace("skin-", "")
            disp = skin_folders[matched]["display_name"]
            final_name = get_best_name(fn, clean)
            final_desc = get_best_description(clean, fn, asset.get("body", ""), f"{disp} Skin")

            skin_folders[matched]["items"].append({
                "name": final_name,
                "version": ver,
                "description": final_desc,
                "file": asset["url"],
                "image": image_url(disp_skin.split("_")[0]) or image_url("skins")
            })

for norm_k, f_data in sorted(skin_folders.items()):
    data["categories"]["skins"].append({
        "name": f_data["display_name"],
        "items": f_data["items"]
    })


# -------------------------------------------------
# 5. معالجة بقية الأقسام (Novaler, Picons, Channels, Tools, Plugins)
# -------------------------------------------------
def handle_flat(cat_key, matcher_func, default_desc):
    items = []
    seen = set()

    if os.path.isdir(cat_key):
        for fn in sorted(os.listdir(cat_key)):
            if not fn.endswith(EXTENSIONS):
                continue
            seen.add(fn)
            clean = clean_filename(fn)
            ver = clean.split("_")[-2] if "_" in clean else "1.0"
            disp_name = clean.replace("enigma2-plugin-extensions-", "").replace("enigma2-plugin-", "")
            f_url = f"{BASE_URL}/{cat_key}/{fn}"
            body_desc = ""
            for asset in release_assets_pool:
                if asset["filename"] == fn:
                    f_url = asset["url"]
                    body_desc = asset.get("body", "")
                    break

            final_name = get_best_name(fn, clean)
            final_desc = get_best_description(clean, fn, body_desc, default_desc)

            items.append({
                "name": final_name,
                "version": ver,
                "description": final_desc,
                "file": f_url,
                "image": image_url(disp_name.split("_")[0]) or image_url(cat_key)
            })

    for asset in release_assets_pool:
        fn = asset["filename"]
        fn_norm = normalize_text(fn)
        if fn in seen or fn in assigned_releases:
            continue

        if matcher_func(fn_norm):
            assigned_releases.add(fn)
            seen.add(fn)
            clean = clean_filename(fn)
            ver = clean.split("_")[-2] if "_" in clean else "1.0"
            disp_name = clean.replace("enigma2-plugin-extensions-", "").replace("enigma2-plugin-", "")
            final_name = get_best_name(fn, clean)
            final_desc = get_best_description(clean, fn, asset.get("body", ""), default_desc)

            items.append({
                "name": final_name,
                "version": ver,
                "description": final_desc,
                "file": asset["url"],
                "image": image_url(disp_name.split("_")[0]) or image_url(cat_key)
            })

    data["categories"][cat_key] = items


handle_flat("novaler", lambda n: "novaler" in n or "noflayer" in n, "Novaler Package")
handle_flat("picons", lambda n: "picon" in n or "snp" in n or "srp" in n, "Picons Package")
handle_flat("channels", lambda n: any(k in n for k in ["channel", "setting", "bouquet", "satellites", "fav"]), "Channels Settings")
handle_flat("tools", lambda n: any(k in n for k in ["ncam", "oscam", "softcam", "emu", "tool", "script", "tweak"]), "Tool Package")
handle_flat("plugins", lambda n: True, "Plugin Extension")


# -------------------------------------------------
# 6. حفظ الفهرس بترميز UTF-8 لدعم الحروف العربية
# -------------------------------------------------
os.makedirs("feed", exist_ok=True)
with open("feed/index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("🎉 Successfully generated feed/index.json preserving Arabic descriptions & names perfectly!")
