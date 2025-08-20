import os
import json
import pytest
import tempfile
import shutil
import sqlite3
from unittest.mock import MagicMock, patch, call
from fastapi.testclient import TestClient
from src.api import app
from src.db import DataBase
from src import logger


# # Фикстура для изолированной базы данных
# @pytest.fixture(scope="function")
# def db():
#     # Создаем временную базу данных на диске для решения проблем с потоками
#     db_path = tempfile.mktemp(suffix='.db')
#     test_db = DataBase(db_path)
#     test_db.create_table('accounts', (
#         ('username', 'TEXT UNIQUE'),
#         ('password', 'TEXT'),
#         ('email_username', 'TEXT'),
#         ('email_password', 'TEXT'),
#         ('cookies', 'TEXT'),
#         ('proxy', 'TEXT')
#     ))
#     yield test_db
#     test_db.close()
#     if os.path.exists(db_path):
#         os.remove(db_path)
#
#
# # Фикстура для тестового клиента
# @pytest.fixture(scope="function")
# def client(db):
#     # Передаем базу данных в приложение
#     app.db = db
#     with TestClient(app) as client:
#         yield client
#
#
# # Фикстура для временных директорий
# @pytest.fixture(scope="function")
# def temp_dirs(monkeypatch):
#     base_dir = tempfile.mkdtemp()
#     dirs = {
#         "base": base_dir,
#         "videos": os.path.join(base_dir, "videos"),
#         "titles": os.path.join(base_dir, "titles"),
#         "accounts": os.path.join(base_dir, "accounts"),
#         "proxy": os.path.join(base_dir, "proxy")
#     }
#
#     # Создаем директории
#     for d in dirs.values():
#         os.makedirs(d, exist_ok=True)
#
#     # Монкируем пути в приложении
#     def mock_abspath(path):
#         if path == __file__:
#             return os.path.join(base_dir, "src", "api.py")
#         return os.path.abspath(path)
#
#     monkeypatch.setattr("src.api.os.path.abspath", mock_abspath)
#
#     # Создаем структуру проекта
#     os.makedirs(os.path.join(base_dir, "src"))
#     with open(os.path.join(base_dir, "src", "api.py"), "w") as f:
#         f.write("# Mocked file")
#
#     yield dirs
#     shutil.rmtree(base_dir)
#
#
# # Фикстура для мока Dolphin
# @pytest.fixture(scope="function")
# def dolphin_mock():
#     mock = MagicMock()
#     app.dolphin = mock
#     yield mock
#
#
# # Тесты для модуля загрузки
# def test_prepare_accounts_upload(client, db, requests_mock):
#     # Настраиваем мок для внешнего API
#     mock_data = {
#         "accounts": [
#             {"username": "user1", "password": "pass1", "email_username": "email1", "email_password": "pass1",
#              "cookies": "cookie1"},
#             {"username": "user2", "password": "pass2", "email_username": "email2", "email_password": "pass2",
#              "cookies": "cookie2"}
#         ]
#     }
#     requests_mock.get(
#         "http://91.108.227.166/get-accounts",
#         json=mock_data,
#         status_code=200
#     )
#
#     response = client.post("/upload/prepare_accounts", json={"count": 2})
#     assert response.status_code == 200
#     assert response.json() == {"message": "Accounts prepared successfully"}
#
#     # Проверяем записи в БД
#     accounts = db.select("accounts")
#     assert len(accounts) == 2
#     assert accounts[0]["username"] == "user1"
#     assert accounts[1]["email_username"] == "email2"
#
#
# def test_upload_videos(client, temp_dirs):
#     # Создаем тестовые файлы
#     files = [
#         ("files", ("video1.mp4", b"video content 1", "video/mp4")),
#         ("files", ("video2.mp4", b"video content 2", "video/mp4"))
#     ]
#
#     response = client.post("/upload/upload_videos/", files=files)
#     assert response.status_code == 200
#     assert response.json() == {"message": "Videos uploaded successfully"}
#
#     # Проверяем сохранение файлов
#     videos_dir = temp_dirs["videos"]
#     assert os.path.exists(videos_dir)
#     assert "video1.mp4" in os.listdir(videos_dir)
#     assert "video2.mp4" in os.listdir(videos_dir)
#
#
# def test_upload_titles(client, temp_dirs):
#     # Создаем тестовый файл
#     file_content = b"Title 1\nTitle 2\nTitle 3"
#     files = {"file": ("titles.txt", file_content, "text/plain")}
#
#     response = client.post("/upload/upload_titles", files=files)
#     assert response.status_code == 200
#     assert response.json() == {"message": "Titles file uploaded successfully"}
#
#     # Проверяем сохранение файла
#     titles_dir = temp_dirs["titles"]
#     assert "titles.txt" in os.listdir(titles_dir)
#     with open(os.path.join(titles_dir, "titles.txt"), "rb") as f:
#         assert f.read() == file_content
#
#
# def test_prepare_config(client, db, temp_dirs):
#     # Добавляем аккаунты в БД
#     db.insert("accounts", {"username": "user1"})
#     db.insert("accounts", {"username": "user2"})
#
#     # Создаем тестовые видео и заголовки
#     videos_dir = temp_dirs["videos"]
#     with open(os.path.join(videos_dir, "video1.mp4"), "wb") as f:
#         f.write(b"video1")
#     with open(os.path.join(videos_dir, "video2.mp4"), "wb") as f:
#         f.write(b"video2")
#
#     titles_dir = temp_dirs["titles"]
#     with open(os.path.join(titles_dir, "titles.txt"), "w") as f:
#         f.write("Title 1\nTitle 2")
#
#     data = {
#         "music_name": "test_music",
#         "location": "test_location",
#         "mentions": ["@user1", "@user2"],
#         "upload_cycles": "1"
#     }
#
#     response = client.post("/upload/prepare_config", json=data)
#     assert response.status_code == 200
#     assert os.path.exists(os.path.join(temp_dirs["base"], "config.json"))
#
#     # Проверяем содержимое конфига
#     with open(os.path.join(temp_dirs["base"], "config.json")) as f:
#         config = json.load(f)
#         assert config["music_name"] == "test_music"
#         assert config["location"] == "test_location"
#         assert config["mentions"] == ["@user1", "@user2"]
#         assert len(config["accounts"]) == 2
#         assert {acc["name"] for acc in config["accounts"]} == {"user1", "user2"}
#
#
# @patch("src.api.send_message")
# @patch("src.api.main_upload_loop")
# def test_start_upload(mock_upload_loop, mock_send, client, temp_dirs):
#     # Создаем тестовый конфиг
#     config = {
#         "accounts": [{"name": "test_user", "video": "test.mp4", "title": "Test"}],
#         "music_name": "test",
#         "location": "test",
#         "mentions": []
#     }
#     config_path = os.path.join(temp_dirs["base"], "config.json")
#     with open(config_path, "w") as f:
#         json.dump(config, f)
#
#     # Добавляем аккаунт в БД
#     client.app.db.insert("accounts", {
#         "username": "test_user",
#         "cookies": "test_cookies"
#     })
#
#     response = client.post("/upload/start_upload")
#     assert response.status_code == 200
#     mock_upload_loop.assert_called_once()
#     mock_send.assert_called()
#
#
# # Тесты для модуля прогрева
# def test_upload_accounts_booster(client, temp_dirs):
#     file_content = b"user1:pass1:email1:pass1\nuser2:pass2:email2:pass2"
#     files = {"file": ("accounts.txt", file_content, "text/plain")}
#
#     response = client.post("/booster/upload_accounts", files=files)
#     assert response.status_code == 200
#     assert response.json() == {"message": "Accounts file uploaded successfully"}
#
#     # Проверяем сохранение файла
#     accounts_dir = temp_dirs["accounts"]
#     assert "accounts.txt" in os.listdir(accounts_dir)
#     with open(os.path.join(accounts_dir, "accounts.txt"), "rb") as f:
#         assert f.read() == file_content
#
#
# def test_upload_proxies(client, temp_dirs):
#     file_content = b"host1:port1@user1:pass1\nhost2:port2@user2:pass2"
#     files = {"file": ("proxies.txt", file_content, "text/plain")}
#
#     response = client.post("/booster/upload_proxies", files=files)
#     assert response.status_code == 200
#     assert response.json() == {"message": "Proxy file uploaded successfully"}
#
#     # Проверяем сохранение файла
#     proxy_dir = temp_dirs["proxy"]
#     assert "proxies.txt" in os.listdir(proxy_dir)
#     with open(os.path.join(proxy_dir, "proxies.txt"), "rb") as f:
#         assert f.read() == file_content
#
#
# @patch("src.api.dolphin")
# def test_prepare_accounts_booster(mock_dolphin, client, db, temp_dirs):
#     # Создаем тестовые файлы
#     accounts_dir = temp_dirs["accounts"]
#     with open(os.path.join(accounts_dir, "acc.txt"), "w") as f:
#         f.write("user1:pass1:email1:pass1\nuser2:pass2:email2:pass2")
#
#     proxy_dir = temp_dirs["proxy"]
#     with open(os.path.join(proxy_dir, "proxy.txt"), "w") as f:
#         f.write("host1:port1@user1:pass1\nhost2:port2@user2:pass2")
#
#     # Настраиваем мок Dolphin
#     mock_profile = MagicMock()
#     mock_dolphin.get_profiles.return_value = []
#     mock_dolphin.make_profile.return_value = mock_profile
#
#     response = client.post("/booster/prepare_accounts")
#     assert response.status_code == 200
#     data = response.json()
#     assert data["message"] == "Accounts prepared successfully"
#     assert data["inserted_accounts"] == 2
#     assert data["processed_profiles"] == 2
#
#     # Проверяем записи в БД
#     accounts = db.select("accounts")
#     assert len(accounts) == 2
#     assert {acc["username"] for acc in accounts} == {"user1", "user2"}
#
#
# @patch("src.api.send_message")
# @patch("src.api.main_booster_loop")
# def test_start_booster(mock_booster_loop, mock_send, client, db):
#     # Добавляем тестовый аккаунт
#     db.insert("accounts", {"username": "test_user"})
#
#     response = client.post("/booster/start_booster")
#     assert response.status_code == 200
#     assert response.json() == {"message": "Booster finished"}
#     mock_booster_loop.assert_called_once()
#     mock_send.assert_called()
#
#
# # Тесты для основных функций
# @patch("src.api.Uploader")
# @patch("src.api.Auth")
# @patch("src.api.Video")
# def test_main_upload_loop(mock_video, mock_auth, mock_uploader, dolphin_mock, db):
#     # Настройка тестовых данных
#     config = {
#         "accounts": [
#             {"name": "user1", "video": "video1.mp4", "title": "Title 1"},
#             {"name": "user2", "video": "video2.mp4", "title": "Title 2"}
#         ]
#     }
#
#     # Настройка моков
#     mock_playwright = MagicMock()
#     mock_profile = MagicMock()
#     dolphin_mock.get_profile_by_name.return_value = mock_profile
#
#     # Мок для базы данных
#     db.insert("accounts", {"username": "user1", "cookies": "cookies1"})
#     db.insert("accounts", {"username": "user2", "cookies": "cookies2"})
#
#     # Вызов тестируемой функции
#     from src.api import main_upload_loop
#     main_upload_loop(config, mock_playwright)
#
#     # Проверки
#     assert dolphin_mock.get_profile_by_name.call_count == 2
#     assert mock_profile.import_cookies.call_count == 2
#     assert mock_uploader.return_value.upload_videos.call_count == 2
#
#
# @patch("src.api.Booster")
# @patch("src.api.Auth")
# def test_main_booster_loop(mock_auth, mock_booster, dolphin_mock, db):
#     # Подготовка тестовых данных
#     accounts = [
#         {"username": "user1", "password": "pass1", "email_username": "email1", "email_password": "pass1"},
#         {"username": "user2", "password": "pass2", "email_username": "email2", "email_password": "pass2"}
#     ]
#
#     # Настройка моков
#     mock_playwright = MagicMock()
#     mock_profile = MagicMock()
#     dolphin_mock.get_profile_by_name.return_value = mock_profile
#
#     mock_auth_instance = MagicMock()
#     mock_auth.return_value = mock_auth_instance
#     mock_auth_instance.authenticate.return_value = "page_object"
#
#     # Вызов тестируемой функции
#     from src.api import main_booster_loop
#     main_booster_loop(accounts, mock_playwright)
#
#     # Проверки
#     assert mock_auth.call_count == 2
#     mock_booster.assert_called_with(mock_auth_instance)
#     assert mock_booster.return_value.start.call_count == 2