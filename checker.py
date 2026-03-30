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

kiev_tz = pytz.timezone('Europe/Kiev')
# Используем твой G_TOKEN
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
    try:
        import xml.etree.ElementTree as ET
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
    """Парсинг НП Глобал на основе твоих скриншотов Network"""
    try:
        s = requests.Session()
        # Имитируем твой браузер со скринов
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://novaposhtaglobal.ua/track/'
        }
        
        # 1. Загружаем страницу, чтобы найти токен в HTML
        response = s.get("https://novaposhtaglobal.ua/track/", headers=headers, timeout=10)
        # Ищем длинный токен из Payload (скрин image_e670bf.jpg)
        token_match = re.search(r'name="token"\s+value="([^"]+)"', response.text)
        
        if not token_match:
            # Запасной вариант: поиск в JS-контексте на странице
            token_match = re.search(r'token\s*:\s*"([^"]+)"', response.text)
            
        if token_match:
            token = token_match.group(1)
            api_url = "https://personal.novaposhtaglobal.ua/tracking.php"
            payload = {'token': token, 'num': track.strip(), 'lang': 'uk'}
            
            # 2. Делаем POST запрос как на твоем скрине image_b4161a.png
            r = s.post(api_url, data=payload, headers=headers, timeout=15)
            data = r.json()
            
            # Парсим JSON на основе твоего скрина Preview (image_e67384.jpg)
            if data.get('historyStatus') and len(data['historyStatus']) > 0:
                last_event = data['historyStatus'][0] # Берем верхнее событие
                status_text = last_event.get('status', 'Статус не указан')
                date_text = data.get('date', '') # Общая дата из ответа
                return f"🚚 {date_text} | {status_text}"
    except Exception as e:
        print(f"NP Debug Error: {e}")
    return "Номер не найден"

try:
    g = Github(G_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file.decoded_content.decode('utf-8')))
    
    now = datetime.now(kiev_tz).strftime("%d.%m %H:%M")
    updated_any = False

    for i, row in df.iterrows():
        track = str(row['track_number']).strip()
        carrier = row['carrier']
        old_status = str(row['status']).strip()
        
        new_status = get_meest_status(track) if "Мист" in carrier else get_np_global_status(track)
        
        # Обновляем время чека всегда
        df.at[i, 'check_time'] = now
        
        # Если статус реально изменился
        if new_status != old_status and "Номер не найден" not in new_status:
            df.at[i, 'status'] = new_status
            df.at[i, 'last_change'] = now
            comment = f" ({row['comment']})" if row['comment'] != "-" else ""
            msg = f"🔔 <b>ОБНОВЛЕНИЕ</b> ({carrier})\n📦 <code>{track}</code>{comment}\n{new_status}"
            send_telegram(msg)
            updated_any = True
        
        time.sleep(3) # Чуть больше пауза для стабильности

    repo.update_file(file.path, f"Pulse {now}", df.to_csv(index=False), file.sha)
    print(f"Done at {now}")
except Exception as e:
    print(f"Global Error: {e}")
