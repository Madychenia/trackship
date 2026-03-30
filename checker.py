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
        url = f"https://t.meest-group.com/api/v1/track/{track}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': 'https://ua.meest.com/',
            'Accept': 'application/json'
        }
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            # Проверяем события
            events = data.get('events', [])
            if events:
                return f"{events[0].get('status')} ({events[0].get('city', '')})"
            return data.get('config', {}).get('status', "Статус уточняется")
        return f"Meest: Код {r.status_code}"
    except Exception as e:
        return f"Ошибка парсинга Meest"

def get_np_status(track):
    try:
        # Для НП используем другой метод, так как старый начал выдавать ошибку JSON (line 1)
        url = "https://novapost.com/api/v1/tracking" # Используем их международный API
        params = {"number": track}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        r = requests.get(url, params=params, headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            if data.get('data'):
                return data['data'][0].get('status_description_ru', 'В пути')
            return "НП: Данные не найдены"
        
        # Если API не отвечает, пробуем старый добрый метод с заголовками
        return f"НП: Ошибка {r.status_code}"
    except Exception as e:
        if "Expecting value" in str(e):
            return "НП: Защита от ботов"
        return "Ошибка парсинга НП"

# --- ОСНОВНОЙ ЦИКЛ ---
try:
    # 1. Сначала приветствие
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
            elif carrier == "Новая почта":
                new_status = get_np_status(track)
            else:
                new_status = "Неизвестный логист"
            
            # 2. Отправка отчета по каждому треку
            send_telegram(f"🔔 Обновление трека {track} ({carrier}):\n{new_status}")
            
            df.at[index, 'status'] = new_status
            df.at[index, 'last_check'] = datetime.now().strftime("%d.%m %H:%M")

        # 3. Сохранение и финал
        new_csv = df.to_csv(index=False)
        repo.update_file("data.csv", "Auto-update statuses", new_csv, file_content.sha)
        send_telegram("✅ Все статусы обновлены в базе.")

except Exception as e:
    send_telegram(f"💥 Сбой: {str(e)}")
