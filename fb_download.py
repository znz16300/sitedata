#!/usr/bin/env python3
"""
Facebook post scraper — отримує текст допису та завантажує фото.
Використовує Selenium (headless Chrome) або requests+BeautifulSoup як fallback.

Встановлення залежностей:
    pip install selenium webdriver-manager requests beautifulsoup4 Pillow

Використання:
    python fb_scraper.py --url "https://www.facebook.com/share/p/1Aq4nRLeSP/" --output ./downloads
"""

import argparse
import os
import re
import sys
import time
import json
import urllib.request
import shutil
from pathlib import Path
from urllib.parse import urlparse, urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Встановіть залежності: pip install requests beautifulsoup4")
    sys.exit(1)

def clear_output_dir(output_dir: Path):
    """Очищує папку перед завантаженням."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
        print(f"🗑️  Папку очищено: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# Варіант 1: через Selenium (рекомендовано)
# ──────────────────────────────────────────────
def scrape_with_selenium(url: str, output_dir: Path) -> dict:
    """Скрейпінг через headless Chrome — обходить JS-рендеринг Facebook."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        print("Selenium не встановлено. Спробую requests-метод...")
        return None

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    # Українська мова інтерфейсу
    options.add_argument("--lang=uk-UA")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    print("🚀 Запускаю Chrome (headless)...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    result = {"text": "", "images": [], "url": url}

    try:
        driver.get(url)
        time.sleep(4)  # чекаємо завантаження

        # Закрити cookie-банер якщо є
        for selector in [
            "[data-cookiebanner='accept_button']",
            "[aria-label='Allow all cookies']",
            "button[title='Allow all cookies']",
        ]:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, selector)
                btn.click()
                time.sleep(1)
                break
            except Exception:
                pass

        # ── Текст допису ──
        text_selectors = [
            "div[data-ad-preview='message']",
            "div[data-testid='post_message']",
            "[data-ad-comet-preview='message']",
            "div.xdj266r",          # внутрішній клас FB (може мінятись)
            "div[dir='auto']",
        ]
        post_text = ""
        for sel in text_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                t = el.text.strip()
                if len(t) > 20:  # ігноруємо дрібні шматки
                    post_text = t
                    break
            if post_text:
                break

        # Fallback: весь видимий текст сторінки (перші 3000 символів)
        if not post_text:
            body = driver.find_element(By.TAG_NAME, "body")
            post_text = body.text[:3000]

        result["text"] = post_text
        print(f"\n📝 Текст допису:\n{'─'*60}\n{post_text}\n{'─'*60}\n")

        # ── Зображення ──
        img_elements = driver.find_elements(By.CSS_SELECTOR, "img")
        image_urls = set()

        for img in img_elements:
            src = img.get_attribute("src") or ""
            # Facebook фото мають характерні URL
            if any(
                x in src
                for x in ["scontent", "fbcdn.net", "fbsbx.com", "lookaside.fbsbx"]
            ) and src.startswith("http"):
                # Фільтруємо аватари (зазвичай маленькі)
                width = img.get_attribute("width") or "0"
                height = img.get_attribute("height") or "0"
                try:
                    if int(width) < 100 or int(height) < 100:
                        continue
                except ValueError:
                    pass
                image_urls.add(src)

        result["images"] = list(image_urls)
        print(f"🖼️  Знайдено зображень: {len(image_urls)}")

    finally:
        driver.quit()

    return result


# ──────────────────────────────────────────────
# Варіант 2: через requests + BeautifulSoup
# ──────────────────────────────────────────────
def scrape_with_requests(url: str) -> dict:
    """
    Легкий варіант без браузера.
    Обмеження: Facebook повертає мало даних без JS,
    але іноді спрацьовує для публічних постів.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    session = requests.Session()
    resp = session.get(url, headers=headers, timeout=15, allow_redirects=True)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Open Graph мета-теги (найнадійніший спосіб)
    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")
    og_image = soup.find("meta", property="og:image")

    text_parts = []
    if og_title and og_title.get("content"):
        text_parts.append(og_title["content"])
    if og_desc and og_desc.get("content"):
        text_parts.append(og_desc["content"])

    images = []
    if og_image and og_image.get("content"):
        images.append(og_image["content"])

    # Додаткові зображення
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "scontent" in src or "fbcdn" in src:
            images.append(src)

    return {
        "text": "\n\n".join(text_parts),
        "images": list(set(images)),
        "url": url,
    }


# ──────────────────────────────────────────────
# Завантаження зображень
# ──────────────────────────────────────────────
def download_images(image_urls: list, output_dir: Path) -> list:
    """Завантажує зображення у папку, повертає список збережених файлів."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.facebook.com/",
    }

    for i, img_url in enumerate(image_urls, 1):
        try:
            # Визначаємо розширення
            parsed = urlparse(img_url)
            ext = Path(parsed.path).suffix or ".jpg"
            if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                ext = ".jpg"

            filename = output_dir / f"image_{i:03d}{ext}"
            print(f"  ⬇️  Завантажую {i}/{len(image_urls)}: {filename.name}")

            resp = requests.get(img_url, headers=headers, timeout=20, stream=True)
            resp.raise_for_status()

            with open(filename, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            saved.append(str(filename))
            print(f"     ✅ Збережено ({filename.stat().st_size // 1024} KB)")

        except Exception as e:
            print(f"     ❌ Помилка при завантаженні {img_url[:80]}...: {e}")

    return saved


# ──────────────────────────────────────────────
# Збереження тексту
# ──────────────────────────────────────────────
def save_text(text: str, output_dir: Path, url: str) -> str:
    """Зберігає текст допису у .txt файл."""
    output_dir.mkdir(parents=True, exist_ok=True)
    text_file = output_dir / "post_text.txt"

    with open(text_file, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write("=" * 60 + "\n\n")
        f.write(text)

    print(f"\n💾 Текст збережено: {text_file}")
    return str(text_file)


# ──────────────────────────────────────────────
# Головна функція
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Скачує текст і фото з допису Facebook"
    )
    parser.add_argument(
        "--url", "-u",
        required=True,
        help="Посилання на допис Facebook",
    )
    parser.add_argument(
        "--output", "-o",
        default="./fb_downloads",
        help="Папка для збереження (за замовчуванням: ./fb_downloads)",
    )
    parser.add_argument(
        "--no-selenium",
        action="store_true",
        help="Використовувати лише requests (без Chrome)",
    )
    args = parser.parse_args()



    output_dir = Path(args.output)
    print(f"\n📂 Папка збереження: {output_dir.resolve()}\n")
    clear_output_dir(output_dir)


    # ── Скрейпінг ──
    data = None

    if not args.no_selenium:
        data = scrape_with_selenium(args.url, output_dir)

    if not data or not data.get("text"):
        print("🔄 Спробую метод через requests...")
        data = scrape_with_requests(args.url)

    if not data:
        print("❌ Не вдалося отримати дані з допису.")
        sys.exit(1)

    # ── Зберігаємо текст ──
    if data["text"]:
        save_text(data["text"], output_dir, args.url)
    else:
        print("⚠️  Текст допису не знайдено (можливо, пост приватний).")

    # ── Завантажуємо фото ──
    if data["images"]:
        print(f"\n📥 Завантажую {len(data['images'])} зображень у {output_dir}...")
        saved = download_images(data["images"], output_dir)
        print(f"\n✅ Готово! Завантажено {len(saved)} файлів.")
    else:
        print("⚠️  Зображення не знайдено.")

    # ── Підсумок ──
    print(f"\n{'═'*60}")
    print(f"📁 Всі файли збережено у: {output_dir.resolve()}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()

# https://docs.google.com/forms/d/e/1FAIpQLScSNSgoHz9ZGkmUH3IKNM1FVrIIJO7OQlp0C5BzaSN4wmg4wg/viewform
# ──────────────────────────────────────────────
# pip install requests beautifulsoup4 
# pip install selenium webdriver-manager
