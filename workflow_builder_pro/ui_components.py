# ui_components.py - Все UI компоненты для Streamlit (без опасных присваиваний)
import streamlit as st
import pandas as pd
import plotly.express as px
import tempfile
from datetime import datetime
from io import BytesIO
from PIL import Image

from config import CONFIG, NodeType, WorkflowStatus, ImageEditOperation
from utils import logger, save_messages_auto, save_tables_auto
from condition_parser import RussianConditionParser
from workflow import WorkflowExecutor
from voice import text_to_speech_mp3, recognize_speech_from_audio, VOICE_SUPPORT


def render_sidebar() -> str:
    """Рендерит боковую панель и возвращает API ключ"""
    st.markdown("## 🧠 МОИ ИИ АГЕНТЫ")
    
    api_key = st.text_input(
        "🔑 DeepSeek API Ключ",
        type="password",
        help="Получите бесплатно на platform.deepseek.com",
        key="sidebar_api_key"
    )
    
    st.markdown("---")
    
    from ai_agent import AgentManager
    agent_manager = st.session_state.get('agent_manager')
    if agent_manager is None:
        agent_manager = AgentManager()
        st.session_state.agent_manager = agent_manager
    
    for agent in agent_manager.agents.values():
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
    st.markdown("## 📊 СТАТИСТИКА")
    st.metric("Агентов", len(agent_manager.agents))
    
    current_agent = agent_manager.get_current_agent()
    if current_agent:
        st.metric("Обучений", current_agent.stats['total_trainings'])
        st.metric("Диалогов", current_agent.stats['total_conversations'])
    
    return api_key


def render_chat_tab(agent_manager, api_key):
    """Рендерит вкладку диалога с агентом"""
    current_agent = agent_manager.get_current_agent()
    
    if not current_agent:
        st.warning("⚠️ Выберите агента в боковой панели")
        return
    
    st.subheader(f"💬 {current_agent.name}")
    st.caption(f"Роль: {current_agent.role}")
    
    # Поле ввода сверху
    st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
    
    user_input = st.text_area(
        "✏️ Напишите сообщение...",
        height=80,
        key="chat_input",
        placeholder="Введите ваш вопрос...",
        label_visibility="collapsed"
    )
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
    with col1:
        use_training = st.checkbox("📚 Обуч.", value=True, key="chat_use_training")
    with col2:
        if VOICE_SUPPORT and st.button("🎤", use_container_width=True, help="Голосовой ввод"):
            st.session_state.voice_show_upload = True
    with col3:
        if st.button("🔊", use_container_width=True, help="Озвучить ответ"):
            if st.session_state.agent_messages and st.session_state.agent_messages[-1]['role'] == 'agent':
                audio = text_to_speech_mp3(st.session_state.agent_messages[-1]['content'])
                if audio:
                    st.audio(audio, format="audio/mp3")
    with col4:
        if st.button("🚀 Отправить", type="primary", use_container_width=True):
            if user_input.strip():
                st.session_state.agent_messages.append({'role': 'user', 'content': user_input.strip()})
                # Убрали строку очистки st.session_state.chat_input
                with st.spinner("🤖 Агент думает..."):
                    response = current_agent.generate_response(user_input.strip(), api_key, use_training)
                st.session_state.agent_messages.append({'role': 'agent', 'content': response})
                current_agent.add_conversation(user_input.strip(), response)
                agent_manager.save_agents()
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # История сообщений
    st.markdown("### 📜 История диалога")
    
    if not st.session_state.agent_messages:
        st.info("💬 Начните диалог, введя сообщение выше")
    else:
        for msg in st.session_state.agent_messages:
            if msg['role'] == 'user':
                st.markdown(f'<div class="chat-message-user"><strong>👤 Вы:</strong><br>{msg["content"]}</div>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message-agent"><strong>🤖 {current_agent.name}:</strong><br>{msg["content"]}</div>',
                            unsafe_allow_html=True)
    
    # Голосовой ввод
    if st.session_state.voice_show_upload:
        with st.expander("🎤 Голосовой ввод", expanded=True):
            audio_file = st.file_uploader("Выберите файл", type=["wav", "mp3"], key="voice_upload")
            if audio_file:
                recognized = recognize_speech_from_audio(audio_file.read())
                if recognized:
                    st.success(f"✅ Распознано: {recognized}")
                    # Больше не присваиваем st.session_state.chat_input
                    st.session_state.voice_show_upload = False
                    st.rerun()
                else:
                    st.error("❌ Не удалось распознать речь")
    
    if st.button("🗑️ Очистить диалог", use_container_width=True):
        st.session_state.agent_messages = []
        save_messages_auto([])
        st.rerun()


# Остальные функции (render_training_tab, render_memory_tab, render_analytics_tab,
# render_workflow_tab, render_conditions_tab, render_tables_tab, render_images_tab,
# render_help_tab) остаются без изменений. 
# Убедитесь, что они присутствуют в вашем файле.
# (Для экономии места они здесь не повторяются, но вы можете взять их из предыдущего полного кода)
