import pandas as pd
from github import Github
import datetime
import pytz
import io
import os
import time
import hashlib
import requests
import re
import xml.etree.ElementTree as ET

# Настройка времени
kiev_tz = pytz.timezone('Europe/Kiev')

# Секреты из GitHub Actions
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
    """Рабочая версия Meest Экспресс (MD5 + Salt)"""
    try:
        salt = "721f9793f5f239a47d69df922795267d"
        chk = hashlib.md5(f"{salt}{track}{salt}".encode()).hexdigest()
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&chk={chk}"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            items = root.findall(".//items")
            if items:
                msg = items[-1].find('ActionMessages').text or "В пути"
                return f"🕒 {msg}"
    except:
        pass
    return "📦 Meest: Данные уточняются"

def get_np_global_status(track):
    """Парсинг НП Глобал с динамическим токеном"""
    session = requests.Session()
    headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    try:
        main_page = session.get("https://novaposhtaglobal.ua/track/", headers=headers, timeout=10)
        token_match = re.search(r'name="token"\s+value="([^"]+)"', main_page.text)
        if not token_match:
            return "⚠️ Ошибка токена"
        
        token = token_match.group(1)
        api_url = 'https://personal.novaposhtaglobal.ua/tracking.php'
        files = {
            'token': (None, token),
            'num': (None, str(track)),
            'lang': (None, 'Українська'),
        }
        r = session.post(api_url, files=files, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get('last_status'):
                status = data['last_status']['status_name']
                date = data['last_status']['date_status']
                return f"🚚 {status} ({date})"
    except:
        pass
    return "📦 Номер не найден"

try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    
    # Колонки
    df.columns = ['track_number', 'carrier', 'comment', 'status', 'last_change', 'check_time']
    
    updated = False
    now = datetime.datetime.now(kiev_tz).strftime("%d.%m %H:%M")

    for i, row in df.iterrows():
        track = str(row['track_number']).strip()
        carrier = row['carrier']
        old_status = str(row['status'])
        
        if carrier == "Мист Экспресс":
            new_status = get_meest_status(track)
        else:
            new_status = get_np_global_status(track)

        df.at[i, 'check_time'] = now
        if new_status != old_status:
            df.at[i, 'status'] = new_status
            df.at[i, 'last_change'] = now
            send_telegram(f"🔔 {carrier}\n📦 {track}\n{new_status}")
            updated = True
        time.sleep(1)

    repo.update_file("data.csv", f"Update: {now}", df.to_csv(index=False), file_content.sha)
except Exception as e:
    print(f"Ошибка: {e}")
