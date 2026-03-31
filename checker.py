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
        # Пробуем через их API с твоими новыми параметрами из cURL
        # Я использую старую соль, но если она не сработает - мы увидим это в логах
        salt = "721f9793f5f239a47d69df922795267d"
        chk = hashlib.md5(f"{salt}{track}{salt}".encode()).hexdigest()
        
        # Ссылка в точности как в твоем успешном запросе
        url = f"https://t.meest-group.com/get.php?what=tracking&number={track}&lang=ru&ext_track=&chk={chk}&referer=https://us.meest.com/"
        
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
            'referer': 'https://t.meest-group.com/t/ru/us/',
            'accept': 'application/xml, text/xml, */*; q=0.01'
        }

        r = requests.post(url, headers=headers, timeout=15)
        
        if r.status_code == 200 and "<items>" in r.text:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(r.text)
            items = root.findall(".//items")
            if items:
                last = items[-1]
                dt = last.find('DateTimeAction').text or ""
                city = last.find('City').text or ""
                msg = last.find('ActionMessages').text or ""
                return f"🕒 {dt} | {city} | {msg}".strip()
        
        # ЕСЛИ API НЕ ПУСТИЛ - ПЛАН Б: ПАРСИМ ЧИСТЫЙ HTML СТРАНИЦЫ
        html_url = f"https://t.meest-group.com/int/ru/{track}"
        r_html = requests.get(html_url, headers=headers, timeout=15)
        
        if r_html.status_code == 200:
            # Ищем последнюю дату в формате ГГГГ-ММ-ДД
            dates = re.findall(r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2})', r_html.text)
            if dates:
                last_dt = dates[-1]
                return f"🕒 {last_dt} | Обновлено через HTML"

        # ДИАГНОСТИКА: Если мы здесь, значит Мист нас реально забанил
        # Отправляем тебе в Телеграм ЧТО ИМЕННО видит скрипт
        debug_info = f"❌ <b>MEEST DEBUG ({track})</b>\nAPI: {r.status_code}\nHTML: {r_html.status_code}\nОтвет API: <code>{r.text[:50]}</code>"
        send_telegram(debug_info)

    except Exception as e:
        send_telegram(f"⚠️ <b>Ошибка Meest:</b> <code>{str(e)[:100]}</code>")
        
    return "Ожидает регистрации"

def get_np_global_status(track):
    try:
        s = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        res = s.get("https://novaposhtaglobal.ua/track/", headers=headers, timeout=10)
        token = re.search(r'token["\']\s*:\s*["\']([^"\']+)["\']', res.text).group(1)
        payload = {'token': token, 'num': track.strip(), 'lang': 'uk'}
        r = s.post("https://personal.novaposhtaglobal.ua/tracking.php", data=payload, headers=headers, timeout=15)
        data = r.json()
        if 'historyStatus' in data and len(data['historyStatus']) > 0:
            last = data['historyStatus'][0]
            return f"🚚 {last.get('date', '')} | {last.get('status', '')}"
    except: pass
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
        
        new_status = get_meest_status(track) if "Мист" in str(carrier) else get_np_global_status(track) if "Новая" in str(carrier) else old_status

        df.at[i, 'check_time'] = now
        
        # Если статус реально изменился и это не заглушка ошибки
        if new_status != old_status and "Ожидает регистрации" not in new_status and "Номер не найден" not in new_status:
            df.at[i, 'status'] = new_status
            df.at[i, 'last_change'] = now
            
            comment = f" ({row['comment']})" if str(row['comment']) != "-" else ""
            msg = f"🔔 <b>ОБНОВЛЕНИЕ</b> ({carrier})\n📦 <code>{track}</code>{comment}\n{new_status}"
            send_telegram(msg)
            updated_any = True
        
        time.sleep(2)

    repo.update_file(file.path, f"Pulse update {now}", df.to_csv(index=False), file.sha)

except Exception as e:
    send_telegram(f"⚠️ <b>Крит. ошибка:</b> {e}")
