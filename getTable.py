import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials

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

if __name__ == "__main__":
    getTable('1Dk0WYpOKeRoDATgzMkIkFjUcFwNAG5MRn4W7bEyzd0M')
    getTable('1F6QVr9WNio-_ODmnIlMTSHeSQxLOjgnd0nYB1_z0BeI')
    getTable('1G1l3J4HHLOItVLYbrPL08ml3TtON_fAULcpecqn0vwM')
    getTable('15D-n7O5AdsttUF3LfkOhRexS-Q4T78MfXDbUlmsPHRc')
