#### ДОДАЄМО НОВИНУ З ГУГЛ ТАБЛИЦІ

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

def download_file_from_google_drive(file_url, output_folder, name_file):
    # Парсимо URL, щоб отримати file_id
    parsed_url = urllib.parse.urlparse(file_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    file_id = query_params.get("id", [None])[0]
    print('parsed_url', parsed_url)
    if not file_id:
        print("❌ Не вдалося отримати file id з URL.")
        return

    # Формуємо URL для завантаження файлу
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    try:
        response = requests.get(download_url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Помилка завантаження файлу: {e}")
        return

    # Визначаємо розширення файлу за Content-Type
    content_type = response.headers.get('Content-Type', '')
    if 'image/jpeg' in content_type:
        ext = '.jpg'
    elif 'image/png' in content_type:
        ext = '.png'
    elif 'image/webp' in content_type:
        ext = '.webp'
    else:
        print(f"❌ Невідомий формат файлу або непідтримуваний тип: {content_type}")
        return

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
    except IOError as e:
        print(f"❌ Помилка запису файлу: {e}")
    return f'{file_path}/{file_path}'

def get_file_extension(filename: str) -> str:
    if '.' in filename:
        return filename.rsplit('.', 1)[-1]
    return ''

# https://docs.google.com/spreadsheets/d/13aUrQMqqoZT8H8PByphDqln3s06u3Vg_/edit?usp=sharing&ouid=107211966436332045560&rtpof=true&sd=true
def extract_drive_file_id(url: str) -> str:
    if url.startswith("https://drive.google.com/open?id="):
        return url.split("id=")[-1]
    elif url.startswith("https://drive.google.com/file/d/") and "/view" in url:
        return url.split("/d/")[1].split("/view")[0]
    elif url.startswith("https://drive.google.com/uc?export=download&id="):
        return url.split("id=")[-1]
    elif url.startswith("https://drive.google.com/drive/folders/"):
        return url.split("folders/")[-1]
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

def compress_image(image_path, image_path_dest, max_size_kb=300):
    """
    Зменшує розмір зображення до зазначеного розміру (у кілобайтах).
    """
    img = Image.open(image_path)
    quality = 85  # Початкова якість
    while True:
        img.save(image_path_dest, format="JPEG", quality=quality)
        if os.path.getsize(image_path) <= max_size_kb * 1024 or quality <= 10:
            break
        quality -= 5

def getTable(idTable):
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
            
            names = []
            if key == "Фото":
                s = value
                if s.startswith("https://drive.google.com/open?id="):
                    listt = s.split(', ')
                    for i, item in enumerate(listt):
                        name = download_file_from_google_drive(item, "downloaded_files", str(i))
                        file_path = os.path.join("downloaded_files", name)
                        
                        # if os.path.exists(file_path) and os.path.getsize(file_path) > 1 * 1024 * 1024:
                        #     compress_image(file_path, 'downloaded_files')
                        
                        names.append(name)
                    
                    if "Позначка часу" in new_row:
                        name_folder = new_row['Позначка часу'].replace(" ", "_").replace(":", "_")
                        
                        newNames = process_downloaded_files(name_folder)
                        new_row[key] = newNames
                        update_photo_in_table(idTable, new_row['Позначка часу'], newNames)
            if key == "Файл(и) документу":
                file_path = new_row['Файл(и) документу'].split(', ')[0]
                # Якщо це файл чи папка на гугл диску, то отримуємо його ID
                new_row['info'] = "--"
                new_row['type'] = "--"
                new_row['size'] = "--"
                # https://drive.google.com/file/d/1A_dnaeuYaOjcat6v0FCSVMRK-JNSj271/view?usp=sharing"
                file_id = extract_drive_file_id(file_path.split(', ')[0])
                # print('file_id', file_id)
                if  file_id != '':
                    try:
                        file_info = get_drive_file_info(file_id)
                        if file_info:
                            new_row['info'] = f"{file_info['name']} ({file_info['type']}, {file_info['size_mb']} MB)"
                            new_row['type'] = get_file_extension(file_info['name'])
                            new_row['size'] = f"{file_info['size_mb']}"
                        else:
                            new_row['info'] = '--'
                    except Exception as e:
                        print(f"Помилка при отриманні інформації про файл {file_id}: {e}")
                        new_row['info'] = '--'
            
        new_data.append(new_row)

    output_dir = os.path.join(os.getcwd(), 'data')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_file_path = os.path.join(output_dir, f'{idTable}.json')
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)

    print(f"JSON файл для таблиці {idTable} створено.")
    
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)


# def getTable(idTable):
#     #Очищуємо папку output_folder
#     output_folder = "downloaded_files"
#     if os.path.exists(output_folder):
#         shutil.rmtree(output_folder)
#     os.makedirs(output_folder)

#     scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#     creds = ServiceAccountCredentials.from_json_keyfile_name('project-fa0cf409504d.json', scope)
#     client = gspread.authorize(creds)
#     sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{idTable}/').sheet1
#     data = sheet.get_all_records()
#     new_data = []
#     for index, row in enumerate(data):
#         new_row = {}
#         new_row['id'] = str(index)
#         for key, value in row.items():
#             if key != "":
#                 new_row[key] = str(value)
#             names = []
#             if key == "Фото":
#                 s = value
#                 if s.startswith("https://drive.google.com/open?id="):
#                     listt = s.split(', ')
#                     for index, item in enumerate(listt):
#                         name = download_file_from_google_drive(item, "downloaded_files", str(index))
#                         names.append(name)
#                     if "Позначка часу" in new_row:
#                         name_folder = new_row['Позначка часу'].replace(" ", "_").replace(":", "_")

#                         newNames = process_downloaded_files(name_folder)
#                         new_row[key] = newNames
#                         update_photo_in_table(idTable, new_row['Позначка часу'], newNames)
#                     else:
#                         pass
#                 else:
#                     pass

#         new_data.append(new_row)

#     # Створюємо шлях до папки "test"
#     output_dir = os.path.join(os.getcwd(), 'data')
#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)
        
#     # Створюємо шлях до файлу JSON у папці "test"
#     output_file_path = os.path.join(output_dir, f'{idTable}.json')

#     # Зберігаємо JSON файл
#     with open(output_file_path, 'w', encoding='utf-8') as f:
#         json.dump(new_data, f, ensure_ascii=False, indent=4)

#     print(f"JSON файл для таблиці {idTable} створено.")
            
#     output_folder = "downloaded_files"
#     if os.path.exists(output_folder):
#         shutil.rmtree(output_folder)
#     os.makedirs(output_folder)

def process_downloaded_files(folder):

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

    # # Якщо така папка вже існує, 
    if os.path.exists(new_folder_path) == False:

        # Створюємо нову папку
        os.makedirs(new_folder_path)
        print(f"Створено папку: {new_folder_path}")

    # Шлях до папки з завантаженими файлами
    downloaded_dir = "downloaded_files"
    if not os.path.exists(downloaded_dir):
        print(f"Папка {downloaded_dir} не існує!")
        return ""

    # Отримуємо список файлів у папці downloaded_files
    files = [f for f in os.listdir(downloaded_dir) if os.path.isfile(os.path.join(downloaded_dir, f))]

    print("Список файлів:", files)
    # Список для зберігання повних URL файлів
    file_urls = []

    

    # Копіюємо файли у створену папку та видаляємо їх з downloaded_files----------')
    for file_name in files:
        src_path = os.path.join(downloaded_dir, file_name)
        dst_path = os.path.join(new_folder_path, file_name)
        try:
            if os.path.exists(src_path) and os.path.getsize(src_path) > 1 * 1024 * 1024:
                compress_image(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)
            # Видаляємо файл з папки downloaded_files
            os.remove(src_path)
            # Формуємо URL для файлу
            file_url = f"{base_url}/{new_folder_name}/{file_name}"
            file_urls.append(file_url)
        except Exception as e:
            print(f"Помилка при обробці файлу {file_name}: {e}")
    # Повертаємо результуючий рядок, де імена файлів розділені символом \n
    # Отримуємо список файлів у новій папці
    new_files = [f for f in os.listdir(new_folder_path) if os.path.isfile(os.path.join(new_folder_path, f))]
    # Додаємо '{base_url}/{new_folder_name}/{f}' до кожного елемента списку і сортуємо список
    new_files_urls = [f"{base_url}/{new_folder_name}/{f}" for f in sorted(new_files)]
    return "\n".join(new_files_urls)

def update_photo_in_table(idTable, timestamp, new_photo_url):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('project-fa0cf409504d.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{idTable}/').sheet1
    data = sheet.get_all_records()
    for index, row in enumerate(data, start=2):
        if row.get("Позначка часу") == timestamp:
            sheet.update_cell(index, list(row.keys()).index("old_photo") + 1, row.get("Фото", ""))
            sheet.update_cell(index, list(row.keys()).index("Фото") + 1, new_photo_url)
            print(f"Оновлено значення у стовпці 'Фото' для рядка з 'Позначка часу' = {timestamp}")
            return
    
    print("Рядок із вказаною 'Позначка часу' не знайдено.")

if __name__ == "__main__":
    print("Запуск utils.py")
    compress_image('downloaded_files/1.jpg', 'test/1.jpg', 300)



