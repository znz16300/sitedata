import os
import json
import subprocess

def load_config(config_path="config.json"):
    """Завантажує конфігурацію з JSON-файлу."""
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print("❌ Файл config.json не знайдено!")
        exit(1)
    except json.JSONDecodeError:
        print("❌ Помилка у форматі config.json!")
        exit(1)

def run_git_command(command, repo_path):
    """Виконує Git-команду в заданому репозиторії."""
    try:
        result = subprocess.run(command, cwd=repo_path, text=True, check=True, capture_output=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Помилка при виконанні команди {command}: {e.stderr}")
        exit(1)

def push_to_github():
    """Основна функція для пушу змін у GitHub."""
    config = load_config()
    repo_paths = config["repo_path"]
    branch = config["branch"]
    commit_message = config["commit_message"]

    # Перевіряємо наявність змін у всіх файлах репозиторію
    result = subprocess.run(["git", "status", "--porcelain"], cwd='', text=True, capture_output=True)

    # Виконуємо команди Git для додавання змін в основному репозиторії
    run_git_command(["git", "add", "."], '')
    run_git_command(["git", "commit", "-m", commit_message], '')
    run_git_command(["git", "push", "origin", branch], '')

    print(f"✅ Зміни успішно запушені у GitHub для репозиторію: {''}")

if __name__ == "__main__":
    push_to_github()
