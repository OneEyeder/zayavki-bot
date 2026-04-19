# Деплой на Render.com (Free Tier) — Native Python

**Docker не нужен!** Render запускает Python напрямую.

## Шаг 1: Подготовка

Убедись, что файл создан:
- `render.yaml` — конфигурация Render (free tier, native Python)

## Шаг 2: Регистрация на Render

1. Перейди на https://render.com
2. Зарегистрируйся через GitHub или email
3. Подтверди email

## Шаг 3: Создание сервиса

**Вариант A: Через Blueprint (render.yaml) — рекомендуется**

1. Загрузи код на GitHub
2. В Render Dashboard нажми **Blueprint**
3. Подключи GitHub репозиторий `zayavki-bot`
4. Render автоматически создаст сервис из `render.yaml`

**Вариант B: Вручную**

1. В Dashboard нажми **New** → **Web Service**
2. Подключи GitHub репозиторий
3. Настройки:
   - **Name**: `zayavki-bot`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: Free
4. Нажми **Create Web Service**

## Шаг 4: Настройка переменных окружения

В разделе **Environment** добавь:

```
BOT_TOKEN=твой_токен_бота
ADMIN_ID=id_админа_или_список_через_запятую
SHEET_ID=id_google_таблицы
GOOGLE_CREDS_JSON=/opt/render/project/src/google-creds.json
DATA_DIR=/opt/render/project/src
```

**Важно**: 
- Для Google ключей есть 2 варианта:
  1. **Secret File**: Загрузи `halogen-byte-493719-c8-a029f4c82941.json` в разделе **Secret Files**, укажи путь
  2. **Inline**: Скопируй содержимое JSON и вставь как значение `GOOGLE_CREDS_JSON` (если Render поддерживает)

## Шаг 5: Деплой

1. Нажми **Manual Deploy** → **Deploy latest commit**
2. Жди сборки (1-2 минуты)
3. Проверь логи в разделе **Logs**

## Шаг 6: Проверка работы

1. Напиши боту `/start`
2. Проверь, что меню появляется
3. Отправь тестовую заявку
4. Проверь, что админ получил уведомление

## Проблемы и решения

### Бот "засыпает" на free tier

**Решение**: Используй UptimeRobot:

1. Зарегистрируйся на https://uptimerobot.com
2. Добавь мониторинг:
   - **Type**: HTTP(s)
   - **URL**: URL твоего сервиса на Render (взять из Dashboard)
   - **Interval**: 5 минут (максимум для free)
3. Это будет "будить" сервис каждые 5 минут

### Ошибка подключения к Google Sheets

Проверь:
- Файл кредов загружен как Secret File
- Переменная `GOOGLE_CREDS_JSON` указывает правильный путь
- Права доступа к таблице настроены для service account

### SQLite база на free tier

На free tier Render пересоздаёт окружение при каждом деплое. **База будет теряться!**

**Решения:**
1. **Использовать PostgreSQL**: Render даёт бесплатный PostgreSQL
2. **Загружать бэкап**: Делать экспорт данных перед деплоем
3. **Google Sheets как основное хранилище**: Не критично если SQLite обнуляется

Для простого бота — SQLite достаточно, просто имей в виду что данные сбросятся при деплое.

## Обновление бота

1. Внеси изменения в код
2. Закоммить и запушь на GitHub
3. В Render Dashboard нажми **Manual Deploy** → **Deploy latest commit**

## Полезные ссылки

- Dashboard: https://dashboard.render.com
- Документация: https://render.com/docs

## Бесплатные ограничения

- **Спящий режим**: После 15 минут бездействия
- **Пробуждение**: ~30 секунд
- **Лимит**: 750 часов/месяц
- **База**: SQLite сбрасывается при деплое (см. выше)
