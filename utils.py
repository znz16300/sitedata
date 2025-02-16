#### ДОДАЄМО НОВИНУ З ГУГЛ ТАБЛИЦІ

import os
import requests
import urllib.parse
import shutil
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

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

def getTable(idTable):
    # Налаштовуємо авторизацію
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('project-fa0cf409504d.json', scope)
    client = gspread.authorize(creds)

    # Відкриваємо таблицю за її URL
    sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{idTable}/').sheet1

    # Отримуємо всі дані з таблиці
    data = sheet.get_all_records()

    # Перетворюємо дані: додаємо поле id, перетворюємо всі значення в рядки,
    # і видаляємо ключі, які є порожніми ("")
    new_data = []
    for index, row in enumerate(data):
        new_row = {}
        new_row['id'] = str(index)
        for key, value in row.items():
            if key != "":  # Пропускаємо записи з порожнім ключем
                new_row[key] = str(value)
            names = []
            if key == "Фото":
                s = value
                if s.startswith("https://drive.google.com/open?id="):
                    listt = s.split(', ')
                    for index, item in enumerate(listt):
                        name = download_file_from_google_drive(item, "downloaded_files", str(index))
                        names.append(name)
                    name_folder = new_row['Позначка часу'].replace(" ", "_").replace(":", "_")
                    newNames = process_downloaded_files(name_folder)
                    new_row[key] = newNames
                else:
                    pass

        new_data.append(new_row)



    # Створюємо шлях до папки "test"
    output_dir = os.path.join(os.getcwd(), 'data')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Створюємо шлях до файлу JSON у папці "test"
    output_file_path = os.path.join(output_dir, f'{idTable}.json')

    # Зберігаємо JSON файл
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)

    print(f"JSON файл для таблиці {idTable} створено.")

def process_downloaded_files(folder):
    """
    Функція створює нову папку в img-news з поточною датою (формат YYYY-MM-DD).
    Якщо така папка вже існує, додає суфікс -1, -2, ... до отримання унікального імені.
    Далі копіює всі файли з папки downloaded_files у створену папку,
    очищає папку downloaded_files, та повертає рядок, де кожне ім'я файлу доповнене
    префіксом "https://znz16300.github.io/sitedata/img-news/" і розділене символом "\n".
    """
    # Отримуємо поточну дату у форматі YYYY-MM-DD
    # base_folder_name = datetime.now().strftime("%Y-%m-%d")
    base_folder_name = folder
    target_dir = "img-news"
    
    # Переконуємося, що папка img-news існує, інакше створюємо її
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    # Формуємо початкове ім'я нової папки
    new_folder_name = base_folder_name
    new_folder_path = os.path.join(target_dir, new_folder_name)

    # # Якщо така папка вже існує, додаємо суфікс -1, -2, ...
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

        # Список для зберігання повних URL файлів
        file_urls = []

        # Базовий URL для дописування до імен файлів
        base_url = "https://znz16300.github.io/sitedata/img-news"

        # Копіюємо файли у створену папку та видаляємо їх з downloaded_files
        for file_name in files:
            src_path = os.path.join(downloaded_dir, file_name)
            dst_path = os.path.join(new_folder_path, file_name)
            try:
                shutil.copy2(src_path, dst_path)
                # Видаляємо файл з папки downloaded_files
                os.remove(src_path)
                # Формуємо URL для файлу
                file_url = f"{base_url}/{new_folder_name}/{file_name}"
                file_urls.append(file_url)
            except Exception as e:
                print(f"Помилка при обробці файлу {file_name}: {e}")
        # Повертаємо результуючий рядок, де імена файлів розділені символом \n
        return "\n".join(sorted(file_urls))


