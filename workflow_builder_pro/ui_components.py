# ui_components.py - Все UI компоненты для Streamlit (ПОЛНАЯ ВЕРСИЯ)
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
    """Рендерит вкладку workflow"""
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
                if block['type'] == NodeType.DEEPSEEK_AI.value:
                    cfg['system_prompt'] = st.text_area("Системный", cfg.get('system_prompt', ''), height=60, key=f"ai_sys_{i}")
                    cfg['user_prompt'] = st.text_area("Запрос", cfg.get('user_prompt', ''), height=60, key=f"ai_user_{i}")
                elif block['type'] == NodeType.CONDITION.value:
                    cfg['condition'] = st.text_area("Условие", cfg.get('condition', ''), height=60, key=f"cond_{i}")
                    if cfg.get('condition'):
                        parsed = RussianConditionParser.parse(cfg['condition'])
                        if parsed.get('code'):
                            st.code(parsed['code'], language='python')
                elif block['type'] == NodeType.AI_AGENT.value:
                    agent = agent_manager.agents.get(block.get('agent_id'))
                    if agent:
                        st.info(f"🧠 {agent.name}")
                    cfg['question'] = st.text_area("Вопрос", cfg.get('question', ''), height=60, key=f"agent_q_{i}")
                block['config'] = cfg
                if st.button(f"🗑️ Удалить", key=f"del_wf_{i}"):
                    st.session_state.workflow.pop(i)
                    st.rerun()
        
        if st.button("🚀 ЗАПУСТИТЬ", type="primary", use_container_width=True):
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
                st.success(f"✅ Успешно за {result['execution_time']:.1f}с")
                with st.expander("📋 Результаты", expanded=True):
                    for res in result['results']:
                        st.json({k: v for k, v in res['result'].items() if k != 'df'})
            else:
                st.error(f"❌ Ошибка: {result.get('error')}")


def render_conditions_tab():
    """Рендерит вкладку условий"""
    st.subheader("🔀 Русские условия")
    st.markdown("""
<div class="info-box">
    <b>Примеры:</b><br>
    • если цена больше 1000 то отправить уведомление<br>
    • если статус равно 'успех' иначе отправить ошибку<br>
</div>
""", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        for ex in RussianConditionParser.EXAMPLES[:5]:
            st.code(f"📌 {ex}")
    with col2:
        test_cond = st.text_area("Введите условие", height=150, key="test_condition")
        if test_cond:
            parsed = RussianConditionParser.parse(test_cond)
            st.metric("Тип", parsed.get('type'))
            st.metric("Уверенность", f"{parsed.get('confidence', 0)*100:.0f}%")
            if parsed.get('code'):
                st.success(f"💻 `{parsed['code']}`")


def render_tables_tab(api_key):
    """Рендерит вкладку таблиц"""
    st.subheader("🗂 Таблицы + ИИ + Редактор")
    
    with st.expander("📚 Сохранённые таблицы"):
        if not st.session_state.saved_tables:
            st.info("💡 Нет сохранённых таблиц")
        else:
            for table_id, df in st.session_state.saved_tables.items():
                with st.expander(f"📊 {table_id} ({df.shape[0]}×{df.shape[1]})"):
                    st.dataframe(df.head(5), use_container_width=True)
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("✏️ Открыть", key=f"open_{table_id}"):
                            st.session_state.current_df = df.copy()
                            st.session_state.editing_table_id = table_id
                            st.rerun()
                    with col2:
                        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                            st.session_state.table_manager.write_excel(df, tmp.name)
                            with open(tmp.name, 'rb') as f:
                                st.download_button("📥 Скачать", f, file_name=f"{table_id}.xlsx")
                    with col3:
                        if st.button("🗑️ Удалить", key=f"del_saved_{table_id}"):
                            del st.session_state.saved_tables[table_id]
                            save_tables_auto(st.session_state.saved_tables)
                            if st.session_state.editing_table_id == table_id:
                                st.session_state.current_df = None
                            st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📥 Загрузка данных")
        uploaded = st.file_uploader("Excel файл", type=['xlsx', 'xls', 'csv'], key="excel_upload")
        if uploaded:
            with st.spinner("Чтение файла..."):
                try:
                    if uploaded.name.endswith('.csv'):
                        df = pd.read_csv(uploaded)
                    else:
                        df = st.session_state.table_manager.read_excel(uploaded)
                    if df is not None:
                        table_id = f"ex_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        st.session_state.current_df = df
                        st.session_state.editing_table_id = table_id
                        st.session_state.saved_tables[table_id] = df.copy()
                        save_tables_auto(st.session_state.saved_tables)
                        st.success(f"✅ Загружено: {df.shape}")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
    
    with col2:
        if st.session_state.current_df is not None:
            st.markdown(f"### 📊 Редактор: {st.session_state.editing_table_id}")
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
    """Рендерит вкладку изображений"""
    st.subheader("🖼️ Редактор изображений с ИИ")
    image_manager = st.session_state.image_manager
    if image_manager:
        image_manager.api_key = api_key
    
    uploaded_files = st.file_uploader(
        "Выберите изображения",
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
                st.error(f"Ошибка: {e}")
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
        selected_filename = st.selectbox("Выберите изображение", list(st.session_state.uploaded_images.keys()))
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
    st.subheader("📖 Справка")
    st.markdown("""
## 🚀 Быстрый старт
1. **Получите API ключ**: [platform.deepseek.com](https://platform.deepseek.com)
2. **Вставьте ключ** в боковой панели
3. **Выберите или создайте агента**
4. **Начните диалог** или постройте workflow
---
## 🖼️ Работа с изображениями
- 📥 **Массовая загрузка** - до 10,000+ изображений
- 🎨 **Удаление фона** - автоматическое (rembg)
- 💧 **Удаление водяных знаков через ИИ** - DeepSeek API
- 💬 **Добавление текста** - водяные знаки
- 💾 **Сохранение результатов** - с тем же именем
---
## 🗂 Редактирование таблиц
- ✏️ **Полноценный редактор** - изменяйте данные
- 💾 **Автосохранение** - изменения сохраняются
- 📥 **Экспорт** - скачивайте в Excel
- 🤖 **ИИ-трансформация** - описывайте изменения
---
*Workflow Builder Pro v9.3 • Монопоточная версия • © 2026*
""")
