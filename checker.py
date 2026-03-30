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

kiev_tz = pytz.timezone('Europe/Kiev')
G_TOKEN = os.getenv("G_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(message):
    if TG_TOKEN and TG_CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TG_CHAT_ID, "text": message}, timeout=10)

def get_meest_status(track):
    try:
        salt = "721f9793f5f239a47d69df922795267d"
        chk = hashlib.md5(f"{salt}{track}{salt}".encode()).hexdigest()
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&chk={chk}"
        r = requests.get(url, timeout=15)
        root = ET.fromstring(r.text)
        items = root.findall(".//items")
        if items:
            msg = items[-1].find('ActionMessages').text
            return f"🕒 {msg.strip()}"
    except: pass
    return "📦 Meest: Нет данных"

def get_np_global_status(track):
    try:
        s = requests.Session()
        # Имитируем реальный браузер максимально точно
        h = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://novaposhtaglobal.ua/track/'
        }
        # Шаг 1: заходим на страницу за куками и токеном
        res = s.get("https://novaposhtaglobal.ua/track/", headers=h, timeout=15)
        token_search = re.search(r'name="token"\s+value="([^"]+)"', res.text)
        
        if not token_search:
            return "📦 НП: Ошибка токена"
            
        token = token_search.group(1)
        
        # Шаг 2: сам запрос статуса
        api_url = "https://personal.novaposhtaglobal.ua/tracking.php"
        payload = {'token': token, 'num': track.strip(), 'lang': 'uk'}
        r = s.post(api_url, data=payload, headers=h, timeout=15)
        
        data = r.json()
        if data.get('last_status'):
            st_name = data['last_status']['status_name'].strip()
            st_date = data['last_status']['date_status'].strip()
            return f"🚚 {st_name} ({st_date})"
    except Exception as e:
        print(f"Ошибка НП для {track}: {e}")
    return "📦 Номер не найден"

try:
    g = Github(G_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file.decoded_content.decode('utf-8')))
    
    now = datetime.datetime.now(kiev_tz).strftime("%d.%m %H:%M")
    changed = False

    for i, row in df.iterrows():
        track = str(row['track_number']).strip()
        carrier = row['carrier']
        # Чистим старый статус от пробелов для верного сравнения
        old_status = str(row['status']).strip()
        
        if "Мист" in carrier:
            new_status = get_meest_status(track)
        else:
            new_status = get_np_global_status(track)

        df.at[i, 'check_time'] = now
        # Сравниваем очищенные строки
        if new_status.strip() != old_status:
            df.at[i, 'status'] = new_status
            df.at[i, 'last_change'] = now
            send_telegram(f"🔔 ОБНОВЛЕНИЕ\n📦 {track}\n{new_status}")
            changed = True
        time.sleep(3) # Увеличил паузу, чтобы сайты не банили

    repo.update_file(file.path, f"Auto-check {now}", df.to_csv(index=False), file.sha)
except Exception as e:
    print(f"Критическая ошибка: {e}")
