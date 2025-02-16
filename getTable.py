import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials

def getTable (idTable):
    # Налаштовуємо авторизацію
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('project-fa0cf409504d.json', scope)
    client = gspread.authorize(creds)

    # Відкриваємо таблицю за її URL або ім'ям
    sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{idTable}/').sheet1

    # Отримуємо всі дані з таблиці
    data = sheet.get_all_records()

    # Додаємо поле id
    for index, row in enumerate(data, start=0):
        row['id'] = str(index)
    # Створюємо шлях до папки "test"
    output_dir = os.path.join(os.getcwd(), 'data')
    # Перевіряємо, чи існує папка, якщо ні, створюємо її
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # Створюємо шлях до файлу output.json у папці test
    output_file_path = os.path.join(output_dir, f'{idTable}.json')

    # Зберігаємо JSON файл у папку "test"
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("JSON файл створено.")



if __name__ == "__main__":
    getTable('1Dk0WYpOKeRoDATgzMkIkFjUcFwNAG5MRn4W7bEyzd0M')
    getTable('1F6QVr9WNio-_ODmnIlMTSHeSQxLOjgnd0nYB1_z0BeI')
    getTable('1G1l3J4HHLOItVLYbrPL08ml3TtON_fAULcpecqn0vwM')
    getTable('15D-n7O5AdsttUF3LfkOhRexS-Q4T78MfXDbUlmsPHRc')

