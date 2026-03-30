import streamlit as st
import pandas as pd
from github import Github
from datetime import datetime
import pytz
import io

# Настройка страницы
st.set_page_config(page_title="TrackShip", layout="wide")
kiev_tz = pytz.timezone('Europe/Kiev')

# ФИКСИРУЕМ G_TOKEN
G_TOKEN = st.secrets["G_TOKEN"]
REPO_NAME = st.secrets["REPO_NAME"]

g = Github(G_TOKEN)
repo = g.get_repo(REPO_NAME)

emergency_map = {'Трек': 'track_number', 'Оператор': 'carrier', 'Коммент': 'comment', 'Статус': 'status', 'Ласт': 'last_change', 'Чек': 'check_time'}
tech_cols = ['track_number', 'carrier', 'comment', 'status', 'last_change', 'check_time']

def load_data():
    file_content = repo.get_contents("data.csv")
    df = pd.read_csv(io.StringIO(file_content.decoded_content.decode('utf-8')))
    if 'track_number' not in df.columns:
        df.columns = tech_cols
    return df, file_content.sha

def save_data(df, sha, msg="Update"):
    repo.update_file("data.csv", msg, df.to_csv(index=False), sha)

def trigger_action():
    # Файл должен называться check.yml
    workflow = repo.get_workflow("check.yml") 
    workflow.create_dispatch(repo.default_branch)

st.title("📦 TrackShip")

try:
    df, file_sha = load_data()
except:
    df = pd.DataFrame(columns=tech_cols)

if st.button("🔄 Обновить сейчас"):
    if df.empty:
        st.warning("Список треков пуст.")
    else:
        try:
            trigger_action()
            st.info("Запрос отправлен в GitHub. Подожди 1-2 минуты.")
        except Exception as e:
            st.error(f"Ошибка запуска: {e}")

# ТВОИ ДВЕ КОЛОНКИ
col_add, col_del = st.columns(2)
with col_add:
    with st.expander("➕ Добавить новую посылку"):
        with st.form("add_form", clear_on_submit=True):
            carrier = st.selectbox("Логист", ["Мист Экспресс", "Новая почта"])
            track = st.text_input("Трек-номер")
            comment = st.text_input("Что внутри? (Комментарий)")
            if st.form_submit_button("Сохранить"):
                if track:
                    now = datetime.now(kiev_tz).strftime("%d.%m %H:%M")
                    new_row = pd.DataFrame([{
                        "track_number": track.strip(), "carrier": carrier, 
                        "comment": comment.strip() or "-", "status": "Ожидает регистрации", 
                        "last_change": now, "check_time": now
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                    save_data(df, file_sha, f"Add: {track}")
                    st.success("Добавлено!")
                    st.rerun()

with col_del:
    if not df.empty:
        with st.expander("🗑 Удалить посылку"):
            with st.form("delete_form"):
                options = df.index.tolist()
                def format_func(idx):
                    row = df.loc[idx]
                    return f"📝 {row['comment']} [{row['track_number']}]"
                selected_idx = st.selectbox("Выберите для удаления", options, format_func=format_func)
                if st.form_submit_button("Удалить"):
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
    column_config={col: st.column_config.Column(disabled=True) for col in display_df.columns}
)
