import logging
import os
import platform
import sys
import traceback
from datetime import datetime


class Logger:
    def __init__(self, append=False, debug=True):
        self._log_file = 'log.txt'
        self.is_debug = debug

        # Инициализация файла лога
        if not append:
            if os.path.exists(self._log_file):
                os.remove(self._log_file)
            with open(self._log_file, "w") as log:
                log.write(f'{datetime.today()}\n')
                log.write(f'Platform: {platform.platform()}\n\n')

        # Настройка логгера
        self._log = logging.getLogger('log')
        self._log.setLevel(logging.DEBUG if debug else logging.INFO)
        self._log.handlers = []  # Очистка старых обработчиков

        self._FH = logging.FileHandler(self._log_file, encoding='utf-8')
        self._formatter = logging.Formatter('[%(asctime)s]:[%(levelname)s] %(message)s')
        self._FH.setFormatter(self._formatter)
        self._log.addHandler(self._FH)

        # Запрет распространения на корневой логгер
        self._log.propagate = False

    def log_err(self):
        # Сохраняем оригинальный форматтер
        original_formatter = self._FH.formatter

        # Устанавливаем временный формат для ошибок
        err_formatter = logging.Formatter(
            f'[%(asctime)s] : [%(levelname)s][LINE {self.get_error_line()}] : %(message)s'
        )
        self._FH.setFormatter(err_formatter)

        # Логируем ошибку
        self._log.error(traceback.format_exc())

        # Восстанавливаем оригинальный форматтер
        self._FH.setFormatter(original_formatter)

    def info(self, *args):
        self._log.info(*args)

    def debug(self, *args):
        if self.is_debug:
            self._log.debug(*args)

    def error(self, *args):
        self._log.error(*args)

    def warning(self, *args):
        self._log.warning(*args)

    @staticmethod
    def get_error_line():
        try:
            frame = traceback.extract_tb(sys.exc_info()[2])
            return str(frame[-1].lineno)
        except:
            return "UNKNOWN"
