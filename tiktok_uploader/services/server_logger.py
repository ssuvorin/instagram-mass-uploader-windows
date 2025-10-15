"""
Server Operations Logger
========================

Логирование всех операций с серверами в отдельный файл.
"""

import logging
import os
from datetime import datetime
from pathlib import Path


class ServerLogger:
    """Логгер для операций с серверами"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        # Создаем директорию logs если её нет
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Настраиваем логгер
        self.logger = logging.getLogger('tiktok_server_operations')
        self.logger.setLevel(logging.INFO)
        
        # Очищаем существующие handlers
        self.logger.handlers.clear()
        
        # File handler
        log_file = log_dir / 'server_operations.log'
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Console handler (optional)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_server_added(self, server_name, host, port, user=None):
        """Лог добавления сервера"""
        user_str = f" by {user}" if user else ""
        self.logger.info(f"SERVER ADDED: {server_name} ({host}:{port}){user_str}")
    
    def log_server_edited(self, server_name, changes, user=None):
        """Лог редактирования сервера"""
        user_str = f" by {user}" if user else ""
        changes_str = ", ".join([f"{k}={v}" for k, v in changes.items()])
        self.logger.info(f"SERVER EDITED: {server_name} - {changes_str}{user_str}")
    
    def log_server_deleted(self, server_name, user=None):
        """Лог удаления сервера"""
        user_str = f" by {user}" if user else ""
        self.logger.info(f"SERVER DELETED: {server_name}{user_str}")
    
    def log_ping(self, server_name, success, response_time=None, error=None):
        """Лог проверки доступности"""
        if success:
            self.logger.info(f"PING SUCCESS: {server_name} - {response_time:.0f}ms")
        else:
            self.logger.warning(f"PING FAILED: {server_name} - {error}")
    
    def log_ping_all(self, total, online_count, offline_count):
        """Лог массовой проверки"""
        self.logger.info(f"PING ALL: {total} servers checked - {online_count} online, {offline_count} offline")
    
    def log_task_created(self, server_name, task_type, task_name, user=None):
        """Лог создания задачи"""
        user_str = f" by {user}" if user else ""
        self.logger.info(f"TASK CREATED: {task_type} '{task_name}' on {server_name}{user_str}")
    
    def log_task_started(self, server_name, task_name, remote_task_id):
        """Лог запуска задачи"""
        self.logger.info(f"TASK STARTED: '{task_name}' on {server_name} (remote_id: {remote_task_id})")
    
    def log_task_stopped(self, server_name, task_name, user=None):
        """Лог остановки задачи"""
        user_str = f" by {user}" if user else ""
        self.logger.info(f"TASK STOPPED: '{task_name}' on {server_name}{user_str}")
    
    def log_task_completed(self, server_name, task_name):
        """Лог завершения задачи"""
        self.logger.info(f"TASK COMPLETED: '{task_name}' on {server_name}")
    
    def log_task_failed(self, server_name, task_name, error):
        """Лог ошибки задачи"""
        self.logger.error(f"TASK FAILED: '{task_name}' on {server_name} - {error}")
    
    def log_error(self, operation, error_message):
        """Лог общей ошибки"""
        self.logger.error(f"ERROR in {operation}: {error_message}")


# Singleton instance
server_logger = ServerLogger()

