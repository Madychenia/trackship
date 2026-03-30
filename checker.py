import requests
import pandas as pd
from github import Github
import io
import os
from datetime import datetime
import time
import xml.etree.ElementTree as ET
import hashlib

# --- Секреты (берутся из настроек GitHub Actions) ---
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
    """Генерирует MD5 подпись для Meest на основе секретной соли"""
    salt = "625e1fc064" # Секретная соль, вычисленная из cURL
    string_to_hash = f"{track}{salt}"
    return hashlib.md5(string_to_hash.encode()).hexdigest()

def get_meest_status(track):
    """Получает детальный статус от Meest в формате XML"""
    try:
        chk = generate_meest_chk(track)
        # Формируем URL точно как в браузере
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&ext_track=&chk={chk}"
        
        headers = {
            'accept': 'application/xml, text/xml, */*; q=0.01',
            'origin': 'https://t.meest-group.com',
            'referer': 'https://t.meest-group.com/n/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        # POST запрос без тела (content-length: 0), как в cURL
        r = requests.post(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            items = root.findall(".//items")
            
            if items:
                # Берем самый последний статус (он в конце списка XML)
                last = items[-1]
                
                dt = last.find("DateTimeAction").text   # Дата и время
                msg = last.find("ActionMessages").text  # Сообщение
                country = last.find("Country").text     # Страна
                city = last.find("City").text           # Город
                
                # Собираем строку один в один как на сайте
                return f"{dt} | {country}, {city} | {msg}"
            
            return "📦 Статус: Ожидает регистрации"
            
        return f"Meest: Ошибка {r.status_code} (Bad chk)"
    except Exception as e:
        return f"⚠️ Ошибка парсинга: {str(e)}"

def get_nova_poshta_status(track):
    """Заглушка для Новой Почты (можно будет допилить логику позже)"""
    return "Функция в разработке"

# --- ОСНОВНОЙ ПРОЦЕСС ---
try:
    send_telegram("🤖 Робот запущен. Проверяю все треки...")
    
    # Подключаемся к GitHub
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    # Читаем файл data.csv
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    
    if not df.empty:
        updated_any = False
        
        for index, row in df.iterrows():
            track = str(row['track_number']).strip()
            carrier = row['carrier']
            
            if carrier == "Мист Экспресс":
                new_status = get_meest_status(track)
                
                # Если статус изменился, отправляем уведомление
                if str(row['status']) != new_status:
                    send_telegram(f"🔔 Трек: {track}\n{new_status}")
                    df.at[index, 'status'] = new_status
                    df.at[index, 'last_check'] = datetime.now().strftime("%d.%m %H:%M")
                    updated_any = True
                
                time.sleep(2) # Задержка, чтобы не забанили

        # Если были изменения, сохраняем файл обратно в репозиторий
        if updated_any:
            new_csv = df.to_csv(index=False)
            repo.update_file("data.csv", "Update tracking statuses", new_csv, file_content.sha)
            send_telegram("✅ Таблица на GitHub обновлена.")
        else:
            send_telegram("ℹ️ Новых изменений в статусах нет.")

    else:
        send_telegram("📂 Файл data.csv пуст.")

except Exception as e:
    send_telegram(f"🚨 Критическая ошибка: {str(e)}")
