#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path

def generate_photogallery():
    """
    Сканує папку img-news та всі вкладені папки,
    знаходить всі зображення та створює photogallery.json
    """
    
    # Налаштування
    img_news_path = Path('img-news')  # Папка з зображеннями
    data_path = Path('data')  # Папка для збереження JSON
    
    # Підтримувані розширення зображень
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}
    
    # Перевірка існування папки img-news
    if not img_news_path.exists():
        print(f"❌ Помилка: Папка '{img_news_path}' не знайдена!")
        print(f"   Переконайтесь, що скрипт запущено з правильної директорії.")
        return
    
    # Створення папки data, якщо не існує
    data_path.mkdir(exist_ok=True)
    
    # Список для зберігання шляхів до зображень
    photos = []
    
    # Рекурсивний пошук всіх зображень
    print(f"🔍 Сканування папки '{img_news_path}'...")
    
    for root, dirs, files in os.walk(img_news_path):
        for file in sorted(files):  # Сортування для передбачуваного порядку
            # Перевірка розширення файлу
            file_ext = Path(file).suffix.lower()
            if file_ext in image_extensions:
                # Створення відносного шляху
                relative_path = os.path.join(root, file)
                # Конвертація в Unix-стиль (з /)
                unix_path = relative_path.replace(os.sep, '/')
                # Додавання / на початок
                photo_path = f"/{unix_path}"
                photos.append(photo_path)
                print(f"  ✓ Знайдено: {photo_path}")
    
    # Створення JSON структури
    gallery_data = {
        "title": "Фотогалерея",
        "description": "Колекція фотографій з новин",
        "photos": photos
    }
    
    # Збереження у файл
    output_file = data_path / 'photogallery.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(gallery_data, f, ensure_ascii=False, indent=2)
    
    # Виведення результатів
    print(f"\n✅ Успішно створено {output_file}")
    print(f"📊 Знайдено зображень: {len(photos)}")
    print(f"\n📁 Структура:")
    
    # Підрахунок зображень по папках
    folders = {}
    for photo in photos:
        folder = os.path.dirname(photo)
        folders[folder] = folders.get(folder, 0) + 1
    
    for folder, count in sorted(folders.items()):
        print(f"   {folder}: {count} файл(ів)")

if __name__ == "__main__":
    print("=" * 60)
    print("🖼️  Генератор photogallery.json")
    print("=" * 60)
    print()
    
    try:
        generate_photogallery()
        print("\n✨ Готово!")
    except Exception as e:
        print(f"\n❌ Помилка: {e}")
        import traceback
        traceback.print_exc()

