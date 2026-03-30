import requests
import pandas as pd
from github import Github
import io
import os
from datetime import datetime
import time

# Секреты
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
        session = requests.Session()
        # Имитируем реальный визит
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Referer': 'https://ua.meest.com/'
        }
        
        # Запрос к API
        api_url = f"https://t.meest-group.com/api/v1/track/{track}"
        r = session.get(api_url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            events = data.get('events', [])
            
            if events and len(events) > 0:
                # Берем самый первый элемент (он последний по времени)
                last_event = events[0]
                status_text = last_event.get('status', 'Обработка')
                city = last_event.get('city', '')
                # Формируем красивую строку статуса
                return f"{status_text} ({city})" if city else status_text
            
            # Если истории нет, берем текущий статус из конфига
            return data.get('config', {}).get('status', 'Информация уточняется')
        
        return f"Meest: Код {r.status_code}"
    except Exception:
        return "Ошибка получения данных"

# --- ОСНОВНОЙ ЦИКЛ ---
try:
    send_telegram("🤖 Робот запущен, проверяю треки...")
    
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    
    if not df.empty:
        for index, row in df.iterrows():
            track = str(row['track_number']).strip()
            carrier = row['carrier']
            
            if carrier == "Мист Экспресс":
                new_status = get_meest_status(track)
                send_telegram(f"🔔 Трек {track} (Мист):\n{new_status}")
                
                df.at[index, 'status'] = new_status
                df.at[index, 'last_check'] = datetime.now().strftime("%d.%m %H:%M")
                time.sleep(1) # Защита от бана

        # Сохранение
        new_csv = df.to_csv(index=False)
        repo.update_file("data.csv", "Auto-update statuses", new_csv, file_content.sha)
        send_telegram("✅ Проверка завершена.")

except Exception as e:
    send_telegram(f"💥 Ошибка: {str(e)}")
