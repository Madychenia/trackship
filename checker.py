import pandas as pd
from github import Github
from datetime import datetime
import pytz
import io
import os
import time
import hashlib
import requests
import re
import xml.etree.ElementTree as ET

kiev_tz = pytz.timezone('Europe/Kiev')
# ТУТ ТОЖЕ G_TOKEN
G_TOKEN = os.getenv("G_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except: pass

def get_meest_status(track):
    """Возвращаем полную строку как раньше"""
    try:
        salt = "721f9793f5f239a47d69df922795267d"
        chk = hashlib.md5(f"{salt}{track}{salt}".encode()).hexdigest()
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&chk={chk}"
        r = requests.get(url, timeout=15)
        if "<items>" in r.text:
            root = ET.fromstring(r.text)
            last = root.findall(".//items")[-1]
            dt = last.find('DateTimeAction').text or ""
            city = last.find('City').text if last.find('City') is not None else ""
            msg = last.find('ActionMessages').text or ""
            return f"🕒 {dt} | {city} | {msg}".strip()
    except: pass
    return "Ожидает регистрации"

def get_np_global_status(track):
    """Парсинг НП Глобал через tracking.php"""
    try:
        s = requests.Session()
        h = {'User-Agent': 'Mozilla/5.0 Mac'}
        r_init = s.get("https://novaposhtaglobal.ua/track/", headers=h, timeout=10)
        token = re.search(r'name="token"\s+value="([^"]+)"', r_init.text).group(1)
        api_url = "https://personal.novaposhtaglobal.ua/tracking.php"
        r = s.post(api_url, data={'token': token, 'num': track.strip(), 'lang': 'uk'}, headers=h, timeout=15)
        data = r.json()
        if data.get('last_status'):
            dt = data['last_status']['date_status'].strip()
            st_name = data['last_status']['status_name'].strip()
            return f"🚚 {dt} | {st_name}"
    except: pass
    return "Номер не найден"

try:
    g = Github(G_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file.decoded_content.decode('utf-8')))
    
    now = datetime.now(kiev_tz).strftime("%d.%m %H:%M")
    updated = False

    for i, row in df.iterrows():
        track = str(row['track_number']).strip()
        carrier = row['carrier']
        old_status = str(row['status']).strip()
        
        new_status = get_meest_status(track) if "Мист" in carrier else get_np_global_status(track)
        
        df.at[i, 'check_time'] = now
        if new_status != old_status and "Ошибка" not in new_status:
            df.at[i, 'status'] = new_status
            df.at[i, 'last_change'] = now
            comment = f" ({row['comment']})" if row['comment'] != "-" else ""
            # Полное сообщение в Телеграм
            msg = f"🔔 <b>ОБНОВЛЕНИЕ</b> ({carrier})\n📦 <code>{track}</code>{comment}\n{new_status}"
            send_telegram(msg)
            updated = True
        time.sleep(2)

    repo.update_file(file.path, f"Pulse {now}", df.to_csv(index=False), file.sha)
except Exception as e:
    print(f"Error: {e}")
