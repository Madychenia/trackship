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
        # Используем мобильный API эндпоинт, он стабильнее
        url = f"https://t.meest-group.com/api/v1/track/{track}"
        headers = {
            'User-Agent': 'Meest/1.0 (Android 11; Build/RP1A.200720.011)',
            'Accept': 'application/json',
            'Host': 't.meest-group.com'
        }
        
        r = requests.get(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            
            # Проверяем наличие событий (самое новое — первое в списке)
            events = data.get('events', [])
            if isinstance(events, list) and len(events) > 0:
                last = events[0]
                status = last.get('status', 'Обработка')
                city = last.get('city', '')
                return f"{status} ({city})" if city else status
            
            # Если событий нет, смотрим основной статус в конфиге
            if 'config' in data and data['config'].get('status'):
                return data['config']['status']
                
            return "Статус уточняется"
            
        return f"Meest: Ошибка {r.status_code}"
    except Exception as e:
        return "Ошибка парсинга Meest"

def get_np_status(track):
    # Оставляем заглушку, пока чиним Мист
    return "Проверка НП пока отключена"

# --- ОСНОВНОЙ ЦИКЛ ---
try:
    send_telegram("🤖 Робот запущен, проверяю треки...")
    
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    
    if df.empty:
        send_telegram("⚠️ В базе пусто.")
    else:
        # Проходим по ВСЕМ строкам таблицы
        for index, row in df.iterrows():
            track = str(row['track_number']).strip()
            carrier = row['carrier']
            
            # Нам важен только Мист сейчас
            if carrier == "Мист Экспресс":
                new_status = get_meest_status(track)
                
                # Обновляем статус в таблице ПЕРЕД отправкой в ТГ
                df.at[index, 'status'] = new_status
                df.at[index, 'last_check'] = datetime.now().strftime("%d.%m %H:%M")
                
                # Отправляем отчет по конкретному треку
                send_telegram(f"🔔 Трек {track} (Мист):\n{new_status}")

        # Сохраняем обновленную таблицу на GitHub один раз в конце
        new_csv = df.to_csv(index=False)
        repo.update_file("data.csv", "Auto-update Meest statuses", new_csv, file_content.sha)
        send_telegram("✅ Все данные по Мист Экспресс обновлены.")

except Exception as e:
    send_telegram(f"💥 Критическая ошибка: {str(e)}")
