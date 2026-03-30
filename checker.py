import requests
import pandas as pd
from github import Github
import io
import os
from datetime import datetime

# Берем секреты из настроек GitHub Actions
GITHUB_TOKEN = os.getenv("G_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TG_CHAT_ID, "text": message}, timeout=10)
    except:
        pass

def get_meest_status(track):
    try:
        url = f"https://t.meest-group.com/api/v1/track/{track}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://ua.meest.com/'
        }
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            # Пробуем достать статус из разных полей API
            if 'config' in data and 'status' in data['config']:
                return data['config']['status']
            elif 'events' in data and len(data['events']) > 0:
                return data['events'][0].get('status', 'Обработка')
            return "Данные получены (статус уточняется)"
        return f"Сайт Meest ответил: {r.status_code}"
    except Exception as e:
        return f"Ошибка Meest: {str(e)[:25]}"

def get_np_status(track):
    try:
        url = f"https://tracking.novaposhta.ua/v2/tracking/ru/{track}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get('data'):
                return data['data'][0].get('last_status_ru', 'В пути')
        return f"НП ответила: {r.status_code}"
    except Exception as e:
        return f"Ошибка НП: {str(e)[:25]}"

# --- ОСНОВНОЙ ЦИКЛ ---
try:
    send_telegram("🤖 Робот начал проверку...")
    
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file_content = repo.get_contents("data.csv")
    csv_text = file_content.decoded_content.decode('utf-8')
    
    # Читаем CSV
    df = pd.read_csv(io.StringIO(csv_text))
    
    if df.empty:
        send_telegram("⚠️ В списке посылок пока пусто.")
    else:
        for index, row in df.iterrows():
            track = str(row['track_number']).strip()
            carrier = row['carrier']
            old_status = str(row['status'])
            
            # Определяем новый статус
            if carrier == "Мист Экспресс":
                new_status = get_meest_status(track)
            elif carrier == "Новая почта":
                new_status = get_np_status(track)
            else:
                new_status = "Неизвестный перевозчик"
            
            # Всегда пишем результат в лог телеграма для проверки
            send_telegram(f"🔍 Трек {track}:\nСтатус: {new_status}")
            
            # Обновляем данные в таблице
            df.at[index, 'status'] = new_status
            df.at[index, 'last_check'] = datetime.now().strftime("%d.%m %H:%M")

        # Сохраняем обновленный файл на GitHub
        new_csv_string = df.to_csv(index=False)
        repo.update_file("data.csv", "Auto-update statuses", new_csv_string, file_content.sha)
        send_telegram("✅ Все статусы обновлены в базе.")

except Exception as e:
    send_telegram(f"💥 Критическая ошибка: {str(e)}")
