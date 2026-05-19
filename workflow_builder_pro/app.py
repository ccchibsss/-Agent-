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
    render_chat_tab, render_training_tab, render_memory_tab,
    render_analytics_tab, render_workflow_tab, render_conditions_tab,
    render_tables_tab, render_images_tab, render_help_tab,
    render_economy_tab
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
        'chat_input': "",
        'manual_edit_select': None,
        'ai_edit_select': None,
        'batch_operation': None,
        'train_input': "",
        'train_output': "",
        'mem_key': "",
        'mem_value': "",
        'test_condition': "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

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
    st.set_page_config(page_title=CONFIG.APP_TITLE, page_icon=CONFIG.APP_ICON, layout="wide", initial_sidebar_state="expanded")
    st.markdown(get_app_styles(), unsafe_allow_html=True)
    with st.spinner("Загрузка приложения..."):
        initialize_session_state()

    if st.session_state.workflow:
        save_workflow_auto(st.session_state.workflow)
    if st.session_state.agent_messages:
        save_messages_auto(st.session_state.agent_messages)
    if st.session_state.saved_tables:
        save_tables_auto(st.session_state.saved_tables)

    st.markdown(f"""
    <div class="main-header">
        <h1>{CONFIG.APP_ICON} WORKFLOW BUILDER PRO v{CONFIG.APP_VERSION}</h1>
        <p>Обучаемые ИИ агенты | Таблицы | Изображения | Голос | Экономика</p>
        <span class="version-badge">Монопоточная версия • {datetime.now().strftime('%Y')}</span>
    </div>""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## 🧠 МОИ ИИ АГЕНТЫ")
        api_key = st.text_input("🔑 DeepSeek API Ключ", type="password",
                                help="Получите бесплатно на platform.deepseek.com",
                                key="api_key_main")
        st.markdown("---")

        if st.session_state.agent_manager is None:
            st.session_state.agent_manager = AgentManager(api_key)
        agent_manager = st.session_state.agent_manager

        if st.session_state.table_manager:
            st.session_state.table_manager.api_key = api_key
        if st.session_state.image_manager:
            st.session_state.image_manager.api_key = api_key
        agent_manager.api_key = api_key

        for agent in agent_manager.agents.values():
            is_sel = agent_manager.current_agent_id == agent.id
            cls = "agent-card-selected" if is_sel else ""
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(f"📋 {agent.name}", key=f"select_{agent.id}", width='stretch'):
                    agent_manager.set_current_agent(agent.id)
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{agent.id}"):
                    agent_manager.delete_agent(agent.id)
                    st.rerun()

        st.markdown("---")

        with st.expander("➕ СОЗДАТЬ АГЕНТА", expanded=False):
            name = st.text_input("Имя", placeholder="Мой Помощник", key="new_agent_name")
            role = st.text_input("Роль", placeholder="эксперт по...", key="new_agent_role")
            prompt = st.text_area("Промпт", height=80, key="new_agent_prompt")
            if st.button("✨ Создать", width='stretch', key="create_agent_btn"):
                if name and role and prompt:
                    agent_manager.add_agent(name, role, prompt)
                    st.success(f"✅ Агент {name} создан!")
                    st.rerun()
                else:
                    st.warning("Заполните все поля")

        st.markdown("---")

        with st.expander("🔄 ЭКСПОРТ/ИМПОРТ", expanded=False):
            current = agent_manager.get_current_agent()
            if current:
                exp = agent_manager.export_agent(current.id)
                st.download_button("📤 Экспорт", exp, f"agent_{current.name}.json", "application/json")
            imp = st.file_uploader("Импорт", type=['json'], key="import_agent_file")
            if imp:
                content = imp.read().decode('utf-8')
                if agent_manager.import_agent(content):
                    st.success("✅ Агент импортирован!")
                    st.rerun()

        st.markdown("---")

        with st.expander("🗑️ Управление данными", expanded=False):
            if st.button("🔄 Сбросить workflow", width='stretch'):
                st.session_state.workflow = []
                save_workflow_auto([])
                st.rerun()
            if st.button("🗑️ Очистить чат", width='stretch'):
                st.session_state.agent_messages = []
                save_messages_auto([])
                st.rerun()
            if st.button("⚠️ Сбросить ВСЁ", width='stretch', type="secondary"):
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
        cur = agent_manager.get_current_agent()
        if cur:
            st.metric("Обучений", cur.stats['total_trainings'])
            st.metric("Диалогов", cur.stats['total_conversations'])
        st.metric("Загружено изобр.", len(st.session_state.uploaded_images))
        st.metric("Обработано изобр.", len(st.session_state.processed_images))

    if st.session_state.table_manager is None:
        st.session_state.table_manager = TableManager(api_key)
    if st.session_state.image_manager is None:
        st.session_state.image_manager = ImageManager(api_key)

    tabs = st.tabs([
        "💬 Диалог", "📚 Обучение", "🧠 Память", "📊 Аналитика",
        "🤖 Workflow", "🔀 Условия", "🗂 Таблицы+ИИ", "🧠 Экономика",
        "🖼️ Изображения", "📖 Справка"
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
        render_economy_tab(api_key)
    with tabs[8]:
        render_images_tab(api_key)
    with tabs[9]:
        render_help_tab()


if __name__ == "__main__":
    from config import WORKFLOW_FILE, AGENTS_FILE, MESSAGES_FILE, HISTORY_FILE, TABLES_FILE, IMAGES_METADATA_FILE, IMAGES_DIR
    main()
