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
        # Используем альтернативный эндпоинт, который реже блокируют
        url = f"https://t.meest-group.com/api/v1/track/{track}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
            'Origin': 'https://ua.meest.com',
            'Referer': 'https://ua.meest.com/'
        }
        
        # Делаем запрос через сессию для лучшей имитации браузера
        session = requests.Session()
        r = session.get(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            # Проверяем наличие событий (самое свежее обычно первое)
            events = data.get('events', [])
            if events:
                last_event = events[0]
                status = last_event.get('status', 'В обработке')
                city = last_event.get('city', '')
                return f"{status} ({city})" if city else status
            
            # Если событий нет, проверяем общее поле статуса
            if 'config' in data and 'status' in data['config']:
                return data['config']['status']
                
            return "Информация ожидается"
        
        if r.status_code == 403:
            return "Meest: Доступ заблокирован (403)"
        return f"Meest: Код {r.status_code}"
    except Exception as e:
        # Если это ошибка JSON, значит сайт вернул не текст
        if "Expecting value" in str(e):
            return "Meest: Блокировка робота (JSON Error)"
        return f"Ошибка Meest: {str(e)[:20]}"

def get_np_status(track):
    # Пока оставляем как есть, вернемся к ней позже
    try:
        url = f"https://tracking.novaposhta.ua/v2/tracking/ru/{track}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('data'):
                return data['data'][0].get('last_status_ru', 'В пути')
        return f"НП: {r.status_code}"
    except:
        return "Ошибка НП"

# --- ОСНОВНОЙ ЦИКЛ ---
try:
    send_telegram("🤖 Проверка статусов запущена...")
    
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    
    if df.empty:
        send_telegram("⚠️ В базе нет треков.")
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
            
            # Отправка отчета в ТГ
            send_telegram(f"📦 {track}\n📍 Статус: {new_status}")
            
            df.at[index, 'status'] = new_status
            df.at[index, 'last_check'] = datetime.now().strftime("%d.%m %H:%M")

        # Сохранение на GitHub
        new_csv = df.to_csv(index=False)
        repo.update_file("data.csv", "Auto-update statuses", new_csv, file_content.sha)
        send_telegram("✅ База данных обновлена.")

except Exception as e:
    send_telegram(f"💥 Сбой системы: {str(e)}")
