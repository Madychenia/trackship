import streamlit as st
import pandas as pd
from datetime import datetime

# Настройка страницы
st.set_page_config(page_title="TrackShip", page_icon="📦", layout="centered")

st.title("📦 TrackShip: Управление заказами")

# Инициализация "базы данных" в сессии (пока временная)
if 'orders' not in st.session_state:
    st.session_state.orders = []

# --- Кнопка "Новый ордер" в сайдбаре или сверху ---
with st.expander("➕ Добавить новый ордер", expanded=False):
    with st.form("new_order_form", clear_on_submit=True):
        carrier = st.selectbox("Выберите логиста", ["Мист Экспресс", "Новая почта"])
        track_number = st.text_input("Введите трек-номер")
        submit_button = st.form_submit_button("Окей, добавить")

        if submit_button:
            if track_number:
                new_entry = {
                    "Дата": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Перевозчик": carrier,
                    "Трек-номер": track_number,
                    "Статус": "Ожидает обновления...",
                    "Последняя проверка": "-"
                }
                st.session_state.orders.append(new_entry)
                st.success(f"Трек {track_number} добавлен!")
            else:
                st.error("Введите номер трека!")

# --- Список заказов ---
st.subheader("Мои отслеживания")
if st.session_state.orders:
    df = pd.DataFrame(st.session_state.orders)
    st.dataframe(df, use_container_width=True)
    
    if st.button("🔄 Проверить статусы сейчас"):
        st.info("Здесь мы запустим парсер, когда пропишем логику...")
else:
    st.write("Пока нет активных заказов. Добавь первый!")

# Футер с информацией об автообновлении
st.divider()
st.caption("Автоматическая проверка: раз в 2 часа | Уведомления: Telegram")
