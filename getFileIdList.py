import requests
import json

def load_api_key(json_file_path):
    """Завантажує API ключ з JSON файлу."""
    with open(json_file_path, 'r') as file:
        data = json.load(file)
        return data.get('api_key')  # Припускаємо, що ключ зберігається у полі 'api_key'

def get_files_in_folder(folder_id, api_key):
    """Отримує список файлів у папці на Google Drive."""
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        'q': f"'{folder_id}' in parents and trashed = false",
        'fields': 'files(id, name)',
        'key': api_key  # Використовуємо API ключ
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        files = response.json().get('files', [])
        return json.dumps(files, indent=4)
    else:
        return json.dumps({'error': 'Не вдалося отримати файли', 'status_code': response.status_code}, indent=4)

# Шлях до вашого JSON файлу з API ключем
# json_file_path = 'project-fa0cf409504d.json'
json_file_path = 'apikey.json'
with open(json_file_path, 'r') as file:
    data = json.load(file)


# Завантажуємо API ключ
# api_key = data['private_key_id']
api_key = data['key']


# ID вашої папки
# folder_id = '13JSCJBsEoLGhsVzVCY6cc0saYTx0qffg'
folder_id = '17sytNdRdRpi7g1Tv-lwFB3GSQH9hDT6b'

# Отримуємо список файлів
files_list = get_files_in_folder(folder_id, api_key)
print(files_list)
