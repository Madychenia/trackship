import requests
import pandas as pd
from github import Github
import io
import os
from datetime import datetime
import time
import xml.etree.ElementTree as ET
import hashlib

# --- Секреты ---
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
    salt = "721f9793f5f239a47d69df922795267d"
    string_to_hash = f"{salt}{track}{salt}"
    return hashlib.md5(string_to_hash.encode()).hexdigest()

def get_meest_status(track):
    try:
        chk = generate_meest_chk(track)
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&ext_track=&chk={chk}"
        headers = {
            'accept': 'application/xml, text/xml, */*; q=0.01',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
            'referer': 'https://t.meest-group.com/n/'
        }
        session = requests.Session()
        session.get("https://t.meest-group.com/n/", headers=headers, timeout=10)
        r = session.post(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            if not r.text.strip() or "<items>" not in r.text:
                return "📦 Ожидает регистрации"
            root = ET.fromstring(r.text)
            items = root.findall(".//items")
            if items:
                last = items[-1]
                dt = last.find("DateTimeAction").text
                msg = last.find("ActionMessages").text
                city = last.find("City").text if last.find("City") is not None else ""
                # Формируем красивый статус для Telegram
                return f"🕒 {dt} | {city} | {msg}"
        return f"Meest: Код {r.status_code}"
    except Exception as e:
        return f"⚠️ Ошибка: {str(e)}"

# --- ОСНОВНОЙ ЦИКЛ ОБРАБОТКИ ---
try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))

    # УДАЛЯЕМ ЛИШНЕЕ (если колонки существуют)
    cols_to_drop = ['Unnamed: 0', 'id', 'link', 'date_added']
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    if not df.empty:
        updated_any = False
        for index, row in df.iterrows():
            track = str(row['track_number']).strip()
            carrier = row['carrier']
            # Обработка пустых статусов при первом добавлении
            current_status = str(row['status']) if pd.notna(row['status']) else ""
            
            if carrier == "Мист Экспресс":
                new_status = get_meest_status(track)
                
                # Если статус изменился ИЛИ он был пустым (новый трек)
                if new_status != current_status:
                    send_telegram(f"🔔 *ОБНОВЛЕНИЕ ТРЕКА*\n📦 {track}\n{new_status}")
                    df.at[index, 'status'] = new_status
                    df.at[index, 'last_check'] = datetime.now().strftime("%d.%m %H:%M")
                    updated_any = True
            
            time.sleep(2)

        if updated_any:
            # Сохраняем упрощенную структуру обратно в GitHub
            new_csv = df.to_csv(index=False)
            repo.update_file("data.csv", "Clean Interface Update", new_csv, file_content.sha)
            
except Exception as e:
    send_telegram(f"🚨 Ошибка интерфейса: {str(e)}")
