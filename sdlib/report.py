"""Звіт про запуск: у консоль і (на GitHub) — у підсумок запуску Actions."""
from __future__ import annotations

import os
from collections import defaultdict


class Report:
    def __init__(self) -> None:
        self.lines: dict[str, list[str]] = defaultdict(list)
        self.warnings: dict[str, list[str]] = defaultdict(list)
        self.errors: dict[str, list[str]] = defaultdict(list)

    def info(self, table: str, msg: str) -> None:
        print(f"  {msg}")
        self.lines[table].append(msg)

    def warn(self, table: str, msg: str) -> None:
        print(f"  ⚠️  {msg}")
        self.warnings[table].append(msg)

    def error(self, table: str, msg: str) -> None:
        print(f"  ❌ {msg}")
        self.errors[table].append(msg)

    @property
    def has_errors(self) -> bool:
        return any(self.errors.values())

    def write_github_summary(self, changed_files: list[str]) -> None:
        path = os.environ.get("GITHUB_STEP_SUMMARY")
        if not path:
            return
        out = ["## Оновлення даних сайту", ""]
        out.append(f"Змінено файлів: **{len(changed_files)}**" if changed_files else "Змін немає.")
        tables = list(dict.fromkeys([*self.lines, *self.warnings, *self.errors]))
        for t in tables:
            out += ["", f"### {t}"]
            out += [f"- {m}" for m in self.lines[t]]
            out += [f"- ⚠️ {m}" for m in self.warnings[t]]
            out += [f"- ❌ {m}" for m in self.errors[t]]
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
