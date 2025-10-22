"""
Windows Compatibility Module
Исправления для совместимости с Windows
"""

import os
import sys
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Union


def is_windows() -> bool:
    """Проверка, что система Windows"""
    return platform.system().lower() == "windows"


def get_windows_temp_dir() -> str:
    """Получение временной директории для Windows"""
    if is_windows():
        # Используем системную временную директорию Windows
        temp_dir = os.environ.get('TEMP') or os.environ.get('TMP') or tempfile.gettempdir()
        # Создаем подпапку для проекта
        project_temp = os.path.join(temp_dir, 'instagram_uploader')
        os.makedirs(project_temp, exist_ok=True)
        return project_temp
    else:
        return tempfile.gettempdir()


def normalize_path(path: str) -> str:
    """Нормализация пути для Windows"""
    if is_windows():
        # Заменяем прямые слеши на обратные для Windows
        return path.replace('/', '\\')
    return path


def get_project_root() -> str:
    """Получение корневой директории проекта"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Ищем manage.py в родительских директориях
    for _ in range(5):  # Ограничиваем поиск 5 уровнями
        if os.path.exists(os.path.join(current_dir, 'manage.py')):
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:  # Достигли корня файловой системы
            break
        current_dir = parent_dir
    
    # Fallback - возвращаем текущую директорию
    return os.getcwd()


def setup_windows_environment():
    """Настройка окружения для Windows"""
    if not is_windows():
        return
    
    # Добавляем корневую директорию проекта в sys.path
    project_root = get_project_root()
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Настройка переменных окружения для Windows
    os.environ.setdefault('PYTHONPATH', project_root)
    os.environ.setdefault('TEMP_DIR', get_windows_temp_dir())
    
    # Отключаем некоторые проверки Playwright для Windows
    os.environ.setdefault('PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS', '1')
    os.environ.setdefault('PLAYWRIGHT_QUIET', '1')


def run_subprocess_windows(
    cmd: List[str],
    timeout: int = 300,
    cwd: Optional[str] = None,
    capture_output: bool = True,
    text: bool = True
) -> subprocess.CompletedProcess:
    """
    Запуск subprocess с Windows-совместимыми настройками
    """
    if not is_windows():
        return subprocess.run(
            cmd, 
            timeout=timeout, 
            cwd=cwd, 
            capture_output=capture_output, 
            text=text
        )
    
    # Windows-специфичные настройки
    startupinfo = None
    if hasattr(subprocess, 'STARTUPINFO'):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    
    # Используем shell=True для Windows, если команда содержит переменные окружения
    use_shell = any('$' in arg or '%' in arg for arg in cmd)
    
    try:
        return subprocess.run(
            cmd,
            timeout=timeout,
            cwd=cwd or get_project_root(),
            capture_output=capture_output,
            text=text,
            startupinfo=startupinfo,
            shell=use_shell
        )
    except subprocess.TimeoutExpired:
        # Принудительное завершение процессов на Windows
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if any(any(arg in str(cmdline) for arg in cmd) for arg in cmd):
                        proc.terminate()
                        proc.wait(timeout=5)
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    pass
        except ImportError:
            pass
        raise


def get_python_executable() -> str:
    """Получение пути к исполняемому файлу Python"""
    if is_windows():
        # На Windows используем sys.executable
        return sys.executable
    else:
        # На Unix-системах используем 'python'
        return 'python'


def create_windows_safe_temp_file(suffix: str = '', prefix: str = 'tmp') -> str:
    """Создание временного файла, безопасного для Windows"""
    temp_dir = get_windows_temp_dir()
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=temp_dir)
    os.close(fd)
    return path


def cleanup_windows_temp_files():
    """Очистка временных файлов на Windows"""
    if not is_windows():
        return
    
    temp_dir = get_windows_temp_dir()
    try:
        for file in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file)
            try:
                if os.path.isfile(file_path):
                    # Проверяем, что файл не используется
                    if not is_file_in_use(file_path):
                        os.remove(file_path)
            except (OSError, PermissionError):
                # Игнорируем ошибки доступа
                pass
    except (OSError, PermissionError):
        # Игнорируем ошибки доступа к директории
        pass


def is_file_in_use(file_path: str) -> bool:
    """Проверка, используется ли файл другим процессом"""
    if not is_windows():
        return False
    
    try:
        with open(file_path, 'r+b') as f:
            return False
    except (OSError, PermissionError):
        return True


def get_windows_browser_path() -> str:
    """Получение пути к браузерам Playwright на Windows"""
    if is_windows():
        # На Windows браузеры устанавливаются в пользовательскую директорию
        user_home = os.path.expanduser('~')
        browser_path = os.path.join(user_home, 'AppData', 'Local', 'ms-playwright')
        if os.path.exists(browser_path):
            return browser_path
        else:
            # Fallback - используем системную директорию
            return os.path.join(os.getcwd(), 'browsers')
    else:
        return os.path.join(os.getcwd(), 'browsers')


def fix_windows_paths():
    """Исправление путей для Windows"""
    if not is_windows():
        return
    
    # Создаем необходимые директории
    directories = ['logs', 'media', 'staticfiles', 'prepared_videos', 'temp']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)


def get_windows_dolphin_api_url() -> str:
    """Получение URL для Dolphin API на Windows"""
    if is_windows():
        # На Windows используем localhost для локального запуска
        return "http://localhost:3001/v1.0"
    else:
        # На других системах используем стандартный URL
        return "http://localhost:3001/v1.0"


def setup_windows_logging():
    """Настройка логирования для Windows"""
    if not is_windows():
        return
    
    import logging
    
    # Use centralized logging - all logs go to django.log through Django configuration
    # No need for basicConfig - Django handles all logging configuration


# Автоматическая настройка при импорте модуля
setup_windows_environment()
fix_windows_paths()
setup_windows_logging() 