import streamlit as st
import pandas as pd
from github import Github
import datetime
import pytz
import io

st.set_page_config(page_title="TrackShip", layout="wide")
kiev_tz = pytz.timezone('Europe/Kiev')

# Защищенная загрузка секретов
try:
    GITHUB_TOKEN = st.secrets["G_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"]
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    secrets_ok = True
except Exception:
    st.error("🚨 Ошибка: Не найдены секреты G_TOKEN или REPO_NAME в настройках Streamlit!")
    secrets_ok = False

emergency_map = {'Трек': 'track_number', 'Оператор': 'carrier', 'Коммент': 'comment', 'Статус': 'status', 'Ласт': 'last_change', 'Чек': 'check_time'}
tech_cols = ['track_number', 'carrier', 'comment', 'status', 'last_change', 'check_time']

def load_data():
    file_content = repo.get_contents("data.csv")
    decoded = file_content.decoded_content.decode('utf-8')
    df = pd.read_csv(io.StringIO(decoded))
    # Проверка колонок
    if 'track_number' not in df.columns:
        df.columns = tech_cols
    return df, file_content.sha

def save_data(df, sha, msg="Update"):
    repo.update_file("data.csv", msg, df.to_csv(index=False), sha)

st.title("📦 TrackShip")

if secrets_ok:
    try:
        df, file_sha = load_data()
        
        if st.button("🔄 Запустить обновление (GitHub Actions)"):
            repo.get_workflow("main.yml").create_dispatch(repo.default_branch)
            st.success("Робот запущен! Обнови страницу через минуту.")

        # Отображение таблицы без кликабельности
        display_df = df.copy()
        display_df.columns = [next((k for k, v in emergency_map.items() if v == col), col) for col in df.columns]
        st.table(display_df)

        with st.expander("➕ Добавить посылку"):
            with st.form("add_form", clear_on_submit=True):
                carrier = st.selectbox("Логист", ["Мист Экспресс", "Новая почта"])
                track = st.text_input("Трек-номер")
                comment = st.text_input("Комментарий")
                if st.form_submit_button("Сохранить"):
                    now = datetime.datetime.now(kiev_tz).strftime("%d.%m %H:%M")
                    new_row = pd.DataFrame([[track.strip(), carrier, comment.strip() or "-", "Ожидает обновления", now, now]], columns=tech_cols)
                    df = pd.concat([df, new_row], ignore_index=True)
                    save_data(df, file_sha, f"Add {track}")
                    st.rerun()
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
