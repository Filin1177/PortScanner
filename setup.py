# setup.py - конфигурация сборки cx_Freeze
import sys
import os
from cx_Freeze import setup, Executable

# Базовые настройки
APP_NAME = "AdvancedPortScanner"
VERSION = "2.0"
DESCRIPTION = "Advanced Port Scanner with GUI"
AUTHOR = "cx_Freeze_build-3-1-4"

# Определяем базовые настройки для Windows
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # Для GUI приложений без консоли

# Пути
base_dir = os.path.dirname(os.path.abspath(__file__))

# Файлы для включения в сборку
include_files = [
    ("pepper.txt", "pepper.txt"),
    ("backups", "backups"),
    ("old", "old"),
]

# Пакеты и модули для включения
packages = [
    "tkinter",
    "socket",
    "threading",
    "queue",
    "json",
    "os",
    "time",
    "subprocess",
    "platform",
    "webbrowser",
    "datetime",
    "urllib",
    "requests",
    "concurrent",
    "hashlib",
    "random",
    "ssl",  # Для безопасных запросов
]


# Настройки сборки
build_exe_options = {
    "packages": packages,
#    "excludes": excludes,
    "include_files": include_files,
#    "include_msvcr": True,  # Включаем Visual C++ Runtime
    "optimize": 2,
    "zip_include_packages": ["*"],
    "zip_exclude_packages": [],  # Можно оставить пустым
    "silent": True,
}

# Создаем исполняемый файл
executables = [
    Executable(
        "main_scanner.py",  # Главный файл
        base=base,
        target_name=f"{APP_NAME}.exe",
        icon=None,  # Можно добавить иконку: icon="icon.ico"
        copyright=f"Copyright (C) 2024 {AUTHOR}",
        trademarks="Advanced Port Scanner",
        shortcut_name=APP_NAME,
        shortcut_dir="DesktopFolder",  # Создаст ярлык на рабочем столе
    )
]

setup(
    name=APP_NAME,
    version=VERSION,
    description=DESCRIPTION,
    author=AUTHOR,
    options={
        "build_exe": build_exe_options,
        "bdist_msi": {
            "upgrade_code": "{EFFB6102-3C8A-4F7D-9A5B-1234567890AB}",
            "add_to_path": False,
            "initial_target_dir": f"[ProgramFilesFolder]\\{APP_NAME}",
            "install_icon": None,  # Можно указать иконку для установщика
        }
    },
    executables=executables,
)
