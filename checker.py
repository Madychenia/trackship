import pandas as pd
from github import Github
from datetime import datetime
import pytz
import io
import os
import time
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
        # Идем через публичную страницу, раз она нам открылась (HTML 200)
        url = f"https://t.meest-group.com/int/ru/{track}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'
        }
        
        r = requests.get(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            html = r.text
            # Ищем все даты (2026-03-20 19:55:48)
            dates = re.findall(r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})', html)
            
            if dates:
                last_dt = dates[-1]
                # Берем кусок текста после этой даты
                content_after = html.split(last_dt)[-1].split('</tr>')[0] # Ограничиваем одной строкой таблицы
                
                # Вычищаем все HTML теги и лишние пробелы
                clean_text = re.sub('<[^<]+?>', '|', content_after)
                parts = [p.strip() for p in clean_text.split('|') if p.strip() and len(p.strip()) > 1]
                
                # По логике сайта: [Страна, Город, К-во мест, Статус]
                if len(parts) >= 4:
                    city = parts[1]
                    status_msg = parts[3]
                    return f"🕒 {last_dt} | {city} | {status_msg}"
                elif len(parts) >= 1:
                    return f"🕒 {last_dt} | {parts[-1]}"
            
            # Если дат нет, возможно посылка еще не в системе
            if "Результат поиска" in html and "не найдено" in html:
                return "Ожидает регистрации"
                
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
        
        # ЕСЛИ СТАТУС ИЗМЕНИЛСЯ (был "Ожидает регистрации", а стал реальным)
        if new_status != old_status and new_status not in ["Номер не найден", "Ожидает регистрации"]:
            df.at[i, 'status'] = new_status
            df.at[i, 'last_change'] = now
            
            comment = f" ({row['comment']})" if str(row['comment']) != "-" else ""
            msg = f"🔔 <b>ОБНОВЛЕНИЕ</b> ({carrier})\n📦 <code>{track}</code>{comment}\n{new_status}"
            send_telegram(msg)
            updated_any = True
        
        time.sleep(2)

    # Сохраняем обновленный файл
    repo.update_file(file.path, f"Pulse update {now}", df.to_csv(index=False), file.sha)

    # Если было хоть одно обновление - шлем финальный отчет
    if updated_any:
        report = "📋 <b>АКТУАЛЬНЫЙ СПИСОК ПОСЫЛОК:</b>\n" + "—" * 20 + "\n"
        for _, row in df.iterrows():
            trk = row['track_number']
            crr = "🚛" if "Новая" in str(row['carrier']) else "📦"
            cmt = f" ({row['comment']})" if str(row['comment']) != "-" else ""
            st_clean = str(row['status']).split('|')[-1].strip()
            report += f"{crr} <code>{trk}</code>{cmt}\n└ {st_clean}\n\n"
        send_telegram(report)

except Exception as e:
    send_telegram(f"⚠️ <b>Крит. ошибка скрипта:</b> {e}")
