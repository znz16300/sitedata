"""Експорт таблиць Google Sheets у JSON для сайту."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from gspread.utils import rowcol_to_a1

from . import images as im
from .report import Report

STATUS_COLUMN = "Статус публікації"
OLD_PHOTO_COLUMN = "old_photo"
THUMBS_FIELD = "Мініатюри"

_TS = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})\D+(\d{1,2}):(\d{2})(?::(\d{2}))?")


@dataclass
class Context:
    out_dir: Path
    images: im.ImageSettings
    never_publish: list[re.Pattern]
    report: Report
    write_back: bool = True
    skip_images: bool = False


@dataclass
class TableResult:
    data: object
    sheet_updates: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------- helpers

def stable_id(value: str) -> str | None:
    """'24.01.2024 21:15:13' → '20240124211513' — не змінюється, якщо рядки в таблиці переставити."""
    m = _TS.search(value or "")
    if not m:
        return None
    d, mo, y, h, mi, s = m.groups()
    return f"{y}{int(mo):02d}{int(d):02d}{int(h):02d}{mi}{s or '00'}"


def folder_name(value: str) -> str:
    """Назва папки з фото — як і раніше: '05.11.2026 14:16:11' → '05.11.2026_14_16_11'."""
    return re.sub(r"[^\w.\-]+", "_", value.strip().replace(":", "_").replace(" ", "_")).strip("_")


def load_previous(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def header_index(header: list[str]) -> dict[str, int]:
    """Назва колонки → номер (перше входження; колонки без назви ігноруються)."""
    idx: dict[str, int] = {}
    for i, h in enumerate(header):
        h = h.strip()
        if h and h not in idx:
            idx[h] = i
    return idx


def published_columns(t: dict, idx: dict[str, int], ctx: Context) -> list[str]:
    def blocked(name: str) -> bool:
        return any(p.search(name) for p in ctx.never_publish)

    wanted = t.get("columns", "*")
    if wanted == "*":
        cols = [c for c in idx if not blocked(c)]
    else:
        cols = []
        for c in wanted:
            if blocked(c):
                ctx.report.warn(t["name"], f"колонка «{c}» заборонена в never_publish_columns — пропущена")
            elif c not in idx and c not in t.get("defaults", {}):
                ctx.report.warn(t["name"], f"колонки «{c}» немає в таблиці")
            else:
                cols.append(c)
    cols += [c for c in t.get("defaults", {}) if c not in cols]
    return cols


# ---------------------------------------------------------------- photos

def process_photos(
    value: str, row_label: str, folder: str, t: dict, ctx: Context, client
) -> tuple[list[str], list[str], list[str], bool]:
    """Повертає (посилання на фото, мініатюри, проблеми, чи змінились посилання)."""
    s = ctx.images
    links = im.split_links(value)
    out, thumbs, problems = [], [], []
    changed = False

    for k, url in enumerate(links):
        file_id = im.drive_file_id(url)
        if file_id and not ctx.skip_images:
            got = client.drive_download(file_id)
            if not got:
                problems.append(
                    f"фото {k + 1} недоступне — відкрийте доступ «Усі, хто має посилання» "
                    f"або надайте доступ {client.email}"
                )
                out.append(url)
                thumbs.append(url)
                continue
            try:
                main, thumb = im.save_photo(got[0], s.root / folder, str(k), s)
            except Exception as e:  # не зображення / пошкоджений файл
                problems.append(f"фото {k + 1} не вдалося обробити ({type(e).__name__})")
                out.append(url)
                thumbs.append(url)
                continue
            out.append(s.url_for(main))
            thumbs.append(s.url_for(thumb))
            changed = True
            ctx.report.info(t["name"], f"{row_label}: фото {k + 1} → {main.as_posix()}")
            continue

        local = s.local_path_for(url)
        thumb = im.ensure_thumb(local, s) if local else None
        out.append(url)
        thumbs.append(s.url_for(thumb) if thumb else url)

    return out, thumbs, problems, changed


# ---------------------------------------------------------------- documents

def file_info(link_value: str, prev: dict, client) -> dict:
    """info/type/size для першого файлу документа (з кешем із попереднього JSON)."""
    links = im.split_links(link_value)
    if not links:
        return {"info": "--", "type": "--", "size": "--"}
    first = links[0]
    if first in prev:
        return prev[first]
    fid = im.drive_file_id(first)
    meta = client.drive_file_meta(fid) if fid else None
    if not meta or "name" not in meta:
        return {"info": "--", "type": "--", "size": "--"}
    size_mb = round(int(meta["size"]) / (1024 * 1024), 2) if meta.get("size") else 0
    name = meta["name"]
    return {
        "info": f"{name} ({meta.get('mimeType', 'unknown')}, {size_mb} MB)",
        "type": name.rsplit(".", 1)[-1] if "." in name else "",
        "size": f"{size_mb}",
    }


# ---------------------------------------------------------------- exporters

def export_rows(client, t: dict, ctx: Context) -> TableResult:
    """Перший аркуш таблиці → список об'єктів (як раніше get_all_records)."""
    name = t["name"]
    ws, values = client.first_sheet_values(t["id"])
    if not values:
        ctx.report.warn(name, "таблиця порожня")
        return TableResult([])

    header, rows = values[0], values[1:]
    idx = header_index(header)
    cols = published_columns(t, idx, ctx)
    defaults: dict[str, str] = t.get("defaults", {})
    photos_col = t.get("photos_column")
    file_col = t.get("file_info_column")
    id_from = t.get("stable_id_from")
    folder_from = t.get("photo_folder_from") or id_from

    prev = load_previous(ctx.out_dir / f"{t['id']}.json")
    prev_file_info = {}
    if file_col and isinstance(prev, list):
        for r in prev:
            links = im.split_links(r.get(file_col, ""))
            if links and r.get("info", "--") != "--":
                prev_file_info[links[0]] = {k: r.get(k, "--") for k in ("info", "type", "size")}

    updates: list[dict] = []

    def cell(row_i: int, col: str) -> str:
        c = idx.get(col)
        row = rows[row_i]
        return row[c].strip() if c is not None and c < len(row) else ""

    def queue(row_i: int, col: str, value: str) -> None:
        if col in idx and ctx.write_back:
            updates.append({"range": rowcol_to_a1(row_i + 2, idx[col] + 1), "values": [[value]]})

    out: list[dict] = []
    seen_ids: set[str] = set()
    filled_defaults = processed_photos = 0

    for i, row in enumerate(rows):
        if not any(v.strip() for v in row):
            continue  # порожній рядок (номер i все одно зберігаємо в "n" для старих посилань)

        rid = stable_id(cell(i, id_from)) if id_from else None
        rid = rid or str(i)
        base, n = rid, 2
        while rid in seen_ids:
            rid, n = f"{base}-{n}", n + 1
        seen_ids.add(rid)

        item: dict[str, str] = {"id": rid}
        if id_from:
            item["n"] = str(i)  # старий id (номер рядка) — щоб працювали давні посилання ?id=5
        for c in cols:
            item[c] = cell(i, c)

        # Значення за замовчуванням (напр. show = "1")
        for c, v in defaults.items():
            if item.get(c, "") == "":
                item[c] = v
                if t.get("write_defaults_to_sheet") and c in idx:
                    queue(i, c, v)
                    filled_defaults += 1

        row_label = f"рядок {i + 2}"
        problems: list[str] = []

        if photos_col and item.get(photos_col):
            folder = folder_name(cell(i, folder_from)) if folder_from and cell(i, folder_from) else f"row_{i + 2}"
            photos, thumbs, problems, changed = process_photos(item[photos_col], row_label, folder, t, ctx, client)
            if changed:
                processed_photos += 1
                new_value = "\n".join(photos)
                queue(i, photos_col, new_value)
                if OLD_PHOTO_COLUMN in idx and not cell(i, OLD_PHOTO_COLUMN):
                    queue(i, OLD_PHOTO_COLUMN, item[photos_col])
            item[photos_col] = "\n".join(photos)
            item[THUMBS_FIELD] = "\n".join(thumbs)

        if file_col:
            item.update(file_info(cell(i, file_col), prev_file_info, client))

        if STATUS_COLUMN in idx:
            status = "⚠️ " + "; ".join(problems) if problems else "✅ опубліковано"
            if cell(i, STATUS_COLUMN) != status:
                queue(i, STATUS_COLUMN, status)
        for p in problems:
            ctx.report.warn(name, f"{row_label} ({item.get('Назва новини') or item.get('Назва документу') or rid}): {p}")

        out.append(item)

    ctx.report.info(name, f"рядків: {len(out)}")
    if filled_defaults:
        ctx.report.info(name, f"заповнено значень за замовчуванням: {filled_defaults} ({', '.join(defaults)})")
    if processed_photos:
        ctx.report.info(name, f"оброблено фото з Google Drive у {processed_photos} рядках")
    return TableResult(out, updates)


def export_all_sheets(client, t: dict, ctx: Context) -> TableResult:
    """Усі аркуші таблиці (розклади, заміни…) у форматі, який очікує сайт:
    [{templFile: <назва аркуша>, header: [[...]], data: [[...], ...]}, ...]"""
    out = []
    for title, values in client.all_sheets_raw(t["id"]):
        out.append(
            {
                "templFile": title,
                "header": values[:1],
                "data": [r for r in values[1:] if len(r) > 0],
            }
        )
    ctx.report.info(t["name"], f"аркушів: {len(out)}")
    return TableResult(out)


EXPORTERS = {"rows": export_rows, "all_sheets": export_all_sheets}


def write_json(path: Path, data: object) -> bool:
    """Записує файл лише якщо вміст змінився (менше «порожніх» комітів). True — якщо змінився."""
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True
