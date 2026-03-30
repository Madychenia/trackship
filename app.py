import streamlit as st
import pandas as pd
from github import Github
import datetime
import pytz
import io

st.set_page_config(page_title="TrackShip", layout="wide")
kiev_tz = pytz.timezone('Europe/Kiev')

# Секреты
G_TOKEN = st.secrets["G_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]

g = Github(G_TOKEN)
repo = g.get_repo(REPO_NAME)

def load_data():
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    return df, file_content.sha

def save_data(df, sha, msg="Update"):
    repo.update_file("data.csv", msg, df.to_csv(index=False), sha)

st.title("📦 Таблица заказов")

# --- ИНТЕРФЕЙС СВЕРХУ ---
with st.expander("➕ Добавить новую посылку", expanded=False):
    with st.form("add_form", clear_on_submit=True):
        carrier = st.selectbox("Оператор", ["Мист Экспресс", "Новая почта"])
        track = st.text_input("Трек-номер")
        comment = st.text_input("Комментарий")
        if st.form_submit_button("Сохранить"):
            df, file_sha = load_data()
            now = datetime.datetime.now(kiev_tz).strftime("%d.%m %H:%M")
            new_row = pd.DataFrame([[track.strip(), carrier, comment.strip() or "-", "Ожидает", now, now]], 
                                   columns=['track_number', 'carrier', 'comment', 'status', 'last_change', 'check_time'])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, file_sha, f"Add {track}")
            st.rerun()

if st.button("🔄 Обновить статусы"):
    # ИСПРАВЛЕНО: теперь стучимся именно в check.yml
    workflow = repo.get_workflow("check.yml") 
    workflow.create_dispatch(repo.default_branch)
    st.info("Запрос отправлен в GitHub Actions (файл check.yml)...")

# --- ТАБЛИЦА ---
df, file_sha = load_data()
disp_df = df.rename(columns={
    'track_number': 'Трек', 'carrier': 'Оператор', 'comment': 'Коммент', 
    'status': 'Статус', 'last_change': 'Ласт', 'check_time': 'Чек'
})

st.dataframe(disp_df, use_container_width=True, hide_index=True)
