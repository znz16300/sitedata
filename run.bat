@echo off
REM Ручний запуск на Windows (зазвичай не потрібен — працює GitHub Actions).
chcp 65001 >nul
cd /d "%~dp0"

if not exist venv ( python -m venv venv )
call venv\Scripts\activate.bat
pip install -q -r requirements.txt

git pull --rebase --autostash
python publish.py %*
if errorlevel 2 exit /b 1
if errorlevel 1 echo Частина таблиць з помилками - публікуємо те, що вдалося.

git add data img-news
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "data: оновлення %date% %time:~0,5%"
  git push
) else (
  echo Змін немає — нічого не публікуємо.
)
