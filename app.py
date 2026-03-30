import streamlit as st
import pandas as pd
from github import Github
from datetime import datetime
import io

st.set_page_config(page_title="TrackShip", layout="wide")

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

def load_data():
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    
    # 1. Защита от прошлого сбоя: если в файле русские заголовки, возвращаем им английский вид
    emergency_map = {'Трек': 'track_number', 'Оператор': 'carrier', 'Статус': 'status', 'Ласт': 'last_change', 'Чек': 'check_time'}
    df = df.rename(columns=emergency_map)

    # 2. Строго фиксируем технические колонки
    tech_cols = ['track_number', 'carrier', 'status', 'last_change', 'check_time']
    for col in tech_cols:
        if col not in df.columns:
            df[col] = "-"
            
    return df[tech_cols], file_content.sha

def save_data(df, sha):
    # Сохраняем ВСЕГДА только технические названия
    repo.update_file("data.csv", "Update tracking data", df.to_csv(index=False), sha)

st.title("📦 TrackShip")

try:
    df, file_sha = load_data()
except Exception as e:
    st.error(f"Ошибка загрузки: {e}")
    df = pd.DataFrame(columns=['track_number', 'carrier', 'status', 'last_change', 'check_time'])

with st.expander("➕ Новый ордер"):
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1: carrier = st.selectbox("Логист", ["Мист Экспресс", "Новая почта"])
        with col2: track = st.text_input("Трек-номер")
        if st.form_submit_button("Добавить"):
            if track:
                now = datetime.now().strftime("%d.%m %H:%M")
                new_row = pd.DataFrame([{
                    "track_number": track.strip(), 
                    "carrier": carrier, 
                    "status": "Ожидает регистрации", 
                    "last_change": now, 
                    "check_time": now
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df, file_sha)
                st.success("Добавлено!")
                st.rerun()

if not df.empty:
    st.write("### Твои посылки")
    
    # 3. Переводим на русский ТОЛЬКО для визуала (не меняя исходник)
    display_df = df.rename(columns={
        'track_number': 'Трек',
        'carrier': 'Оператор',
        'status': 'Статус',
        'last_change': 'Ласт',
        'check_time': 'Чек'
    })
    
    st.dataframe(
        display_df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Статус": st.column_config.TextColumn("Статус", width="large"),
            "Трек": st.column_config.TextColumn("Трек", width="medium"),
            "Оператор": st.column_config.TextColumn("Оператор", width="small"),
            "Ласт": st.column_config.TextColumn("Ласт", width="small"),
            "Чек": st.column_config.TextColumn("Чек", width="small")
        }
    )
