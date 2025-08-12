# Интеграция Bulk Worker Service с UI

Этот документ описывает, как UI должен взаимодействовать с изолированным модулем `modules/bulk_worker_service` (FastAPI) для запуска массовых загрузок. Сейчас веб-часть не содержит этих эндпоинтов — они будут добавлены позднее. Модуль воркера уже готов к pull‑режиму.

## Что должно быть в вебе (для pull‑режима)
Реализовать следующие защищённые эндпоинты (Bearer-токен), чтобы воркер мог работать удалённо:
- `GET /api/bulk-tasks/{id}/aggregate` — агрегат задачи:
  - Список аккаунтов (`account_task_id`, `account{username,password,tfa_secret,email_username,email_password,dolphin_profile_id,proxy}`)
  - Список видео (`id, order, title, location, mentions`)
  - `default_location`, `default_mentions`
- `GET /api/media/{video_id}/download` — поток файла видео.
- `POST /api/bulk-tasks/{id}/status` — обновление статуса задачи и логов `{status?, log?, log_append?}`.
- `POST /api/bulk-accounts/{account_task_id}/status` — обновление статуса аккаунта и логов `{status?, log_append?}`.
- `POST /api/bulk-accounts/{account_task_id}/counters` — инкремент счётчиков `{success, failed}`.

Рекомендации безопасности:
- Переменная окружения `WORKER_API_TOKEN`; заголовок `Authorization: Bearer <WORKER_API_TOKEN>`.
- HTTPS между UI и воркером; ограниченный IP-список для воркеров.

## Поток запуска
1. В UI создаётся `BulkUploadTask`, привязываются аккаунты/видео/титулы/локация/упоминания.
2. В UI отправляется запрос на воркер:
   ```json
   POST http://<worker_host>:8088/api/v1/bulk-tasks/start
   { "mode": "pull", "task_id": 123, "options": { "concurrency": 2, "headless": true } }
   ```
3. Воркер вызывает UI API (см. список выше):
   - тянет агрегат,
   - скачивает медиа,
   - пишет статусы/логи/счётчики.
4. UI отображает прогресс в реальном времени (polling/WS) по данным из БД.

## Состояние на сейчас
- Воркера можно разворачивать и тестировать локально (см. `modules/bulk_worker_service/README.md`).
- Веб-эндпоинты для pull‑режима не включены — их нужно будет добавить при интеграции.

## Масштабирование
- Несколько воркеров на Windows-серверах, ограничения параллельности и батчи настроены в воркере.
- Веб: добавить блокировки аккаунтов на уровне БД при старте задач для эксклюзивного выполнения.

## Расширения в будущем
- Поддержка push‑режима (UI отправляет агрегат и медиа напрямую на воркер) — модуль уже готов к этому режиму, но по умолчанию используем pull.
- Вынесение warmup/bulk-login/avatar/bio/follow в такие же интерфейсы. 