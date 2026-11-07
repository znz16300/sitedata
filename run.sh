#!/usr/bin/env bash
# Ручний запуск на своєму комп'ютері (зазвичай не потрібен — працює GitHub Actions).
set -euo pipefail
cd "$(dirname "$0")"

[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt

git pull --rebase --autostash
python publish.py "$@" || echo "⚠️  Частина таблиць з помилками — публікуємо те, що вдалося."

git add data img-news
if git diff --cached --quiet; then
  echo "Змін немає — нічого не публікуємо."
else
  git commit -m "data: оновлення $(date '+%d.%m.%Y %H:%M')"
  git push
fi
