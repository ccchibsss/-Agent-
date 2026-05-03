"""
Workflow Builder Pro – Главный модуль приложения
Версия: 9.3.0 (с быстрым ИИ-редактированием Excel)
"""
import streamlit as st
from datetime import datetime

# Импорты из модулей проекта
from config import CONFIG
from utils import initialize_session_state, logger
from styles import get_app_styles
from table_manager import TableManager
from ai_agent import AgentManager
from image_manager import ImageManager
from ui_components import (
    render_chat_tab,
    render_training_tab,
    render_memory_tab,
    render_analytics_tab,
    render_workflow_tab,
    render_conditions_tab,
    render_tables_tab,
    render_images_tab,
    render_help_tab,
    render_sidebar
)


def main():
    """Точка входа приложения"""
    st.set_page_config(
        page_title=CONFIG.APP_TITLE,
        page_icon=CONFIG.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(get_app_styles(), unsafe_allow_html=True)

    # Инициализация session_state (создаёт все нужные переменные)
    initialize_session_state()

    # Заголовок
    st.markdown(f"""
    <div class="main-header">
        <h1>{CONFIG.APP_ICON} WORKFLOW BUILDER PRO v{CONFIG.APP_VERSION}</h1>
        <p>Обучаемые ИИ агенты | Таблицы | Изображения | Голос | Мобильная версия</p>
        <span class="version-badge">Монопоточная версия • {datetime.now().strftime('%Y')}</span>
    </div>
    """, unsafe_allow_html=True)

    # Боковая панель (рендерится отдельно, возвращает api_key)
    api_key = render_sidebar()

    # --- ИНИЦИАЛИЗАЦИЯ МЕНЕДЖЕРОВ С ОБНОВЛЕНИЕМ API-КЛЮЧА ---
    # TableManager
    if "table_manager" not in st.session_state:
        st.session_state.table_manager = TableManager(api_key)
    else:
        # Если ключ изменился – обновляем его в менеджере
        if st.session_state.table_manager.api_key != api_key:
            st.session_state.table_manager.api_key = api_key
            logger.info("API ключ обновлён в TableManager")

    # ImageManager
    if "image_manager" not in st.session_state:
        st.session_state.image_manager = ImageManager(api_key)
    else:
        if st.session_state.image_manager.api_key != api_key:
            st.session_state.image_manager.api_key = api_key

    # AgentManager (в его конструкторе api_key не требуется)
    if "agent_manager" not in st.session_state:
        st.session_state.agent_manager = AgentManager()

    agent_manager = st.session_state.agent_manager

    # --- ПРОВЕРКА НАЛИЧИЯ МЕТОДА ai_edit_excel_file (профилактика) ---
    if not hasattr(st.session_state.table_manager, 'ai_edit_excel_file'):
        st.error("❌ Ошибка: в TableManager отсутствует метод ai_edit_excel_file. Обновите table_manager.py")
        st.stop()

    # Основные вкладки
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
        render_tables_tab(api_key)          # <-- вызывает функцию из ui_components (с быстрым ИИ-редактором)
    with tabs[7]:
        render_images_tab(api_key)
    with tabs[8]:
        render_help_tab()


if __name__ == "__main__":
    main()
