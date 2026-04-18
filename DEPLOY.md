# Деплой на Render.com

## Пошаговая инструкция

### 1. Подготовка

Убедитесь, что у вас есть:
- Аккаунт на [Render.com](https://render.com) (бесплатный)
- Все файлы проекта готовы:
  - `main.py` — основной код бота
  - `database.py` — модуль SQLite
  - `requirements.txt` — зависимости
  - `Dockerfile` — конфигурация Docker
  - `.dockerignore` — исключения для Docker
  - `halogen-byte-493719-c8-a029f4c82941.json` — ключ Google Sheets

### 2. Регистрация на Render.com

1. Перейдите на https://render.com
2. Нажмите "Get Started for Free"
3. Зарегистрируйтесь через GitHub или email

### 3. Создание Web Service

1. В Dashboard нажмите **"New +"** → **"Web Service"**
2. Выберите способ деплоя:
   - **Option A: Deploy from GitHub repo** (рекомендуется)
     - Подключите GitHub
     - Выберите репозиторий с проектом
   - **Option B: Deploy from Docker image**
     - Выполните шаги 4 и 5 локально, затем загрузите

### 4. Настройка Environment Variables

В Render Dashboard → ваш сервис → **Environment** добавьте:

```
BOT_TOKEN=8642122641:AAGTS6TDe2srWAOn3ZQXIbXR1eOfCdiZxnw
ADMIN_ID=1023041853,1407010331,977618042
SHEET_ID=1_s7oYGpUvR3QTMapZmRgDWQwECC1BggvnUQQcFTQnwo
GOOGLE_CREDS_JSON=halogen-byte-493719-c8-a029f4c82941.json
DATA_DIR=/app/data
```

⚠️ **Важно**: Загрузите файл `halogen-byte-493719-c8-a029f4c82941.json` в корень проекта через:
- Dashboard → Files (для загрузки секретов)
- Или используйте Render Secrets (рекомендуется для production)

### 5. Настройка Build & Start

В настройках сервиса:

**Build Command:**
```
docker build -t bot .
```

**Start Command:**
```
docker run -p 10000:10000 bot
```

Или для Docker-опыта Render использует автоматически `Dockerfile`.

### 6. Запуск

1. Нажмите **"Create Web Service"**
2. Дождитесь билда (2-5 минут)
3. Сервис автоматически запустится

### 7. Проверка логов

Dashboard → ваш сервис → **Logs**

Должно появиться:
```
[INFO] Bot started
```

### 8. Проверка работы

- Отправьте `/start` боту
- Проверьте, что заявки записываются в Google Sheets
- Проверьте `/admin` для админов

## Важные моменты

### Бесплатный tier (Free)
- Сервис "засыпает" после 15 минут без активности
- При первом запросе просыпается (задержка 30-60 сек)
- Для постоянной работы используйте cron-задачу (ping каждые 10 мин)

### SQLite на Render
- Файловая система эфемерная (при перезапуске данные сохраняются, но лучше бэкапить)
- БД хранится в `/app/data/applications.db`

### Google Sheets на Render
- Убедитесь, что таблица расшарена на `service-account@halogen-byte-493719-c8.iam.gserviceaccount.com`
- Проверьте логи на ошибки `[ERROR] Google Sheets`

## Альтернатива: GitHub → Render (лучший способ)

1. Загрузите код на GitHub (без `.env` и `applications.db`!)
2. В Render: New → Web Service → Build and deploy from Git repository
3. Укажите переменные окружения в Dashboard
4. Render автоматически деплоит при push в main

## Troubleshooting

**Ошибка: "chat not found"**
- Админы должны написать боту `/start` хотя бы раз

**Ошибка: Google Sheets не работает**
- Проверьте, что файл `halogen-byte-493719-c8-a029f4c82941.json` загружен
- Проверьте `SHEET_ID` и права доступа

**Бот не отвечает**
- Проверьте логи в Render Dashboard
- Убедитесь, что `BOT_TOKEN` правильный
