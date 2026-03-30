import streamlit as st
import pandas as pd
from github import Github
import datetime
import pytz
import io

# Настройка страницы
st.set_page_config(page_title="TrackShip", layout="wide")
kiev_tz = pytz.timezone('Europe/Kiev')

# Секреты
GITHUB_TOKEN = st.secrets["G_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

emergency_map = {'Трек': 'track_number', 'Оператор': 'carrier', 'Коммент': 'comment', 'Статус': 'status', 'Ласт': 'last_change', 'Чек': 'check_time'}
tech_cols = ['track_number', 'carrier', 'comment', 'status', 'last_change', 'check_time']

def load_data():
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    df = df.rename(columns=emergency_map)
    for col in tech_cols:
        if col not in df.columns: df[col] = "-"
    return df[tech_cols], file_content.sha

def save_data(df, sha, msg="Update"):
    repo.update_file("data.csv", msg, df.to_csv(index=False), sha)

def trigger_action():
    workflow = repo.get_workflow("main.yml") 
    workflow.create_dispatch(repo.default_branch)

st.title("📦 TrackShip")

df, file_sha = load_data()

col1, col2 = st.columns([1, 5])
with col1:
    if st.button("🔄 Обновить сейчас"):
        trigger_action()
        st.info("Запрос отправлен...")

# Статичный вывод таблицы
st.table(df.rename(columns={v: k for k, v in emergency_map.items()}))

with st.expander("➕ Добавить новую посылку"):
    with st.form("add_form", clear_on_submit=True):
        carrier = st.selectbox("Логист", ["Новая почта", "Мист Экспресс"])
        track = st.text_input("Трек-номер")
        comment = st.text_input("Комментарий")
        if st.form_submit_button("Сохранить"):
            now = datetime.datetime.now(kiev_tz).strftime("%d.%m %H:%M")
            new_row = pd.DataFrame([{
                "track_number": track.strip(), 
                "carrier": carrier, 
                "comment": comment.strip() or "-", 
                "status": "Ожидает регистрации", 
                "last_change": now, 
                "check_time": now
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, file_sha, f"Add: {track}")
            st.rerun()
