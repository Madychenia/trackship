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
        salt = '14e4e61ff1b43e7cdfe637371c188588'
        chk = hashlib.md5(f"{salt}{track}{salt}".encode()).hexdigest()
        
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
                city_el = last.find('City_RU') if last.find('City_RU') is not None else last.find('City')
                city = city_el.text if city_el is not None else ""
                msg_el = last.find('ActionMessages_RU') if last.find('ActionMessages_RU') is not None else last.find('ActionMessages')
                msg = msg_el.text if msg_el is not None else ""
                return f"🕒 {dt} | {city} | {msg}".strip()
        
        # План Б: HTML парсинг
        html_url = f"https://t.meest-group.com/int/ru/{track}"
        r_html = requests.get(html_url, headers=headers, timeout=15)
        if r_html.status_code == 200:
            dates = re.findall(r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})', r_html.text)
            if dates:
                last_dt = dates[-1]
                return f"🕒 {last_dt} | Обновлено через HTML"
                
    except: pass
    return "Ожидает регистрации"

def get_np_status(track):
    try:
        url = "https://personal.novaposhtaglobal.ua/tracking.php"
        token = "0cAFcWeA6nN8pnUq2D0XeRoY-gvgM_Zper_x50lC409vBb0HlDQpFbHRnCyWxfl5tRFSwxdSfBlMq2ZC8xGDVpQeOqEun5ufyc3xm8ftXzxhY7yTqe5dyZTit6BND7Fq-ShgKToHwto_XTEkQew-anYI45DlWPVhXzHUxq3zfJRnShIC2M53LSoYECbWeafTfKkrnIgF_W7zGJB-b8fqrIG2gb84Y1jjSvfLp26JLIo3HF9uq0L5GV7-Czum9D473uwJutY_W5Ekcz2_qXPI6IC50xqWu9-uhIl5fGR6DD2ep_t3_M2Wl02lap63V34b399Tt1-qg7d8YM7foGA1iBUPrGLx9XpllHKSKc7C5bvadSBWQqepLj8RswgbvDTcbH6O64OPukRwYa0LiOAAObsoLcvFWMKQeEYvPqU3auFTqc9juPkzJLZ5AhC_3FvAsYY-zEjxPETLlNwjkCBvk68P9AjURlvSvw2YKDh60ck-3N4cfmL6qU6UXsa0XL9knGePC-wWHKKOcEqcvs3cJxD97Otd-xiuqtIi6W2rbYk53BH_M3wlF8xsbEi_VswYLpUjeH1MR81r3igRYzQ8VfF-vhGXD32uiJwbLJ50MgEls0WowqwVXujcU_En0NQ3sPwNXwhPN-eRvNzI7kMd1ORY6W3waoQP1qCLFeVqxUVmT1jvbWxOuyv1lDbHEQpal5dn9pqcOTucssCziDuTyd1QHt92jHTWTWRm-ERsvDtEExL0mA2YOtPY0HCzKZHlOmSjsAKUwF8LPnLkp8X-HcyjfV1hRQZc5h1BZ1yNlTzCa7-f1iuEJ9nUFHF9vZf-Ioe77kno-_tFO0SSMb6yYX_N-NNniu_cbLgOGT00C8mmiq7UnxdbL-T250BsE0WISclpNzed7KqTNeaDlyR1XTS7zNTassoDbEJt7cYYYfcrb1T--tYTzUsGHE6Qcy4yoNkXT3bCatsy9kkk7sDDi1WJJeMSGqsaGiwR0QtwGGrKeg8cxY2Xszls-UmJxOfWa3YIn2RdxkiLDmEIZAysvMuWs2HK_abCN4JG3_mrlqMA6Wkx0-OXESkv85w7c87jpugiIfdrx6HUhtXJKFYpqoac8XO525IwAMzAfeFz3FkjzjOmjCd8OzWW2OsyBvfkHuiSLhp-6Rc8bPsBZqfUV-U2jbZ-UFiK1xIvi5bHOLH0ZUXD1MuLs95FOWJQLPbR_S2QYS471Xx-7uwMLnC7YrGLOkQv9CQKPjZnkY_RJyS-Bam7BSalIU2fOfh8_Arwm8mbgjBhQfonzlXFWoUk3Wr8zS_cYDQMPFNSfGpGIkExcHI0b517rDAfZITgHdvWAEnBtiTh09_XFKjj5H5SpxGDbA_WfbBxI21RRKU4apJe7uK3_mLVXHCrtGUNgg43JhhaoXHqXFd8YpA3L3i1C6yM4H0NsB-tQ0sBnVKBvd2e3vDzMmFcmWWKhIw201MKhwCinhO4tMD5KwsA0hixOUTd4cU-PB6QCOjmK5RnkGI-uUVf4C0cPBnZQquQGUMYxBrN7aa4ElpzOUN25NwalNjQcbHEMamX2iygdrdDpoIn5lEaBpu8esqJ8dH58DPoCbFRlK3e1eR-YCL3ZdTRhy02l5FV3QIqP3I3dchEPxmjNkyko9dQkabgZI24G4UYDvqjwWIq_Ny857GS4IxCvYXnO4K8ZOxRqGvXW6c8u2O-HOFhKoKntcU68U8sm8UpL5Yx4keUC1iND-H-xofVv0GgU3eI3jKYizmLpoW5n_9xQGkXptqBkl6tZz6pqZezRluimIO-qAJY3TiVxktwhf0K-aU9MbTy5Pu32WKXqQoOaaqOmTlhN2LSENHF-D_WSvWURnEHWuoYUP32T4_5Inq0gKhqAeP-MM_0xy36o3f_u8NDY0Pv2X0hjs43jkegO_XmncnN68Ih9Cdx7nTNuCh0lGlp5lyMOt0tF3qstmrOgtJs-i6q-qxQe1aipmbN67PbnEhf5sJNjcWO2orPLkDDJlRiTraPoGZ_X4dQNs1fosno5Zt1TFIRlAvdPY5DDmAiP2TQrO3Os1an3zrlqFiW1PC4N6g-PJTRQfPzLit7wrL7zKNlT5R41rgMoChMkxcRlIYiQxrsGo3xLmBc9bCw9FxaX0kh9SM0PB4DKzkGgAy8MgjW1CfPlkM1SIwQKX9opSAlyOoEJ2o52-4Jt-bsATgxXvccg9kEXInld9e9aMGN9CV20t5oEBIf7g16eslcytt4UTzJ"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'Origin': 'https://novaposhtaglobal.ua',
            'Referer': 'https://novaposhtaglobal.ua/'
        }

        # Отправляем именно через files= для multipart/form-data
        payload = {
            'token': (None, token),
            'num': (None, str(track).strip()),
            'lang': (None, 'Українська')
        }

        r = requests.post(url, files=payload, headers=headers, timeout=15)
        data = r.json()
        
        if 'historyStatus' in data and len(data['historyStatus']) > 0:
            last = data['historyStatus'][0] 
            return f"🚚 {last.get('date', '')} | {last.get('status', '')}"
            
    except: pass
    return "Ожидает регистрации"

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
            new_status = get_np_status(track)
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

    repo.update_file(file.path, f"Sync fix {now}", df.to_csv(index=False), file.sha)
    send_telegram(f"✅ <b>Проверка завершена</b> ({now})")

except Exception as e:
    send_telegram(f"🆘 <b>Ошибка:</b> {e}")
