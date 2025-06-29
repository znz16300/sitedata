import json
import requests

def get_drive_file_info(file_id: str) -> dict:
    """
    Отримати інформацію про файл на Google Drive: розмір і тип.
    """
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"

    json_file_path = 'apikey.json'
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Завантажуємо API ключ
    api_key = data['key']

    params = {
        "key": api_key,
        "fields": "id, name, mimeType, size"
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        return {
            "name": data.get("name", ""),
            "type": data.get("mimeType", ""),
            "size_bytes": int(data["size"]) if "size" in data else None,
            "size_mb": round(int(data["size"]) / (1024 * 1024), 2) if "size" in data else None
        }
    else:
        print(f"Помилка: {response.status_code}, {response.text}")
        return {}
