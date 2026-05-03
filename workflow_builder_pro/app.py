"""
Workflow Builder Pro - Главный файл приложения
"""
import streamlit as st

from config import CONFIG
from styles import get_app_styles
from utils import initialize_session_state, save_workflow_auto, save_messages_auto, save_history_auto, save_tables_auto
from ui_tabs import render_sidebar
from ai_agent import AgentManager
from table_manager import TableManager
from image_manager import ImageManager


def render_main_tabs(agent_manager, api_key):
    """Рендеринг всех вкладок"""
    from ui_tabs import (
        render_chat_tab, render_training_tab, render_memory_tab,
        render_analytics_tab, render_workflow_tab, render_conditions_tab,
        render_tables_tab, render_images_tab, render_help_tab
    )
    
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


def main():
    """Точка входа в приложение"""
    # Настройка страницы
    st.set_page_config(
        page_title=CONFIG.APP_TITLE,
        page_icon=CONFIG.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Стили
    st.markdown(get_app_styles(), unsafe_allow_html=True)
    
    # Инициализация
    initialize_session_state()
    
    # Заголовок
    st.markdown(f"""
    <div class="main-header">
        <h1>{CONFIG.APP_ICON} WORKFLOW BUILDER PRO v{CONFIG.APP_VERSION}</h1>
        <p>Обучаемые ИИ агенты | Таблицы | Изображения | Голос | Мобильная версия</p>
        <span class="version-badge">Монопоточная версия • ИИ удаление водяных знаков</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Боковая панель
    with st.sidebar:
        api_key = render_sidebar()
    
    # Инициализация менеджеров
    agent_manager = AgentManager()
    table_manager = TableManager(api_key)
    image_manager = ImageManager(api_key)
    
    st.session_state.agent_manager = agent_manager
    st.session_state.table_manager = table_manager
    st.session_state.image_manager = image_manager
    st.session_state.api_key = api_key
    
    # Автосохранение
    save_workflow_auto(st.session_state.get('workflow', []))
    save_messages_auto(st.session_state.get('agent_messages', []))
    save_history_auto(st.session_state.get('history', []))
    save_tables_auto(st.session_state.get('saved_tables', {}))
    
    # Основные вкладки
    render_main_tabs(agent_manager, api_key)


if __name__ == "__main__":
    main()


# ========== ТРЕБОВАНИЯ (requirements.txt) ==========
REQUIREMENTS_CONTENT = """
streamlit>=1.28.0
pandas>=2.0.0
openpyxl>=3.1.0
openai>=1.0.0
plotly>=5.17.0
requests>=2.31.0
Pillow>=10.0.0
rembg>=2.0.0
numpy>=1.24.0
python-dotenv>=1.0.0
SpeechRecognition>=3.10.0
gTTS>=2.3.0
"""
