import os
import json
import urllib.request

repo = os.environ.get("GITHUB_REPOSITORY")
token = os.environ.get("GITHUB_TOKEN")

api_url = f"https://api.github.com/repos/{repo}/releases/latest"

req = urllib.request.Request(
    api_url, 
    headers={"Authorization": f"token {token}", "User-Agent": "ActionScript"}
)

try:
    with urllib.request.urlopen(req) as response:
        release_data = json.loads(response.read().decode())
        assets = release_data.get("assets", [])
        
        json_file = "index.json"
        if os.path.exists(json_file):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"store_name": "M Store", "version": "1.0", "categories": {}}

        categories = data.setdefault("categories", {})
        
        # التأكد من وجود الأقسام الرئيسية بنفس هيكلتك
        categories.setdefault("plugins", [])
        categories.setdefault("tools", [])
        categories.setdefault("picons", [])
        categories.setdefault("channels", [])
        categories.setdefault("system_images", [])
        categories.setdefault("skins", [])

        if assets:
            for asset in assets:
                file_name = asset["name"]
                download_url = asset["browser_download_url"]
                lower_name = file_name.lower()

                # تحديد القسم المناسب بناءً على اسم الملف
                target_category = "plugins" # افتراضي
                
                if any(ext in lower_name for ext in ["egami", "openatv", "blackhole", "vti", "pure2", "img", "nfi"]) and ("vu" in lower_name or "solo" in lower_name or "duo" in lower_name or "image" in lower_name):
                    target_category = "system_images"
                elif "skin" in lower_name or lower_name.endswith(".xml"):
                    target_category = "skins"
                elif "picon" in lower_name:
                    target_category = "picons"
                elif "channel" in lower_name or "backup" in lower_name:
                    target_category = "channels"
                elif "tool" in lower_name or "script" in lower_name or "ncam" in lower_name or "oscam" in lower_name:
                    target_category = "tools"

                # بناء العنصر بنفس الهيكل والخصائص المعتمدة لديك (name, version, description, file, image)
                new_item = {
                    "name": file_name,
                    "version": "1.0",
                    "description": "",
                    "file": download_url,
                    "image": ""
                }

                # التعامل مع الأقسام العادية (plugins, tools, picons, channels, system_images)
                if target_category != "skins":
                    existing_files = [item.get("file") for item in categories.get(target_category, [])]
                    if download_url not in existing_files:
                        categories[target_category].append(new_item)
                        print(f"Added '{file_name}' to category: '{target_category}'")
                else:
                    # تخصيص للسكينات إذا تم رفعها للريليس، يتم وضعها تحت أول مجموعة أو إنشاء مجموعة عامة
                    # للتأكد من عدم ضياعها، سنضيفها تحت قسم Skuins العام أو أول عنصر فرعي
                    skins_list = categories.get("skins", [])
                    if skins_list and isinstance(skins_list[0], dict) and "items" in skins_list[0]:
                        existing_files = [item.get("file") for item in skins_list[0]["items"]]
                        if download_url not in existing_files:
                            skins_list[0]["items"].append(new_item)
                            print(f"Added release skin '{file_name}' to first skin group.")

        # حفظ الملف بالهيكل الصحيح والترميز المطلوب
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        print("Successfully updated index.json with exact schema matching!")
except Exception as e:
    print(f"Error updating JSON: {e}")
