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
            data = {"categories": {}}

        categories = data.setdefault("categories", {})
        
        # التأكد من وجود الأقسام الأساسية مع الحفاظ على محتوياتها القديمة إن وجدت
        categories.setdefault("system_images", [])
        categories.setdefault("plugins", [])
        categories.setdefault("skins", [])
        categories.setdefault("picons", [])
        categories.setdefault("tools", [])

        if assets:
            for asset in assets:
                file_name = asset["name"]
                download_url = asset["browser_download_url"]
                lower_name = file_name.lower()

                # تحديد القسم المناسب تلقائياً حسب نوع الملف
                target_category = "plugins"
                
                if any(ext in lower_name for ext in ["egami", "openatv", "blackhole", "vti", "pure2", "img", "nfi"]) and ("vu" in lower_name or "solo" in lower_name or "duo" in lower_name or "image" in lower_name):
                    target_category = "system_images"
                elif "skin" in lower_name or lower_name.endswith(".xml"):
                    target_category = "skins"
                elif "picon" in lower_name:
                    target_category = "picons"
                elif "tool" in lower_name or "script" in lower_name:
                    target_category = "tools"

                # منع تكرار نفس رابط الـ Release إذا كان مسجلاً مسبقاً
                existing_urls = [item.get("url") for item in categories.get(target_category, [])]
                if download_url not in existing_urls:
                    new_item = {
                        "name": file_name,
                        "version": "1.0",
                        "description": f"Auto-sorted release item for {target_category}",
                        "url": download_url
                    }
                    categories[target_category].append(new_item)
                    print(f"Added '{file_name}' to category: '{target_category}'")

        # حفظ الملف بنجاح مع دمج الملفات القديمة والجديدة
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ensure_ascii=False if hasattr(json, 'ensure_ascii') else 4) # تم ضبط الترميز ليدعم العربية
            
        print("Successfully updated index.json while keeping local files intact!")
except Exception as e:
    print(f"Error updating JSON: {e}")
