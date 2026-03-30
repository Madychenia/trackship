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

# Добавили "Коммент" в структуру базы
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

# Панель управления (Добавление и Удаление)
col_add, col_del = st.columns(2)

with col_add:
    with st.expander("➕ Новый ордер"):
        with st.form("add_form", clear_on_submit=True):
            carrier = st.selectbox("Логист", ["Мист Экспресс", "Новая почта"])
            track = st.text_input("Трек-номер")
            comment = st.text_input("Комментарий (что едет?)")
            
            if st.form_submit_button("Добавить"):
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
                    save_data(df, file_sha, f"Add track: {track}")
                    st.success("Добавлено!")
                    st.rerun()

with col_del:
    if not df.empty:
        with st.expander("🗑 Удалить ордер"):
            with st.form("delete_form"):
                # Используем индексы для безопасного удаления
                options = df.index.tolist()
                
                # Формируем красивое отображение в выпадающем списке (Трек + Коммент)
                def format_dropdown(idx):
                    tr = df.loc[idx, 'track_number']
                    cm = df.loc[idx, 'comment']
                    return f"{tr} ({cm})" if cm and cm != "-" else tr
                
                selected_idx = st.selectbox("Выберите посылку для удаления", options, format_func=format_dropdown)
                
                if st.form_submit_button("Удалить безвозвратно"):
                    track_to_delete = df.loc[selected_idx, 'track_number']
                    df = df.drop(selected_idx)
                    save_data(df, file_sha, f"Delete track: {track_to_delete}")
                    st.success(f"Трек удален!")
                    st.rerun()

if not df.empty:
    st.write("### Твои посылки")
    
    display_df = df.rename(columns={v: k for k, v in emergency_map.items()})
    
    st.dataframe(
        display_df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Статус": st.column_config.TextColumn("Статус", width="large"),
            "Коммент": st.column_config.TextColumn("Коммент", width="medium"),
            "Трек": st.column_config.TextColumn("Трек", width="medium"),
            "Оператор": st.column_config.TextColumn("Оператор", width="small"),
            "Ласт": st.column_config.TextColumn("Ласт", width="small"),
            "Чек": st.column_config.TextColumn("Чек", width="small")
        }
    )
