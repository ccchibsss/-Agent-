#!/usr/bin/env python3
"""
Супер-запускатор - всё в одном!
"""
import subprocess
import sys
import os
import venv
from pathlib import Path

def main():
    print("=" * 50)
    print("🚀 Workflow Builder Pro - Автоматический запуск")
    print("=" * 50)
    
    # 1. Создаём виртуальное окружение, если нет
    if not Path("venv").exists():
        print("📦 Создаю виртуальное окружение...")
        venv.create("venv", with_pip=True)
    
    # 2. Определяем путь к python в venv
    if sys.platform == "win32":
        python_path = Path("venv/Scripts/python")
        pip_path = Path("venv/Scripts/pip")
    else:
        python_path = Path("venv/bin/python")
        pip_path = Path("venv/bin/pip")
    
    # 3. Устанавливаем зависимости
    print("📦 Устанавливаю зависимости...")
    subprocess.run([str(pip_path), "install", "--upgrade", "pip"], capture_output=True)
    subprocess.run([str(pip_path), "install", "-r", "requirements.txt"])
    
    # 4. Запускаем приложение
    print("🌟 Запускаю Workflow Builder Pro...")
    print("🌐 Откройте http://localhost:8501\n")
    
    subprocess.run([
        str(python_path), "-m", "streamlit", "run", "app.py",
        "--server.port=8501",
        "--server.address=localhost"
    ])

if __name__ == "__main__":
    main()
