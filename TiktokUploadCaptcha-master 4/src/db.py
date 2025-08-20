import sqlite3
import threading
from contextlib import contextmanager
import json

from src import logger


class DataBase:
    def __init__(self, db_file='database.db'):
        """
        Инициализация подключения к базе данных SQLite.
        Каждое соединение будет привязано к потоку.

        :param db_file: Путь к файлу базы данных SQLite
        """
        self.db_file = db_file
        self.local = threading.local()
        logger.info(f"Database connection pool initialized for file: {db_file}")

    @contextmanager
    def _get_connection(self):
        """
        Контекстный менеджер для получения соединения с БД,
        привязанного к текущему потоку.
        """
        # Создаем новое соединение для потока, если его нет
        if not hasattr(self.local, 'conn') or self.local.conn is None:
            self.local.conn = sqlite3.connect(self.db_file)
            self.local.conn.row_factory = sqlite3.Row
            logger.debug(f"Created new DB connection in thread: {threading.get_ident()}")

        try:
            yield self.local.conn
        finally:
            # Не закрываем соединение здесь - оно будет переиспользоваться в потоке
            pass

    def close(self):
        """
        Закрывает все соединения с базой данных во всех потоках.
        """
        if hasattr(self.local, 'conn') and self.local.conn:
            self.local.conn.close()
            self.local.conn = None
            logger.info("Database connection closed")

    def execute(self, query, params=()):
        """
        Выполняет SQL-запрос без возврата результата.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                conn.commit()
                logger.info(f"Executed query: {query} with params: {params}")
            except Exception as e:
                logger.log_err()
                raise

    def fetch_all(self, query, params=()):
        """
        Выполняет SQL-запрос и возвращает все результаты.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                results = cursor.fetchall()
                logger.info(f"Fetched all results for query: {query} with params: {params}")
                return results
            except Exception as e:
                logger.log_err()
                raise

    def fetch_one(self, query, params=()):
        """
        Выполняет SQL-запрос и возвращает одну строку результата.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                result = cursor.fetchone()
                logger.info(f"Fetched one result for query: {query} with params: {params}")
                return result
            except Exception as e:
                logger.log_err()
                raise

    def create_table(self, table_name, columns):
        """
        Создает таблицу, если она не существует.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                column_defs = ', '.join([f"{col[0]} {col[1]}" for col in columns])
                query = f'CREATE TABLE IF NOT EXISTS {table_name} ({column_defs})'
                cursor.execute(query)
                conn.commit()
                logger.info(f"Created table: {table_name} with columns: {column_defs}")
            except Exception as e:
                logger.log_err()
                raise

    def insert(self, table_name, data):
        """
        Вставляет одну строку в таблицу.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                values = tuple(data.values())
                query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                cursor.execute(query, values)
                conn.commit()
                logger.info(f"Inserted data into {table_name}: {data}")
            except Exception as e:
                logger.log_err()
                raise

    def select(self, table_name, columns='*', where=None, params=()):
        """
        Получает список строк из таблицы по условию.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                query = f"SELECT {columns} FROM {table_name}"
                if where:
                    query += f" WHERE {where}"
                cursor.execute(query, params)
                results = cursor.fetchall()
                logger.info(f"Selected data from {table_name} with where: {where}")
                return results
            except Exception as e:
                logger.log_err()
                raise

    def select_one(self, table_name, columns='*', where=None, params=()):
        """
        Получает одну строку из таблицы по условию.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                query = f"SELECT {columns} FROM {table_name}"
                if where:
                    query += f" WHERE {where}"
                cursor.execute(query, params)
                result = cursor.fetchone()
                logger.info(f"Selected one row from {table_name} with where: {where}")
                return result
            except Exception as e:
                logger.log_err()
                raise

    def update(self, table_name, data, where=None, params=()):
        """
        Обновляет строки в таблице.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                set_clause = ', '.join([f"{col} = ?" for col in data.keys()])
                values = tuple(data.values())
                query = f"UPDATE {table_name} SET {set_clause}"
                if where:
                    query += f" WHERE {where}"
                    values += tuple(params)
                cursor.execute(query, values)
                conn.commit()
                logger.info(f"Updated {table_name} with data: {data} where: {where}")
            except Exception as e:
                logger.log_err()
                raise

    def delete(self, table_name, where=None, params=()):
        """
        Удаляет строки из таблицы по условию.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                query = f"DELETE FROM {table_name}"
                if where:
                    query += f" WHERE {where}"
                cursor.execute(query, params)
                conn.commit()
                logger.info(f"Deleted from {table_name} where: {where}")
            except Exception as e:
                logger.log_err()
                raise

    def insert_and_get_id(self, table_name, data, id_column='id'):
        """
        Вставляет строку и возвращает ID новой записи.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                values = tuple(data.values())
                query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                cursor.execute(query, values)
                conn.commit()
                row_id = cursor.lastrowid
                logger.info(f"Inserted data into {table_name} and got ID: {row_id}")
                return row_id
            except Exception as e:
                logger.log_err()
                raise