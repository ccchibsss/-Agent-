# app.py - теперь только 150 строк вместо 1000!
import streamlit as st
from config import CONFIG
from utils import initialize_session_state, save_workflow_auto, save_messages_auto, save_history_auto, save_tables_auto
from ui_tabs import render_all_tabs
from styles import get_app_styles

def main():
    # Настройка страницы
    st.set_page_config(
        page_title=CONFIG.APP_TITLE,
        page_icon=CONFIG.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Применение стилей
    st.markdown(get_app_styles(), unsafe_allow_html=True)
    
    # Инициализация сессии
    initialize_session_state()
    
    # Автосохранение
    save_workflow_auto(st.session_state.get('workflow', []))
    save_messages_auto(st.session_state.get('agent_messages', []))
    save_history_auto(st.session_state.get('history', []))
    save_tables_auto(st.session_state.get('saved_tables', {}))
    
    # Заголовок
    st.markdown(f"""
    <div class="main-header">
        <h1>{CONFIG.APP_ICON} WORKFLOW BUILDER PRO v{CONFIG.APP_VERSION}</h1>
        <p>Обучаемые ИИ агенты | Таблицы | Изображения | Голос | Мобильная версия</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Рендерим все вкладки (код вынесен в ui_tabs.py)
    render_all_tabs()

if __name__ == "__main__":
    main()
