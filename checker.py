import pandas as pd
from github import Github
import datetime
import pytz
import io
import os
import time
import requests

kiev_tz = pytz.timezone('Europe/Kiev')

# Переменные из Secrets
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

def get_np_global_status(track):
    """Парсинг Nova Poshta Global на основе твоего cURL"""
    url = 'https://personal.novaposhtaglobal.ua/tracking.php'
    
    # Тот самый токен из твоего запроса
    token = "0cAFcWeA7QMDv5taakZI9qezdhVlxCWBHetXLx0tyZbFuMezcIwmM1KeC1ficSFa25xIUnLUGfDhjBzolyFSwRczguYhM0zJNicIZPB--yrJ5N-7NojNWdGf2KV5AzdARqcObsO0hl90XMSczxVPpf1hO3llGRBDTUa1DXPGfZDyuY7FbZrB9vx0waCEEatTKrlEWTzJiThG-yCL4Bb13UonbD3C27ge4SblP4sbH6RELJuMmUivcgt0AUynhE8Teh-1f9zM0rhpVJe1ne0das351xpnfWXybCGXRD1R748oh_fCWQEOv4_AS0DfOz8PLLjP4M_6vwnvnO60zbsa6IW8esM1Sk0Gc9-1HKTXSDMyEgbhzG0qBfumdd9aqIvapGkBbtjMf4NDc687wkCByfaw0s1ckvPQPUKWj72lCtF1_OfCtkmS7kxEgbD5vl2ewnzpGBqyXEkFzKtX79YmEDlv1MiroiH4BOGTt0NUPKhVxR3lLp-UycWOqwOlzEGEiuVyV4z5YDlf2VECdzqPPP_l8WrGS4Mo9YQrEnMj2juLX-91h3uOSnm6WTKipBb5FwLMJULRjXFk_vS3zZnm1bZx8FusuVsCLlj7vC2W8WVYzO9UUnpcxLUOWyQ_lbZJMZSsU8yaMUzz4caPVKgOQE5SvoEjNUuYHbkXN3ctFvUH6MEswvRqto69Dc6YpXDPHT6gxMpXDKXp2YaA5w_Nlgi57z8zeqZw5P7T0-KdBQU44UXqzdFMAFpt01ZkQ4Sv8RFguGUpf-y2MQo-1mcjocCMYKk6_H4amRWR-tP1Xhbjhu3yWPulYzp94KE33xbT_UkbDahYfZm5D08Vgi_Kss6BYqYmkD-0MkBcJfgcWwLE6thgODqBPJABS8cD1gNXCkxg2-qpIUnYO1tI0-x1MhucldP6HHdylhedwkH8ayalONE-TqsERYi8YpYV7vtQMN49jrb254tI7ZCzFtQLvoEcoqxd8Hpi26Y8637vBMPA9AN7IpyjPxHUWO3NoTldS4TcnQxoLwi3GLQUYbioLrieEfh-XhCvXwRbSyI0PhdxeYkuPlYJi1Xuip_9zyIarKOR6q-dsYyuXmzytlxakw7-W56C9kF5MQ2MViuDhtrVtFLMFYjFs9jFTjbhw6SRpepF74wV7TR_0uHFW6-faWIDXvhlagn6rnE1PYHuKRLbWtbfJxZhDyi8VhcE07AuDwy_8HYc12rqhFXsSku_BjJUSjX4lnFAvAhehWtXjXqrLanjmyNodQM3xMb-7yETNpv7SgAitI9j3X8kR6p8SNcKr--32Anh4822albID6Zfq9XUKuzgRZmL4uGza0z986o8-HZfXBEU8z9zn75LiQ2HeEIaIyzxJ0v_nGnBXY4dfVl3eN16Kf0EbvneLGWLIDQwwqtoHsAt8q2Kg4vWflxrO8EUYMk6KF9aODqaqWfaR1ha549as5vLB8g6VvynHqpF8a2nzSQnyVnmG4xVoUIziOcPwG_Mgo4M1LdiH5S54EG_f0tPQBul0-vU8pt6RpEvp7BwyG1ReS4dIaqcsmQ52ov82Lr-XkgZGepF6OrOcd2ACy7Yp4jKqxAw5ga3VHS9zS_hj9DQg9k1Ax5gNzSV_hFP0uO6tf0V-hAD_-3F0t2MlrD7IZJxoPvkRxaScH0zkVCEFUUIs9b9Gbu7eLAE5T4br6SQAzd3mtM7vnHWusaEdp1_A1rA771hjMrrZobUH9T6is_ZpcP2ItmGFuIVgmONsH5IRHSDsb-7f_vu_i_cMPZrDElGnCTXGh_HAGlH04MZBoLQN5mc3ztxztxdfYKCb_sGEmXdC8IFiVKx59JHM6bacptEWC4jJig-lmf8nKNsM-hiJ0QwfZHh9qu-ULfL6z5xO8wfM4OHWWO-Fe2U0s24j9ZxiOpDZt6jVWyAgzoGlCfnUP__25zYwW_kSvbpC2LKxwlxGwPSxHV3FRV0fChbLu9CdTi4k0kUPnwkii27VMLS4oN-xi_hSQkXOP1UKSuKb_nBnC3JitOK8nScldkp6tr-aY5vP5fe7L_N-fHpWkyrvSNGa0OgJOxbnAZEqqtzQGjQUCjULqYo3qxk1CT-GUntNo2MKWzyO6O5ivk2pvJpsfBPYdszzut8k0_roJ5GmpL7B0gazwCQ6DHuU6gQW-1F7GxR9eXuH2as118exYfZWHt3ncWG1R_RPT59Hyfs0FpSnmkkyEmUAvtKO7mEQv7Qp1bu20f0dT1vRUa8WRemn2q93"
    
    files = {
        'token': (None, token),
        'num': (None, str(track)),
        'lang': (None, 'Українська'),
    }

    try:
        response = requests.post(url, files=files, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('error') == 0 and data.get('last_status'):
                status_text = data['last_status'].get('status_name', 'Нет данных')
                status_date = data['last_status'].get('date_status', '')
                return f"📦 {status_text} ({status_date})"
            return "📦 Номер не найден"
    except:
        return "⚠️ Ошибка связи с НП"
    return "⌛ Проверка..."

# ... (остальной код загрузки CSV и цикла проверки остается прежним) ...

# В цикле проверки замени вызов на:
# if carrier == "Новая почта":
#     new_status = get_np_global_status(track)
