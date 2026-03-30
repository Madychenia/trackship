def get_meest_status(track):
    try:
        import xml.etree.ElementTree as ET
        import hashlib
        import requests

        salt = "721f9793f5f239a47d69df922795267d"
        chk = hashlib.md5(f"{salt}{track}{salt}".encode()).hexdigest()
        
        # Строго хардкодим URL как в твоем старом рабочем коде (без словарей params)
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&chk={chk}"
        
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 
            'x-requested-with': 'XMLHttpRequest'
        }
        
        # Делаем именно POST запрос
        r = requests.post(url, headers=headers, timeout=15)
        
        if r.status_code == 200 and "<items>" in r.text:
            root = ET.fromstring(r.text)
            items = root.findall(".//items")
            if items:
                last = items[-1]
                dt = last.find('DateTimeAction').text or ""
                city = last.find('City').text if last.find('City') is not None else ""
                msg = last.find('ActionMessages').text or ""
                return f"🕒 {dt} | {city} | {msg}".strip()
    except Exception as e:
        print(f"Meest Error: {e}")
        pass
        
    return "Ожидает регистрации"
