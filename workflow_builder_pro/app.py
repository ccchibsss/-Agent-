"""
Workflow Builder Pro – Главный модуль приложения
Версия: 9.2.1 (исправлена ошибка агентов, добавлено ИИ-редактирование Excel)
"""
import streamlit as st
from datetime import datetime

# Импорты из модулей проекта
from config import CONFIG
from utils import handle_errors, cache_result, logger, initialize_session_state
from styles import get_app_styles
from table_manager import TableManager
from ai_agent import AgentManager, AIAgent
from workflow import WorkflowExecutor
from image_manager import ImageManager
from condition_parser import RussianConditionParser
from voice import recognize_speech_from_audio, text_to_speech_mp3
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

# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ СЛОВАРЯ АГЕНТОВ (адаптация под разные реализации)
# ============================================================================
def get_agents_dict(agent_manager):
    """Возвращает словарь агентов {id: agent} из agent_manager или session_state"""
    # Пробуем разные возможные источники
    if hasattr(agent_manager, 'agents') and agent_manager.agents is not None:
        return agent_manager.agents
    if hasattr(agent_manager, '_agents') and agent_manager._agents is not None:
        return agent_manager._agents
    if hasattr(agent_manager, 'get_agents') and callable(agent_manager.get_agents):
        return agent_manager.get_agents()
    if 'agents' in st.session_state:
        return st.session_state.agents
    return {}

# ============================================================================
# РАСШИРЕННАЯ ВКЛАДКА ТАБЛИЦ С БЫСТРЫМ ИИ-РЕДАКТИРОВАНИЕМ EXCEL
# ============================================================================
def render_tables_tab_with_ai_edit(api_key: str):
    """Добавляет блок быстрого ИИ-редактирования Excel, затем вызывает оригинальную вкладку"""
    st.subheader("🗂 Таблицы + ИИ + Редактор")
    
    # ---------- БЫСТРОЕ ИИ-РЕДАКТИРОВАНИЕ EXCEL ----------
    st.markdown("## 🤖 Быстрое ИИ-редактирование Excel")
    st.markdown("Загрузите файл → опишите изменения на русском → скачайте результат")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        uploaded_excel = st.file_uploader(
            "📂 Выберите Excel файл",
            type=['xlsx', 'xls', 'csv'],
            key="ai_upload_excel",
            help="Поддерживаются .xlsx, .xls, .csv"
        )
    with col2:
        ai_instruction = st.text_area(
            "✏️ Инструкция для ИИ",
            height=120,
            placeholder="Примеры:\n- удалить пустые строки\n- создать столбец 'Итого' = Цена * Количество\n- отсортировать по дате\n- заменить все пропуски на 0",
            key="ai_instruction_quick"
        )
        run_ai = st.button("🚀 Применить ИИ", type="primary", use_container_width=True, key="run_ai_excel")
    
    if uploaded_excel and run_ai:
        if not api_key:
            st.error("❌ Введите API ключ DeepSeek в боковой панели")
        elif not ai_instruction.strip():
            st.warning("⚠️ Введите инструкцию для ИИ")
        else:
            with st.spinner("🧠 ИИ анализирует и применяет изменения..."):
                if "table_manager" not in st.session_state:
                    st.session_state.table_manager = TableManager(api_key)
                result = st.session_state.table_manager.ai_edit_excel_file(
                    input_file=uploaded_excel,
                    instruction=ai_instruction,
                    api_key=api_key,
                    sheet_name=0
                )
            if result['success']:
                st.success(result['message'])
                if result['transformations_applied']:
                    st.markdown("**🔧 Выполненные операции:**")
                    for desc in result['transformations_applied']:
                        st.markdown(f"- {desc}")
                st.markdown("### 👁️ Превью результата (первые 10 строк)")
                st.dataframe(result['df'].head(10), use_container_width=True)
                st.download_button(
                    label="📥 Скачать исправленный Excel",
                    data=result['output_bytes'],
                    file_name=f"fixed_{uploaded_excel.name}",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.error(f"❌ {result['error']}")
    
    st.markdown("---")
    
    # Оригинальная вкладка таблиц (из ui_components)
    try:
        render_tables_tab(api_key)
    except Exception as e:
        st.info(f"ℹ️ Дополнительные функции таблиц: {e}")

# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ ПРИЛОЖЕНИЯ
# ============================================================================
def main():
    st.set_page_config(
        page_title=CONFIG.APP_TITLE,
        page_icon=CONFIG.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(get_app_styles(), unsafe_allow_html=True)
    
    # Инициализация session_state (если есть функция из utils)
    if 'initialized' not in st.session_state:
        try:
            initialize_session_state()
        except:
            # Базовая инициализация
            st.session_state.agent_manager = None
            st.session_state.workflow = []
            st.session_state.agent_messages = []
            st.session_state.saved_tables = {}
            st.session_state.uploaded_images = {}
            st.session_state.processed_images = {}
        st.session_state.initialized = True
    
    # Заголовок
    st.markdown(f"""
    <div class="main-header">
        <h1>{CONFIG.APP_ICON} WORKFLOW BUILDER PRO v{CONFIG.APP_VERSION}</h1>
        <p>Обучаемые ИИ агенты | Таблицы | Изображения | Голос | Мобильная версия</p>
        <span class="version-badge">Монопоточная версия • {datetime.now().strftime('%Y')}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Боковая панель
    with st.sidebar:
        st.markdown("## 🧠 МОИ ИИ АГЕНТЫ")
        api_key = st.text_input(
            "🔑 DeepSeek API Ключ",
            type="password",
            help="Получите бесплатно на platform.deepseek.com",
            key="api_key_main"
        )
        st.session_state.api_key = api_key
        st.markdown("---")
        
        # Инициализация менеджера агентов
        if st.session_state.agent_manager is None:
            st.session_state.agent_manager = AgentManager()
        agent_manager = st.session_state.agent_manager
        
        # Получаем словарь агентов (без падения)
        agents_dict = get_agents_dict(agent_manager)
        
        if agents_dict:
            # Отображаем каждого агента
            for agent_id, agent in agents_dict.items():
                # agent может быть объектом или словарём
                if isinstance(agent, dict):
                    agent_name = agent.get('name', 'Без имени')
                    agent_id_val = agent_id
                else:
                    agent_name = agent.name if hasattr(agent, 'name') else str(agent)
                    agent_id_val = agent.id if hasattr(agent, 'id') else agent_id
                
                # Проверяем, выбран ли этот агент
                is_selected = False
                if hasattr(agent_manager, 'current_agent_id'):
                    is_selected = (agent_manager.current_agent_id == agent_id_val)
                
                col1, col2 = st.columns([4, 1])
                with col1:
                    btn_label = f"📋 {agent_name}" + (" ✅" if is_selected else "")
                    if st.button(btn_label, key=f"select_{agent_id_val}", use_container_width=True):
                        if hasattr(agent_manager, 'set_current_agent'):
                            agent_manager.set_current_agent(agent_id_val)
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"del_{agent_id_val}"):
                        if hasattr(agent_manager, 'delete_agent'):
                            agent_manager.delete_agent(agent_id_val)
                        st.rerun()
        else:
            st.info("Нет агентов. Создайте нового.")
        
        st.markdown("---")
        
        # Создание нового агента
        with st.expander("➕ СОЗДАТЬ АГЕНТА", expanded=False):
            new_name = st.text_input("Имя", placeholder="Мой Помощник", key="new_agent_name")
            new_role = st.text_input("Роль", placeholder="эксперт по...", key="new_agent_role")
            new_prompt = st.text_area("Промпт", height=80, key="new_agent_prompt")
            if st.button("✨ Создать", use_container_width=True):
                if new_name and new_role and new_prompt:
                    if hasattr(agent_manager, 'add_agent'):
                        agent_manager.add_agent(new_name, new_role, new_prompt)
                        st.success(f"✅ Агент {new_name} создан!")
                        st.rerun()
                    else:
                        st.error("Метод add_agent не найден в AgentManager")
        
        st.markdown("---")
        
        # Статистика
        st.markdown("## 📊 СТАТИСТИКА")
        if agents_dict:
            st.metric("Агентов", len(agents_dict))
        if hasattr(agent_manager, 'get_current_agent'):
            current = agent_manager.get_current_agent()
            if current:
                if hasattr(current, 'stats'):
                    stats = current.stats
                    st.metric("Обучений", stats.get('total_trainings', 0))
                    st.metric("Диалогов", stats.get('total_conversations', 0))
        
        st.markdown("---")
        if st.button("🗑️ Очистить workflow", use_container_width=True):
            st.session_state.workflow = []
            st.rerun()
    
    # Инициализация менеджеров (если ещё нет)
    if "table_manager" not in st.session_state:
        st.session_state.table_manager = TableManager(api_key)
    if "image_manager" not in st.session_state:
        st.session_state.image_manager = ImageManager(api_key)
    
    # Вкладки
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
        render_tables_tab(api_key)   # используем функцию из ui_components
    with tabs[7]:
        render_images_tab(api_key)
    with tabs[8]:
        render_help_tab()

if __name__ == "__main__":
    main()
