#!/bin/bash

# Запускаємо Python скрипт
python3 getTable.py

# Додаємо всі зміни до Git
git add .

# Створюємо комміт з повідомленням "deploy"
git commit -m "deploy"

# Пушимо зміни на віддалений репозиторій
git push

