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

emergency_map = {'Трек': 'track_number', 'Оператор': 'carrier', 'Коммент': 'comment', 'Статус': 'status', 'Ласт': 'last_change', 'Чек': 'check_time'}
tech_cols = ['track_number', 'carrier', 'comment', 'status', 'last_change', 'check_time']

def load_data():
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    df = df.rename(columns=emergency_map)
    for col in tech_cols:
        if col not in df.columns:
            df[col] = "-"
    return df[tech_cols], file_content.sha

def save_data(df, sha, commit_message="Update tracking data"):
    repo.update_file("data.csv", commit_message, df.to_csv(index=False), sha)

st.title("📦 TrackShip")

try:
    df, file_sha = load_data()
except Exception as e:
    st.error(f"Ошибка загрузки: {e}")
    df = pd.DataFrame(columns=tech_cols)

col_add, col_del = st.columns(2)

with col_add:
    with st.expander("➕ Добавить новую посылку"):
        with st.form("add_form", clear_on_submit=True):
            carrier = st.selectbox("Логист", ["Мист Экспресс", "Новая почта"])
            track = st.text_input("Трек-номер")
            comment = st.text_input("Что внутри? (Комментарий)")
            
            if st.form_submit_button("Сохранить"):
                if track:
                    now = datetime.now().strftime("%d.%m %H:%M")
                    new_row = pd.DataFrame([{
                        "track_number": track.strip(), 
                        "carrier": carrier, 
                        "comment": comment.strip() if comment else "-",
                        "status": "Ожидает регистрации", 
                        "last_change": now, 
                        "check_time": now
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                    save_data(df, file_sha, f"Add: {track}")
                    st.success("Добавлено!")
                    st.rerun()

with col_del:
    if not df.empty:
        with st.expander("🗑 Удалить посылку"):
            with st.form("delete_form"):
                # Создаем список индексов для выбора
                options = df.index.tolist()
                
                # Функция красивого отображения: Сначала Коммент, потом Трек
                def format_func(idx):
                    row = df.loc[idx]
                    comment = str(row['comment'])
                    track = str(row['track_number'])
                    if comment and comment != "-":
                        return f"📝 {comment}  [{track}]"
                    return f"📦 {track}"
                
                selected_idx = st.selectbox(
                    "Поиск по названию или треку", 
                    options, 
                    format_func=format_func,
                    help="Начни вводить название товара для быстрого поиска"
                )
                
                if st.form_submit_button("Удалить выбранное"):
                    track_val = df.loc[selected_idx, 'track_number']
                    df = df.drop(selected_idx)
                    save_data(df, file_sha, f"Delete: {track_val}")
                    st.success("Удалено!")
                    st.rerun()

if not df.empty:
    st.write("### Активные отслеживания")
    display_df = df.rename(columns={v: k for k, v in emergency_map.items()})
    st.dataframe(
        display_df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Статус": st.column_config.TextColumn("Статус", width="large"),
            "Коммент": st.column_config.TextColumn("Коммент", width="medium"),
            "Трек": st.column_config.TextColumn("Трек", width="medium"),
        }
    )
