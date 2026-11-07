"""Фото новин: завантаження з Google Drive, конвертація у WebP, мініатюри.

Структура на диску (і на сайті):
    img-news/<папка новини>/0.webp            — основне фото (до max_size px по довшій стороні)
    img-news/<папка новини>/thumbs/0.webp.webp — мініатюра для карток (thumb_size px)

Для старих фото (jpg/png, завантажених до цієї версії) мініатюри створюються автоматично
при першому запуску; самі старі файли не змінюються, тож посилання на них не ламаються.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

try:  # фото з iPhone (HEIC) — якщо встановлено pillow-heif
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:  # pragma: no cover
    pass

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".heif"}
THUMBS_DIR = "thumbs"

_DRIVE_ID = re.compile(r"(?:/d/|[?&]id=|/folders/)([-\w]{20,})")


def drive_file_id(url: str) -> str | None:
    if "google.com" not in url:
        return None
    m = _DRIVE_ID.search(url)
    return m.group(1) if m else None


def split_links(value: str) -> list[str]:
    """Посилання з клітинки: через кому, кому з пробілом або новий рядок."""
    return [p.strip() for p in re.split(r"[\n,]+", value or "") if p.strip()]


@dataclass
class ImageSettings:
    root: Path
    public_base: str  # https://znz16300.github.io/sitedata
    max_size: int = 1600
    quality: int = 82
    thumb_size: int = 640
    thumb_quality: int = 74

    @property
    def public_prefix(self) -> str:
        return f"{self.public_base.rstrip('/')}/{self.root.as_posix()}/"

    def url_for(self, path: Path) -> str:
        return f"{self.public_base.rstrip('/')}/{path.as_posix()}"

    def local_path_for(self, url: str) -> Path | None:
        """Локальний файл для посилання на наш же img-news (або None для чужих посилань)."""
        if not url.startswith(self.public_prefix):
            return None
        rel = url[len(self.public_base.rstrip('/')) + 1 :]
        return Path(rel)


def _prepare(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)  # фото з телефона не буде «лежати на боці»
    if img.mode in ("P", "LA"):
        img = img.convert("RGBA")
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    return img


def _resized(img: Image.Image, size: int) -> Image.Image:
    if max(img.size) <= size:
        return img
    out = img.copy()
    out.thumbnail((size, size), Image.Resampling.LANCZOS)
    return out


def thumb_path_for(original: Path) -> Path:
    return original.parent / THUMBS_DIR / f"{original.name}.webp"


def save_photo(data: bytes, dest_dir: Path, name: str, s: ImageSettings) -> tuple[Path, Path]:
    """Зберігає фото як <name>.webp + мініатюру. Повертає (фото, мініатюра)."""
    img = _prepare(Image.open(io.BytesIO(data)))
    dest_dir.mkdir(parents=True, exist_ok=True)
    main = dest_dir / f"{name}.webp"
    _resized(img, s.max_size).save(main, "WEBP", quality=s.quality, method=6)
    thumb = thumb_path_for(main)
    thumb.parent.mkdir(parents=True, exist_ok=True)
    _resized(img, s.thumb_size).save(thumb, "WEBP", quality=s.thumb_quality, method=6)
    return main, thumb


def ensure_thumb(original: Path, s: ImageSettings) -> Path | None:
    """Мініатюра для вже наявного фото (створюється один раз)."""
    thumb = thumb_path_for(original)
    if thumb.exists():
        return thumb
    if not original.exists() or original.suffix.lower() not in IMAGE_EXT:
        return None
    try:
        img = _prepare(Image.open(original))
        thumb.parent.mkdir(parents=True, exist_ok=True)
        _resized(img, s.thumb_size).save(thumb, "WEBP", quality=s.thumb_quality, method=6)
        return thumb
    except Exception:
        return None


def iter_gallery_images(root: Path):
    """Усі фото для галереї (без мініатюр), у стабільному порядку."""
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXT and THUMBS_DIR not in path.parts:
            yield path
