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
        requests.post(url, data={"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)

def get_meest_status(track):
    """Рабочая логика Мист (соль + MD5) с вытягиванием полной строки"""
    try:
        salt = "721f9793f5f239a47d69df922795267d"
        chk = hashlib.md5(f"{salt}{track}{salt}".encode()).hexdigest()
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&chk={chk}"
        r = requests.get(url, timeout=15)
        root = ET.fromstring(r.text)
        items = root.findall(".//items")
        if items:
            # Берем последнее событие и вытягиваем ActionMessages целиком
            msg = items[-1].find('ActionMessages').text
            dt = items[-1].find('ActionDate').text or ""
            return f"{dt} | {msg.strip()}"
    except: pass
    return "📦 Meest: Нет данных"

def get_np_global_status(track):
    """Парсинг НП Глобал"""
    try:
        s = requests.Session()
        h = {'User-Agent': 'Mozilla/5.0 Mac', 'Referer': 'https://novaposhtaglobal.ua/track/'}
        res = s.get("https://novaposhtaglobal.ua/track/", headers=h, timeout=15)
        token = re.search(r'name="token"\s+value="([^"]+)"', res.text).group(1)
        api_url = "https://personal.novaposhtaglobal.ua/tracking.php"
        r = s.post(api_url, data={'token': token, 'num': track.strip(), 'lang': 'uk'}, headers=h, timeout=15)
        data = r.json()
        if data.get('last_status'):
            st = data['last_status']['status_name'].strip()
            dt = data['last_status']['date_status'].strip()
            return f"{dt} | {st}"
    except: pass
    return "Номер не найден"

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
        comment = str(row['comment'])
        old_status = str(row['status']).strip()
        
        if "Мист" in carrier:
            new_status = get_meest_status(track)
        else:
            new_status = get_np_global_status(track)

        df.at[i, 'check_time'] = now
        
        if new_status.strip() != old_status:
            df.at[i, 'status'] = new_status
            df.at[i, 'last_change'] = now
            
            # ФОРМИРУЕМ КРАСИВОЕ СООБЩЕНИЕ КАК РАНЬШЕ
            # Трек в кавычках, коммент, и полный статус с новой строки
            tg_msg = (
                f"🔔 <b>ОБНОВЛЕНИЕ</b> ({carrier})\n"
                f"📦 <code>{track}</code> ({comment})\n"
                f"💬 {new_status}"
            )
            send_telegram(tg_msg)
            changed = True
        time.sleep(3)

    repo.update_file(file.path, f"Auto-check {now}", df.to_csv(index=False), file.sha)
except Exception as e:
    print(f"Error: {e}")
