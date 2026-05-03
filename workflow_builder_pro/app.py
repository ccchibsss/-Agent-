"""
Главное приложение Streamlit.
"""
import streamlit as st
from datetime import datetime
from config import CONFIG
from styles import get_app_styles
from utils import (
    save_workflow_auto, save_messages_auto, save_history_auto, save_tables_auto,
    load_workflow_auto, load_messages_auto, load_history_auto, load_agents_auto, load_tables_auto
)
from ai_agent import AgentManager
from table_manager import TableManager
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
    render_help_tab
)
import shutil

def initialize_session_state():
    defaults = {
        'agent_manager': None,
        'workflow': [],
        'agent_messages': [],
        'history': [],
        'analytics': {'total_executions': 0, 'successful_executions': 0, 'failed_executions': 0},
        'voice_show_upload': False,
        'table_manager': None,
        'current_df': None,
        'excel_loaded': False,
        'data_loaded': False,
        'saved_tables': {},
        'table_edit_mode': False,
        'editing_table_id': None,
        'image_manager': None,
        'uploaded_images': {},
        'processed_images': {},
        'image_batch_progress': 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    if not st.session_state.get('data_loaded'):
        saved_workflow = load_workflow_auto()
        if saved_workflow:
            st.session_state.workflow = saved_workflow
        
        saved_messages = load_messages_auto()
        if saved_messages:
            st.session_state.agent_messages = saved_messages
        
        saved_history = load_history_auto()
        if saved_history:
            st.session_state.history = saved_history
        
        saved_agents = load_agents_auto()
        if saved_agents and 'agents' not in st.session_state:
            st.session_state.agents = saved_agents
        
        saved_tables = load_tables_auto()
        if saved_tables:
            st.session_state.saved_tables = saved_tables
        
        st.session_state.data_loaded = True

def main():
    st.set_page_config(
        page_title=CONFIG.APP_TITLE,
        page_icon=CONFIG.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(get_app_styles(), unsafe_allow_html=True)
    initialize_session_state()
    
    # Автосохранение изменений
    if 'workflow' in st.session_state:
        save_workflow_auto(st.session_state.workflow)
    if 'agent_messages' in st.session_state:
        save_messages_auto(st.session_state.agent_messages)
    if 'saved_tables' in st.session_state:
        save_tables_auto(st.session_state.saved_tables)
    
    st.markdown(f"""
    <div class="main-header">
        <h1>{CONFIG.APP_ICON} WORKFLOW BUILDER PRO v{CONFIG.APP_VERSION}</h1>
        <p>Обучаемые ИИ агенты | Таблицы | Изображения | Голос | Мобильная версия</p>
        <span class="version-badge">Монопоточная версия • {datetime.now().strftime('%Y')}</span>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("## 🧠 МОИ ИИ АГЕНТЫ")
        api_key = st.text_input("🔑 DeepSeek API Ключ", type="password", help="Получите бесплатно на platform.deepseek.com", key="api_key_main")
        st.markdown("---")
        
        if st.session_state.agent_manager is None:
            st.session_state.agent_manager = AgentManager()
        agent_manager = st.session_state.agent_manager
        
        for agent in agent_manager.agents.values():
            is_selected = agent_manager.current_agent_id == agent.id
            selected_class = "agent-card-selected" if is_selected else ""
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(f"📋 {agent.name}", key=f"select_{agent.id}", use_container_width=True):
                    agent_manager.set_current_agent(agent.id)
                    st.rerun()
            with col2:
                if st.button(f"🗑️", key=f"del_{agent.id}"):
                    agent_manager.delete_agent(agent.id)
                    st.rerun()
        
        st.markdown("---")
        with st.expander("➕ СОЗДАТЬ АГЕНТА", expanded=False):
            new_name = st.text_input("Имя", placeholder="Мой Помощник", key="new_agent_name")
            new_role = st.text_input("Роль", placeholder="эксперт по...", key="new_agent_role")
            new_prompt = st.text_area("Промпт", height=80, key="new_agent_prompt")
            if st.button("✨ Создать", use_container_width=True, key="create_agent_btn"):
                if new_name and new_role and new_prompt:
                    agent_manager.add_agent(new_name, new_role, new_prompt)
                    st.success(f"✅ Агент {new_name} создан!")
                    st.rerun()
                else:
                    st.warning("Заполните все поля")
        
        st.markdown("---")
        with st.expander("🔄 ЭКСПОРТ/ИМПОРТ", expanded=False):
            current = agent_manager.get_current_agent()
            if current:
                export_json = agent_manager.export_agent(current.id)
                st.download_button("📤 Экспорт", export_json, f"agent_{current.name}.json", "application/json")
            import_file = st.file_uploader("Импорт", type=['json'], key="import_agent_file")
            if import_file:
                content = import_file.read().decode('utf-8')
                if agent_manager.import_agent(content):
                    st.success("✅ Агент импортирован!")
                    st.rerun()
        
        st.markdown("---")
        with st.expander("🗑️ Управление данными", expanded=False):
            if st.button("🔄 Сбросить workflow", use_container_width=True):
                st.session_state.workflow = []
                save_workflow_auto([])
                st.rerun()
            if st.button("🗑️ Очистить чат", use_container_width=True):
                st.session_state.agent_messages = []
                save_messages_auto([])
                st.rerun()
            if st.button("⚠️ Сбросить ВСЁ", use_container_width=True, type="secondary"):
                from config import WORKFLOW_FILE, AGENTS_FILE, MESSAGES_FILE, HISTORY_FILE, TABLES_FILE, IMAGES_METADATA_FILE, IMAGES_DIR
                for f in [WORKFLOW_FILE, AGENTS_FILE, MESSAGES_FILE, HISTORY_FILE, TABLES_FILE, IMAGES_METADATA_FILE]:
                    if f.exists():
                        f.unlink()
                if IMAGES_DIR.exists():
                    shutil.rmtree(IMAGES_DIR)
                    IMAGES_DIR.mkdir(exist_ok=True)
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        st.markdown("---")
        st.markdown("## 📊 СТАТИСТИКА")
        st.metric("Агентов", len(agent_manager.agents))
        current = agent_manager.get_current_agent()
        if current:
            st.metric("Обучений", current.stats['total_trainings'])
            st.metric("Диалогов", current.stats['total_conversations'])
        st.metric("Загружено", len(st.session_state.uploaded_images))
        st.metric("Обработано", len(st.session_state.processed_images))
    
    if st.session_state.table_manager is None:
        st.session_state.table_manager = TableManager(api_key)
    if st.session_state.image_manager is None:
        st.session_state.image_manager = ImageManager(api_key)
    
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
