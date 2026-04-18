import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Ваш ID таблицы
SHEET_ID = "1ABCdefGHIjklMNOpqrSTUvwxYZ1234567"  # Замените!

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('google_credentials.json', scope)
client = gspread.authorize(creds)

# Открываем таблицу
sheet = client.open_by_key(SHEET_ID).sheet1

# Добавляем тестовую строку
sheet.append_row(['1', '123456', '@test', 'Иван', 'Python', '3 года', '+7999', 'a@mail.ru', 'текст', 'Новая', '2024-01-01 12:00'])

print("✅ Данные добавлены! Проверьте таблицу.")