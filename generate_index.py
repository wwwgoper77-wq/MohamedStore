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
            if f.endswith('.ipk') or f.endswith('.tar.gz') or f.endswith('.zip'):
                # تعديل دقة استخراج الاسم والإصدار ليعمل على المتجر مباشرة
                parts = f.split('_')
                display_name = parts[0] if parts else f
                version = parts[1] if len(parts) > 1 else 1.0
                
                target_list.append({
                    'name': display_name,
                    'file': f"{folder_name}/{f}",
                    'image': f"images/{display_name}.png",
                    'version': version
                })

scan_folder('plugins', data['plugins'])
scan_folder('skins', data['skins'])
scan_folder('tools', data['tools'])
scan_folder('system_images', data['system_images'])

with open('index.json', 'w') as x:
    json.dump(data, x, indent=4)
