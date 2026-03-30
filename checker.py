import pandas as pd
from github import Github
import datetime
import pytz
import io
import os
import time
import requests

kiev_tz = pytz.timezone('Europe/Kiev')

# Переменные из Secrets
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

def get_np_global_status(track):
    session = requests.Session()
    # 1. Заходим на страницу, чтобы получить куки и сессию
    main_url = "https://novaposhtaglobal.ua/track/"
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    
    try:
        response = session.get(main_url, headers=headers, timeout=15)
        # Ищем токен прямо в тексте страницы (он там зашит в скриптах)
        import re
        token_search = re.search(r'name="token"\s+value="([^"]+)"', response.text)
        
        if token_search:
            token = token_search.group(1)
        else:
            # Если в лоб не нашли, используем тот, что ты прислал, как запасной
            token = "0cAFcWeA7QMDv5taakZI9qezdhVlxCWBHetXLx0tyZbFuMezcIwmM1KeC1ficSFa25xIUnLUGfDhjBzolyFSwRczguYhM0zJNicIZPB"

        # 2. Делаем сам запрос статуса
        api_url = 'https://personal.novaposhtaglobal.ua/tracking.php'
        files = {
            'token': (None, token),
            'num': (None, str(track)),
            'lang': (None, 'Українська'),
        }
        
        res = session.post(api_url, files=files, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data.get('error') == 0 and data.get('last_status'):
                status_text = data['last_status'].get('status_name', 'Нет данных')
                status_date = data['last_status'].get('date_status', '')
                return f"🚚 {status_text} ({status_date})"
        
        return "📦 Ожидает регистрации"
    except Exception as e:
        return f"⚠️ Ошибка НП: {str(e)[:15]}"

# ... (остальной код загрузки CSV и цикла проверки остается прежним) ...

# В цикле проверки замени вызов на:
# if carrier == "Новая почта":
#     new_status = get_np_global_status(track)
