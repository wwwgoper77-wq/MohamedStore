import os
import json

# قائمة المجلدات
FOLDERS = ['plugins', 'skins', 'tools', 'system_images']

# إنشاء المجلدات تلقائياً إذا لم تكن موجودة
for folder in FOLDER:
    if not os.path.exists(folder):
        os.makedirs(folder)

# الهيكل الأساسي لملف البيانات
data = {
    'store': 'Enigma2 Store',
    'plugins': [],
    'skins': [],
    'tools': [],
    'system_images': []
}

# دالة مسح المجلدات واستخراج الملفات
def scan_folder(folder_name, target_list):
    if os.path.exists(folder_name):
        for f in os.listdir(folder_name):
            # التحقق من صيغ الملفات المدعومة
            if f.endswith('.ipk') or f.endswith('.tar.gz') or f.endswith('.zip'):
                parts = f.split('_')
                
                # استخراج الاسم
                display_name = parts[0] if parts else f
                
                # استخراج الإصدار أو تعيين قيمة افتراضية
                version = parts[1] if len(parts) > 1 else '1.0'
                
                target_list.append({
                    'name': display_name,
                    'file': f"{folder_name}/{f}",
                    'image': f"images/{display_name}.png",
                    'version': version
                })

# تنفيذ عملية المسح لجميع المجلدات
scan_folder('plugins', data['plugins'])
scan_folder('skins', data['skins'])
scan_folder('tools', data['tools'])
scan_folder('system_images', data['system_images'])

# حفظ البيانات في ملف index.json
with open('index.json', 'w', encoding='utf-8') as x:
    json.dump(data, x, indent=4, ensure_ascii=False)

print("تم إنشاء ملف index.json بنجاح!")
