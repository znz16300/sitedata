#!/usr/bin/env python3
"""Публікація даних шкільного сайту з Google Таблиць.

    python publish.py                  # усі таблиці з config.json + фотогалерея
    python publish.py --only news      # лише вказані таблиці (через кому)
    python publish.py --no-write-back  # нічого не записувати назад у Google Таблиці
    python publish.py --skip-images    # не завантажувати фото з Drive (швидкий прогін)
    python publish.py --list           # показати таблиці з config.json

Що робить (див. README.md):
  • читає таблиці, лишає лише дозволені колонки (email та інші особисті дані — ніколи);
  • для новин ставить show = "1", якщо поле порожнє (і в JSON, і в самій таблиці);
  • переносить фото з Google Drive у img-news/ (WebP) і робить мініатюри для карток;
  • записує data/<id таблиці>.json лише якщо дані змінились;
  • оновлює data/photogallery.json.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--only", help="назви таблиць через кому (поле name у config.json)")
    ap.add_argument("--no-write-back", action="store_true", help="не змінювати Google Таблиці")
    ap.add_argument("--skip-images", action="store_true", help="не завантажувати фото з Google Drive")
    ap.add_argument("--list", action="store_true", help="показати таблиці й вийти")
    args = ap.parse_args()

    import os

    os.chdir(ROOT)  # усі шляхи в config.json — відносно папки проєкту
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    tables = cfg["tables"]

    if args.list:
        for t in tables:
            print(f"{t['name']:12} {t.get('type', 'rows'):10} {t['id']}  {t.get('title', '')}")
        return 0

    if args.only:
        wanted = {n.strip() for n in args.only.split(",")}
        unknown = wanted - {t["name"] for t in tables}
        if unknown:
            print(f"❌ Невідомі таблиці: {', '.join(sorted(unknown))}. Див. python publish.py --list")
            return 2
        tables = [t for t in tables if t["name"] in wanted]

    from sdlib.gallery import build_gallery
    from sdlib.google_client import GoogleClient
    from sdlib.images import ImageSettings
    from sdlib.report import Report
    from sdlib.tables import EXPORTERS, Context, write_json

    report = Report()
    img_cfg = cfg.get("images", {})
    ctx = Context(
        out_dir=Path(cfg.get("output_dir", "data")),
        images=ImageSettings(
            root=Path(img_cfg.get("dir", "img-news")),
            public_base=cfg["public_base_url"],
            max_size=img_cfg.get("max_size", 1600),
            quality=img_cfg.get("quality", 82),
            thumb_size=img_cfg.get("thumb_size", 640),
            thumb_quality=img_cfg.get("thumb_quality", 74),
        ),
        never_publish=[re.compile(p) for p in cfg.get("never_publish_columns", [])],
        report=report,
        write_back=not args.no_write_back,
        skip_images=args.skip_images,
    )

    client = GoogleClient(cfg.get("credentials_file", "secrets/service-account.json"))
    print(f"🔑 Сервісний акаунт: {client.email}")

    changed: list[str] = []
    started = time.time()
    for t in tables:
        name = t["name"]
        print(f"\n📄 {t.get('title', name)} ({name})")
        try:
            result = EXPORTERS[t.get("type", "rows")](client, t, ctx)
        except Exception as e:  # одна таблиця не повинна зупиняти решту
            report.error(name, f"{type(e).__name__}: {e}")
            continue

        path = ctx.out_dir / f"{t['id']}.json"
        if write_json(path, result.data):
            changed.append(path.as_posix())
            report.info(name, f"оновлено {path.as_posix()}")
        else:
            print("  без змін")

        if result.sheet_updates:
            try:
                ws = client.spreadsheet(t["id"]).sheet1
                ws.batch_update(result.sheet_updates, value_input_option="RAW")
                report.info(name, f"записано в таблицю клітинок: {len(result.sheet_updates)}")
            except Exception as e:
                report.error(name, f"не вдалося записати в таблицю: {type(e).__name__}: {e}")

    gal = cfg.get("gallery")
    if gal and not args.only:
        print("\n🖼️  Фотогалерея")
        data = build_gallery(ctx.images.root, gal.get("title", ""), gal.get("description", ""))
        path = ctx.out_dir / gal.get("output", "photogallery.json")
        if write_json(path, data):
            changed.append(path.as_posix())
            report.info("gallery", f"фото у галереї: {len(data['photos'])}")
        else:
            print("  без змін")

    print(f"\n{'✅' if not report.has_errors else '⚠️'} Готово за {time.time() - started:.0f} с. Змінено файлів: {len(changed)}")
    report.write_github_summary(changed)
    return 1 if report.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
