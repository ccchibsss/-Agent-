"""
UI-функции для рендеринга вкладок приложения.
Добавлены расширенные настройки подключения для Email, Telegram, HTTP.
Улучшена работа с таблицами: быстрый предпросмотр, сохранение в Google Sheets.
Добавлена вкладка "Экономика" – построение юнит-экономики для маркетплейса.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from PIL import Image
from io import BytesIO
import tempfile
import shutil
import re
import requests
from config import CONFIG, IMAGES_DIR
from utils import (
    save_tables_auto, save_messages_auto, save_workflow_auto,
    NodeType, WorkflowStatus, ImageEditOperation
)
from voice import recognize_speech_from_audio, text_to_speech_mp3
from condition_parser import RussianConditionParser
from workflow import WorkflowExecutor, AIWorkflowGenerator
from ai_agent import AgentManager
from table_manager import TableManager
from image_manager import ImageManager
from openai import OpenAI

try:
    from bs4 import BeautifulSoup
    BS_AVAILABLE = True
except ImportError:
    BS_AVAILABLE = False


# ====================== ЧАТ ======================
def render_chat_tab(agent_manager: AgentManager, api_key: str):
    current = agent_manager.get_current_agent()
    if not current:
        st.warning("⚠️ Выберите агента в боковой панели")
        return
    st.subheader(f"💬 {current.name}")
    st.caption(f"Роль: {current.role}")

    st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
    user_input = st.text_area(
        "✏️ Напишите сообщение...", height=80,
        key="chat_input", placeholder="Введите ваш вопрос...",
        label_visibility="collapsed"
    )
    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
    with col1:
        use_training = st.checkbox("📚 Обуч.", value=True, key="chat_use_training")
    with col2:
        if st.button("🎤", width='stretch', help="Голосовой ввод"):
            st.session_state.voice_show_upload = True
    with col3:
        if st.button("🔊", width='stretch', help="Озвучить последний ответ"):
            msgs = st.session_state.agent_messages
            if msgs and msgs[-1]['role'] == 'agent':
                audio = text_to_speech_mp3(msgs[-1]['content'])
                if audio:
                    st.audio(audio, format="audio/mp3")
    with col4:
        if st.button("🚀 Отправить", type="primary", width='stretch'):
            if user_input.strip():
                st.session_state.agent_messages.append({'role': 'user', 'content': user_input.strip()})
                st.session_state.pop("chat_input", None)
                with st.spinner("🤖 Агент думает..."):
                    response = current.generate_response(user_input.strip(), api_key, use_training)
                st.session_state.agent_messages.append({'role': 'agent', 'content': response})
                current.add_conversation(user_input.strip(), response)
                agent_manager.save_agents()
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### 📜 История диалога")
    if not st.session_state.agent_messages:
        st.info("💬 Начните диалог, введя сообщение выше")
    else:
        for msg in st.session_state.agent_messages:
            if msg['role'] == 'user':
                st.markdown(f'<div class="chat-message-user"><strong>👤 Вы:</strong><br>{msg["content"]}</div>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message-agent"><strong>🤖 {current.name}:</strong><br>{msg["content"]}</div>',
                            unsafe_allow_html=True)

    if st.session_state.get('voice_show_upload'):
        with st.expander("🎤 Голосовой ввод", expanded=True):
            audio_file = st.file_uploader("Выберите аудио", type=["wav", "mp3"], key="voice_upload")
            if audio_file:
                recognized = recognize_speech_from_audio(audio_file.read())
                if recognized:
                    st.success(f"✅ Распознано: {recognized}")
                    st.session_state.chat_input = recognized
                    st.session_state.voice_show_upload = False
                    st.rerun()
                else:
                    st.error("Не удалось распознать речь")

    if st.button("🗑️ Очистить диалог", width='stretch'):
        st.session_state.agent_messages = []
        save_messages_auto([])
        st.rerun()


# ====================== ОБУЧЕНИЕ ======================
def render_training_tab(agent_manager: AgentManager):
    current = agent_manager.get_current_agent()
    if not current:
        st.warning("⚠️ Выберите агента")
        return
    st.subheader(f"📚 Обучение: {current.name}")
    with st.expander("➕ Добавить пример", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            ex_input = st.text_area("Вопрос", height=80, key="train_input")
        with col2:
            ex_output = st.text_area("Ответ", height=80, key="train_output")
        ex_context = st.text_input("Контекст", key="train_context")
        if st.button("✨ Добавить", type="primary"):
            if ex_input and ex_output:
                current.add_training_example(ex_input, ex_output, ex_context)
                agent_manager.save_agents()
                st.success("✅ Пример добавлен!")
                st.rerun()
    st.markdown(f"### Примеры ({len(current.training_examples)})")
    for i, ex in enumerate(reversed(current.training_examples[-10:])):
        with st.expander(f"#{ex['id']}: {ex['user_input'][:50]}..."):
            st.markdown(f"**Ответ:** {ex['expected_output']}")
            st.caption(f"📅 {ex['timestamp'][:10]}")
            if st.button(f"🗑️ Удалить", key=f"del_ex_{ex['id']}"):
                current.training_examples = [e for e in current.training_examples if e['id'] != ex['id']]
                agent_manager.save_agents()
                st.rerun()
    with st.expander("📚 Массовое обучение (из текста)"):
        bulk = st.text_area("Вопрос -> Ответ (каждая строка)", height=150,
                            placeholder="Как анализировать? -> Для анализа...")
        if st.button("🚀 Обучить на всех примерах"):
            lines = bulk.strip().split('\n')
            added = 0
            for line in lines:
                if '->' in line:
                    q, a = line.split('->', 1)
                    q, a = q.strip(), a.strip()
                    if q and a:
                        current.add_training_example(q, a)
                        added += 1
            if added:
                agent_manager.save_agents()
                st.success(f"✅ Добавлено {added} примеров!")
                st.rerun()
            else:
                st.warning("Не найдено примеров в формате Вопрос -> Ответ")


# ====================== ПАМЯТЬ ======================
def render_memory_tab(agent_manager: AgentManager):
    current = agent_manager.get_current_agent()
    if not current:
        st.warning("⚠️ Выберите агента")
        return
    st.subheader(f"🧠 Память: {current.name}")
    with st.expander("➕ Добавить факт", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            mem_key = st.text_input("Ключ", key="mem_key")
        with col2:
            mem_value = st.text_input("Значение", key="mem_value")
        importance = st.selectbox("Важность", ["low", "normal", "high"], key="mem_importance")
        if st.button("💾 Сохранить"):
            if mem_key and mem_value:
                current.add_to_memory(mem_key, mem_value, importance)
                agent_manager.save_agents()
                st.success("✅ Запомнено!")
                st.rerun()
    st.markdown(f"### Факты ({len(current.memory)})")
    for mem in current.memory:
        icon = "🔴" if mem['importance'] == 'high' else "🟡" if mem['importance'] == 'normal' else "🟢"
        st.markdown(f"""<div class="memory-box">
            {icon} **{mem['key']}** = {mem['value']}<br>
            <small>👁️ {mem['access_count']} | 📅 {mem['timestamp'][:10]}</small>
        </div>""", unsafe_allow_html=True)
        if st.button(f"🗑️", key=f"del_mem_{mem['key']}"):
            current.memory = [m for m in current.memory if m['key'] != mem['key']]
            agent_manager.save_agents()
            st.rerun()
    if st.button("🗑️ Очистить память"):
        current.memory = []
        agent_manager.save_agents()
        st.success("Память очищена")
        st.rerun()


# ====================== АНАЛИТИКА ======================
def render_analytics_tab(agent_manager: AgentManager):
    current = agent_manager.get_current_agent()
    if not current:
        st.warning("⚠️ Выберите агента")
        return
    st.subheader(f"📊 {current.name}")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card"><h3>{current.stats["total_trainings"]}</h3><p>Обучений</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><h3>{current.stats["total_conversations"]}</h3><p>Диалогов</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><h3>{current.stats["success_rate"]:.0f}%</h3><p>Успешность</p></div>', unsafe_allow_html=True)
    with c4:
        total = len(current.training_examples) + len(current.memory)
        st.markdown(f'<div class="stat-card"><h3>{total}</h3><p>Фактов</p></div>', unsafe_allow_html=True)
    if current.training_examples:
        df = pd.DataFrame([{'Дата': ex['timestamp'][:10], 'Пример': i + 1} for i, ex in enumerate(current.training_examples)])
        fig = px.line(df, x='Дата', y='Пример', title="Прогресс обучения")
        st.plotly_chart(fig, width='stretch')
    if current.conversation_history:
        st.subheader("💬 Последние диалоги")
        for conv in current.conversation_history[-5:]:
            with st.expander(f"Диалог от {conv['timestamp'][:19]}"):
                st.markdown(f"**👤** {conv['user'][:200]}")
                st.markdown(f"**🤖** {conv['agent'][:200]}")


# ====================== УСЛОВИЯ ======================
def render_conditions_tab():
    st.subheader("🔀 Русские условия")
    st.markdown("""
    <div class="info-box">
    <b>Примеры:</b><br>
    • если цена больше 1000 то отправить уведомление<br>
    • если статус равно 'успех' иначе отправить ошибку
    </div>""", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        for ex in RussianConditionParser.EXAMPLES:
            st.code(f"📌 {ex}")
    with col2:
        test = st.text_area("Проверить условие", height=100, key="test_condition")
        if test:
            parsed = RussianConditionParser.parse(test)
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Тип", parsed.get('type'))
            with col_b:
                st.metric("Уверенность", f"{parsed.get('confidence', 0) * 100:.0f}%")
            if parsed.get('code'):
                st.success(f"💻 `{parsed['code']}`")
            else:
                st.warning("Не распознано")


# ====================== WORKFLOW ======================
def render_workflow_tab(agent_manager: AgentManager, api_key: str):
    st.subheader("🤖 Конструктор Workflow")
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### 📦 Блоки")
        blocks = [
            ("📖 Google Sheets", NodeType.GOOGLE_SHEETS_READ.value),
            ("📗 Excel", NodeType.EXCEL_READ.value),
            ("🧠 DeepSeek AI", NodeType.DEEPSEEK_AI.value),
            ("🔀 Условие", NodeType.CONDITION.value),
            ("🔄 Цикл", NodeType.LOOP.value),
            ("📧 Email", NodeType.EMAIL.value),
            ("📱 Telegram", NodeType.TELEGRAM.value),
            ("🧠 ИИ Агент", NodeType.AI_AGENT.value),
            ("🧹 Очистка", NodeType.DATA_CLEAN.value),
            ("📊 Сводная", NodeType.PIVOT_TABLE.value),
            ("🌐 HTTP GET", NodeType.HTTP_GET.value),
            ("📤 HTTP POST", NodeType.HTTP_POST.value),
        ]
        for name, btype in blocks:
            if st.button(f"{name}", key=f"add_{btype}", width='stretch'):
                cfg = _default_config(btype)
                if btype == NodeType.AI_AGENT.value:
                    cfg['agent_id'] = ""
                st.session_state.workflow.append({
                    "id": len(st.session_state.workflow),
                    "name": name,
                    "type": btype,
                    "config": cfg,
                    "status": WorkflowStatus.PENDING.value
                })
                st.rerun()

        st.markdown("### 🧠 Агенты")
        for agent in agent_manager.agents.values():
            if st.button(f"🧠 {agent.name}", key=f"wf_agent_{agent.id}", width='stretch'):
                st.session_state.workflow.append({
                    "id": len(st.session_state.workflow),
                    "name": f"Агент: {agent.name}",
                    "type": NodeType.AI_AGENT.value,
                    "config": {
                        "agent_id": agent.id,
                        "question": "",
                        "use_training": True
                    },
                    "status": WorkflowStatus.PENDING.value
                })
                st.rerun()

        st.markdown("---")
        st.markdown("### 🪄 ИИ-генератор")
        desc = st.text_area("Опишите workflow на русском", height=100,
                            placeholder="Пример: прочитай Google таблицу, если цена больше 1000 отправь email")
        if st.button("✨ Сгенерировать Workflow", width='stretch'):
            if desc and api_key:
                with st.spinner("ИИ создаёт workflow..."):
                    generated = AIWorkflowGenerator.generate(desc, api_key)
                    if generated:
                        st.session_state.workflow = generated
                        save_workflow_auto(generated)
                        st.success(f"Создано {len(generated)} блоков!")
                        st.rerun()
                    else:
                        st.error("Не удалось сгенерировать workflow")
            else:
                st.warning("Введите описание и API ключ")

    with col2:
        st.markdown("### 📋 Текущий workflow")
        if not st.session_state.workflow:
            st.info("💡 Добавьте блоки слева или опишите задачу для ИИ")
        else:
            for i, block in enumerate(st.session_state.workflow):
                cls = ""
                if block.get('status') == WorkflowStatus.SUCCESS.value:
                    cls = "workflow-node-success"
                elif block.get('status') == WorkflowStatus.ERROR.value:
                    cls = "workflow-node-error"
                st.markdown(f"""<div class="workflow-node {cls}">
                    <b>{block.get('name')}</b> <small>#{i + 1}</small><br>
                    <small>{block.get('type')}</small>
                </div>""", unsafe_allow_html=True)
                if i < len(st.session_state.workflow) - 1:
                    st.markdown('<div class="workflow-connector">▼</div>', unsafe_allow_html=True)

                with st.expander(f"⚙️ Настроить {block.get('name')}"):
                    _render_block_config(block, i, agent_manager)
                    if st.button("🗑️ Удалить блок", key=f"del_wf_{i}"):
                        st.session_state.workflow.pop(i)
                        st.rerun()

            st.markdown("---")
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                if st.button("🚀 ЗАПУСТИТЬ WORKFLOW", type="primary", width='stretch'):
                    _execute_workflow(agent_manager, api_key)
            with col_act2:
                if st.button("🗑️ Очистить весь workflow", width='stretch'):
                    st.session_state.workflow = []
                    save_workflow_auto([])
                    st.rerun()


def _default_config(node_type: str) -> dict:
    defaults = {
        NodeType.GOOGLE_SHEETS_READ.value: {
            "sheet_url": "", "sheet_name": "", "range_a1": ""
        },
        NodeType.EXCEL_READ.value: {
            "file_path": "", "sheet_name": 0
        },
        NodeType.DEEPSEEK_AI.value: {
            "system_prompt": "Ты полезный ассистент", "user_prompt": "", "temperature": 0.3
        },
        NodeType.CONDITION.value: {
            "condition": "если цена больше 1000"
        },
        NodeType.LOOP.value: {
            "items": '["элемент1", "элемент2"]', "batch_size": 10, "action": "print(item)"
        },
        NodeType.EMAIL.value: {
            "to": "", "subject": "Уведомление", "body": "",
            "smtp_server": "", "smtp_port": 587,
            "sender_email": "", "sender_password": ""
        },
        NodeType.TELEGRAM.value: {
            "chat_id": "", "message": "", "parse_mode": "HTML",
            "bot_token": ""
        },
        NodeType.AI_AGENT.value: {
            "agent_id": "", "question": "Проанализируй данные", "use_training": True
        },
        NodeType.DATA_CLEAN.value: {
            "remove_duplicates": True, "remove_empty": True, "fill_na": ""
        },
        NodeType.PIVOT_TABLE.value: {
            "index": "", "columns": "", "values": "", "aggfunc": "sum"
        },
        NodeType.HTTP_GET.value: {
            "url": "", "headers": "{}", "timeout": 30,
            "auth_type": "none",
            "auth_username": "", "auth_password": "",
            "auth_token": ""
        },
        NodeType.HTTP_POST.value: {
            "url": "", "headers": "{}", "body": "{}", "timeout": 30,
            "auth_type": "none",
            "auth_username": "", "auth_password": "",
            "auth_token": ""
        },
    }
    return defaults.get(node_type, {})


def _render_block_config(block: dict, idx: int, agent_manager: AgentManager):
    cfg = block.get('config', {})
    btype = block.get('type')

    if btype == NodeType.GOOGLE_SHEETS_READ.value:
        cfg['sheet_url'] = st.text_input("URL таблицы", cfg.get('sheet_url', ''), key=f"gs_url_{idx}")
        cfg['sheet_name'] = st.text_input("Имя листа", cfg.get('sheet_name', ''), key=f"gs_sheet_{idx}")
        cfg['range_a1'] = st.text_input("Диапазон (A1:B10)", cfg.get('range_a1', ''), key=f"gs_range_{idx}")

    elif btype == NodeType.EXCEL_READ.value:
        cfg['file_path'] = st.text_input("Путь к файлу", cfg.get('file_path', ''), key=f"ex_path_{idx}")
        cfg['sheet_name'] = st.text_input("Лист (индекс или имя)", cfg.get('sheet_name', 0), key=f"ex_sheet_{idx}")

    elif btype == NodeType.DEEPSEEK_AI.value:
        cfg['system_prompt'] = st.text_area("Системный промпт", cfg.get('system_prompt', ''), height=80, key=f"ai_sys_{idx}")
        cfg['user_prompt'] = st.text_area("Запрос пользователя", cfg.get('user_prompt', ''), height=80, key=f"ai_user_{idx}")
        cfg['temperature'] = st.slider("Температура", 0.0, 1.0, float(cfg.get('temperature', 0.3)), key=f"ai_temp_{idx}")

    elif btype == NodeType.CONDITION.value:
        cfg['condition'] = st.text_area("Условие на русском", cfg.get('condition', ''), height=80, key=f"cond_{idx}")
        if cfg.get('condition'):
            parsed = RussianConditionParser.parse(cfg['condition'])
            if parsed.get('code'):
                st.code(parsed['code'], language='python')

    elif btype == NodeType.LOOP.value:
        cfg['items'] = st.text_area("Элементы (JSON массив)", cfg.get('items', '["элемент1"]'), height=80, key=f"loop_items_{idx}")
        cfg['batch_size'] = st.number_input("Размер пакета", 1, 1000, int(cfg.get('batch_size', 10)), key=f"loop_batch_{idx}")
        cfg['action'] = st.text_area("Действие (Python код)", cfg.get('action', 'print(item)'), height=60, key=f"loop_action_{idx}")

    elif btype == NodeType.EMAIL.value:
        st.markdown("#### Параметры письма")
        cfg['to'] = st.text_input("Кому (email)", cfg.get('to', ''), key=f"email_to_{idx}")
        cfg['subject'] = st.text_input("Тема", cfg.get('subject', 'Уведомление'), key=f"email_subj_{idx}")
        cfg['body'] = st.text_area("Тело письма", cfg.get('body', ''), height=100, key=f"email_body_{idx}")
        st.markdown("#### Настройки SMTP")
        with st.expander("⛓ Подключение к почте (необязательно)"):
            cfg['smtp_server'] = st.text_input("SMTP сервер", cfg.get('smtp_server', ''),
                                               help="Например smtp.yandex.ru", key=f"smtp_srv_{idx}")
            cfg['smtp_port'] = st.number_input("Порт", min_value=1, value=int(cfg.get('smtp_port', 587)), key=f"smtp_port_{idx}")
            cfg['sender_email'] = st.text_input("Email отправителя", cfg.get('sender_email', ''), key=f"sender_email_{idx}")
            cfg['sender_password'] = st.text_input("Пароль (приложения)", cfg.get('sender_password', ''),
                                                   type="password", key=f"sender_pwd_{idx}")

    elif btype == NodeType.TELEGRAM.value:
        cfg['chat_id'] = st.text_input("Chat ID", cfg.get('chat_id', ''), key=f"tg_chat_{idx}")
        cfg['message'] = st.text_area("Сообщение", cfg.get('message', ''), height=80, key=f"tg_msg_{idx}")
        cfg['parse_mode'] = st.selectbox("Parse Mode", ["HTML", "Markdown", "None"],
                                         index=["HTML", "Markdown", "None"].index(cfg.get('parse_mode', 'HTML')),
                                         key=f"tg_parse_{idx}")
        with st.expander("⚡ Токен бота (опционально)"):
            cfg['bot_token'] = st.text_input("Bot Token", cfg.get('bot_token', ''),
                                            type="password", key=f"bot_token_{idx}")

    elif btype == NodeType.AI_AGENT.value:
        agent_ids = list(agent_manager.agents.keys())
        agent_names = [agent_manager.agents[a].name for a in agent_ids]
        current_agent_id = cfg.get('agent_id', '')
        if current_agent_id in agent_ids:
            current_idx = agent_ids.index(current_agent_id)
        else:
            current_idx = 0 if agent_ids else -1
        if agent_names:
            new_agent_name = st.selectbox("Агент", agent_names, index=current_idx, key=f"agent_sel_{idx}")
            cfg['agent_id'] = agent_ids[agent_names.index(new_agent_name)]
        else:
            st.warning("Нет доступных агентов")
        cfg['question'] = st.text_area("Вопрос агенту", cfg.get('question', ''), height=60, key=f"agent_q_{idx}")
        cfg['use_training'] = st.checkbox("Использовать обучение", cfg.get('use_training', True), key=f"agent_train_{idx}")

    elif btype == NodeType.DATA_CLEAN.value:
        cfg['remove_duplicates'] = st.checkbox("Удалить дубликаты", cfg.get('remove_duplicates', True), key=f"clean_dup_{idx}")
        cfg['remove_empty'] = st.checkbox("Удалить пустые строки", cfg.get('remove_empty', True), key=f"clean_empty_{idx}")
        cfg['fill_na'] = st.text_input("Заполнить пропуски значением", cfg.get('fill_na', ''), key=f"clean_fill_{idx}")

    elif btype == NodeType.PIVOT_TABLE.value:
        cfg['index'] = st.text_input("Индекс (столбцы через запятую)", cfg.get('index', ''), key=f"pivot_idx_{idx}")
        cfg['columns'] = st.text_input("Колонки", cfg.get('columns', ''), key=f"pivot_col_{idx}")
        cfg['values'] = st.text_input("Значения", cfg.get('values', ''), key=f"pivot_val_{idx}")
        cfg['aggfunc'] = st.selectbox("Агрегация", ["sum", "mean", "count", "min", "max"], index=0, key=f"pivot_agg_{idx}")

    elif btype in (NodeType.HTTP_GET.value, NodeType.HTTP_POST.value):
        cfg['url'] = st.text_input("URL", cfg.get('url', ''), key=f"http_url_{idx}")
        cfg['headers'] = st.text_area("Заголовки (JSON)", cfg.get('headers', '{}'), height=60, key=f"http_headers_{idx}")
        cfg['timeout'] = st.number_input("Таймаут (сек)", 1, 120, int(cfg.get('timeout', 30)), key=f"http_timeout_{idx}")
        if btype == NodeType.HTTP_POST.value:
            cfg['body'] = st.text_area("Тело запроса (JSON)", cfg.get('body', '{}'), height=80, key=f"post_body_{idx}")
        st.markdown("#### Аутентификация")
        auth = st.selectbox("Тип", ["none", "basic", "bearer"],
                           index=["none", "basic", "bearer"].index(cfg.get('auth_type', 'none')),
                           key=f"http_auth_{idx}")
        cfg['auth_type'] = auth
        if auth == "basic":
            cfg['auth_username'] = st.text_input("Логин", cfg.get('auth_username', ''), key=f"http_user_{idx}")
            cfg['auth_password'] = st.text_input("Пароль", cfg.get('auth_password', ''), type="password", key=f"http_pwd_{idx}")
        elif auth == "bearer":
            cfg['auth_token'] = st.text_input("Токен", cfg.get('auth_token', ''), type="password", key=f"http_token_{idx}")

    block['config'] = cfg


def _execute_workflow(agent_manager, api_key):
    progress = st.progress(0)
    status = st.empty()

    def update_progress(idx, node):
        progress.progress((idx + 1) / len(st.session_state.workflow))
        status.text(f"🔄 {node.get('name')}")

    table_manager = st.session_state.table_manager
    executor = WorkflowExecutor(st.session_state.workflow, api_key, agent_manager, table_manager)
    result = executor.execute(update_progress)
    progress.progress(1.0)

    if result['success']:
        st.balloons()
        st.success(f"✅ Workflow выполнен за {result['execution_time']:.1f}с")
        with st.expander("📋 Результаты", expanded=True):
            for res in result['results']:
                st.markdown(f"**📌 {res['node']}**")
                st.json({k: v for k, v in res['result'].items() if k != 'df'})
    else:
        st.error(f"❌ Ошибка: {result.get('error')}")


# ====================== ТАБЛИЦЫ + ИИ ======================
def render_tables_tab(api_key: str):
    st.subheader("🗂 Таблицы + ИИ + Редактор")
    table_manager = st.session_state.table_manager
    with st.expander("📚 Сохранённые таблицы", expanded=not st.session_state.saved_tables):
        if not st.session_state.saved_tables:
            st.info("Нет сохранённых таблиц. Загрузите или создайте.")
        else:
            for table_id, df in st.session_state.saved_tables.items():
                with st.expander(f"📊 {table_id} ({df.shape[0]}×{df.shape[1]})", expanded=False):
                    st.dataframe(df.head(5), width='stretch')
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button("✏️ Открыть", key=f"open_{table_id}", width='stretch'):
                            st.session_state.current_df = df.copy()
                            st.session_state.editing_table_id = table_id
                            st.rerun()
                    with col_b:
                        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                            table_manager.write_excel(df, tmp.name)
                            with open(tmp.name, 'rb') as f:
                                st.download_button("📥 Скачать", f, f"{table_id}.xlsx",
                                                   key=f"dl_saved_{table_id}", width='stretch')
                    with col_c:
                        if st.button("🗑️ Удалить", key=f"del_saved_{table_id}", width='stretch'):
                            del st.session_state.saved_tables[table_id]
                            save_tables_auto(st.session_state.saved_tables)
                            if st.session_state.editing_table_id == table_id:
                                st.session_state.current_df = None
                                st.session_state.editing_table_id = None
                            st.rerun()
    st.markdown("---")
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("### 📥 Загрузка данных")
        source = st.radio("Источник", ["Google Sheets", "Excel"], key="table_source")
        if source == "Google Sheets":
            url = st.text_input("URL", placeholder="https://docs.google.com/spreadsheets/d/...", key="gs_url_input")
            if st.button("📊 Загрузить из Google", width='stretch'):
                if url:
                    with st.spinner("Загрузка..."):
                        df = table_manager.read_google_sheets(url)
                        if df is not None:
                            tid = f"gs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            st.session_state.current_df = df
                            st.session_state.editing_table_id = tid
                            st.session_state.saved_tables[tid] = df.copy()
                            save_tables_auto(st.session_state.saved_tables)
                            st.success(f"✅ Загружено: {df.shape}")
                            st.rerun()
        else:
            uploaded = st.file_uploader("Excel или CSV", type=['xlsx', 'xls', 'csv'], key="excel_upload")
            max_rows = st.slider("Строк для предпросмотра (0 = все)", min_value=0, max_value=10000, value=1000, step=500,
                                 help="Ограничьте число строк для быстрой загрузки. 0 – загрузить все.")
            if uploaded:
                with st.spinner("Чтение..."):
                    if uploaded.name.endswith('.csv'):
                        try:
                            df = pd.read_csv(uploaded, nrows=max_rows if max_rows > 0 else None)
                        except Exception as e:
                            st.error(f"❌ Ошибка чтения CSV: {e}")
                            df = None
                    else:
                        df = table_manager.read_excel(uploaded, max_rows=max_rows if max_rows > 0 else None)
                        if df is None:
                            st.error("❌ Файл не является корректным Excel-файлом или повреждён.")
                    if df is not None:
                        tid = f"ex_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        st.session_state.current_df = df
                        st.session_state.editing_table_id = tid
                        st.session_state.saved_tables[tid] = df.copy()
                        save_tables_auto(st.session_state.saved_tables)
                        st.success(f"✅ Загружено: {df.shape}")
                        st.rerun()
    with col_right:
        if st.session_state.current_df is not None and st.session_state.editing_table_id:
            st.markdown('<div class="table-editor">', unsafe_allow_html=True)
            st.markdown(f"### 📊 Редактор: {st.session_state.editing_table_id}")
            st.caption(f"{st.session_state.current_df.shape[0]} строк × {st.session_state.current_df.shape[1]} столбцов")
            c_save, c_del, c_dl, c_ai = st.columns(4)
            with c_save:
                if st.button("💾 Сохранить", key=f"save_{st.session_state.editing_table_id}", width='stretch'):
                    st.session_state.saved_tables[st.session_state.editing_table_id] = st.session_state.current_df.copy()
                    save_tables_auto(st.session_state.saved_tables)
                    st.success("✅")
            with c_del:
                if st.button("🗑️ Удалить", key=f"delete_{st.session_state.editing_table_id}", width='stretch'):
                    if st.session_state.editing_table_id in st.session_state.saved_tables:
                        del st.session_state.saved_tables[st.session_state.editing_table_id]
                        save_tables_auto(st.session_state.saved_tables)
                    st.session_state.current_df = None
                    st.session_state.editing_table_id = None
                    st.rerun()
            with c_dl:
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                    table_manager.write_excel(st.session_state.current_df, tmp.name)
                    with open(tmp.name, 'rb') as f:
                        st.download_button("📥 Excel", f, file_name=f"{st.session_state.editing_table_id}.xlsx",
                                           key=f"dl_{st.session_state.editing_table_id}", width='stretch')
            with c_ai:
                if st.button("🤖 ИИ", key=f"ai_{st.session_state.editing_table_id}", width='stretch'):
                    st.session_state.table_edit_mode = True
            edited = st.data_editor(st.session_state.current_df, num_rows="dynamic",
                                    width='stretch', key=f"editor_{st.session_state.editing_table_id}",
                                    hide_index=True)
            if not st.session_state.current_df.equals(edited):
                st.session_state.current_df = edited
                st.session_state.saved_tables[st.session_state.editing_table_id] = edited.copy()
                save_tables_auto(st.session_state.saved_tables)
                st.toast("💾 Изменения сохранены")
            if st.session_state.table_edit_mode:
                with st.expander("🤖 ИИ-помощник", expanded=True):
                    instr = st.text_area("Опишите, что сделать:", placeholder="Пример: удали пустые строки, добавь столбец Итого",
                                         height=80, key=f"ai_instr_{st.session_state.editing_table_id}")
                    if st.button("🚀 Применить ИИ", type="primary", key=f"ai_apply_{st.session_state.editing_table_id}"):
                        if instr and api_key:
                            with st.spinner("Анализ..."):
                                result = table_manager.ai_analyze_dataframe(edited, instr, api_key)
                                if 'error' not in result:
                                    st.success("✅ Анализ завершён")
                                    st.markdown(f"**Анализ:** {result.get('analysis', '')}")
                                    if result.get('ready_code'):
                                        st.code(result['ready_code'], language='python')
                                        if st.button("💾 Применить код", key=f"apply_code_{st.session_state.editing_table_id}"):
                                            try:
                                                transformed = table_manager.execute_transformation(edited.copy(), result['ready_code'])
                                                st.session_state.current_df = transformed
                                                st.session_state.saved_tables[st.session_state.editing_table_id] = transformed.copy()
                                                save_tables_auto(st.session_state.saved_tables)
                                                st.success("✅ Применено!")
                                                st.session_state.table_edit_mode = False
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"❌ {e}")
                                else:
                                    st.error(f"❌ {result['error']}")
            st.markdown("#### Запись данных обратно в Google Sheets")
            gsheet_write_url = st.text_input("URL Google Таблицы для записи",
                                             value=st.session_state.get('last_gsheet_url', ''),
                                             placeholder="https://docs.google.com/spreadsheets/d/...",
                                             key="gsheet_write_url")
            gsheet_sheet_name = st.text_input("Имя листа", value="Sheet1", key="gsheet_write_sheet")
            if st.button("📤 Записать в Google Sheets", width='stretch'):
                if not gsheet_write_url:
                    st.warning("Введите URL")
                else:
                    try:
                        table_manager.write_google_sheets(st.session_state.current_df, gsheet_write_url, gsheet_sheet_name)
                        st.success("✅ Данные записаны в Google Sheets!")
                        st.session_state.last_gsheet_url = gsheet_write_url
                    except PermissionError as pe:
                        st.error(f"🔒 Ошибка доступа: {pe}. Убедитесь, что в secrets настроены GSPREAD_CREDENTIALS.")
                    except Exception as e:
                        st.error(f"❌ Ошибка записи: {e}")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("💡 Загрузите таблицу слева или выберите из сохранённых")


# ====================== ИЗОБРАЖЕНИЯ ======================
def render_images_tab(api_key: str):
    st.subheader("🖼️ Редактор изображений с ИИ")
    image_manager = st.session_state.image_manager
    if not image_manager:
        st.error("Менеджер изображений не инициализирован")
        return
    tabs = st.tabs(["📥 Загрузка", "✏️ Ручное редактирование", "🤖 ИИ‑редактирование",
                    "🎨 Массовая обработка", "🧠 Массовая ИИ‑обработка", "💾 Результаты", "📊 Статистика"])

    with tabs[0]:
        st.markdown("### 📥 Массовая загрузка изображений")
        st.info(f"До {CONFIG.MAX_IMAGE_UPLOAD} файлов, форматы: {', '.join(CONFIG.SUPPORTED_IMAGE_FORMATS)}")
        uploaded_files = st.file_uploader("Выберите изображения", type=list(CONFIG.SUPPORTED_IMAGE_FORMATS),
                                          accept_multiple_files=True, key="image_upload")
        if uploaded_files:
            progress_bar = st.progress(0)
            status_text = st.empty()
            for i, file in enumerate(uploaded_files):
                try:
                    if file.size / (1024 * 1024) > CONFIG.MAX_IMAGE_SIZE_MB:
                        st.warning(f"Файл {file.name} превышает {CONFIG.MAX_IMAGE_SIZE_MB}MB, пропущен")
                        continue
                    img = Image.open(file)
                    st.session_state.uploaded_images[file.name] = img
                    progress_bar.progress((i + 1) / len(uploaded_files))
                    status_text.text(f"Загрузка: {file.name} ({img.size[0]}x{img.size[1]})")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
            progress_bar.empty()
            status_text.empty()
            st.success(f"✅ Загружено {len(st.session_state.uploaded_images)} изображений")
            if st.session_state.uploaded_images:
                cols = st.columns(3)
                for idx, (fn, img) in enumerate(list(st.session_state.uploaded_images.items())[:6]):
                    with cols[idx % 3]:
                        st.image(img, caption=f"{fn} ({img.size[0]}x{img.size[1]})", width='stretch')

    with tabs[1]:
        st.markdown("### ✏️ Ручное редактирование")
        if not st.session_state.uploaded_images:
            st.info("Загрузите изображения")
        else:
            selected = st.selectbox("Выберите изображение", list(st.session_state.uploaded_images.keys()), key="manual_edit_select")
            if selected:
                original = st.session_state.uploaded_images[selected]
                col1, col2 = st.columns(2)
                with col1:
                    st.image(original, width='stretch', caption="Оригинал")
                with col2:
                    op = st.selectbox("Операция", [e.value for e in ImageEditOperation],
                                      format_func=lambda x: {
                                          'remove_background': 'Удалить фон', 'remove_watermark': 'Удалить вод.знак',
                                          'resize': 'Изменить размер', 'crop': 'Обрезать', 'rotate': 'Повернуть',
                                          'enhance': 'Улучшить', 'filter': 'Фильтр', 'add_watermark': 'Водяной знак',
                                          'convert_format': 'Формат'
                                      }.get(x, x), key="manual_op")
                    params = {}
                    if op == 'resize':
                        params['width'] = st.number_input("Ширина", value=original.size[0])
                        params['height'] = st.number_input("Высота", value=original.size[1])
                        params['maintain_aspect'] = st.checkbox("Сохранить пропорции", True)
                    elif op == 'enhance':
                        params['brightness'] = st.slider("Яркость", 0.0, 2.0, 1.0)
                        params['contrast'] = st.slider("Контраст", 0.0, 2.0, 1.0)
                        params['sharpness'] = st.slider("Четкость", 0.0, 2.0, 1.0)
                    elif op == 'filter':
                        params['filter_type'] = st.selectbox("Фильтр", ['blur', 'sharpen', 'edge_enhance', 'contour',
                                                                         'emboss', 'smooth', 'detail'])
                    elif op == 'add_watermark':
                        params['text'] = st.text_input("Текст", "Watermark")
                        params['position'] = st.selectbox("Позиция", ['top-left', 'top-right', 'bottom-left', 'bottom-right'])
                        params['font_size'] = st.slider("Размер шрифта", 10, 100, 40)
                        params['opacity'] = st.slider("Прозрачность", 0, 255, 128)
                    elif op == 'convert_format':
                        params['format'] = st.selectbox("Формат", ['PNG', 'JPEG', 'WEBP', 'BMP'])
                    if st.button("🚀 Применить", type="primary", key="manual_apply"):
                        try:
                            processed = image_manager._apply_operation(original, ImageEditOperation(op), params)
                            st.session_state.processed_images[f"manual_{selected}"] = processed
                            st.success("✅ Обработано!")
                            st.image(processed, caption="Результат", width='stretch')
                        except Exception as e:
                            st.error(f"❌ {e}")

    with tabs[2]:
        st.markdown("### 🤖 ИИ‑редактирование (по описанию)")
        if not st.session_state.uploaded_images:
            st.info("Загрузите изображения")
        else:
            selected_ai = st.selectbox("Изображение для ИИ", list(st.session_state.uploaded_images.keys()), key="ai_edit_select")
            if selected_ai:
                img = st.session_state.uploaded_images[selected_ai]
                st.image(img, caption="Исходное изображение", width='stretch')
                instruction = st.text_area("Что нужно сделать?", placeholder="Пример: удали фон, поверни на 45 градусов, сделай черно-белым и добавь водяной знак 'Фото'",
                                           height=80, key="ai_instruction")
                if st.button("🤖 Обработать с ИИ", type="primary", width='stretch'):
                    if not instruction.strip():
                        st.warning("Введите инструкцию")
                    elif not api_key:
                        st.error("Введите API-ключ в боковой панели")
                    else:
                        with st.spinner("ИИ думает и применяет операции..."):
                            try:
                                processed_ai = image_manager.apply_ai_edits(img, instruction, api_key=api_key)
                                st.session_state.processed_images[f"ai_{selected_ai}"] = processed_ai
                                st.success("✅ ИИ‑редактирование выполнено!")
                                st.image(processed_ai, caption="Результат ИИ", width='stretch')
                            except Exception as e:
                                st.error(f"❌ Ошибка ИИ‑редактирования: {e}")

    with tabs[3]:
        st.markdown("### 🎨 Массовая обработка (одинаковая операция)")
        if not st.session_state.uploaded_images:
            st.info("Сначала загрузите изображения")
        else:
            st.markdown(f"Доступно: {len(st.session_state.uploaded_images)}")
            bop = st.selectbox("Операция для всех", [e.value for e in ImageEditOperation],
                               format_func=lambda x: {
                                   'remove_background': 'Удалить фон', 'remove_watermark': 'Удалить вод.знак',
                                   'resize': 'Изменить размер', 'enhance': 'Улучшить', 'convert_format': 'Конвертировать'
                               }.get(x, x), key="batch_operation")
            bparams = {}
            if bop == 'resize':
                bparams['width'] = st.number_input("Ширина", value=800)
                bparams['height'] = st.number_input("Высота", value=600)
                bparams['maintain_aspect'] = st.checkbox("Сохранять пропорции", True)
            elif bop == 'enhance':
                bparams['brightness'] = st.slider("Яркость", 0.0, 2.0, 1.0)
                bparams['contrast'] = st.slider("Контраст", 0.0, 2.0, 1.0)
            elif bop == 'convert_format':
                bparams['format'] = st.selectbox("Формат", ['PNG', 'JPEG', 'WEBP'])
            if st.button("🚀 Обработать все", type="primary"):
                progress = st.progress(0)
                status = st.empty()
                def update_progress(current, total, filename):
                    progress.progress(current / total)
                    status.text(f"{filename} ({current}/{total})")
                results = image_manager.process_batch(list(st.session_state.uploaded_images.items()),
                                                      ImageEditOperation(bop), bparams, update_progress)
                for fn, img in results:
                    if img: st.session_state.processed_images[f"batch_{fn}"] = img
                progress.empty()
                status.empty()
                st.success(f"Обработано {len(results)} изображений")
                if st.button("💾 Сохранить все результаты"):
                    for fn, img in st.session_state.processed_images.items():
                        if img: img.save(IMAGES_DIR / fn)
                    st.success(f"Сохранено в {IMAGES_DIR}")

    with tabs[4]:
        st.markdown("### 🧠 Массовая ИИ‑обработка (единая инструкция)")
        if not st.session_state.uploaded_images:
            st.info("Сначала загрузите изображения")
        else:
            st.markdown(f"Будет обработано **{len(st.session_state.uploaded_images)}** изображений")
            instruction_mass = st.text_area("Единая инструкция для всех изображений",
                                            placeholder="Пример: удали фон и добавь водяной знак 'Мой бренд'",
                                            height=80, key="mass_ai_instruction")
            if st.button("🤖 Применить ко всем", type="primary", width='stretch'):
                if not instruction_mass.strip():
                    st.warning("Введите инструкцию")
                elif not api_key:
                    st.error("Введите API-ключ в боковой панели")
                else:
                    progress = st.progress(0)
                    status = st.empty()
                    def update_progress(current, total, filename):
                        progress.progress(current / total)
                        status.text(f"ИИ‑обработка: {filename} ({current}/{total})")
                    images_list = list(st.session_state.uploaded_images.items())
                    try:
                        results = image_manager.batch_ai_edit(images_list, instruction_mass,
                                                              api_key=api_key, progress_callback=update_progress)
                        for fn, img in results:
                            if img:
                                st.session_state.processed_images[f"mass_ai_{fn}"] = img
                        progress.empty()
                        status.empty()
                        st.success(f"Обработано {len(results)} изображений")
                    except Exception as e:
                        st.error(f"❌ Ошибка: {e}")

    with tabs[5]:
        st.markdown("### 💾 Сохранённые результаты")
        if not st.session_state.processed_images:
            st.info("Нет обработанных изображений")
        else:
            cols = st.columns(3)
            for idx, (fn, img) in enumerate(st.session_state.processed_images.items()):
                with cols[idx % 3]:
                    st.image(img, caption=fn, width='stretch')
                    cs, cd, cx = st.columns(3)
                    with cs:
                        if st.button("💾", key=f"save_res_{idx}"): img.save(IMAGES_DIR / fn); st.success("✅")
                    with cd:
                        buf = BytesIO(); img.save(buf, format='PNG')
                        st.download_button("📥", buf, fn, "image/png", key=f"dl_res_{idx}")
                    with cx:
                        if st.button("🗑️", key=f"del_res_{idx}"): del st.session_state.processed_images[fn]; st.rerun()
            if st.button("💾 Сохранить все в папку", width='stretch'):
                for fn, img in st.session_state.processed_images.items():
                    if img: img.save(IMAGES_DIR / fn)
                st.success(f"Сохранено в {IMAGES_DIR}")

    with tabs[6]:
        st.markdown("### 📊 Статистика")
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Загружено", len(st.session_state.uploaded_images))
        with c2: st.metric("Обработано", len(st.session_state.processed_images))
        with c3:
            total_px = sum(img.size[0] * img.size[1] for img in st.session_state.uploaded_images.values())
            st.metric("Общий размер", f"{total_px:,} px")
        with c4:
            disk = sum(1 for _ in IMAGES_DIR.glob("*")) if IMAGES_DIR.exists() else 0
            st.metric("На диске", disk)
        if st.session_state.uploaded_images:
            fmt_counts = {}
            for fn in st.session_state.uploaded_images:
                ext = fn.rsplit('.', 1)[-1].upper()
                fmt_counts[ext] = fmt_counts.get(ext, 0) + 1
            df_fmt = pd.DataFrame({'Формат': list(fmt_counts.keys()), 'Количество': list(fmt_counts.values())})
            fig = px.pie(df_fmt, values='Количество', names='Формат', title="По форматам")
            st.plotly_chart(fig, width='stretch')


# ====================== ЭКОНОМИКА (ЮНИТ-ЭКОНОМИКА ДЛЯ МАРКЕТПЛЕЙСА) ======================
def render_economy_tab(api_key: str):
    st.subheader("🧠 Экономика – Юнит-экономика для маркетплейса")
    st.markdown("""
    <div class="info-box">
    <b>Как это работает:</b><br>
    1. Вставьте ссылку на Google-таблицу с данными (или загрузите свою)<br>
    2. ИИ автоматически построит юнит-экономику по структуре Яндекс Маркет<br>
    3. Скачайте готовый Excel с формулами
    </div>
    """, unsafe_allow_html=True)

    source = st.radio("Источник данных", ["Google Sheets (образец)", "Загрузить Excel/CSV", "Создать пустой шаблон"], key="econ_source")
    
    df = None
    table_manager = st.session_state.table_manager

    if source == "Google Sheets (образец)":
        gs_url = st.text_input(
            "URL Google Таблицы",
            value="https://docs.google.com/spreadsheets/d/1KwHE161o0G6BJsz3LfaN2LBnJ3OJyEcOZzKtK5e0TOI/edit?gid=1679952747#gid=1679952747",
            key="econ_gs_url"
        )
        if st.button("📊 Загрузить таблицу", width='stretch'):
            if gs_url:
                with st.spinner("Загрузка..."):
                    df = table_manager.read_google_sheets(gs_url)
                    if df is not None:
                        st.session_state.econ_df = df
                        st.success(f"✅ Загружено: {df.shape}")
                        st.rerun()
    
    elif source == "Загрузить Excel/CSV":
        uploaded = st.file_uploader("Excel или CSV", type=['xlsx', 'xls', 'csv'], key="econ_upload")
        if uploaded:
            with st.spinner("Чтение..."):
                if uploaded.name.endswith('.csv'):
                    df = pd.read_csv(uploaded)
                else:
                    df = table_manager.read_excel(uploaded)
                if df is not None:
                    st.session_state.econ_df = df
                    st.success(f"✅ Загружено: {df.shape}")
                    st.rerun()
    
    elif source == "Создать пустой шаблон":
        if st.button("📋 Создать шаблон", width='stretch'):
            template_data = {
                "Показатель": [
                    "Цена товара (Ц)",
                    "Себестоимость (С)",
                    "Комиссия маркетплейса",
                    "Логистика",
                    "Хранение",
                    "Реклама",
                    "Прочие расходы",
                    "Налог (УСН 6%)",
                    "",
                    "Итого расходы",
                    "Маржинальная прибыль",
                    "Рентабельность",
                ],
                "Значение": [2000, 800, 200, 150, 50, 100, 50, 0, "", 0, 0, ""],
                "Формула": [
                    "", "", "Ц * 10%", "", "", "", "", "Ц * 6%", "",
                    "С + Комиссия + Логистика + Хранение + Реклама + Прочие + Налог",
                    "Ц - Итого расходы",
                    "Маржинальная прибыль / Ц * 100"
                ],
                "Результат": ["", "", "", "", "", "", "", "", "", "", "", ""]
            }
            df = pd.DataFrame(template_data)
            st.session_state.econ_df = df
            st.success("✅ Шаблон создан!")
            st.rerun()
    
    if 'econ_df' in st.session_state and st.session_state.econ_df is not None:
        df = st.session_state.econ_df
        st.markdown("### 📊 Исходные данные")
        st.dataframe(df, width='stretch')

    if df is not None:
        st.markdown("---")
        st.markdown("### 🤖 Построить юнит-экономику")
        
        description = st.text_area(
            "Опишите дополнительные параметры (необязательно)",
            placeholder="Например: цена товара 2000 руб, себестоимость 800 руб, комиссия 10%, логистика 150 руб...",
            height=80,
            key="econ_description"
        )
        
        if st.button("🚀 Рассчитать юнит-экономику", type="primary", width='stretch'):
            if not api_key:
                st.error("Введите API-ключ DeepSeek в боковой панели")
            else:
                with st.spinner("ИИ анализирует данные и строит модель..."):
                    try:
                        df_text = df.to_string() if df is not None else ""
                        
                        client = OpenAI(api_key=api_key, base_url=CONFIG.DEEPSEEK_BASE_URL)
                        prompt = f"""
Ты эксперт по юнит-экономике для маркетплейсов (Яндекс Маркет, Ozon, Wildberries).

На основе предоставленной таблицы создай Python-код, который:
1. Берёт за основу структуру таблицы (показатели и значения)
2. Заполняет ВСЕ формулы и рассчитывает результаты
3. Вычисляет итоговые показатели:
   - Итого расходы = сумма всех расходов
   - Маржинальная прибыль = Цена - Итого расходы
   - Рентабельность = Маржинальная прибыль / Цена * 100%

Формулы для расчёта:
- Комиссия = Цена * процент_комиссии (обычно 5-15%)
- Налог УСН = Цена * 0.06 (для УСН 6%)
- Итого расходы = Себестоимость + Комиссия + Логистика + Хранение + Реклама + Прочие + Налог
- Маржинальная прибыль = Цена - Итого расходы
- Рентабельность = (Маржинальная прибыль / Цена) * 100

Код должен:
- Создать DataFrame с колонками: Показатель, Значение, Формула, Результат
- Заполнить ВСЕ строки данными и формулами
- Рассчитать все результаты
- Вывести итоговую таблицу в переменную df

ДАННЫЕ ТАБЛИЦЫ:
{df_text}

ДОПОЛНИТЕЛЬНЫЕ ПАРАМЕТРЫ:
{description if description else "Использовать стандартные значения"}

Верни ТОЛЬКО код Python в блоке ```python, без пояснений.
"""
                        response = client.chat.completions.create(
                            model=CONFIG.DEEPSEEK_MODEL,
                            messages=[{"role": "system", "content": "Ты эксперт по финансовому моделированию. Возвращай только код Python."},
                                      {"role": "user", "content": prompt}],
                            temperature=0.2,
                            timeout=CONFIG.API_TIMEOUT,
                            max_tokens=CONFIG.MAX_TOKENS
                        )
                        
                        code = response.choices[0].message.content
                        
                        if "```python" in code:
                            code = code.split("```python", 1)[1].split("```", 1)[0]
                        elif "```" in code:
                            code = code.split("```", 1)[1].split("```", 1)[0]
                        code = code.strip()
                        
                        local_vars = {}
                        exec(code, {"pd": pd, "np": __import__('numpy')}, local_vars)
                        
                        result_df = local_vars.get('df')
                        if result_df is None:
                            for var in local_vars.values():
                                if isinstance(var, pd.DataFrame):
                                    result_df = var
                                    break
                        
                        if result_df is None:
                            st.error("Код не создал DataFrame. Проверьте сгенерированный код:")
                            st.code(code, language='python')
                        else:
                            st.success("✅ Юнит-экономика рассчитана!")
                            
                            st.markdown("### 📊 Юнит-экономика")
                            st.dataframe(result_df, width='stretch')
                            
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                result_df.to_excel(writer, index=False, sheet_name='Юнит-экономика')
                            st.download_button(
                                label="📥 Скачать Excel с формулами",
                                data=output.getvalue(),
                                file_name="unit_economy_marketplace.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                width='stretch'
                            )
                            
                            with st.expander("📐 Сгенерированный код Python"):
                                st.code(code, language='python')
                    
                    except Exception as e:
                        st.error(f"❌ Ошибка: {str(e)}")


def render_help_tab():
    st.markdown("""
    ## 🚀 Быстрый старт
    1. Получите API ключ на platform.deepseek.com
    2. Вставьте его в боковую панель
    3. Выберите или создайте агента
    4. Начните диалог или постройте workflow
    """)
