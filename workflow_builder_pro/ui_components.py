"""
UI-функции для рендеринга вкладок приложения.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from PIL import Image
from io import BytesIO
import tempfile
import shutil
import time
import numpy as np
from config import CONFIG, IMAGES_DIR
from utils import (
    save_tables_auto, save_messages_auto, save_workflow_auto,
    NodeType, WorkflowStatus, ImageEditOperation
)
from voice import VOICE_SUPPORT, recognize_speech_from_audio, text_to_speech_mp3
from condition_parser import RussianConditionParser
from workflow import WorkflowExecutor
from ai_agent import AgentManager
from table_manager import TableManager
from image_manager import ImageManager

def render_chat_tab(agent_manager: AgentManager, api_key: str):
    current_agent = agent_manager.get_current_agent()
    if not current_agent:
        st.warning("⚠️ Выберите агента в боковой панели")
        return

    st.subheader(f"💬 {current_agent.name}")
    st.caption(f"Роль: {current_agent.role}")

    st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
    user_input = st.text_area(
        "✏️ Напишите сообщение...", height=80,
        key="chat_input", placeholder="Введите ваш вопрос...",
        label_visibility="collapsed"
    )

    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
    with col1:
        use_training = st.checkbox("📚 Обуч.", value=True, key="chat_use_training",
                                   help="Использовать примеры обучения")
    with col2:
        if VOICE_SUPPORT and st.button("🎤", use_container_width=True, help="Голосовой ввод"):
            st.session_state.voice_show_upload = True
    with col3:
        if st.button("🔊", use_container_width=True, help="Озвучить последний ответ"):
            if st.session_state.agent_messages and st.session_state.agent_messages[-1]['role'] == 'agent':
                audio = text_to_speech_mp3(st.session_state.agent_messages[-1]['content'])
                if audio:
                    st.audio(audio, format="audio/mp3")
    with col4:
        if st.button("🚀 Отправить", type="primary", use_container_width=True):
            if user_input.strip():
                st.session_state.agent_messages.append({'role': 'user', 'content': user_input.strip()})
                st.session_state.chat_input = ""
                with st.spinner("🤖 Агент думает..."):
                    response = current_agent.generate_response(user_input.strip(), api_key, use_training)
                st.session_state.agent_messages.append({'role': 'agent', 'content': response})
                current_agent.add_conversation(user_input.strip(), response)
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
                st.markdown(f'<div class="chat-message-agent"><strong>🤖 {current_agent.name}:</strong><br>{msg["content"]}</div>',
                            unsafe_allow_html=True)

    if st.session_state.get('voice_show_upload'):
        with st.expander("🎤 Голосовой ввод", expanded=True):
            st.info("Загрузите аудиофайл (WAV/MP3) для распознавания речи")
            audio_file = st.file_uploader("Выберите файл", type=["wav", "mp3"], key="voice_upload")
            if audio_file:
                recognized = recognize_speech_from_audio(audio_file.read())
                if recognized:
                    st.success(f"✅ Распознано: {recognized}")
                    st.session_state.chat_input = recognized
                    st.session_state.voice_show_upload = False
                    st.rerun()
                else:
                    st.error("❌ Не удалось распознать речь")

    if st.button("🗑️ Очистить диалог", use_container_width=True):
        st.session_state.agent_messages = []
        save_messages_auto([])
        st.rerun()


def render_training_tab(agent_manager: AgentManager):
    current_agent = agent_manager.get_current_agent()
    if not current_agent:
        st.warning("⚠️ Выберите агента")
        return
    st.subheader(f"📚 Обучение: {current_agent.name}")

    with st.expander("➕ Добавить пример", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            ex_input = st.text_area("Вопрос", height=80, key="train_input")
        with col2:
            ex_output = st.text_area("Ответ", height=80, key="train_output")
        ex_context = st.text_input("Контекст", key="train_context")
        if st.button("✨ Добавить", type="primary"):
            if ex_input and ex_output:
                current_agent.add_training_example(ex_input, ex_output, ex_context)
                agent_manager.save_agents()
                st.success("✅ Пример добавлен!")
                st.rerun()

    st.markdown(f"### Примеры ({len(current_agent.training_examples)})")
    for i, ex in enumerate(reversed(current_agent.training_examples[-10:])):
        with st.expander(f"#{ex['id']}: {ex['user_input'][:50]}..."):
            st.markdown(f"**Ответ:** {ex['expected_output']}")
            st.caption(f"📅 {ex['timestamp'][:10]}")
            if st.button(f"🗑️ Удалить", key=f"del_ex_{ex['id']}"):
                current_agent.training_examples = [e for e in current_agent.training_examples if e['id'] != ex['id']]
                agent_manager.save_agents()
                st.rerun()

    with st.expander("📚 МАССОВОЕ ОБУЧЕНИЕ (из текста)"):
        bulk_text = st.text_area("Вопрос -> Ответ (каждая строка)", height=150,
                                 placeholder="Как анализировать данные? -> Для анализа данных нужно...")
        if st.button("🚀 Обучить на всех примерах"):
            lines = bulk_text.strip().split('\n')
            added = 0
            for line in lines:
                if '->' in line:
                    parts = line.split('->', 1)
                    question, answer = parts[0].strip(), parts[1].strip()
                    if question and answer:
                        current_agent.add_training_example(question, answer)
                        added += 1
            if added:
                agent_manager.save_agents()
                st.success(f"✅ Добавлено {added} примеров!")
                st.rerun()
            else:
                st.warning("Не найдено примеров в формате Вопрос -> Ответ")


def render_memory_tab(agent_manager: AgentManager):
    current_agent = agent_manager.get_current_agent()
    if not current_agent:
        st.warning("⚠️ Выберите агента")
        return
    st.subheader(f"🧠 Память: {current_agent.name}")

    with st.expander("➕ Добавить факт", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            mem_key = st.text_input("Ключ", key="mem_key")
        with col2:
            mem_value = st.text_input("Значение", key="mem_value")
        importance = st.selectbox("Важность", ["low", "normal", "high"], key="mem_importance")
        if st.button("💾 Сохранить"):
            if mem_key and mem_value:
                current_agent.add_to_memory(mem_key, mem_value, importance)
                agent_manager.save_agents()
                st.success("✅ Запомнено!")
                st.rerun()

    st.markdown(f"### Факты ({len(current_agent.memory)})")
    for mem in current_agent.memory:
        icon = "🔴" if mem['importance'] == 'high' else "🟡" if mem['importance'] == 'normal' else "🟢"
        st.markdown(f"""
        <div class="memory-box">
            {icon} **{mem['key']}** = {mem['value']}<br>
            <small>👁️ {mem['access_count']} | 📅 {mem['timestamp'][:10]}</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"🗑️", key=f"del_mem_{mem['key']}"):
            current_agent.memory = [m for m in current_agent.memory if m['key'] != mem['key']]
            agent_manager.save_agents()
            st.rerun()

    if st.button("🗑️ Очистить память"):
        current_agent.memory = []
        agent_manager.save_agents()
        st.success("Память очищена")
        st.rerun()


def render_analytics_tab(agent_manager: AgentManager):
    current_agent = agent_manager.get_current_agent()
    if not current_agent:
        st.warning("⚠️ Выберите агента")
        return
    st.subheader(f"📊 {current_agent.name}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><h3>{current_agent.stats["total_trainings"]}</h3><p>Обучений</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><h3>{current_agent.stats["total_conversations"]}</h3><p>Диалогов</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><h3>{current_agent.stats["success_rate"]:.0f}%</h3><p>Успешность</p></div>', unsafe_allow_html=True)
    with col4:
        total = len(current_agent.training_examples) + len(current_agent.memory)
        st.markdown(f'<div class="stat-card"><h3>{total}</h3><p>Фактов</p></div>', unsafe_allow_html=True)

    if current_agent.training_examples:
        st.subheader("📈 Прогресс обучения")
        df = pd.DataFrame([
            {'Дата': ex['timestamp'][:10], 'Пример': i+1}
            for i, ex in enumerate(current_agent.training_examples)
        ])
        fig = px.line(df, x='Дата', y='Пример', title="Накопление примеров")
        st.plotly_chart(fig, use_container_width=True)

    if current_agent.conversation_history:
        st.subheader("💬 Последние диалоги")
        for conv in current_agent.conversation_history[-5:]:
            with st.expander(f"Диалог от {conv['timestamp'][:19]}"):
                st.markdown(f"**👤 Пользователь:** {conv['user'][:200]}")
                st.markdown(f"**🤖 Агент:** {conv['agent'][:200]}")


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
        ]
        for name, btype in blocks:
            if st.button(f"{name}", key=f"add_{btype}", use_container_width=True):
                st.session_state.workflow.append({
                    "id": len(st.session_state.workflow),
                    "name": name,
                    "type": btype,
                    "config": {},
                    "status": WorkflowStatus.PENDING.value
                })
                st.rerun()

        st.markdown("### 🧠 Агенты в workflow")
        for agent in agent_manager.agents.values():
            if st.button(f"🧠 {agent.name}", key=f"wf_agent_{agent.id}", use_container_width=True):
                st.session_state.workflow.append({
                    "id": len(st.session_state.workflow),
                    "name": f"Агент: {agent.name}",
                    "type": NodeType.AI_AGENT.value,
                    "agent_id": agent.id,
                    "config": {"question": "", "use_training": True},
                    "status": WorkflowStatus.PENDING.value
                })
                st.rerun()

    with col2:
        st.markdown("### 📋 Текущий workflow")
        if not st.session_state.workflow:
            st.info("💡 Добавьте блоки слева")
            return

        for i, block in enumerate(st.session_state.workflow):
            status_cls = ""
            if block.get('status') == WorkflowStatus.SUCCESS.value:
                status_cls = "workflow-node-success"
            elif block.get('status') == WorkflowStatus.ERROR.value:
                status_cls = "workflow-node-error"

            st.markdown(f"""
            <div class="workflow-node {status_cls}">
                <b>{block.get('name')}</b> <small>#{i+1}</small><br>
                <small>{block.get('type')}</small>
            </div>
            """, unsafe_allow_html=True)

            if i < len(st.session_state.workflow) - 1:
                st.markdown('<div class="workflow-connector">▼</div>', unsafe_allow_html=True)

            with st.expander(f"⚙️ Настроить {block.get('name')}"):
                cfg = block.get('config', {})
                if block['type'] == NodeType.GOOGLE_SHEETS_READ.value:
                    cfg['sheet_url'] = st.text_input("URL", cfg.get('sheet_url', ''), key=f"gs_url_{i}")
                    cfg['sheet_name'] = st.text_input("Лист", cfg.get('sheet_name', ''), key=f"gs_sheet_{i}")
                elif block['type'] == NodeType.EXCEL_READ.value:
                    cfg['file_path'] = st.text_input("Путь к файлу", cfg.get('file_path', ''), key=f"ex_path_{i}")
                elif block['type'] == NodeType.DEEPSEEK_AI.value:
                    cfg['system_prompt'] = st.text_area("Инструкция ИИ", cfg.get('system_prompt', ''), height=60, key=f"ai_sys_{i}")
                    cfg['user_prompt'] = st.text_area("Запрос", cfg.get('user_prompt', ''), height=60, key=f"ai_user_{i}")
                elif block['type'] == NodeType.CONDITION.value:
                    cfg['condition'] = st.text_area("Условие на русском", cfg.get('condition', ''), height=60, key=f"cond_{i}")
                    if cfg.get('condition'):
                        parsed = RussianConditionParser.parse(cfg['condition'])
                        if parsed.get('code'):
                            st.code(parsed['code'], language='python')
                elif block['type'] == NodeType.AI_AGENT.value:
                    agent = agent_manager.agents.get(block.get('agent_id'))
                    if agent:
                        st.info(f"🧠 Агент: {agent.name}")
                        cfg['question'] = st.text_area("Вопрос агенту", cfg.get('question', ''), height=60, key=f"agent_q_{i}")
                elif block['type'] == NodeType.DATA_CLEAN.value:
                    cfg['remove_duplicates'] = st.checkbox("Удалить дубли", cfg.get('remove_duplicates', True), key=f"clean_dup_{i}")
                    cfg['remove_empty'] = st.checkbox("Удалить пустые", cfg.get('remove_empty', True), key=f"clean_empty_{i}")
                elif block['type'] == NodeType.EMAIL.value:
                    cfg['to'] = st.text_input("Кому", cfg.get('to', ''), key=f"to_{i}")
                    cfg['subject'] = st.text_input("Тема", cfg.get('subject', ''), key=f"subj_{i}")
                    cfg['body'] = st.text_area("Сообщение", cfg.get('body', ''), height=60, key=f"body_{i}")
                elif block['type'] == NodeType.TELEGRAM.value:
                    cfg['chat_id'] = st.text_input("Chat ID", cfg.get('chat_id', ''), key=f"chat_{i}")
                    cfg['message'] = st.text_area("Сообщение", cfg.get('message', ''), height=60, key=f"msg_{i}")
                elif block['type'] == NodeType.HTTP_GET.value:
                    cfg['url'] = st.text_input("URL", cfg.get('url', ''), key=f"get_url_{i}")
                elif block['type'] == NodeType.HTTP_POST.value:
                    cfg['url'] = st.text_input("URL", cfg.get('url', ''), key=f"post_url_{i}")
                    cfg['body'] = st.text_area("Тело JSON", cfg.get('body', '{}'), height=60, key=f"post_body_{i}")

                block['config'] = cfg
                if st.button(f"🗑️ Удалить блок", key=f"del_wf_{i}"):
                    st.session_state.workflow.pop(i)
                    st.rerun()

        st.markdown("---")
        if st.button("🚀 ЗАПУСТИТЬ WORKFLOW", type="primary", use_container_width=True):
            progress = st.progress(0)
            status = st.empty()

            def update_progress(idx, node):
                progress.progress((idx + 1) / len(st.session_state.workflow))
                status.text(f"🔄 {node.get('name')}")

            table_manager = st.session_state.table_manager
            executor = WorkflowExecutor(
                st.session_state.workflow, api_key, agent_manager, table_manager
            )
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


def render_conditions_tab():
    st.subheader("🔀 Русские условия для workflow")
    st.markdown("""
    <div class="info-box">
    <b>Примеры:</b><br>
    • если цена больше 1000 то отправить уведомление<br>
    • если статус равно 'успех' иначе отправить ошибку<br>
    • если количество меньше 5 то пополнить склад<br>
    • если текст содержит 'срочно' то отметить как важное
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📝 Примеры условий")
        for ex in RussianConditionParser.EXAMPLES:
            st.code(f"📌 {ex}")
    with col2:
        st.markdown("### 🔧 Проверьте своё условие")
        test_cond = st.text_area("Напишите условие:", height=100,
                                 placeholder="например: если температура больше 30 то включить кондиционер")
        if test_cond:
            parsed = RussianConditionParser.parse(test_cond)
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Тип", parsed.get('type'))
            with col_b:
                st.metric("Уверенность", f"{parsed.get('confidence', 0)*100:.0f}%")
            if parsed.get('code'):
                st.success(f"💻 Сгенерированный код: `{parsed['code']}`")
            else:
                st.warning("⚠️ Не удалось распознать условие")

    st.markdown("---")
    st.markdown("### 💡 Доступные операторы")
    st.markdown("""
    | Что написать | Как понять | Пример |
    |--------------|------------|--------|
    | `больше`, `>`, `выше` | Больше чем | `цена больше 1000` |
    | `меньше`, `<`, `ниже` | Меньше чем | `количество меньше 5` |
    | `равно`, `=`, `равняется` | Равно | `статус равно успех` |
    | `содержит`, `включает` | Содержит подстроку | `текст содержит срочно` |
    | `пусто`, `не заполнено` | Пустое значение | `поле пусто` |
    | `между ... и ...` | В диапазоне | `сумма между 1000 и 5000` |
    """)


def render_tables_tab(api_key: str):
    st.subheader("🗂 Таблицы + ИИ + Редактор")
    table_manager = st.session_state.table_manager

    if not table_manager:
        st.warning("Менеджер таблиц не инициализирован")
        return

    # Сохранённые таблицы
    with st.expander("📚 Сохранённые таблицы", expanded=not st.session_state.saved_tables):
        if not st.session_state.saved_tables:
            st.info("💡 Нет сохранённых таблиц. Загрузите или создайте таблицу, чтобы сохранить её здесь.")
        else:
            for table_id, df in st.session_state.saved_tables.items():
                with st.expander(f"📊 {table_id} ({df.shape[0]}×{df.shape[1]})", expanded=False):
                    st.dataframe(df.head(5), use_container_width=True)
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("✏️ Открыть", key=f"open_{table_id}", use_container_width=True):
                            st.session_state.current_df = df.copy()
                            st.session_state.editing_table_id = table_id
                            st.rerun()
                    with col2:
                        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                            table_manager.write_excel(df, tmp.name)
                            with open(tmp.name, 'rb') as f:
                                st.download_button("📥 Скачать", f, file_name=f"{table_id}.xlsx",
                                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                                   key=f"dl_saved_{table_id}", use_container_width=True)
                    with col3:
                        if st.button("🗑️ Удалить", key=f"del_saved_{table_id}", use_container_width=True):
                            del st.session_state.saved_tables[table_id]
                            save_tables_auto(st.session_state.saved_tables)
                            if st.session_state.editing_table_id == table_id:
                                st.session_state.current_df = None
                                st.session_state.editing_table_id = None
                            st.rerun()

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📥 Загрузка данных")
        source = st.radio("Источник", ["Google Sheets", "Excel"], key="table_source")
        if source == "Google Sheets":
            gs_url = st.text_input("URL Google Sheets", placeholder="https://docs.google.com/spreadsheets/d/...", key="gs_url_input")
            if st.button("📊 Загрузить из Google", use_container_width=True):
                if gs_url:
                    with st.spinner("Загрузка..."):
                        df = table_manager.read_google_sheets(gs_url)
                        if df is not None:
                            table_id = f"gs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            st.session_state.current_df = df
                            st.session_state.editing_table_id = table_id
                            st.session_state.saved_tables[table_id] = df.copy()
                            save_tables_auto(st.session_state.saved_tables)
                            st.success(f"✅ Загружено: {df.shape}")
                            st.rerun()
        else:
            uploaded = st.file_uploader("Excel файл", type=['xlsx', 'xls', 'csv'], key="excel_upload")
            if uploaded:
                with st.spinner("Чтение файла..."):
                    try:
                        if uploaded.name.endswith('.csv'):
                            df = pd.read_csv(uploaded)
                        else:
                            df = table_manager.read_excel(uploaded)
                        if df is not None:
                            table_id = f"ex_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            st.session_state.current_df = df
                            st.session_state.editing_table_id = table_id
                            st.session_state.saved_tables[table_id] = df.copy()
                            save_tables_auto(st.session_state.saved_tables)
                            st.success(f"✅ Загружено: {df.shape}")
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Ошибка чтения: {e}")

    with col2:
        if st.session_state.current_df is not None and st.session_state.editing_table_id:
            st.markdown(f'<div class="table-editor">', unsafe_allow_html=True)
            st.markdown(f"### 📊 Редактор: {st.session_state.editing_table_id}")
            st.caption(f"Размер: {st.session_state.current_df.shape[0]} строк × {st.session_state.current_df.shape[1]} столбцов")

            col_actions = st.columns(4)
            with col_actions[0]:
                if st.button("💾 Сохранить", key=f"save_{st.session_state.editing_table_id}", use_container_width=True):
                    st.session_state.saved_tables[st.session_state.editing_table_id] = st.session_state.current_df.copy()
                    save_tables_auto(st.session_state.saved_tables)
                    st.success("✅ Сохранено!")
            with col_actions[1]:
                if st.button("🗑️ Удалить", key=f"delete_{st.session_state.editing_table_id}", use_container_width=True):
                    if st.session_state.editing_table_id in st.session_state.saved_tables:
                        del st.session_state.saved_tables[st.session_state.editing_table_id]
                        save_tables_auto(st.session_state.saved_tables)
                    st.session_state.current_df = None
                    st.session_state.editing_table_id = None
                    st.success("🗑️ Удалено")
                    st.rerun()
            with col_actions[2]:
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                    table_manager.write_excel(st.session_state.current_df, tmp.name)
                    with open(tmp.name, 'rb') as f:
                        st.download_button("📥 Excel", f, file_name=f"{st.session_state.editing_table_id}.xlsx",
                                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                           key=f"dl_{st.session_state.editing_table_id}", use_container_width=True)
            with col_actions[3]:
                if st.button("✏️ ИИ", key=f"ai_{st.session_state.editing_table_id}", use_container_width=True):
                    st.session_state.table_edit_mode = True

            st.markdown("#### ✏️ Редактирование данных")
            edited_df = st.data_editor(
                st.session_state.current_df,
                num_rows="dynamic",
                use_container_width=True,
                key=f"editor_{st.session_state.editing_table_id}",
                hide_index=True
            )
            if not st.session_state.current_df.equals(edited_df):
                st.session_state.current_df = edited_df
                st.session_state.saved_tables[st.session_state.editing_table_id] = edited_df.copy()
                save_tables_auto(st.session_state.saved_tables)
                st.toast("🔄 Изменения сохранены", icon="💾")

            if st.session_state.table_edit_mode:
                with st.expander("🤖 ИИ-помощник для таблиц", expanded=True):
                    instruction = st.text_area(
                        "Опишите, что сделать с таблицей:",
                        placeholder="Пример: удали пустые строки, добавь столбец Итого",
                        height=80,
                        key=f"ai_instruction_{st.session_state.editing_table_id}"
                    )
                    if st.button("🚀 Применить ИИ", type="primary", key=f"ai_apply_{st.session_state.editing_table_id}"):
                        if instruction and api_key:
                            with st.spinner("🧠 Анализирую..."):
                                result = table_manager.ai_analyze_dataframe(
                                    edited_df, instruction, api_key
                                )
                                if 'error' not in result:
                                    st.success("✅ Анализ завершён")
                                    st.markdown(f"**🔍 Анализ:** {result.get('analysis', '')}")
                                    if result.get('ready_code'):
                                        st.code(result['ready_code'], language='python')
                                        if st.button("💾 Применить код", key=f"apply_code_{st.session_state.editing_table_id}"):
                                            try:
                                                transformed_df = table_manager.execute_transformation(
                                                    edited_df.copy(), result['ready_code']
                                                )
                                                st.session_state.current_df = transformed_df
                                                st.session_state.saved_tables[st.session_state.editing_table_id] = transformed_df.copy()
                                                save_tables_auto(st.session_state.saved_tables)
                                                st.success("✅ Применено!")
                                                st.session_state.table_edit_mode = False
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"❌ Ошибка: {e}")
                                else:
                                    st.error(f"❌ {result['error']}")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("💡 Загрузите таблицу слева или выберите из сохранённых выше")


def render_images_tab(api_key: str):
    st.subheader("🖼️ Редактор изображений с ИИ")
    image_manager = st.session_state.image_manager

    if not image_manager:
        st.error("Менеджер изображений не инициализирован")
        return

    # Проверка поддержки изображений
    try:
        from PIL import Image
    except ImportError:
        st.error("Установите pillow: pip install pillow")
        return

    tabs = st.tabs(["📥 Загрузка", "✏️ Редактирование", "🎨 Массовая обработка", "💾 Результаты", "📊 Статистика"])

    with tabs[0]:
        st.markdown("### 📥 Массовая загрузка изображений")
        st.info(f"Поддерживается до {CONFIG.MAX_IMAGE_UPLOAD} файлов. Форматы: {', '.join(CONFIG.SUPPORTED_IMAGE_FORMATS)}")
        uploaded_files = st.file_uploader(
            "Выберите изображения", type=list(CONFIG.SUPPORTED_IMAGE_FORMATS),
            accept_multiple_files=True, key="image_upload"
        )
        if uploaded_files:
            progress_bar = st.progress(0)
            status_text = st.empty()
            for i, uploaded_file in enumerate(uploaded_files):
                try:
                    file_size_mb = uploaded_file.size / (1024 * 1024)
                    if file_size_mb > CONFIG.MAX_IMAGE_SIZE_MB:
                        st.warning(f"⚠️ Файл {uploaded_file.name} превышает {CONFIG.MAX_IMAGE_SIZE_MB}MB и пропущен")
                        continue
                    image = Image.open(uploaded_file)
                    st.session_state.uploaded_images[uploaded_file.name] = image
                    progress_bar.progress((i + 1) / len(uploaded_files))
                    status_text.text(f"Загрузка: {uploaded_file.name} ({image.size[0]}x{image.size[1]})")
                except Exception as e:
                    st.error(f"❌ Ошибка загрузки {uploaded_file.name}: {e}")
            progress_bar.empty()
            status_text.empty()
            st.success(f"✅ Загружено {len(st.session_state.uploaded_images)} изображений")
            if st.session_state.uploaded_images:
                st.markdown("### 👁️ Предпросмотр")
                cols = st.columns(3)
                for idx, (filename, img) in enumerate(list(st.session_state.uploaded_images.items())[:6]):
                    with cols[idx % 3]:
                        st.image(img, caption=f"{filename} ({img.size[0]}x{img.size[1]})", use_container_width=True)

    with tabs[1]:
        st.markdown("### ✏️ Редактирование изображения")
        if not st.session_state.uploaded_images:
            st.info("💡 Загрузите изображения на вкладке 'Загрузка'")
        else:
            selected_filename = st.selectbox("Выберите изображение", list(st.session_state.uploaded_images.keys()), key="edit_select")
            if selected_filename:
                original_image = st.session_state.uploaded_images[selected_filename]
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### Оригинал")
                    st.image(original_image, use_container_width=True)
                with col2:
                    st.markdown("#### Операции")
                    operation = st.selectbox("Операция", [op.value for op in ImageEditOperation],
                                             format_func=lambda x: {
                                                 'remove_background': 'Удалить фон',
                                                 'remove_watermark': 'Удалить водяной знак',
                                                 'resize': 'Изменить размер',
                                                 'crop': 'Обрезать',
                                                 'rotate': 'Повернуть',
                                                 'enhance': 'Улучшить',
                                                 'filter': 'Фильтр',
                                                 'add_watermark': 'Добавить водяной знак',
                                                 'convert_format': 'Конвертировать формат'
                                             }.get(x, x),
                                             key="edit_operation")
                    params = {}
                    if operation == 'resize':
                        params['width'] = st.number_input("Ширина", min_value=1, value=original_image.size[0])
                        params['height'] = st.number_input("Высота", min_value=1, value=original_image.size[1])
                        params['maintain_aspect'] = st.checkbox("Сохранить пропорции", value=True)
                    elif operation == 'rotate':
                        params['angle'] = st.slider("Угол", -180, 180, 0)
                    elif operation == 'enhance':
                        params['brightness'] = st.slider("Яркость", 0.0, 2.0, 1.0)
                        params['contrast'] = st.slider("Контраст", 0.0, 2.0, 1.0)
                        params['sharpness'] = st.slider("Четкость", 0.0, 2.0, 1.0)
                    elif operation == 'filter':
                        params['filter_type'] = st.selectbox("Фильтр", ['blur','sharpen','edge_enhance','contour','emboss','smooth','detail'])
                    elif operation == 'add_watermark':
                        params['text'] = st.text_input("Текст", value="Watermark")
                        params['position'] = st.selectbox("Позиция", ['top-left','top-right','bottom-left','bottom-right'])
                        params['font_size'] = st.slider("Размер шрифта", 10, 100, 40)
                        params['opacity'] = st.slider("Прозрачность", 0, 255, 128)
                    elif operation == 'convert_format':
                        params['format'] = st.selectbox("Формат", ['PNG','JPEG','WEBP','BMP'])
                    if st.button("🚀 Применить", type="primary"):
                        try:
                            processed = image_manager._apply_operation(original_image, ImageEditOperation(operation), params)
                            st.session_state.processed_images[f"edited_{selected_filename}"] = processed
                            st.success("✅ Обработано!")
                            st.image(processed, caption="Результат", use_container_width=True)
                            if st.button("💾 Сохранить результат"):
                                save_path = IMAGES_DIR / f"edited_{selected_filename}"
                                processed.save(save_path)
                                st.success(f"Сохранено в {save_path}")
                        except Exception as e:
                            st.error(f"❌ Ошибка: {e}")

    with tabs[2]:
        st.markdown("### 🎨 Массовая обработка")
        if not st.session_state.uploaded_images:
            st.info("💡 Сначала загрузите изображения")
        else:
            st.markdown(f"Доступно изображений: {len(st.session_state.uploaded_images)}")
            batch_op = st.selectbox("Операция для всех", [op.value for op in ImageEditOperation],
                                    format_func=lambda x: {
                                        'remove_background': 'Удалить фон',
                                        'remove_watermark': 'Удалить водяной знак',
                                        'resize': 'Изменить размер',
                                        'enhance': 'Улучшить',
                                        'convert_format': 'Конвертировать'
                                    }.get(x, x), key="batch_operation")
            batch_params = {}
            if batch_op == 'resize':
                batch_params['width'] = st.number_input("Ширина", value=800)
                batch_params['height'] = st.number_input("Высота", value=600)
                batch_params['maintain_aspect'] = st.checkbox("Сохранять пропорции", True)
            elif batch_op == 'enhance':
                batch_params['brightness'] = st.slider("Яркость", 0.0, 2.0, 1.0)
                batch_params['contrast'] = st.slider("Контраст", 0.0, 2.0, 1.0)
            elif batch_op == 'convert_format':
                batch_params['format'] = st.selectbox("Формат", ['PNG','JPEG','WEBP'])
            if st.button("🚀 Обработать все", type="primary"):
                progress = st.progress(0)
                status = st.empty()
                def update_progress(current, total, filename):
                    progress.progress(current / total)
                    status.text(f"Обработка: {filename} ({current}/{total})")
                images_list = list(st.session_state.uploaded_images.items())
                results = image_manager.process_batch(images_list, ImageEditOperation(batch_op), batch_params, update_progress)
                for filename, img in results:
                    if img is not None:
                        st.session_state.processed_images[f"batch_{filename}"] = img
                progress.empty()
                status.empty()
                st.success(f"Обработано {len(results)} изображений")
                if st.button("💾 Сохранить все результаты"):
                    for fn, img in st.session_state.processed_images.items():
                        if img:
                            img.save(IMAGES_DIR / fn)
                    st.success(f"Сохранено в {IMAGES_DIR}")

    with tabs[3]:
        st.markdown("### 💾 Сохранённые результаты")
        if not st.session_state.processed_images:
            st.info("Нет обработанных изображений")
        else:
            cols = st.columns(3)
            for idx, (fn, img) in enumerate(st.session_state.processed_images.items()):
                with cols[idx % 3]:
                    st.image(img, caption=fn, use_container_width=True)
                    col_s, col_d, col_x = st.columns(3)
                    with col_s:
                        if st.button("💾", key=f"save_res_{idx}"):
                            img.save(IMAGES_DIR / fn)
                            st.success("✅")
                    with col_d:
                        buf = BytesIO()
                        img.save(buf, format='PNG')
                        st.download_button("📥", buf, fn, "image/png", key=f"dl_res_{idx}")
                    with col_x:
                        if st.button("🗑️", key=f"del_res_{idx}"):
                            del st.session_state.processed_images[fn]
                            st.rerun()
            if st.button("💾 Сохранить все в папку", use_container_width=True):
                for fn, img in st.session_state.processed_images.items():
                    if img:
                        img.save(IMAGES_DIR / fn)
                st.success(f"Сохранено в {IMAGES_DIR}")

    with tabs[4]:
        st.markdown("### 📊 Статистика изображений")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Загружено", len(st.session_state.uploaded_images))
        with c2:
            st.metric("Обработано", len(st.session_state.processed_images))
        with c3:
            total_pixels = sum(img.size[0]*img.size[1] for img in st.session_state.uploaded_images.values())
            st.metric("Общий размер (пикселей)", f"{total_pixels:,}")
        with c4:
            on_disk = sum(1 for _ in IMAGES_DIR.glob("*")) if IMAGES_DIR.exists() else 0
            st.metric("Файлов на диске", on_disk)
        if st.session_state.uploaded_images:
            fmt_counts = {}
            for fn in st.session_state.uploaded_images:
                ext = fn.rsplit('.', 1)[-1].upper()
                fmt_counts[ext] = fmt_counts.get(ext, 0) + 1
            df_fmts = pd.DataFrame({'Формат': list(fmt_counts.keys()), 'Количество': list(fmt_counts.values())})
            fig = px.pie(df_fmts, values='Количество', names='Формат', title="Распределение по форматам")
            st.plotly_chart(fig, use_container_width=True)


def render_help_tab():
    st.subheader("📖 Полная инструкция")
    st.markdown("""
    ## 🚀 Быстрый старт
    1. Получите API ключ на [platform.deepseek.com](https://platform.deepseek.com)
    2. Вставьте его в боковую панель
    3. Выберите или создайте агента
    4. Начните диалог или постройте workflow

    ## 💬 Чат-интерфейс
    - Поле ввода всегда сверху
    - Автоочистка после отправки
    - Голосовой ввод и озвучка ответов

    ## 🗂 Таблицы
    - Загрузка Google Sheets и Excel
    - Редактирование в реальном времени
    - ИИ-трансформация по описанию на русском

    ## 🖼️ Изображения
    - Массовая загрузка до 10 000 файлов
    - Удаление фона, водяных знаков
    - Изменение размера, фильтры, водяные знаки

    ## 🔀 Условия на русском
    Пишите естественно: "если цена больше 1000 то уведомить"

    ## 📱 Мобильная версия
    Интерфейс адаптирован для экранов меньше 768px.

    ## 🔧 Установка
    ```bash
    pip install streamlit pandas openpyxl openai plotly requests pillow rembg numpy SpeechRecognition gTTS
    streamlit run app.py
