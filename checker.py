import requests
import pandas as pd
from github import Github
import io
import os

# Берем секреты (в GitHub Actions они настраиваются отдельно, об этом ниже)
GITHUB_TOKEN = os.getenv("G_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": message})

def get_meest_status(track):
    try:
        # Прямой URL из твоего скриншота Network
        url = f"https://t.meest-group.com/api/v1/track/{track}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://ua.meest.com',
            'Referer': 'https://ua.meest.com/'
        }
        
        r = requests.get(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            # Пробуем достать статус. В новых API Миста он обычно лежит в 'config' или 'events'
            if 'config' in data and 'status' in data['config']:
                return data['config']['status']
            elif 'events' in data and len(data['events']) > 0:
                return data['events'][0].get('status', 'Статус не определен')
            
            return "Данные получены, но статус не найден"
        
        return f"Сайт ответил: {r.status_code}"
    except Exception as e:
        # Выводим конкретную ошибку в телеграм для отладки
        return f"Ошибка: {str(e)[:30]}"


def get_np_status(track):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://tracking.novaposhta.ua/v2/tracking/ru/{track}"
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        if data.get('data'):
            return data['data'][0]['last_status_ru']
        return "Не найдено"
    except Exception as e:
        return f"Ошибка НП: {str(e)[:20]}"

# Основная логика обновления
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)
file_content = repo.get_contents("data.csv")
df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))

changes_made = False

for index, row in df.iterrows():
    old_status = str(row['status'])
    new_status = old_status
    
    if row['carrier'] == "Мист Экспресс":
        new_status = get_meest_status(row['track_number'])
    elif row['carrier'] == "Новая почта":
        new_status = get_np_status(row['track_number'])
    
    if new_status != old_status:
        df.at[index, 'status'] = new_status
        df.at[index, 'last_check'] = pd.Timestamp.now().strftime("%d.%m %H:%M")
        send_telegram(f"🔔 Обновление трека {row['track_number']} ({row['carrier']}):\n{new_status}")
        changes_made = True

if changes_made:
    csv_string = df.to_csv(index=False)
    repo.update_file("data.csv", "Auto-update statuses", csv_string, file_content.sha)


# Добавь это в самый конец файла checker.py
send_telegram("🤖 Робот запущен, проверяю треки...")
