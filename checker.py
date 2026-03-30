import requests
import pandas as pd
from github import Github
import io
import os
from datetime import datetime
import time
import xml.etree.ElementTree as ET

# Секреты
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
    try:
        # Тот самый URL из твоего cURL
        # Параметр chk может меняться, но пока используем этот статично
        chk = "8645141e4284290f547d92f1fa241731"
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&ext_track=&chk={chk}"
        
        headers = {
            'accept': 'application/xml, text/xml, */*; q=0.01',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'origin': 'https://t.meest-group.com',
            'referer': 'https://t.meest-group.com/n/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        # Meest требует POST с пустым телом (content-length: 0)
        r = requests.post(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            # Парсим XML
            root = ET.fromstring(r.text)
            items = root.findall(".//items")
            
            if items:
                # В твоем XML самое последнее событие — в последнем блоке <items>
                last_item = items[-1]
                status_text = last_item.find("ActionMessages").text
                city = last_item.find("City").text
                
                if status_text:
                    return f"{status_text} ({city})" if city else status_text
            
            return "Статус уточняется"
            
        return f"Meest: Код {r.status_code}"
    except Exception as e:
        return f"Ошибка обработки XML"

# --- ОСНОВНОЙ ЦИКЛ ---
try:
    send_telegram("🤖 Робот запущен, проверяю треки (XML Mode)...")
    
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    
    if not df.empty:
        for index, row in df.iterrows():
            track = str(row['track_number']).strip()
            carrier = row['carrier']
            
            if carrier == "Мист Экспресс":
                new_status = get_meest_status(track)
                send_telegram(f"📦 Трек: {track}\n📍 Статус: {new_status}")
                
                df.at[index, 'status'] = new_status
                df.at[index, 'last_check'] = datetime.now().strftime("%d.%m %H:%M")
                time.sleep(2)

        # Сохранение обновленной таблицы
        new_csv = df.to_csv(index=False)
        repo.update_file("data.csv", "Update Meest via XML Parser", new_csv, file_content.sha)
        send_telegram("✅ Все данные обновлены.")

except Exception as e:
    send_telegram(f"💥 Сбой: {str(e)}")
