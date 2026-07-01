import os
import json

folders = ['plugins', 'skins', 'tools', 'system_images']

for folder in folders:
    if not os.path.exists(folder):
        os.makedirs(folder)

data = {
    'store': 'Enigma2 Store',
    'plugins': [],
    'skins': [],
    'tools': [],
    'system_images': []
}

def scan_folder(folder_name, target_list):
    if os.path.exists(folder_name):
        for f in os.listdir(folder_name):
            print("Found:", folder_name, f)
            if f.endswith('.ipk') or f.endswith('.tar.gz') or f.endswith('.zip'):
                # استخراج الاسم الصافي للملف بدون امتدادات
                clean_name = f.replace('.ipk', '').replace('.tar.gz', '').replace('.zip', '')
                
                # معالجة ذكية ومبسطة للاسم لتفادي أي أخطاء في الشرطات السفلية
                parts = [p for p in clean_name.split('_') if p]
                display_name = parts[0] if parts else clean_name
                version = parts[1] if len(parts) > 1 else 1.0
                
                item = {
                    'name': str(display_name),
                    'file': f'https://githubusercontent.com{folder_name}/{f}',
                    'image': f'https://githubusercontent.comimages/{display_name}.png',
                    'version': str(version)
                }
                
                # الإضافة للقسم الأصلي وقائمة البلجنات معاً لضمان القراءة على الشاشة
                target_list.append(item)
                if folder_name != 'plugins':
                    data['plugins'].append(item)

scan_folder('plugins', data['plugins'])
scan_folder('skins', data['skins'])
scan_folder('tools', data['tools'])
scan_folder('system_images', data['system_images'])

with open('index.json', 'w') as x:
    json.dump(data, x, indent=4)
