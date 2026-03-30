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
    return pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8'))), file_content.sha

def save_data(df, sha):
    csv_string = df.to_csv(index=False)
    repo.update_file("data.csv", "Update tracking data", csv_string, sha)

st.title("📦 TrackShip")

# Загрузка данных
try:
    df, file_sha = load_data()
except:
    st.error("Ошибка загрузки data.csv")
    df = pd.DataFrame()

# Форма добавления
with st.expander("➕ Новый ордер"):
    with st.form("add_form", clear_on_submit=True):
        carrier = st.selectbox("Логист", ["Мист Экспресс", "Новая почта"])
        track = st.text_input("Трек-номер")
        if st.form_submit_button("Добавить"):
            new_row = pd.DataFrame([{
                "date": datetime.now().strftime("%d.%m %H:%M"),
                "carrier": carrier,
                "track_number": track,
                "status": "Добавлен",
                "last_check": "-"
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, file_sha)
            st.success("Сохранено в GitHub!")
            st.rerun()

# Отображение таблицы с кликабельными ссылками
if not df.empty:
    # Создаем ссылки для быстрого перехода
    def make_link(row):
        if row['carrier'] == "Мист Экспресс":
            return f"https://ua.meest.com/parcel-track?shipping_number={row['track_number']}"
        else:
            return f"https://novaposhtaglobal.ua/track/?query={row['track_number']}"

    df['Ссылка'] = df.apply(make_link, axis=1)
    st.write("### Твои посылки")
    st.dataframe(df, use_container_width=True)
