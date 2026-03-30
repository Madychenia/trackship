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
    """Рабочая логика Мист (соль + MD5)"""
    try:
        salt = "721f9793f5f239a47d69df922795267d"
        chk = hashlib.md5(f"{salt}{track}{salt}".encode()).hexdigest()
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&chk={chk}"
        r = requests.get(url, timeout=15)
        root = ET.fromstring(r.text)
        items = root.findall(".//items")
        if items:
            msg = items[-1].find('ActionMessages').text
            return f"🕒 {msg}"
    except: pass
    return "📦 Meest: Нет данных"

def get_np_global_status(track):
    """Парсинг НП Глобал с токеном"""
    try:
        s = requests.Session()
        h = {'User-Agent': 'Mozilla/5.0 Mac'}
        res = s.get("https://novaposhtaglobal.ua/track/", headers=h, timeout=10)
        token = re.search(r'name="token"\s+value="([^"]+)"', res.text).group(1)
        
        api_url = "https://personal.novaposhtaglobal.ua/tracking.php"
        r = s.post(api_url, data={'token': token, 'num': track, 'lang': 'uk'}, headers=h, timeout=15)
        data = r.json()
        if data.get('last_status'):
            return f"🚚 {data['last_status']['status_name']} ({data['last_status']['date_status']})"
    except: pass
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
        old_status = str(row['status'])
        
        new_status = get_meest_status(track) if "Мист" in carrier else get_np_global_status(track)
        
        df.at[i, 'check_time'] = now
        if new_status != old_status:
            df.at[i, 'status'] = new_status
            df.at[i, 'last_change'] = now
            send_telegram(f"📦 {track}\n{new_status}")
            changed = True
        time.sleep(2)

    repo.update_file(file.path, f"Update {now}", df.to_csv(index=False), file.sha)
except Exception as e:
    print(f"Error: {e}")
