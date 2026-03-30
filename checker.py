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
        session = requests.Session()
        # Шаг 1: Имитируем заход человека на страницу отслеживания
        main_url = "https://ua.meest.com/parcel-track"
        headers_base = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        session.get(main_url, headers=headers_base, timeout=10)

        # Шаг 2: Запрос к API с поддельным Referer и Origin
        api_url = f"https://t.meest-group.com/api/v1/track/{track}"
        api_headers = {
            **headers_base,
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://ua.meest.com',
            'Referer': 'https://ua.meest.com/',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        r = session.get(api_url, headers=api_headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            # Пытаемся вытянуть статус из событий (events)
            events = data.get('events', [])
            if isinstance(events, list) and len(events) > 0:
                last = events[0]
                status = last.get('status', 'Обработка')
                city = last.get('city', '')
                return f"{status} ({city})" if city else status
            
            # Если событий нет, берем общий конфиг
            config_status = data.get('config', {}).get('status')
            if config_status:
                return config_status
                
            return "Статус в обработке"
        
        return f"Meest: Код {r.status_code}"
    except Exception as e:
        # Если JSON не парсится, значит Meest выдал HTML с блоком
        return "Ошибка данных (Meest блокирует запрос)"
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
