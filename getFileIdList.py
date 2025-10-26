import requests
import json

def load_api_key(json_file_path):
    """Завантажує API ключ з JSON файлу."""
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        return data.get('api_key')  # Припускаємо, що ключ зберігається у полі 'api_key'

def get_files_in_folder(folder_id, api_key):
    """Отримує список файлів і папок у вказаній папці на Google Drive."""
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        'q': f"'{folder_id}' in parents and trashed = false",
        'fields': 'files(id, name, mimeType, size, modifiedTime, owners)',
        'key': api_key
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        files = response.json().get('files', [])
        
        # Обробка даних та декодування Unicode-символів
        result = []
        for file in files:
            result.append({
                'id': file.get('id'),
                'name': file.get('name'),
                'type': 'Папка' if file.get('mimeType') == 'application/vnd.google-apps.folder' else 'Файл',
                'size': file.get('size', 'N/A'),  # Розмір доступний лише для файлів, не папок
                'modifiedTime': file.get('modifiedTime'),
                'owner': file.get('owners', [{}])[0].get('displayName', 'Невідомий')
            })
        
        return json.dumps(result, indent=4, ensure_ascii=False)
    else:
        return json.dumps({'error': 'Не вдалося отримати файли', 'status_code': response.status_code}, indent=4, ensure_ascii=False)

# Шлях до JSON файлу з API ключем
json_file_path = 'project-fa0cf409504d.json'
with open(json_file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Завантажуємо API ключ
api_key = data['key']

# ID вашої папки
folder_id = '1lLT-FsebW0KxJdfydZ6_DPbiAZykZuJA'

# Отримуємо список файлів
files_list = get_files_in_folder(folder_id, api_key)
print(files_list)
