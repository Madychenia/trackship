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
        # ИСПОЛЬЗУЕМ ПУБЛИЧНУЮ СТРАНИЦУ (БЕЗ CHK И API)
        url = f"https://t.meest-group.com/int/ru/{track}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8'
        }
        
        r = requests.get(url, headers=headers, timeout=20)
        
        if r.status_code == 200:
            html = r.text
            # Ищем все даты формата ГГГГ-ММ-ДД ЧЧ:ММ
            dates = re.findall(r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(?::\d{2})?)', html)
            
            if dates:
                # Берем самую последнюю дату на странице (самый свежий статус)
                last_date = dates[-1]
                
                # Ищем текст статуса, который идет после этой даты
                # Meest обычно пишет: Дата | Город | Сообщение
                # Мы ищем кусок текста после даты до следующего тега или конца строки
                pattern = f"{re.escape(last_date)}.*?<td>(.*?)</td>.*?<td>(.*?)</td>"
                match = re.search(pattern, html, re.DOTALL)
                
                if match:
                    city = match.group(1).strip().replace('<br>', ' ').replace('</br>', '')
                    msg = match.group(2).strip().replace('<br>', ' ').replace('</br>', '')
                    # Чистим от HTML тегов если остались
                    city = re.sub('<[^<]+?>', '', city)
                    msg = re.sub('<[^<]+?>', '', msg)
                    return f"🕒 {last_date} | {city} | {msg}"
                else:
                    # Если таблица сверстана иначе, пробуем упрощенный поиск
                    content_after = html.split(last_date)[-1]
                    clean_text = re.sub('<[^<]+?>', '|', content_after[:500])
                    parts = [p.strip() for p in clean_text.split('|') if p.strip() and len(p.strip()) > 2]
                    if len(parts) >= 2:
                        return f"🕒 {last_date} | {parts[0]} | {parts[1]}"
        
        # Если страница вернула 400 или не нашла данные — значит Meest блокирует IP
        if r.status_code == 400:
            print(f"Meest block for {track}")
            
    except Exception as e:
        print(f"Meest HTML Error: {e}")
        
    return "Ожидает регистрации"

def get_np_global_status(track):
    try:
        s = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        main_res = s.get("https://novaposhtaglobal.ua/track/", headers=headers, timeout=10)
        token_match = re.search(r'token["\']\s*:\s*["\']([^"\']+)["\']', main_res.text)
        token = token_match.group(1) if token_match else "0cAFcWeA7QMDv5taakZI9qezdhVlxCWBHetXLx0tyZbFuMezcIwmM1KeC1ficSFa25xIUnLUGfDhjBzolyFSwRczguYhM0zJNicIZPB--yrJ5N-7NojNWdGf2KV5AzdARqcObsO0hl90XMSczxVPpf1hO3llGRBDTUa1DXPGfZDyuY7FbZrB9vx0waCEEatTKrlEWTzJiThG-yCL4Bb13UonbD3C27ge4SblP4sbH6RELJuMmUivcgt0AUynhE8Teh-1f9zM0rhpVJe1ne0das351xpnfWXybCGXRD1R748oh_fCWQEOv4_AS0DfOz8PLLjP4M_6vwnvnO60zbsa6IW8esM1Sk0Gc9-1HKTXSDMyEgbhzG0qBfumdd9aqIvapGkBbtjMf4NDc687wkCByfaw0s1ckvPQPUKWj72lCtF1_OfCtkmS7kxEgbD5vl2ewnzpGBqyXEkFzKtX79YmEDlv1MiroiH4BOGTt0NUPKhVxR3lLp-UycWOqwOlzEGEiuVyV4z5YDlf2VECdzqPPP_l8WrGS4Mo9YQrEnMj2juLX-91h3uOSnm6WTKipBb5FwLMJULRjXFk_vS3zZnm1bZx8FusuVsCLlj7vC2W8WVYzO9UUnpcxLUOWyQ_lbZJMZSsU8yaMUzz4caPVKgOQE5SvoEjNUuYHbkXN3ctFvUH6MEswvRqto69Dc6YpXDPHT6gxMpXDKXp2YaA5w_Nlgi57z8zeqZw5P7T0-KdBQU44UXqzdFMAFpt01ZkQ4Sv8RFguGUpf-y2MQo-1mcjocCMYKk6_H4amRWR-tP1Xhbjhu3yWPulYzp94KE33xbT_UkbDahYfZm5D08Vgi_Kss6BYqYmkD-0MkBcJfgcWwLE6thgODqBPJABS8cD1gNXCkxg2-qpIUnYO1tI0-x1MhucldP6HHdylhedwkH8ayalONE-TqsERYi8YpYV7vtQMN49jrb254tI7ZCzFtQLvoEcoqxd8Hpi26Y8637vBMPA9AN7IpyjPxHUWO3NoTldS4TcnQxoLwi3GLQUYbioLrieEfh-XhCvXwRbSyI0PhdxeYkuPlYJi1Xuip_9zyIarKOR6q-dsYyuXmzytlxakw7-W56C9kF5MQ2MViuDhtrVtFLMFYjFs9jFTjbhw6SRpepF74wV7TR_0uHFW6-faWIDXvhlagn6rnE1PYHuKRLbWtbfJxZhDyi8VhcE07AuDwy_8HYc12rqhFXsSku_BjJUSjX4lnFAvAhehWtXjXqrLanjmyNodQM3xMb-7yETNpv7SgAitI9j3X8kR6p8SNcKr--32Anh4822albID6Zfq9XUKuzgRZmL4uGza0z986o8-HZfXBEU8z9zn75LiQ2HeEIaIyzxJ0v_nGnBXY4dfVl3eN16Kf0EbvneLGWLIDQwwqtoHsAt8q2Kg4vWflxrO8EUYMk6KF9aODqaqWfaR1ha549as5vLB8g6VvynHqpF8a2nzSQnyVnmG4xVoUIziOcPwG_Mgo4M1LdiH5S54EG_f0tPQBul0-vU8pt6RpEvp7BwyG1ReS4dIaqcsmQ52ov82Lr-XkgZGepF6OrOcd2ACy7Yp4jKqxAw5ga3VHS9zS_hj9DQg9k1Ax5gNzSV_hFP0uO6tf0V-hAD_-3F0t2MlrD7IZJxoPvkRxaScH0zkVCEFUUIs9b9Gbu7eLAE5T4br6SQAzd3mtM7vnHWusaEdp1_A1rA771hjMrrZobUH9T6is_ZpcP2ItmGFuIVgmONsH5IRHSDsb-7f_vu_i_cMPZrDElGnCTXGh_HAGlH04MZBoLQN5mc3ztxdfYKCb_sGEmXdC8IFiVKx59JHM6bacptEWC4jJig-lmf8nKNsM-hiJ0QwfZHh9qu-ULfL6z5xO8wfM4OHWWO-Fe2U0s24j9ZxiOpDZt6jVWyAgzoGlCfnUP__25zYwW_kSvbpC2LKxwlxGwPSxHV3FRV0fChbLu9CdTi4k0kUPnwkii27VMLS4oN-xi_hSQkXOP1UKSuKb_nBnC3JitOK8nScldkp6tr-aY5vP5fe7L_N-fHpWkyrvSNGa0OgJOxbnAZEqqtzQGjQUCjULqYo3qxk1CT-GUntNo2MKWzyO6O5ivk2pvJpsfBPYdszzut8k0_roJ5GmpL7B0gazwCQ6DHuU6gQW-1F7GxR9eXuH2as118exYfZWHt3ncWG1R_RPT59Hyfs0FpSnmkkyEmUAvtKO7mEQv7Qp1bu20f0dT1vRUa8WRemn2q93"
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
        
        if new_status != old_status and new_status not in ["Номер не найден", "Ожидает регистрации"]:
            df.at[i, 'status'] = new_status
            df.at[i, 'last_change'] = now
            
            comment = f" ({row['comment']})" if str(row['comment']) != "-" else ""
            msg = f"🔔 <b>ОБНОВЛЕНИЕ</b> ({carrier})\n📦 <code>{track}</code>{comment}\n{new_status}"
            send_telegram(msg)
            updated_any = True
        
        time.sleep(3) # Маленькая пауза чтобы не злить сервера

    repo.update_file(file.path, f"Pulse update {now}", df.to_csv(index=False), file.sha)

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
    print(f"Error: {e}")
