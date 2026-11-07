"""Один вхід у Google на весь запуск: Таблиці (gspread) і Drive (через ту саму сесію).

Ключ сервісного акаунта береться (у такому порядку):
  1. зі змінної середовища GOOGLE_SERVICE_ACCOUNT_JSON — вміст JSON-ключа (так працює GitHub Actions);
  2. з файлу, вказаного в config.json → credentials_file (за замовчуванням secrets/service-account.json).
Папка secrets/ у .gitignore — ключ НІКОЛИ не потрапляє в репозиторій.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import gspread
from gspread.http_client import BackOffHTTPClient
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


class GoogleClient:
    def __init__(self, credentials_file: str):
        info = self._load_info(credentials_file)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        self.email = info.get("client_email", "?")
        # BackOff — автоматичні повтори при перевищенні лімітів Google API (429/5xx)
        self.gc = gspread.authorize(creds, http_client=BackOffHTTPClient)
        self.session = AuthorizedSession(creds)
        self._spreadsheets: dict[str, gspread.Spreadsheet] = {}

    @staticmethod
    def _load_info(credentials_file: str) -> dict:
        raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
        if raw:
            return json.loads(raw)
        path = Path(credentials_file)
        if not path.exists():
            raise SystemExit(
                f"❌ Не знайдено ключ Google.\n"
                f"   Покладіть JSON-ключ сервісного акаунта у {path} (локально)\n"
                f"   або задайте змінну GOOGLE_SERVICE_ACCOUNT_JSON (GitHub Actions).\n"
                f"   Інструкція: README.md → «Спершу: замініть ключ Google»."
            )
        return json.loads(path.read_text(encoding="utf-8"))

    # ---------- Таблиці ----------
    def spreadsheet(self, sheet_id: str) -> gspread.Spreadsheet:
        if sheet_id not in self._spreadsheets:
            self._spreadsheets[sheet_id] = self.gc.open_by_key(sheet_id)
        return self._spreadsheets[sheet_id]

    def first_sheet_values(self, sheet_id: str) -> tuple[gspread.Worksheet, list[list[str]]]:
        ws = self.spreadsheet(sheet_id).sheet1
        return ws, ws.get_all_values()

    def all_sheets_raw(self, sheet_id: str, cells: str = "A1:RO10000") -> list[tuple[str, list[list[str]]]]:
        """Усі аркуші одним запитом; рядки «як у Sheets API» (без доповнення порожніми клітинками)."""
        sh = self.spreadsheet(sheet_id)
        titles = [ws.title for ws in sh.worksheets()]
        ranges = [f"'{t}'!{cells}" for t in titles]
        resp = sh.values_batch_get(ranges)
        out = []
        for title, vr in zip(titles, resp.get("valueRanges", [])):
            out.append((title, vr.get("values", [])))
        return out

    # ---------- Drive ----------
    def drive_file_meta(self, file_id: str) -> dict | None:
        r = self.session.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={"fields": "id,name,mimeType,size", "supportsAllDrives": "true"},
            timeout=30,
        )
        return r.json() if r.ok else None

    def drive_download(self, file_id: str) -> tuple[bytes, str] | None:
        """Вміст файлу і його Content-Type. Спершу через API (файли, відкриті сервісному акаунту
        або «всім, хто має посилання»), потім — публічне посилання як запасний варіант."""
        r = self.session.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={"alt": "media", "supportsAllDrives": "true"},
            timeout=120,
        )
        if r.ok and r.content:
            return r.content, r.headers.get("Content-Type", "")
        import requests  # запасний шлях без авторизації

        r = requests.get(
            "https://drive.google.com/uc", params={"export": "download", "id": file_id}, timeout=120
        )
        ctype = r.headers.get("Content-Type", "")
        if r.ok and r.content and "text/html" not in ctype:
            return r.content, ctype
        return None
