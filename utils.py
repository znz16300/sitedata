import os
import re
import requests
import urllib.parse
import shutil
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from PIL import Image

from getFileInfo import get_drive_file_info
from utils_2 import _read_M


def download_file_from_google_drive(file_url, output_folder, name_file):
    """Завантажує файл з Google Drive."""
    # Парсимо URL, щоб отримати file_id
    parsed_url = urllib.parse.urlparse(file_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    file_id = query_params.get("id", [None])[0]
    
    print(f'Завантаження файлу: {file_url}')
    
    if not file_id:
        print("❌ Не вдалося отримати file id з URL.")
        return None

    # Формуємо URL для завантаження файлу
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    try:
        response = requests.get(download_url, allow_redirects=True)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Помилка завантаження файлу: {e}")
        return None

    # Визначаємо розширення файлу за Content-Type
    content_type = response.headers.get('Content-Type', '')
    
    # Перевіряємо чи це не HTML сторінка (помилка доступу)
    if 'text/html' in content_type:
        print(f"❌ Файл недоступний (потрібен дозвіл на доступ або файл не існує).")
        print(f"   Content-Type: {content_type}")
        print(f"   URL: {file_url}")
        print(f"   File ID: {file_id}")
        return None
    
    if 'image/jpeg' in content_type:
        ext = '.jpg'
    elif 'image/png' in content_type:
        ext = '.png'
    elif 'image/webp' in content_type:
        ext = '.webp'
    else:
        print(f"❌ Невідомий формат файлу або непідтримуваний тип: {content_type}")
        return None

    # Переконуємося, що output_folder існує
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    file_name = f"{name_file}{ext}"
    file_path = os.path.join(output_folder, file_name)
    
    # Записуємо файл
    try:
        with open(file_path, "wb") as f:
            f.write(response.content)
        print(f"✅ Файл завантажено: {file_path}")
        return file_name  # Повертаємо тільки ім'я файлу
    except IOError as e:
        print(f"❌ Помилка запису файлу: {e}")
        return None


def get_file_extension(filename: str) -> str:
    """Отримує розширення файлу."""
    if '.' in filename:
        return filename.rsplit('.', 1)[-1]
    return ''


def extract_drive_file_id(url: str) -> str:
    """Витягує ID файлу з різних форматів Google Drive URL."""
    if url.startswith("https://drive.google.com/open?id="):
        return url.split("id=")[-1]
    elif url.startswith("https://drive.google.com/file/d/") and "/view" in url:
        return url.split("/d/")[1].split("/view")[0]
    elif url.startswith("https://drive.google.com/uc?export=download&id="):
        return url.split("id=")[-1]
    elif url.startswith("http://drive.google.com/uc?export=view&id="):
        return url.split("id=")[-1]
    elif url.startswith("https://drive.google.com/drive/folders/"):
        return url.split("folders/")[-1]
    elif url.startswith("https://docs.google.com/spreadsheets/d/e/"):
        return url.split("d/e/")[1].split("/")[0]
    elif url.startswith("https://docs.google.com/spreadsheets/d/"):
        return url.split("d/")[1].split("/")[0]
    elif url.startswith("https://docs.google.com/document/d/"):
        return url.split("d/")[1].split("/")[0]
    elif url.startswith("https://drive.google.com/file/d/"):
        return url.split("d/")[1].split("/")[0]
    elif url.startswith("https://drive.google.com/open?"):
        match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
    return ''


def compress_image(image_path, image_path_dest, max_size_kb=300, max_dimension=1920):
    """
    Зменшує розмір зображення до зазначеного розміру (у кілобайтах).
    Також зменшує розміри зображення якщо вони перевищують max_dimension.
    
    Args:
        image_path: Шлях до вхідного файлу
        image_path_dest: Шлях до вихідного файлу
        max_size_kb: Максимальний розмір файлу в кілобайтах
        max_dimension: Максимальний розмір по ширині або висоті в пікселях
    """
    try:
        img = Image.open(image_path)
        
        # Конвертуємо в RGB якщо потрібно (для PNG з прозорістю)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Створюємо білий фон
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Зменшуємо розміри якщо потрібно
        width, height = img.size
        if width > max_dimension or height > max_dimension:
            # Зберігаємо пропорції
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(f"  Зменшено розміри з {width}x{height} до {new_width}x{new_height}")
        
        # Стискаємо файл до потрібного розміру
        quality = 85
        while quality >= 10:
            img.save(image_path_dest, format="JPEG", quality=quality, optimize=True)
            
            # Перевіряємо розмір ВИХІДНОГО файлу
            file_size = os.path.getsize(image_path_dest)
            
            if file_size <= max_size_kb * 1024:
                print(f"  ✅ Зображення збережено: {image_path_dest} (якість: {quality}, розмір: {file_size / 1024:.2f} KB)")
                break
            
            quality -= 5
        
        if quality < 10:
            print(f"  ⚠️ Не вдалося стиснути до {max_size_kb} KB навіть з мінімальною якістю")
            
    except Exception as e:
        print(f"❌ Помилка при обробці зображення {image_path}: {e}")
        raise


def getTable(idTable):
    """Завантажує дані з Google Sheets та обробляє зображення."""
    output_folder = "downloaded_files"
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('project-fa0cf409504d.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{idTable}/').sheet1
    data = sheet.get_all_records()
    new_data = []
    
    for index, row in enumerate(data):
        new_row = {"id": str(index)}
        for key, value in row.items():
            if key:
                new_row[key] = str(value)
            
            if key == "Фото":
                s = value
                if s.startswith("https://drive.google.com/open?id="):
                    listt = s.split(', ')
                    names = []
                    
                    print(f"\nОбробка фото для рядка {index}:")
                    for i, item in enumerate(listt):
                        name = download_file_from_google_drive(item, "downloaded_files", str(i))
                        
                        # Перевіряємо чи файл успішно завантажився
                        if name is None:
                            print(f"⚠️ Пропускаємо файл {i} через помилку завантаження")
                            continue
                        
                        file_path = os.path.join("downloaded_files", name)
                        
                        if os.path.exists(file_path):
                            names.append(name)
                        else:
                            print(f"⚠️ Файл {name} не знайдено після завантаження")
                    
                    # Якщо є успішно завантажені файли
                    if names and "Позначка часу" in new_row:
                        name_folder = new_row['Позначка часу'].replace(" ", "_").replace(":", "_")
                        newNames = process_downloaded_files(name_folder)
                        new_row[key] = newNames
                        update_photo_in_table(idTable, new_row['Позначка часу'], newNames)
                    elif not names:
                        print(f"⚠️ Жоден файл не завантажився для рядка {index}")
                        new_row[key] = ""
            
            if key == "Файл(и) документу":
                file_path_list = new_row['Файл(и) документу'].split(', ')
                if file_path_list:
                    file_path = file_path_list[0]
                    new_row['info'] = "--"
                    new_row['type'] = "--"
                    new_row['size'] = "--"
                    
                    file_id = extract_drive_file_id(file_path)
                    
                    if file_id != '':
                        try:
                            file_info = get_drive_file_info(file_id)
                            if file_info and 'name' in file_info:
                                new_row['info'] = f"{file_info['name']} ({file_info.get('type', 'unknown')}, {file_info.get('size_mb', 0)} MB)"
                                new_row['type'] = get_file_extension(file_info['name'])
                                new_row['size'] = f"{file_info.get('size_mb', 0)}"
                            else:
                                new_row['info'] = '--'
                        except Exception as e:
                            print(f"❌ Помилка при отриманні інформації про файл {file_id}: {e}")
                            new_row['info'] = '--'
            
        new_data.append(new_row)

    output_dir = os.path.join(os.getcwd(), 'data')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_file_path = os.path.join(output_dir, f'{idTable}.json')
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)

    print(f"\n✅ JSON файл для таблиці {idTable} створено: {output_file_path}")
    
    # Очищаємо тимчасову папку
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)


def process_downloaded_files(folder):
    """Обробляє завантажені файли: стискає та переміщує в цільову папку."""
    base_folder_name = folder
    target_dir = "img-news"
    
    # Переконуємося, що папка img-news існує, інакше створюємо її
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    # Формуємо початкове ім'я нової папки
    new_folder_name = base_folder_name
    new_folder_path = os.path.join(target_dir, new_folder_name)

    # Базовий URL для дописування до імен файлів
    base_url = "https://znz16300.github.io/sitedata/img-news"

    # Якщо така папка не існує, створюємо
    if not os.path.exists(new_folder_path):
        os.makedirs(new_folder_path)
        print(f"Створено папку: {new_folder_path}")

    # Шлях до папки з завантаженими файлами
    downloaded_dir = "downloaded_files"
    if not os.path.exists(downloaded_dir):
        print(f"Папка {downloaded_dir} не існує!")
        return ""

    # Отримуємо список файлів у папці downloaded_files
    files = [f for f in os.listdir(downloaded_dir) if os.path.isfile(os.path.join(downloaded_dir, f))]

    print(f"Обробка {len(files)} файлів:")
    
    # Копіюємо файли у створену папку та обробляємо їх
    for file_name in files:
        src_path = os.path.join(downloaded_dir, file_name)
        dst_path = os.path.join(new_folder_path, file_name)
        
        try:
            file_size = os.path.getsize(src_path)
            
            # Перевіряємо чи це зображення
            if file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                # Якщо файл більше 1 МБ або потрібно стиснути
                if file_size > 1 * 1024 * 1024:
                    print(f"Стискаємо {file_name} ({file_size / 1024 / 1024:.2f} MB)...")
                    compress_image(src_path, dst_path, max_size_kb=300, max_dimension=1920)
                else:
                    # Просто копіюємо якщо файл невеликий
                    shutil.copy2(src_path, dst_path)
                    print(f"✅ Скопійовано {file_name} ({file_size / 1024:.2f} KB)")
            else:
                # Для не-зображень просто копіюємо
                shutil.copy2(src_path, dst_path)
                print(f"✅ Скопійовано {file_name}")
            
            # Видаляємо файл з папки downloaded_files
            os.remove(src_path)
            
        except Exception as e:
            print(f"❌ Помилка при обробці файлу {file_name}: {e}")
    
    # Отримуємо список файлів у новій папці
    new_files = [f for f in os.listdir(new_folder_path) if os.path.isfile(os.path.join(new_folder_path, f))]
    
    # Додаємо URL до кожного елемента списку і сортуємо список
    new_files_urls = [f"{base_url}/{new_folder_name}/{f}" for f in sorted(new_files)]
    
    return "\n".join(new_files_urls)


def update_photo_in_table(idTable, timestamp, new_photo_url):
    """Оновлює посилання на фото в Google Sheets після обробки."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name('project-fa0cf409504d.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{idTable}/').sheet1
        data = sheet.get_all_records()
        
        for index, row in enumerate(data, start=2):
            if row.get("Позначка часу") == timestamp:
                # Зберігаємо старе фото в old_photo якщо є така колонка
                if "old_photo" in row.keys():
                    sheet.update_cell(index, list(row.keys()).index("old_photo") + 1, row.get("Фото", ""))
                
                # Оновлюємо нове фото
                sheet.update_cell(index, list(row.keys()).index("Фото") + 1, new_photo_url)
                print(f"✅ Оновлено значення у стовпці 'Фото' для рядка з 'Позначка часу' = {timestamp}")
                return
        
        print(f"⚠️ Рядок із вказаною 'Позначка часу' ({timestamp}) не знайдено.")
    except Exception as e:
        print(f"❌ Помилка при оновленні фото в таблиці: {e}")


def getSchedules(idTable):
    """Завантажує розклад з Google Sheets."""
    data = _read_M(idTable)
    output_dir = os.path.join(os.getcwd(), 'data')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_file_path = os.path.join(output_dir, f'{idTable}.json')
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"✅ JSON файл для розкладів {idTable} створено: {output_file_path}")

