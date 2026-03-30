import requests
import pandas as pd
from github import Github
import io, os, hashlib, time
from datetime import datetime
import xml.etree.ElementTree as ET

GITHUB_TOKEN = os.getenv("G_TOKEN")
REPO_NAME = os.getenv("REPO_NAME")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": message}, timeout=10)

def get_meest_status(track):
    try:
        salt = "721f9793f5f239a47d69df922795267d"
        chk = hashlib.md5(f"{salt}{track}{salt}".encode()).hexdigest()
        url = f"https://t.meest-group.com/get.php?what=tracking&test&number={track}&lang=uk&chk={chk}"
        headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'x-requested-with': 'XMLHttpRequest'}
        session = requests.Session()
        session.get("https://t.meest-group.com/n/", timeout=10)
        r = session.post(url, headers=headers, timeout=15)
        if r.status_code == 200 and "<items>" in r.text:
            root = ET.fromstring(r.text)
            last = root.findall(".//items")[-1]
            dt = last.find('DateTimeAction').text or ""
            city_node = last.find('City')
            city = city_node.text if city_node is not None and city_node.text else ""
            msg = last.find('ActionMessages').text or ""
            return f"🕒 {dt} | {city} | {msg}"
        return "📦 Ожидает регистрации"
    except: return "⚠️ Ошибка Meest"

try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))

    emergency_map = {'Трек': 'track_number', 'Оператор': 'carrier', 'Коммент': 'comment', 'Статус': 'status', 'Ласт': 'last_change', 'Чек': 'check_time'}
    df = df.rename(columns=emergency_map)

    tech_cols = ['track_number', 'carrier', 'comment', 'status', 'last_change', 'check_time']
    for col in tech_cols:
        if col not in df.columns: df[col] = "-"

    if not df.empty:
        updated_any = False
        now = datetime.now().strftime("%d.%m %H:%M")
        
        for index, row in df.iterrows():
            if row['carrier'] == "Мист Экспресс":
                track = str(row['track_number']).strip()
                if track == "-" or track == "": continue
                
                # Достаем комментарий для Telegram
                comment = str(row['comment']).strip()
                comment_text = f" ({comment})" if comment and comment != "-" and comment != "nan" else ""
                
                new_status = get_meest_status(track)
                current_status = str(row['status'])
                
                df.at[index, 'check_time'] = now
                
                clean_new = new_status.replace(" | None | ", " | ").replace(" |  | ", " | ")
                clean_old = current_status.replace(" | None | ", " | ").replace(" |  | ", " | ").replace(" | УКРАЇНА None | ", " | ")
                
                if clean_new != clean_old and current_status != "-":
                    df.at[index, 'status'] = new_status
                    df.at[index, 'last_change'] = now
                    if not current_status.startswith("-"):
                        # Сообщение теперь содержит коммент
                        send_telegram(f"🔔 ОБНОВЛЕНИЕ\n📦 {track}{comment_text}\n{new_status}")
                elif current_status == "-":
                    df.at[index, 'status'] = new_status
                    df.at[index, 'last_change'] = now
                
                updated_any = True
            time.sleep(2)
            
        if updated_any:
            repo.update_file("data.csv", f"Pulse: {now}", df[tech_cols].to_csv(index=False), file_content.sha)
except Exception as e: send_telegram(f"🚨 Ошибка: {str(e)}")
