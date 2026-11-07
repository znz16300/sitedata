#!/usr/bin/env python3
"""Зменшує важкі фото в папці БЕЗ зміни назв і форматів (посилання на них не ламаються).

    python tools/optimize_images.py images            # фото вчителів
    python tools/optimize_images.py photogallery --max 1600

Фото, менші за --min-kb, не чіпаються. JPEG → якість 82, PNG → оптимізація без втрат
(або 256 кольорів з --png-colors). Розмір по довшій стороні — не більше --max.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageOps

ap = argparse.ArgumentParser()
ap.add_argument("folder")
ap.add_argument("--max", type=int, default=1200)
ap.add_argument("--min-kb", type=int, default=250)
ap.add_argument("--quality", type=int, default=82)
ap.add_argument("--png-colors", action="store_true", help="зменшити PNG до 256 кольорів (для схем/скріншотів)")
args = ap.parse_args()

total_before = total_after = 0
for p in sorted(Path(args.folder).rglob("*")):
    if p.suffix.lower() not in {".jpg", ".jpeg", ".png"} or not p.is_file():
        continue
    before = p.stat().st_size
    if before < args.min_kb * 1024:
        continue
    img = ImageOps.exif_transpose(Image.open(p))
    if max(img.size) > args.max:
        img.thumbnail((args.max, args.max), Image.Resampling.LANCZOS)
    tmp = p.with_suffix(p.suffix + ".tmp")
    if p.suffix.lower() == ".png":
        if args.png_colors:
            img = img.convert("RGBA").quantize(256)
        img.save(tmp, "PNG", optimize=True)
    else:
        img.convert("RGB").save(tmp, "JPEG", quality=args.quality, optimize=True, progressive=True)
    after = tmp.stat().st_size
    if after < before:
        tmp.replace(p)
    else:
        tmp.unlink()
        after = before
    total_before += before
    total_after += after
    print(f"{p}: {before // 1024} КБ → {after // 1024} КБ")

print(f"\nРазом: {total_before // 1024} КБ → {total_after // 1024} КБ")
