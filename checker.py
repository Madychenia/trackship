import requests
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime

def generate_meest_chk(track):
    # Секретная соль, вычисленная из твоих cURL-запросов
    salt = "625e1fc064" 
    return hashlib.md5(f"{track}{salt}".encode()).hexdigest()

def get_meest_status(track):
    try:
        # Генерируем индивидуальный chk для каждого трека
        chk = generate_meest_chk(track)
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&ext_track=&chk={chk}"
        
        headers = {
            'accept': 'application/xml, text/xml, */*; q=0.01',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        # Meest требует POST без тела
        r = requests.post(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            items = root.findall(".//items")
            
            if items:
                # Забираем самый верхний статус из таблицы (последний в XML)
                last = items[-1]
                
                # Собираем данные как на скриншоте сайта
                date_raw = last.find("DateTimeAction").text   # 2026-03-20 19:55:48
                country = last.find("Country").text          # США
                city = last.find("City").text               # Порт-Рідінг
                message = last.find("ActionMessages").text   # Відправлено з Нью-Джерсі, США
                
                # Форматируем: "Дата | Город | Сообщение"
                return f"{date_raw} | {country}, {city} | {message}"
            
            return "Данные обрабатываются"
        return f"Meest: Ошибка {r.status_code}"
    except Exception as e:
        return f"Ошибка системы: {str(e)}"
