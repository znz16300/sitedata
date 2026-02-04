@echo off
git pull

REM Запускаємо Python скрипт

git pull

python main.py

REM Додаємо всі зміни до Git
git add .

REM Створюємо комміт з повідомленням "deploy"
git commit -m "deploy"

REM Пушимо зміни на віддалений репозиторій
git push

pause
