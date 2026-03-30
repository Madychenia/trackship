import pandas as pd
from github import Github
from datetime import datetime
import pytz
import io
import os
import time
import hashlib
import requests
import xml.etree.ElementTree as ET

# Установка часового пояса
kiev_tz = pytz.timezone('Europe/Kiev')

GITHUB_TOKEN = os.getenv("G_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TG_CHAT_ID, "text": message}, timeout=10)
    except:
        print("Ошибка Telegram")

def get_meest_status(track):
    try:
        salt = "721f9793f5f239a47d69df922795267d"
        chk = hashlib.md5(f"{salt}{track}{salt}".encode()).hexdigest()
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&chk={chk}"
        headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'x-requested-with': 'XMLHttpRequest'}
        r = requests.post(url, headers=headers, timeout=15)
        if r.status_code == 200 and "<items>" in r.text:
            root = ET.fromstring(r.text)
            last = root.findall(".//items")[-1]
            dt = last.find('DateTimeAction').text or ""
            city = last.find('City').text if last.find('City') is not None else ""
            msg = last.find('ActionMessages').text or ""
            return f"🕒 {dt} | {city} | {msg}"
        return "📦 Ожидает регистрации"
    except: return "⚠️ Ошибка Meest"

def get_np_status(track):
    try:
        url = "https://api.novaposhta.ua/v2.0/json/"
        data = {
            "modelName": "TrackingDocument",
            "calledMethod": "getStatusDocuments",
            "methodProperties": {
                "Documents": [{"DocumentNumber": str(track), "Phone": ""}]
            }
        }
        r = requests.post(url, json=data, timeout=15)
        if r.status_code == 200:
            res = r.json()
            if res['success'] and res['data']:
                info = res['data'][0]
                status = info.get('Status', 'Не найдено')
                warehouse = info.get('WarehouseStation', '')
                # Если посылку еще не создали или номер неверный
                if status == "Номер не найден":
                    return "📦 Ожидает регистрации"
                return f"🚚 {status} | {warehouse}"
        return "📦 Номер не найден"
    except: return "⚠️ Ошибка НП"

try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))

    tech_cols = ['track_number', 'carrier', 'comment', 'status', 'last_change', 'check_time']
    mapping = {'Трек': 'track_number', 'Оператор': 'carrier', 'Коммент': 'comment', 'Статус': 'status', 'Ласт': 'last_change', 'Чек': 'check_time'}
    df = df.rename(columns=mapping)
    for col in tech_cols:
        if col not in df.columns: df[col] = "-"

    if not df.empty:
        updated_any = False
        now = datetime.now(kiev_tz).strftime("%d.%m %H:%M")
        
        for index, row in df.iterrows():
            track = str(row['track_number']).strip()
            carrier = row['carrier']
            current_status = str(row['status'])
            
            # Логика выбора оператора
            if carrier == "Мист Экспресс":
                new_status = get_meest_status(track)
            elif carrier == "Новая почта":
                new_status = get_np_status(track)
            else:
                continue
                
            df.at[index, 'check_time'] = now
            
            if new_status != current_status:
                df.at[index, 'status'] = new_status
                df.at[index, 'last_change'] = now
                comment = f" ({row['comment']})" if row['comment'] != "-" else ""
                send_telegram(f"🔔 ОБНОВЛЕНИЕ ({carrier})\n📦 {track}{comment}\n{new_status}")
                updated_any = True
            
            time.sleep(1) # НП работает быстро, 1 сек хватит

        repo.update_file("data.csv", f"Pulse: {now}", df[tech_cols].to_csv(index=False), file_content.sha)

except Exception as e: print(f"Error: {e}")
