def get_meest_status(track):
    try:
        session = requests.Session()
        # Тот самый ключ из твоего cURL, попробуем использовать его как основной
        chk = "8645141e4284290f547d92f1fa241731"
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&ext_track=&chk={chk}"
        
        headers = {
            'accept': 'application/xml, text/xml, */*; q=0.01',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'origin': 'https://t.meest-group.com',
            'referer': 'https://t.meest-group.com/n/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        # POST запрос с пустым телом, как в браузере
        r = session.post(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            items = root.findall(".//items")
            
            if items:
                # Берем самый последний статус (последний в списке XML)
                last_item = items[-1]
                
                # Извлекаем все нужные поля
                raw_date = last_item.find("DateTimeAction").text # 2026-03-20 19:55:48
                msg = last_item.find("ActionMessages").text      # Відправлено з Нью-Джерсі, США
                country = last_item.find("Country").text         # США
                city = last_item.find("City").text               # Порт-Рідінг
                
                # Форматируем дату (убираем секунды и год для краткости, если нужно)
                # Из "2026-03-20 19:55:48" делаем "20.03 19:55"
                try:
                    dt = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
                    pretty_date = dt.strftime("%d.%m %H:%M")
                except:
                    pretty_date = raw_date

                # Собираем финальную строку "один в один"
                full_status = f"{pretty_date} — {msg} ({country}, {city})"
                return full_status
            
            return "Данные о посылке еще не поступили"
            
        return f"Meest: Ошибка {r.status_code}"
    except Exception as e:
        return f"Ошибка обработки: {str(e)}"
