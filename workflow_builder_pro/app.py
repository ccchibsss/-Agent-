"""
Workflow Builder Pro – Главный модуль приложения
Версия: 9.2.1 (с быстрым ИИ-редактированием Excel)
"""
import streamlit as st
from datetime import datetime
from typing import Dict, List, Any

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
    render_tables_tab,      # эта функция будет расширена (см. ниже)
    render_images_tab,
    render_help_tab
)

# ============================================================================
# РАСШИРЕННАЯ ФУНКЦИЯ ДЛЯ ВКЛАДКИ ТАБЛИЦ (ДОБАВЛЯЕМ БЫСТРОЕ ИИ-РЕДАКТИРОВАНИЕ)
# ============================================================================
def render_tables_tab_with_ai_edit(api_key: str):
    """
    Рендерит вкладку таблиц, добавляя блок быстрого ИИ-редактирования Excel.
    Остальной функционал (сохранённые таблицы, редактор) берётся из оригинальной render_tables_tab.
    """
    # Вызываем оригинальную функцию (если она уже содержит базовый интерфейс)
    # Но чтобы не дублировать, мы сначала показываем новый блок, затем – остальное.
    st.subheader("🗂 Таблицы + ИИ + Редактор")
    
    # ---------- НОВЫЙ БЛОК: Быстрое ИИ-редактирование Excel ----------
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
            placeholder="Примеры:\n- удалить пустые строки\n- создать столбец 'Итого' = Цена * Количество\n- отсортировать по дате\n- заменить все пропуски на 0\n- отфильтровать строки, где Статус = 'Активен'",
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
                # Создаём менеджер таблиц, если ещё нет
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
    
    # Вызов оригинальной функции render_tables_tab (без нового блока, чтобы не дублировать)
    # Предполагается, что исходная render_tables_tab из ui_components содержит остальной функционал
    # (сохранённые таблицы, редактор, загрузка из Google Sheets и т.д.)
    try:
        from ui_components import render_tables_tab as original_tables_tab
        original_tables_tab(api_key)
    except ImportError:
        st.info("ℹ️ Основной редактор таблиц не загружен, но быстрый ИИ-режим работает.")


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ ПРИЛОЖЕНИЯ
# ============================================================================
def main():
    """Точка входа приложения"""
    st.set_page_config(
        page_title=CONFIG.APP_TITLE,
        page_icon=CONFIG.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(get_app_styles(), unsafe_allow_html=True)
    
    # Инициализация session_state (должна быть определена в utils.py)
    initialize_session_state()
    
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
        if "agent_manager" not in st.session_state:
            st.session_state.agent_manager = AgentManager()
        agent_manager = st.session_state.agent_manager
        
        # Список агентов
        for agent in agent_manager.agents.values():
            is_selected = agent_manager.current_agent_id == agent.id
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
        
        # Создание агента
        with st.expander("➕ СОЗДАТЬ АГЕНТА", expanded=False):
            new_name = st.text_input("Имя", placeholder="Мой Помощник", key="new_agent_name")
            new_role = st.text_input("Роль", placeholder="эксперт по...", key="new_agent_role")
            new_prompt = st.text_area("Промпт", height=80, key="new_agent_prompt")
            if st.button("✨ Создать", use_container_width=True):
                if new_name and new_role and new_prompt:
                    agent_manager.add_agent(new_name, new_role, new_prompt)
                    st.success(f"✅ Агент {new_name} создан!")
                    st.rerun()
        
        st.markdown("---")
        
        # Статистика
        st.markdown("## 📊 СТАТИСТИКА")
        st.metric("Агентов", len(agent_manager.agents))
        current_agent = agent_manager.get_current_agent()
        if current_agent:
            st.metric("Обучений", current_agent.stats['total_trainings'])
            st.metric("Диалогов", current_agent.stats['total_conversations'])
        
        st.markdown("---")
        
        # Кнопка очистки workflow
        if st.button("🗑️ Очистить workflow", use_container_width=True):
            st.session_state.workflow = []
            st.rerun()
    
    # Инициализация менеджеров, если отсутствуют
    if "table_manager" not in st.session_state:
        st.session_state.table_manager = TableManager(api_key)
    if "image_manager" not in st.session_state:
        st.session_state.image_manager = ImageManager(api_key)
    
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
        # Используем расширенную функцию с ИИ-редактированием Excel
        render_tables_tab_with_ai_edit(api_key)
    with tabs[7]:
        render_images_tab(api_key)
    with tabs[8]:
        render_help_tab()


if __name__ == "__main__":
    main()
