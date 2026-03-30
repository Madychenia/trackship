import streamlit as st
import pandas as pd
from github import Github
from datetime import datetime
import io

# 1. СРАЗУ ВКЛЮЧАЕМ ШИРОКИЙ ЭКРАН
st.set_page_config(page_title="TrackShip", layout="wide")

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

def load_data():
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    
    # Список всех нужных колонок
    mapping = {
        'track_number': 'Трек',
        'carrier': 'Оператор',
        'status': 'Статус',
        'last_change': 'Ласт',
        'check_time': 'Чек'
    }
    
    # Если каких-то колонок нет в файле (после чистки), создаем их пустыми
    for tech_name in mapping.keys():
        if tech_name not in df.columns:
            df[tech_name] = "-"

    # Оставляем и переименовываем строго в нужном порядке
    df = df[list(mapping.keys())].rename(columns=mapping)
    return df, file_content.sha

def save_data(df, sha):
    df_save = df.rename(columns={
        'Трек': 'track_number',
        'Оператор': 'carrier',
        'Статус': 'status',
        'Ласт': 'last_change',
        'Чек': 'check_time'
    })
    repo.update_file("data.csv", "Update tracking data", df_save.to_csv(index=False), sha)

st.title("📦 TrackShip")

try:
    df, file_sha = load_data()
except Exception as e:
    st.error(f"Ошибка загрузки: {e}")
    df = pd.DataFrame(columns=['Трек', 'Оператор', 'Статус', 'Ласт', 'Чек'])

with st.expander("➕ Новый ордер"):
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1: carrier = st.selectbox("Логист", ["Мист Экспресс", "Новая почта"])
        with col2: track = st.text_input("Трек-номер")
        if st.form_submit_button("Добавить"):
            if track:
                now = datetime.now().strftime("%d.%m %H:%M")
                new_row = pd.DataFrame([{"Трек": track.strip(), "Оператор": carrier, "Статус": "Добавлен", "Ласт": now, "Чек": now}])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df, file_sha)
                st.success("Добавлено!")
                st.rerun()

if not df.empty:
    st.write("### Твои посылки")
    # НАСТРОЙКА ОТОБРАЖЕНИЯ: Статус делаем очень широким
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Статус": st.column_config.TextColumn("Статус", width="large"),
            "Трек": st.column_config.TextColumn("Трек", width="medium"),
            "Оператор": st.column_config.TextColumn("Оператор", width="small"),
            "Ласт": st.column_config.TextColumn("Ласт", width="small"),
            "Чек": st.column_config.TextColumn("Чек", width="small"),
        }
    )
