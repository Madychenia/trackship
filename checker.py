import requests
import pandas as pd
from github import Github
import io
import os
from datetime import datetime

# Секреты GitHub
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
        # Используем проверенный путь, который мы видели в Network
        url = f"https://t.meest-group.com/api/v1/track/{track}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://ua.meest.com',
            'Referer': 'https://ua.meest.com/'
        }
        
        r = requests.get(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            
            # 1. Сначала ищем самое свежее событие в списке events
            events = data.get('events', [])
            if isinstance(events, list) and len(events) > 0:
                last_event = events[0]
                status = last_event.get('status', 'Обработка')
                city = last_event.get('city', '')
                return f"{status} ({city})" if city else status
            
            # 2. Если списка событий нет, ищем в конфиге
            config = data.get('config', {})
            if isinstance(config, dict) and config.get('status'):
                return config.get('status')
                
            return "Информация получена, уточняется"
            
        return f"Meest: Ошибка {r.status_code}"
    except Exception as e:
        # Если JSON не пришел, выводим более понятную ошибку
        return "Ошибка данных (Meest)"

def get_np_status(track):
    # Временно оставляем заглушку, чтобы не отвлекаться
    return "Проверка НП пропущена"

# --- ОСНОВНОЙ ЦИКЛ ---
try:
    # Приветствие в самом начале
    send_telegram("🤖 Робот запущен, проверяю треки...")
    
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    
    if df.empty:
        send_telegram("⚠️ В базе пусто.")
    else:
        for index, row in df.iterrows():
            track = str(row['track_number']).strip()
            carrier = row['carrier']
            
            if carrier == "Мист Экспресс":
                new_status = get_meest_status(track)
                
                # Отправляем отчет только по Мисту, раз мы им занимаемся
                send_telegram(f"🔔 Обновление трека {track} (Мист):\n{new_status}")
                
                # Обновляем CSV
                df.at[index, 'status'] = new_status
                df.at[index, 'last_check'] = datetime.now().strftime("%d.%m %H:%M")

        # Сохраняем только если были изменения по Мисту
        new_csv = df.to_csv(index=False)
        repo.update_file("data.csv", "Update Meest statuses", new_csv, file_content.sha)
        send_telegram("✅ Проверка Мист Экспресс завершена.")

except Exception as e:
    send_telegram(f"💥 Сбой: {str(e)}")
