import os
import json

folders = ['plugins', 'skins', 'tools', 'system_images']

# Create directories if they do not exist
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
                # Extract the name by removing the extension
                name_without_ext = f.rsplit('.', 1)[0]
                name = name_without_ext.split('_')[0]
                
                target_list.append({
                    'name': name,
                    'file': f"{folder_name}/{f}",
                    'image': f"images/{name}.png",
                    'version': 1.0
                })

# Scan folders and append data
scan_folder('plugins', data['plugins'])
scan_folder('skins', data['skins'])
scan_folder('tools', data['tools'])
scan_folder('system_images', data['system_images'])

# Save data to index.json
with open('index.json', 'w') as x:
    json.dump(data, x, indent=4)
