# ui_components.py - Все UI компоненты для Streamlit (ПОЛНАЯ ВЕРСИЯ С ИИ-РЕДАКТИРОВАНИЕМ EXCEL И SMS)
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
    
    if st.session_state.voice_show_upload:
        with st.expander("🎤 Голосовой ввод", expanded=True):
            audio_file = st.file_uploader("Выберите файл", type=["wav", "mp3"], key="voice_upload")
            if audio_file:
                recognized = recognize_speech_from_audio(audio_file.read())
                if recognized:
                    st.success(f"✅ Распознано: {recognized}")
                    st.session_state.voice_show_upload = False
                    st.rerun()
                else:
                    st.error("❌ Не удалось распознать речь")
    
    if st.button("🗑️ Очистить диалог", use_container_width=True):
        st.session_state.agent_messages = []
        save_messages_auto([])
        st.rerun()


def render_training_tab(agent_manager):
    """Рендерит вкладку обучения"""
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
    for ex in reversed(current_agent.training_examples[-10:]):
        with st.expander(f"#{ex['id']}: {ex['user_input'][:50]}..."):
            st.markdown(f"**Ответ:** {ex['expected_output']}")
            st.caption(f"📅 {ex['timestamp'][:10]}")
            if st.button(f"🗑️ Удалить", key=f"del_ex_{ex['id']}"):
                current_agent.training_examples = [e for e in current_agent.training_examples if e['id'] != ex['id']]
                agent_manager.save_agents()
                st.rerun()


def render_memory_tab(agent_manager):
    """Рендерит вкладку памяти"""
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


def render_analytics_tab(agent_manager):
    """Рендерит вкладку аналитики"""
    current_agent = agent_manager.get_current_agent()
    if not current_agent:
        st.warning("⚠️ Выберите агента")
        return
    
    st.subheader(f"📊 {current_agent.name}")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Обучений", current_agent.stats['total_trainings'])
    with col2:
        st.metric("Диалогов", current_agent.stats['total_conversations'])
    with col3:
        st.metric("Успешность", f"{current_agent.stats['success_rate']:.0f}%")
    with col4:
        total = len(current_agent.training_examples) + len(current_agent.memory)
        st.metric("Фактов", total)
    
    if current_agent.training_examples:
        st.subheader("📈 Прогресс")
        df = pd.DataFrame([
            {'Дата': ex['timestamp'][:10], 'Пример': i+1}
            for i, ex in enumerate(current_agent.training_examples)
        ])
        if not df.empty:
            fig = px.line(df, x='Дата', y='Пример', title="Накопление примеров")
            st.plotly_chart(fig, use_container_width=True)


def render_workflow_tab(agent_manager, api_key):
    """Рендерит вкладку workflow с поддержкой SMS, условий и улучшенным ИИ"""
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
            ("📱 SMS", "sms"),   # новый тип
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
        
        st.markdown("### 🧠 Агенты")
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
        st.markdown("### 📋 Workflow")
        if not st.session_state.workflow:
            st.info("💡 Добавьте блоки слева")
            return
        
        # Форма для задания глобальных условий для узлов (можно применять перед запуском)
        st.markdown("#### ⚙️ Настройка узлов")
        
        for i, block in enumerate(st.session_state.workflow):
            st.markdown(f"""
<div class="workflow-node">
    <b>{block.get('name')}</b> <small>#{i+1}</small><br>
    <small>{block.get('type')}</small>
</div>
""", unsafe_allow_html=True)
            if i < len(st.session_state.workflow) - 1:
                st.markdown('<div class="workflow-connector">▼</div>', unsafe_allow_html=True)
            
            with st.expander(f"⚙️ {block.get('name')}"):
                cfg = block.get('config', {})
                node_type = block['type']
                
                # Общее поле для условия выполнения узла (только для отправки сообщений и действий)
                if node_type in [NodeType.EMAIL.value, NodeType.TELEGRAM.value, "sms", NodeType.DEEPSEEK_AI.value, NodeType.HTTP_POST.value]:
                    cfg['condition'] = st.text_area(
                        "🔀 Условие выполнения (опционально, на русском)",
                        cfg.get('condition', ''),
                        height=60,
                        key=f"cond_node_{i}",
                        help="Пример: если статус равно 'успех'"
                    )
                
                # Конфигурация в зависимости от типа узла
                if node_type == NodeType.DEEPSEEK_AI.value:
                    cfg['system_prompt'] = st.text_area("Системный промпт", cfg.get('system_prompt', 'Ты полезный ассистент'), height=60, key=f"ai_sys_{i}")
                    cfg['user_prompt'] = st.text_area("Запрос пользователя", cfg.get('user_prompt', ''), height=80, key=f"ai_user_{i}")
                    cfg['temperature'] = st.slider("Температура", 0.0, 1.0, cfg.get('temperature', 0.3), 0.05, key=f"ai_temp_{i}")
                
                elif node_type == NodeType.CONDITION.value:
                    cfg['condition'] = st.text_area("Условие (на русском)", cfg.get('condition', ''), height=80, key=f"cond_{i}")
                    if cfg.get('condition'):
                        parsed = RussianConditionParser.parse(cfg['condition'])
                        if parsed.get('code'):
                            st.code(parsed['code'], language='python')
                            st.caption(f"Уверенность: {parsed.get('confidence',0)*100:.0f}%")
                
                elif node_type == NodeType.LOOP.value:
                    cfg['items'] = st.text_input("Элементы (список или переменная)", cfg.get('items', '[]'), key=f"loop_items_{i}")
                    cfg['batch_size'] = st.number_input("Размер пакета", 1, 100, cfg.get('batch_size', 10), key=f"loop_batch_{i}")
                    cfg['max_iterations'] = st.number_input("Макс. итераций", 1, 10000, cfg.get('max_iterations', 1000), key=f"loop_max_{i}")
                    # В будущем можно добавить редактирование вложенного workflow
                
                elif node_type == NodeType.AI_AGENT.value:
                    agent = agent_manager.agents.get(block.get('agent_id'))
                    if agent:
                        st.info(f"🧠 {agent.name}")
                    cfg['question'] = st.text_area("Вопрос агенту", cfg.get('question', ''), height=80, key=f"agent_q_{i}")
                    cfg['use_training'] = st.checkbox("Использовать обучение", cfg.get('use_training', True), key=f"agent_train_{i}")
                
                elif node_type == NodeType.EMAIL.value:
                    cfg['to'] = st.text_input("Кому", cfg.get('to', ''), key=f"email_to_{i}")
                    cfg['subject'] = st.text_input("Тема", cfg.get('subject', ''), key=f"email_subj_{i}")
                    cfg['body'] = st.text_area("Тело письма", cfg.get('body', ''), height=80, key=f"email_body_{i}")
                
                elif node_type == NodeType.TELEGRAM.value:
                    cfg['chat_id'] = st.text_input("Chat ID", cfg.get('chat_id', ''), key=f"tg_chat_{i}")
                    cfg['message'] = st.text_area("Сообщение", cfg.get('message', ''), height=80, key=f"tg_msg_{i}")
                    cfg['bot_token'] = st.text_input("Bot Token (опционально)", cfg.get('bot_token', ''), type="password", key=f"tg_token_{i}", help="Оставьте пустым, если токен задан в secrets")
                
                elif node_type == "sms":
                    cfg['phone_number'] = st.text_input("Номер телефона", cfg.get('phone_number', ''), key=f"sms_phone_{i}")
                    cfg['message'] = st.text_area("Сообщение", cfg.get('message', ''), height=80, key=f"sms_msg_{i}")
                    cfg['provider'] = st.selectbox("Провайдер", ["twilio", "http"], index=0 if cfg.get('provider')=='twilio' else 1, key=f"sms_prov_{i}")
                    if cfg['provider'] == 'twilio':
                        cfg['twilio_account_sid'] = st.text_input("Account SID", cfg.get('twilio_account_sid', ''), type="password", key=f"twilio_sid_{i}")
                        cfg['twilio_auth_token'] = st.text_input("Auth Token", cfg.get('twilio_auth_token', ''), type="password", key=f"twilio_token_{i}")
                        cfg['twilio_from_number'] = st.text_input("Номер отправителя", cfg.get('twilio_from_number', ''), key=f"twilio_from_{i}")
                    else:
                        cfg['api_url'] = st.text_input("API URL", cfg.get('api_url', 'https://sms.ru/sms/send'), key=f"sms_url_{i}")
                        cfg['api_key'] = st.text_input("API ключ", cfg.get('api_key', ''), type="password", key=f"sms_key_{i}")
                
                elif node_type in [NodeType.EXCEL_READ.value, NodeType.GOOGLE_SHEETS_READ.value]:
                    cfg['file_path'] = st.text_input("Путь к файлу / URL", cfg.get('file_path', ''), key=f"file_{i}")
                    cfg['sheet_name'] = st.text_input("Имя листа (опционально)", cfg.get('sheet_name', ''), key=f"sheet_{i}")
                
                elif node_type == NodeType.EXCEL_WRITE.value:
                    cfg['output_path'] = st.text_input("Путь для сохранения", cfg.get('output_path', 'output.xlsx'), key=f"out_{i}")
                    cfg['apply_formatting'] = st.checkbox("Применить форматирование", cfg.get('apply_formatting', True), key=f"fmt_{i}")
                
                elif node_type in [NodeType.HTTP_GET.value, NodeType.HTTP_POST.value]:
                    cfg['url'] = st.text_input("URL", cfg.get('url', ''), key=f"http_url_{i}")
                    if node_type == NodeType.HTTP_POST.value:
                        cfg['body'] = st.text_area("Тело запроса (JSON)", cfg.get('body', '{}'), height=80, key=f"http_body_{i}")
                
                elif node_type == NodeType.DATA_CLEAN.value:
                    cfg['rules'] = {}
                    cfg['rules']['remove_duplicates'] = st.checkbox("Удалить дубликаты", cfg.get('rules', {}).get('remove_duplicates', False), key=f"clean_dup_{i}")
                    cfg['rules']['remove_empty'] = st.checkbox("Удалить пустые строки", cfg.get('rules', {}).get('remove_empty', False), key=f"clean_empty_{i}")
                    cfg['rules']['fill_na'] = st.checkbox("Заполнить пропуски", cfg.get('rules', {}).get('fill_na', False), key=f"clean_fill_{i}")
                    if cfg['rules'].get('fill_na'):
                        cfg['rules']['fill_value'] = st.text_input("Значение для заполнения", cfg.get('rules', {}).get('fill_value', ''), key=f"clean_val_{i}")
                
                elif node_type == NodeType.PIVOT_TABLE.value:
                    cfg['index'] = st.text_input("Индекс (столбец)", cfg.get('index', ''), key=f"pivot_idx_{i}")
                    cfg['columns'] = st.text_input("Колонки (столбец)", cfg.get('columns', ''), key=f"pivot_col_{i}")
                    cfg['values'] = st.text_input("Значения (столбец)", cfg.get('values', ''), key=f"pivot_val_{i}")
                    cfg['aggfunc'] = st.selectbox("Агрегация", ['sum', 'mean', 'count', 'min', 'max'], index=0, key=f"pivot_agg_{i}")
                
                block['config'] = cfg
                
                if st.button(f"🗑️ Удалить узел", key=f"del_wf_{i}"):
                    st.session_state.workflow.pop(i)
                    st.rerun()
        
        # Кнопка запуска workflow
        if st.button("🚀 ЗАПУСТИТЬ WORKFLOW", type="primary", use_container_width=True):
            progress = st.progress(0)
            status = st.empty()
            def update_progress(idx, node):
                progress.progress((idx + 1) / len(st.session_state.workflow))
                status.text(f"🔄 {node.get('name')}")
            
            executor = WorkflowExecutor(
                st.session_state.workflow,
                api_key,
                agent_manager,
                st.session_state.table_manager
            )
            result = executor.execute(update_progress)
            progress.progress(1.0)
            if result['success']:
                st.balloons()
                st.success(f"✅ Workflow выполнен за {result['execution_time']:.1f}с")
                with st.expander("📋 Детали выполнения", expanded=True):
                    for res in result['results']:
                        # Скрываем большие объекты для читаемости
                        clean_result = {k: v for k, v in res['result'].items() if not isinstance(v, pd.DataFrame)}
                        st.json({
                            'node': res['node'],
                            'type': res['type'],
                            'result': clean_result
                        })
                if result.get('context'):
                    st.subheader("📌 Контекст после выполнения")
                    st.json({k: str(v)[:200] for k, v in result['context'].items() if not isinstance(v, pd.DataFrame)})
            else:
                st.error(f"❌ Ошибка в узле {result.get('error_node')}: {result.get('error')}")


def render_conditions_tab():
    """Рендерит вкладку условий"""
    st.subheader("🔀 Русские условия")
    st.markdown("""
<div class="info-box">
    <b>Примеры:</b><br>
    • если цена больше 1000 то отправить уведомление<br>
    • если статус равно 'успех' иначе отправить ошибку<br>
    • если количество меньше 5 то пополнить склад<br>
    • если текст содержит 'срочно' то отметить как важное<br>
    • если поле пусто то заполнить значением по умолчанию<br>
    • если сумма между 1000 и 5000 то одобрить заявку<br>
</div>
""", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        for ex in RussianConditionParser.EXAMPLES[:5]:
            st.code(f"📌 {ex}")
    with col2:
        test_cond = st.text_area("Введите своё условие", height=150, key="test_condition")
        if test_cond:
            parsed = RussianConditionParser.parse(test_cond)
            st.metric("Тип", parsed.get('type'))
            st.metric("Уверенность", f"{parsed.get('confidence', 0)*100:.0f}%")
            if parsed.get('code'):
                st.success(f"💻 Сгенерированный код:\n```python\n{parsed['code']}\n```")
            if parsed.get('errors'):
                st.error(f"Ошибки: {', '.join(parsed['errors'])}")


def render_tables_tab(api_key):
    """Рендерит вкладку таблиц + быстрое ИИ-редактирование Excel/CSV"""
    st.subheader("🗂 Таблицы + ИИ + Редактор")
    
    # ---------- БЫСТРОЕ ИИ-РЕДАКТИРОВАНИЕ ТАБЛИЦ (Excel/CSV) ----------
    st.markdown("## 🤖 Быстрое ИИ-редактирование")
    st.markdown("Загрузите файл → опишите изменения на русском → скачайте результат")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "📂 Выберите файл",
            type=['xlsx', 'xls', 'csv'],
            key="ai_upload_excel",
            help="Поддерживаются .xlsx, .xls, .csv"
        )
        file_type = "excel"
        if uploaded_file and uploaded_file.name.endswith('.csv'):
            file_type = "csv"
    with col2:
        ai_instruction = st.text_area(
            "✏️ Инструкция для ИИ",
            height=120,
            placeholder="Примеры:\n- удалить пустые строки\n- создать столбец 'Итого' = Цена * Количество\n- отсортировать по дате\n- заменить все пропуски на 0\n- отфильтровать строки, где Статус = 'Активен'",
            key="ai_instruction_quick"
        )
        run_ai = st.button("🚀 Применить ИИ", type="primary", use_container_width=True, key="run_ai_excel")
    
    if uploaded_file and run_ai:
        if not api_key:
            st.error("❌ Введите API ключ DeepSeek в боковой панели")
        elif not ai_instruction.strip():
            st.warning("⚠️ Введите инструкцию для ИИ")
        else:
            with st.spinner("🧠 ИИ анализирует и применяет изменения..."):
                result = st.session_state.table_manager.ai_edit_excel_file(
                    input_file=uploaded_file,
                    instruction=ai_instruction,
                    api_key=api_key,
                    sheet_name=0,
                    file_type=file_type
                )
            if result['success']:
                st.success(result['message'])
                if result['transformations_applied']:
                    st.markdown("**🔧 Выполненные операции:**")
                    for desc in result['transformations_applied']:
                        st.markdown(f"- {desc}")
                st.markdown("### 👁️ Превью результата (первые 10 строк)")
                st.dataframe(result['df'].head(10), use_container_width=True)
                
                # Определяем расширение для скачивания
                ext = "xlsx" if file_type == "excel" else "csv"
                mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if ext == "xlsx" else "text/csv"
                original_name = uploaded_file.name
                new_name = f"fixed_{original_name.rsplit('.',1)[0]}.{ext}"
                
                st.download_button(
                    label="📥 Скачать обработанный файл",
                    data=result['output_bytes'],
                    file_name=new_name,
                    mime=mime,
                    use_container_width=True
                )
            else:
                st.error(f"❌ {result['error']}")
    
    st.markdown("---")
    
    # ---------- УПРАВЛЕНИЕ СОХРАНЁННЫМИ ТАБЛИЦАМИ ----------
    with st.expander("📚 Сохранённые таблицы"):
        if not st.session_state.saved_tables:
            st.info("💡 Нет сохранённых таблиц")
        else:
            for table_id, df in st.session_state.saved_tables.items():
                with st.expander(f"📊 {table_id} ({df.shape[0]}×{df.shape[1]})"):
                    st.dataframe(df.head(5), use_container_width=True)
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("✏️ Открыть в редакторе", key=f"open_{table_id}"):
                            st.session_state.current_df = df.copy()
                            st.session_state.editing_table_id = table_id
                            st.rerun()
                    with col2:
                        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                            st.session_state.table_manager.write_excel(df, tmp.name)
                            with open(tmp.name, 'rb') as f:
                                st.download_button("📥 Скачать Excel", f, file_name=f"{table_id}.xlsx")
                    with col3:
                        if st.button("🗑️ Удалить", key=f"del_saved_{table_id}"):
                            del st.session_state.saved_tables[table_id]
                            save_tables_auto(st.session_state.saved_tables)
                            if st.session_state.editing_table_id == table_id:
                                st.session_state.current_df = None
                            st.rerun()
    
    # ---------- ЗАГРУЗКА НОВОЙ ТАБЛИЦЫ ДЛЯ РЕДАКТИРОВАНИЯ ----------
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📥 Загрузка новой таблицы")
        uploaded = st.file_uploader("Excel или CSV файл", type=['xlsx', 'xls', 'csv'], key="excel_upload")
        if uploaded:
            with st.spinner("Чтение файла..."):
                try:
                    if uploaded.name.endswith('.csv'):
                        df = pd.read_csv(uploaded)
                    else:
                        df = st.session_state.table_manager.read_excel(uploaded)
                    if df is not None:
                        table_id = f"table_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        st.session_state.current_df = df
                        st.session_state.editing_table_id = table_id
                        st.session_state.saved_tables[table_id] = df.copy()
                        save_tables_auto(st.session_state.saved_tables)
                        st.success(f"✅ Загружено: {df.shape[0]} строк, {df.shape[1]} колонок")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
    
    # ---------- ИНТЕРАКТИВНЫЙ РЕДАКТОР ТАБЛИЦЫ ----------
    with col2:
        if st.session_state.current_df is not None:
            st.markdown(f"### ✏️ Редактор: {st.session_state.editing_table_id}")
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


def render_images_tab(api_key):
    """Рендерит вкладку изображений с ИИ-обработкой"""
    st.subheader("🖼️ Редактор изображений с ИИ")
    image_manager = st.session_state.image_manager
    if image_manager:
        image_manager.api_key = api_key
    
    uploaded_files = st.file_uploader(
        "Выберите изображения (jpg, png, webp, bmp, gif)",
        type=list(CONFIG.SUPPORTED_IMAGE_FORMATS),
        accept_multiple_files=True,
        key="image_upload"
    )
    if uploaded_files:
        for uploaded_file in uploaded_files:
            try:
                image = Image.open(uploaded_file)
                st.session_state.uploaded_images[uploaded_file.name] = image
            except Exception as e:
                st.error(f"Ошибка загрузки {uploaded_file.name}: {e}")
        st.success(f"✅ Загружено {len(st.session_state.uploaded_images)} изображений")
    
    if st.session_state.uploaded_images:
        st.markdown("### 📸 Загруженные изображения")
        cols = st.columns(3)
        for idx, (filename, img) in enumerate(list(st.session_state.uploaded_images.items())[:6]):
            with cols[idx % 3]:
                st.image(img, caption=filename, use_container_width=True)
    
    if st.session_state.uploaded_images:
        st.markdown("---")
        st.markdown("### ✏️ Редактирование")
        selected_filename = st.selectbox("Выберите изображение для обработки", list(st.session_state.uploaded_images.keys()))
        if selected_filename:
            original = st.session_state.uploaded_images[selected_filename]
            col1, col2 = st.columns(2)
            with col1:
                st.image(original, caption="Оригинал", use_container_width=True)
            operation = st.selectbox("Операция", [op.value for op in ImageEditOperation])
            if st.button("🚀 Применить", type="primary"):
                with st.spinner("Обработка..."):
                    processed = image_manager._apply_operation(
                        original, ImageEditOperation(operation), {'api_key': api_key}
                    )
                    output_filename = f"processed_{selected_filename}"
                    st.session_state.processed_images[output_filename] = processed
                    st.success("✅ Обработано!")
                    with col2:
                        st.image(processed, caption="Результат", use_container_width=True)
                    from utils import IMAGES_DIR
                    save_path = IMAGES_DIR / output_filename
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    processed.save(save_path)
                    st.success(f"💾 Сохранено в {save_path}")


def render_help_tab():
    """Рендерит вкладку справки"""
    st.subheader("📖 Справка и документация")
    st.markdown("""
## 🚀 Быстрый старт
1. **Получите API ключ DeepSeek**: [platform.deepseek.com](https://platform.deepseek.com)
2. **Вставьте ключ** в боковой панели
3. **Выберите или создайте агента** для диалога
4. **Начните диалог** или постройте workflow автоматизации

---

## 🧠 ИИ Агенты
- **Обучение на примерах** – добавляйте пары вопрос-ответ для улучшения ответов
- **Память** – сохраняйте факты, которые агент будет использовать в диалогах
- **Аналитика** – отслеживайте прогресс обучения и успешность ответов

---

## 🤖 Workflow (Автоматизация)
- **Строите последовательность блоков** перетаскиванием (кнопками)
- **Поддерживаемые блоки**:
  - Чтение/запись Excel и Google Sheets
  - Вызов DeepSeek AI с системными промптами
  - Условия на русском языке (если... то... иначе)
  - Циклы по спискам
  - Отправка Email, Telegram, **SMS** (через Twilio или HTTP провайдера)
  - Вызов обученных ИИ агентов
  - Очистка данных, сводные таблицы, HTTP запросы
- **Узлы могут иметь условия выполнения** – например, отправлять SMS только если статус "успех"

---

## 🗂 Таблицы
- **ИИ-редактирование** – опишите изменения на русском, ИИ применит их
- **Интерактивный редактор** – изменяйте данные прямо в браузере
- **Автосохранение** – все изменения сохраняются

---

## 🖼️ Изображения
- **Удаление фона** (требуется `rembg`)
- **Удаление водяных знаков через ИИ** (DeepSeek)
- **Ресайз, поворот, фильтры, текст** – стандартные операции
- **Пакетная обработка** – для нескольких файлов

---

## 📱 Мобильная версия
Приложение адаптировано для экранов менее 768px. Кнопки и карточки корректно отображаются на смартфонах.

---

## 🔧 Установка дополнительных зависимостей
```bash
# Для SMS через Twilio
pip install twilio

# Для удаления фона
pip install rembg

# Для голосового ввода/вывода
pip install SpeechRecognition gTTS
