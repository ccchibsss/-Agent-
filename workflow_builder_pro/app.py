# app.py - ГЛАВНЫЙ ФАЙЛ ДЛЯ ЗАПУСКА
"""
Workflow Builder Pro - Главный файл приложения для Streamlit
Запуск: streamlit run app.py
"""
import streamlit as st

# Импорт модулей
from config import CONFIG
from styles import get_app_styles
from utils import initialize_session_state, save_workflow_auto, save_messages_auto, save_history_auto, save_tables_auto
from ai_agent import AgentManager
from table_manager import TableManager
from image_manager import ImageManager
from ui_components import (
    render_sidebar,
    render_chat_tab,
    render_training_tab,
    render_memory_tab,
    render_analytics_tab,
    render_workflow_tab,
    render_conditions_tab,
    render_tables_tab,
    render_images_tab,
    render_help_tab
)


def main():
    """Точка входа в приложение"""
    # Настройка страницы Streamlit
    st.set_page_config(
        page_title=CONFIG.APP_TITLE,
        page_icon=CONFIG.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Применение CSS стилей
    st.markdown(get_app_styles(), unsafe_allow_html=True)
    
    # Инициализация session_state
    initialize_session_state()
    
    # Заголовок приложения
    st.markdown(f"""
    <div class="main-header">
        <h1>{CONFIG.APP_ICON} WORKFLOW BUILDER PRO v{CONFIG.APP_VERSION}</h1>
        <p>Обучаемые ИИ агенты | Таблицы | Изображения | Голос | Мобильная версия</p>
        <span class="version-badge">Монопоточная версия • ИИ удаление водяных знаков</span>
    </div>
    """, unsafe_allow_html=True)
    
    # === БОКОВАЯ ПАНЕЛЬ STREAMLIT ===
    with st.sidebar:
        api_key = render_sidebar()
    
    # === ИНИЦИАЛИЗАЦИЯ МЕНЕДЖЕРОВ ===
    agent_manager = AgentManager()
    table_manager = TableManager(api_key)
    image_manager = ImageManager(api_key)
    
    # Сохраняем в session_state для доступа из других функций
    st.session_state.agent_manager = agent_manager
    st.session_state.table_manager = table_manager
    st.session_state.image_manager = image_manager
    st.session_state.api_key = api_key
    
    # === АВТОСОХРАНЕНИЕ ===
    save_workflow_auto(st.session_state.get('workflow', []))
    save_messages_auto(st.session_state.get('agent_messages', []))
    save_history_auto(st.session_state.get('history', []))
    save_tables_auto(st.session_state.get('saved_tables', {}))
    
    # === ОСНОВНЫЕ ВКЛАДКИ STREAMLIT ===
    tabs = st.tabs([
        "💬 Диалог", "📚 Обучение", "🧠 Память", "📊 Аналитика",
        "🤖 Workflow", "🔀 Условия", "🗂 Таблицы+ИИ", "🖼️ Изображения", "📖 Справка"
    ])
    
    with tabs[0]:
        render_chat_tab(agent_manager, api_key)
    with tabs[1]:
        render_training_tab(agent_manager)
    with tabs[2]:
        render_memory_tab(agent_manager)
    with tabs[3]:
        render_analytics_tab(agent_manager)
    with tabs[4]:
        render_workflow_tab(agent_manager, api_key)
    with tabs[5]:
        render_conditions_tab()
    with tabs[6]:
        render_tables_tab(api_key)
    with tabs[7]:
        render_images_tab(api_key)
    with tabs[8]:
        render_help_tab()


if __name__ == "__main__":
    main()
