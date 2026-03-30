import streamlit as st
import pandas as pd
from github import Github
from datetime import datetime
import io

# Конфигурация из Secrets
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]

# Подключение к GitHub
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

def load_data():
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    
    # Оставляем только нужные данные
    needed_cols = ['track_number', 'carrier', 'status', 'last_check']
    df = df[[c for c in needed_cols if c in df.columns]]
    
    # Переименовываем колонки для интерфейса
    df = df.rename(columns={
        'track_number': 'Трек',
        'carrier': 'Керри',
        'status': 'Статус',
        'last_check': 'Ласт'
    })
    return df, file_content.sha

def save_data(df, sha):
    # Перед сохранением возвращаем технические названия, чтобы checker.py их понимал
    df_save = df.rename(columns={
        'Трек': 'track_number',
        'Керри': 'carrier',
        'Статус': 'status',
        'Ласт': 'last_check'
    })
    csv_string = df_save.to_csv(index=False)
    repo.update_file("data.csv", "Update tracking data", csv_string, sha)

st.title("📦 TrackShip")

# Загрузка данных
try:
    df, file_sha = load_data()
except:
    st.error("Ошибка загрузки data.csv")
    df = pd.DataFrame(columns=['Трек', 'Керри', 'Статус', 'Ласт'])

# Форма добавления
with st.expander("➕ Новый ордер"):
    with st.form("add_form", clear_on_submit=True):
        carrier = st.selectbox("Логист", ["Мист Экспресс", "Новая почта"])
        track = st.text_input("Трек-номер")
        if st.form_submit_button("Добавить"):
            if track:
                new_row = pd.DataFrame([{
                    "Трек": track.strip(),
                    "Керри": carrier,
                    "Статус": "Ожидает регистрации",
                    "Ласт": datetime.now().strftime("%d.%m %H:%M")
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df, file_sha)
                st.success("Добавлено!")
                st.rerun()
            else:
                st.warning("Введите трек-номер")

# Отображение таблицы
if not df.empty:
    st.write("### Твои посылки")
    # hide_index убирает левую колонку с цифрами
    st.table(df) 
else:
    st.info("Список посылок пуст")
