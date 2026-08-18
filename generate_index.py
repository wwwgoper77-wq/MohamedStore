import os
import json
import urllib.parse

# إعدادات المستودع
GITHUB_USER = "wwwgoper77-wq"
REPO_NAME = "MohamedStore"
BRANCH = "main"
RAW_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/{BRANCH}"

def generate_feed():
    feed_data = {}
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # المجلدات الممنوع قراءتها
    EXCLUDED_DIRS = {".git", ".github", "__pycache__", "node_modules", "dist", "build"}

    print("جاري فحص المجلدات ودمج الأقسام المكررة...")

    for root, dirs, files in os.walk(current_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith('.')]
        
        rel_path = os.path.relpath(root, current_dir)
        if rel_path == ".":
            continue

        parts = rel_path.split(os.sep)
        
        # تصحيح وتوحيد اسم المجلد والقسم لتجنب أي تكرار
        section_raw = parts[0].strip()
        
        # إذا كان المجلد فرعي (مثل skins/All) نأخذ اسم الفئة الرئيسية
        category_name = section_raw.capitalize()
        if category_name.lower() == "skins":
            category_name = "Skins"
        elif category_name.lower() == "plugins":
            category_name = "Plugins"
        elif category_name.lower() == "softcam":
            category_name = "Softcams"

        # تصفية الملفات المقبولة فقط (.ipk, .tar.gz, .deb, .zip)
        valid_files = [f for f in files if f.endswith(('.ipk', '.tar.gz', '.deb', '.zip', '.sh')) and not f.startswith('.')]

        for filename in valid_files:
            file_path = os.path.join(root, filename)
            file_rel_path = os.path.relpath(file_path, current_dir).replace("\\", "/")
            
            encoded_path = "/".join([urllib.parse.quote(part) for part in file_rel_path.split("/")])
            download_url = f"{RAW_BASE_URL}/{encoded_path}"

            # إنشاء عنصر الملف
            clean_title = filename.replace('.ipk', '').replace('.tar.gz', '').replace('.deb', '').replace('.zip', '')
            item = {
                "name": clean_title,
                "filename": filename,
                "version": "1.0",
                "description": f"Package {clean_title}",
                "url": download_url,
                "path": file_rel_path
            }

            # تحديد القسم الداخلي (مثل All)
            sub_category = "All"
            if len(parts) > 1 and parts[1].lower() != "all":
                sub_category = parts[1].strip()

            target_section = f"{category_name}/{sub_category}" if sub_category != "All" else category_name

            if target_section not in feed_data:
                feed_data[target_section] = []

            # منع تكرار نفس الملف
            if not any(x['filename'] == filename for x in feed_data[target_section]):
                feed_data[target_section].append(item)

    # حفظ ملف index.json
    output_file = os.path.join(current_dir, "index.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(feed_data, f, indent=2, ensure_ascii=False)

    print(f"✅ تم إنشاء الفيد بنجاح ودمج جميع الأقسام المكررة! عدد الأقسام: {len(feed_data)}")

if __name__ == "__main__":
    generate_feed()
