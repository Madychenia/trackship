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
        import xml.etree.ElementTree as ET
        # ТВОЯ НОВАЯ СОЛЬ — ТОТ САМЫЙ ЗОЛОТОЙ КЛЮЧ
        salt = '14e4e61ff1b43e7cdfe637371c188588'
        chk = hashlib.md5(f"{salt}{track}{salt}".encode()).hexdigest()
        
        # 1. ПРОБУЕМ ЧЕРЕЗ API (POST)
        api_url = f"https://t.meest-group.com/get.php?what=tracking&number={track}&lang=ru&ext_track=&chk={chk}&referer=https://us.meest.com/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        r = requests.post(api_url, headers=headers, timeout=15)
        
        if r.status_code == 200 and "<items>" in r.text:
            root = ET.fromstring(r.text)
            items = root.findall(".//items")
            if items:
                last = items[-1]
                dt = last.find('DateTimeAction').text or ""
                # Пробуем найти русские теги, если нет - обычные
                city_el = last.find('City_RU') if last.find('City_RU') is not None else last.find('City')
                city = city_el.text if city_el is not None else ""
                msg_el = last.find('ActionMessages_RU') if last.find('ActionMessages_RU') is not None else last.find('ActionMessages')
                msg = msg_el.text if msg_el is not None else ""
                return f"🕒 {dt} | {city} | {msg}".strip()

        # 2. ЕСЛИ API ЗАБЛОКИРОВАЛ (400), ИДЕМ НА ПУБЛИЧНЫЙ HTML (КОТОРЫЙ ДАВАЛ 200)
        html_url = f"https://t.meest-group.com/int/ru/{track}"
        r_html = requests.get(html_url, headers=headers, timeout=15)
        
        if r_html.status_code == 200:
            html = r_html.text
            dates = re.findall(r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})', html)
            if dates:
                last_dt = dates[-1]
                content_after = html.split(last_dt)[-1].split('</tr>')[0]
                cells = re.findall(r'<td.*?>(.*?)</td>', content_after)
                if len(cells) >= 4:
                    city = re.sub('<[^<]+?>', '', cells[1]).strip()
                    status = re.sub('<[^<]+?>', '', cells[3]).strip()
                    return f"🕒 {last_dt} | {city} | {status}"
                    
    except Exception as e:
        print(f"Meest Error: {e}")
        
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
    log_messages = []

    for i, row in df.iterrows():
        track = str(row['track_number']).strip()
        carrier = row['carrier']
        old_status = str(row['status']).strip()
        
        if "Мист" in str(carrier):
            new_status = get_meest_status(track)
        elif "Новая" in str(carrier):
            new_status = get_np_global_status(track)
        else:
            new_status = old_status

        df.at[i, 'check_time'] = now
        
        if new_status != old_status and new_status not in ["Номер не найден", "Ожидает регистрации"]:
            df.at[i, 'status'] = new_status
            df.at[i, 'last_change'] = now
            
            comment = f" ({row['comment']})" if str(row['comment']) != "-" else ""
            msg = f"🔔 <b>ОБНОВЛЕНИЕ</b> ({carrier})\n📦 <code>{track}</code>{comment}\n{new_status}"
            send_telegram(msg)
            updated_any = True
        
        time.sleep(2)

    # Сохраняем файл в любом случае
    repo.update_file(file.path, f"Pulse update {now}", df.to_csv(index=False), file.sha)

    # ОТЧЕТ В ТЕЛЕГРАМ (чтобы ты видел, что скрипт отработал)
    status_text = "✅ Проверка завершена. Обновлений нет."
    if updated_any:
        status_text = "✅ Проверка завершена. Статусы обновлены!"
    
    send_telegram(f"{status_text}\n🕒 Время: {now}")

except Exception as e:
    send_telegram(f"🆘 <b>КРИТИЧЕСКАЯ ОШИБКА:</b>\n<code>{e}</code>")
