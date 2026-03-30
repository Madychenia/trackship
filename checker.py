import requests
import pandas as pd
from github import Github
import io
import os
from datetime import datetime
import time
import xml.etree.ElementTree as ET
import hashlib

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

def generate_meest_chk(track):
    # Магия вычисления подписи Meest
    # Соль вычислена на основе твоих cURL запросов
    salt = "625e1fc064" 
    string_to_hash = f"{track}{salt}"
    return hashlib.md5(string_to_hash.encode()).hexdigest()

def get_meest_status(track):
    try:
        # Генерируем уникальный ключ для этого конкретного трека
        chk = generate_meest_chk(track)
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&ext_track=&chk={chk}"
        
        headers = {
            'accept': 'application/xml, text/xml, */*; q=0.01',
            'origin': 'https://t.meest-group.com',
            'referer': 'https://t.meest-group.com/n/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        # POST запрос без тела
        r = requests.post(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            items = root.findall(".//items")
            
            if items:
                # Берем самое последнее событие из списка
                last = items[-1]
                
                dt = last.find("DateTimeAction").text   # Дата/Час
                msg = last.find("ActionMessages").text     # Детальное сообщение
                country = last.find("Country").text        # Країна
                city = last.find("City").text              # Місто
                
                # Собираем статус в точности как на сайте
                return f"🕒 {dt}\n📍 {country}, {city}\n📝 {msg}"
            
            return "📦 Статус: Ожидает обработки"
        return f"❌ Ошибка Meest (Код {r.status_code})"
    except Exception as e:
        return f"⚠️ Ошибка парсинга: {str(e)}"

# --- ОСНОВНОЙ ЦИКЛ ---
try:
    send_telegram("🚀 Робот запущен. Полная проверка всех треков...")
    
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
                
                # Отправляем в Телеграм детальный отчет
                send_telegram(f"🆔 Трек: {track}\n{new_status}")
                
                # Обновляем таблицу
                df.at[index, 'status'] = new_status
                df.at[index, 'last_check'] = datetime.now().strftime("%d.%m %H:%M")
                time.sleep(2)

        # Сохранение обновленного файла на GitHub
        new_csv = df.to_csv(index=False)
        repo.update_file("data.csv", "Auto-update: Multi-track Meest support", new_csv, file_content.sha)
        send_telegram("✅ База данных успешно обновлена.")
    else:
        send_telegram("📂 Файл data.csv пуст.")

except Exception as e:
    send_telegram(f"🚨 Критическая ошибка: {str(e)}")
