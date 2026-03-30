def get_meest_status(track):
    try:
        session = requests.Session()
        # ВНИМАНИЕ: Здесь chk всё еще старый. Жду ваш cURL, чтобы это исправить!
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
        
        r = session.post(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            items = root.findall(".//items")
            
            if items:
                # Берем самый свежий статус (последний в XML списке)
                last = items[-1]
                
                # Собираем данные как на сайте
                dt_raw = last.find("DateTimeAction").text   # Дата/Час
                country = last.find("Country").text        # Країна
                city = last.find("City").text              # Місто
                msg = last.find("ActionMessages").text     # Детальне повідомлення
                
                # Форматируем в одну строку
                return f"{dt_raw} | {country}, {city} | {msg}"
            
            return "Статус: Данные в обработке"
            
        return f"Meest: Код {r.status_code} (Нужен новый chk)"
    except Exception as e:
        return f"Ошибка: {str(e)}"
