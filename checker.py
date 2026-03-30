import requests
import pandas as pd
from github import Github
import io
import os
from datetime import datetime
import time
import xml.etree.ElementTree as ET
import hashlib

# --- Секреты GitHub ---
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

def generate_meest_chk(track):
    """Генерирует правильный MD5 chk по формуле salt + track + salt"""
    salt = "721f9793f5f239a47d69df922795267d"
    string_to_hash = f"{salt}{track}{salt}"
    return hashlib.md5(string_to_hash.encode()).hexdigest()

def get_meest_status(track):
    """Получает статус через XML API Meest"""
    try:
        chk = generate_meest_chk(track)
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&ext_track=&chk={chk}"
        
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        r = requests.post(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            if not r.text.strip():
                return "📦 Ожидает регистрации"
            
            root = ET.fromstring(r.text)
            items = root.findall(".//items")
            
            if items:
                last = items[-1]
                dt = last.find("DateTimeAction").text
                msg = last.find("ActionMessages").text
                city = last.find("City").text
                return f"{dt} | {city} | {msg}"
            
            return "📦 Статус не найден"
        return f"Meest Error: {r.status_code}"
    except Exception as e:
        return f"Meest Error: {str(e)}"

def get_nova_poshta_status(track):
    """Получает статус через публичный API Новой Почты"""
    try:
        url = "https://api.novaposhta.ua/v2.0/json/"
        data = {
            "modelName": "TrackingDocument",
            "calledMethod": "getStatusDocuments",
            "methodProperties": {
                "Documents": [{"DocumentNumber": track, "Phone": ""}]
            }
        }
        r = requests.post(url, json=data, timeout=15)
        res = r.json()
        
        if res.get('success'):
            info = res['data'][0]
            status = info.get('Status', 'Нет данных')
            warehouse = info.get('Warehouse', '')
            return f"{status} {warehouse}".strip()
        return "НП: Ошибка данных"
    except Exception as e:
        return f"НП Error: {str(e)}"

# --- ОСНОВНОЙ ЦИКЛ ---
try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    
    if not df.empty:
        updated_any = False
        
        for index, row in df.iterrows():
            track = str(row['track_number']).strip()
            carrier = row['carrier']
            current_status = str(row['status'])
            
            new_status = ""
            if carrier == "Мист Экспресс":
                new_status = get_meest_status(track)
            elif carrier == "Новая почта":
                new_status = get_nova_poshta_status(track)
            
            if new_status and new_status != current_status:
                send_telegram(f"🔔 Трек: {track} ({carrier})\nСтатус: {new_status}")
                df.at[index, 'status'] = new_status
                df.at[index, 'last_check'] = datetime.now().strftime("%d.%m %H:%M")
                updated_any = True
            
            time.sleep(1)

        if updated_any:
            new_csv = df.to_csv(index=False)
            repo.update_file("data.csv", "Update statuses", new_csv, file_content.sha)
    
except Exception as e:
    send_telegram(f"🚨 Ошибка в скрипте: {str(e)}")
