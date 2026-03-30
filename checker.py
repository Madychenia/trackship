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
GITHUB_TOKEN = os.getenv("G_TOKEN")
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
            return f"🕒 {msg}"
    except: pass
    return "📦 Meest: В обработке"

def get_np_global_status(track):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 Mac'}
        # НП Глобал часто требует сначала зайти на главную для кук
        s = requests.Session()
        res = s.get("https://novaposhtaglobal.ua/track/", headers=headers)
        token = re.search(r'name="token"\s+value="([^"]+)"', res.text).group(1)
        
        api_url = "https://personal.novaposhtaglobal.ua/tracking.php"
        data = {'token': token, 'num': track, 'lang': 'uk'}
        r = s.post(api_url, data=data, headers=headers)
        json_data = r.json()
        if json_data.get('last_status'):
            st = json_data['last_status']['status_name']
            dt = json_data['last_status']['date_status']
            return f"🚚 {st} ({dt})"
    except: pass
    return "📦 НП: Не найдено"

try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file.decoded_content.decode('utf-8')))
    
    now = datetime.datetime.now(kiev_tz).strftime("%d.%m %H:%M")
    changed = False

    for i, row in df.iterrows():
        old_status = str(row.get('status', ''))
        carrier = row['carrier']
        track = str(row['track_number'])
        
        new_status = get_meest_status(track) if "Мист" in carrier else get_np_global_status(track)
        
        df.at[i, 'check_time'] = now
        if new_status != old_status:
            df.at[i, 'status'] = new_status
            df.at[i, 'last_change'] = now
            send_telegram(f"📦 {track}\n{new_status}")
            changed = True
        time.sleep(2)

    repo.update_file(file.path, f"Auto-check {now}", df.to_csv(index=False), file.sha)
except Exception as e:
    print(f"Error: {e}")
