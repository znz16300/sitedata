"""data/photogallery.json — усі фото з img-news для галереї кіоску (нові зверху)."""
from __future__ import annotations

import re
from pathlib import Path

from .images import iter_gallery_images

_FOLDER_TS = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})_(\d{1,2})_(\d{2})")


def _folder_key(folder: str) -> str:
    """'05.11.2026_14_16_11' → '202611051416' для сортування за датою."""
    m = _FOLDER_TS.match(folder)
    if not m:
        return "0"
    d, mo, y, h, mi = m.groups()
    return f"{y}{int(mo):02d}{int(d):02d}{int(h):02d}{mi}"


def build_gallery(root: Path, title: str, description: str) -> dict:
    photos = list(iter_gallery_images(root))
    # новіші новини першими, усередині новини — за назвою файлу
    photos.sort(key=lambda p: (_folder_key(p.parent.name), p.parent.name, p.name), reverse=False)
    photos.sort(key=lambda p: _folder_key(p.parent.name), reverse=True)
    return {
        "title": title,
        "description": description,
        "photos": [f"/{p.as_posix()}" for p in photos],
    }
