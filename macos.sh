#!/bin/bash

source venv/bin/activate

# Запускаємо Python скрипт
python3 main.py

# Додаємо всі зміни до Git
git add .

# Створюємо комміт з повідомленням "deploy"
git commit -m "deploy"

# Пушимо зміни на віддалений репозиторій
git push

