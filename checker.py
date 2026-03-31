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
        # Используем публичную страницу, которая у нас открывается (код 200)
        url = f"https://t.meest-group.com/int/ru/{track}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'
        }
        
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return "Ожидает регистрации"

        html = r.text
        # Очищаем HTML от лишних пробелов и переносов для удобства поиска
        content = re.sub(r'\s+', ' ', html)

        # Ищем таблицу с результатами. Находим все даты в формате ГГГГ-ММ-ДД ЧЧ:ММ:СС
        dates = re.findall(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', content)
        
        if dates:
            # Берем самую свежую дату (она обычно последняя в списке)
            last_date = dates[-1]
            
            # Извлекаем кусок текста после этой даты до конца строки таблицы </tr>
            # Верстка Meest: <tr> <td>Дата</td> <td>Страна</td> <td>Город</td> <td>Места</td> <td>Статус</td> </tr>
            after_date = content.split(last_date)[-1].split('</tr>')[0]
            
            # Вытаскиваем всё, что находится внутри <td>...</td>
            cells = re.findall(r'<td.*?>(.*?)</td>', after_date)
            
            if len(cells) >= 4:
                city = re.sub('<[^<]+?>', '', cells[1]).strip() # Город
                status = re.sub('<[^<]+?>', '', cells[3]).strip() # Детальное сообщение
                return f"🕒 {last_date} | {city} | {status}"
            elif len(cells) > 0:
                # Если структура изменилась, берем последний найденный текст в ячейке
                last_info = re.sub('<[^<]+?>', '', cells[-1]).strip()
                return f"🕒 {last_date} | {last_info}"

        if "не найдено" in html or "Result is empty" in html:
            return "Ожидает регистрации"

    except Exception as e:
        print(f"Meest Parser Error: {e}")
    
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
        
        # Обновляем только если статус действительно изменился и это не ошибка
        if new_status != old_status and new_status not in ["Номер не найден", "Ожидает регистрации"]:
            df.at[i, 'status'] = new_status
            df.at[i, 'last_change'] = now
            
            comment = f" ({row['comment']})" if str(row['comment']) != "-" else ""
            msg = f"🔔 <b>ОБНОВЛЕНИЕ</b> ({carrier})\n📦 <code>{track}</code>{comment}\n{new_status}"
            send_telegram(msg)
            updated_any = True
        
        time.sleep(2)

    # Сохраняем результат в GitHub
    repo.update_file(file.path, f"Pulse update {now}", df.to_csv(index=False), file.sha)

    # Если были обновления — отправляем сводный отчет
    if updated_any:
        report = "📋 <b>АКТУАЛЬНЫЙ СПИСОК ПОСЫЛОК:</b>\n" + "—" * 20 + "\n"
        for _, row in df.iterrows():
            trk = row['track_number']
            cmt = f" ({row['comment']})" if str(row['comment']) != "-" else ""
            st_clean = str(row['status']).split('|')[-1].strip()
            report += f"📦 <code>{trk}</code>{cmt}\n└ {st_clean}\n\n"
        send_telegram(report)

except Exception as e:
    send_telegram(f"⚠️ <b>Крит. ошибка скрипта:</b>\n<code>{e}</code>")
