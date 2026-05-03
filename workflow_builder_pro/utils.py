"""
Утилиты, декораторы, автосохранение и вспомогательные функции
"""
import json
import logging
import time
import base64
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple
from io import BytesIO
from datetime import datetime

import streamlit as st
from PIL import Image

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Автосохранение - пути к файлам
DATA_DIR = Path(__file__).parent / ".workflow_data"
DATA_DIR.mkdir(exist_ok=True)

IMAGES_DIR = DATA_DIR / "processed_images"
IMAGES_DIR.mkdir(exist_ok=True)

WORKFLOW_FILE = DATA_DIR / "workflow.json"
AGENTS_FILE = DATA_DIR / "agents.json"
MESSAGES_FILE = DATA_DIR / "messages.json"
HISTORY_FILE = DATA_DIR / "history.json"
TABLES_FILE = DATA_DIR / "tables.json"
IMAGES_METADATA_FILE = DATA_DIR / "images_metadata.json"


# ========== ФУНКЦИИ АВТОСОХРАНЕНИЯ ==========

def save_workflow_auto(workflow: List[Dict]):
    """Автосохранение workflow в локальный файл"""
    try:
        with open(WORKFLOW_FILE, 'w', encoding='utf-8') as f:
            json.dump(workflow, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Не удалось сохранить workflow: {e}")


def load_workflow_auto() -> List[Dict]:
    """Автозагрузка workflow из локального файла"""
    if WORKFLOW_FILE.exists():
        try:
            with open(WORKFLOW_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось загрузить workflow: {e}")
    return []


def save_agents_auto(agents_data: Dict):
    """Автосохранение агентов"""
    try:
        with open(AGENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(agents_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Не удалось сохранить агентов: {e}")


def load_agents_auto() -> Optional[Dict]:
    """Автозагрузка агентов"""
    if AGENTS_FILE.exists():
        try:
            with open(AGENTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось загрузить агентов: {e}")
    return None


def save_messages_auto(messages: List[Dict]):
    """Автосохранение сообщений чата"""
    try:
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Не удалось сохранить сообщения: {e}")


def load_messages_auto() -> List[Dict]:
    """Автозагрузка сообщений чата"""
    if MESSAGES_FILE.exists():
        try:
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось загрузить сообщения: {e}")
    return []


def save_history_auto(history: List[Dict]):
    """Автосохранение истории"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Не удалось сохранить историю: {e}")


def load_history_auto() -> List[Dict]:
    """Автозагрузка истории"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось загрузить историю: {e}")
    return []


def save_tables_auto(tables_data: Dict):
    """Автосохранение таблиц"""
    try:
        with open(TABLES_FILE, 'w', encoding='utf-8') as f:
            serializable = {}
            for key, value in tables_data.items():
                if hasattr(value, 'to_dict'):
                    serializable[key] = {
                        'data': value.to_dict('records'),
                        'columns': list(value.columns),
                        'created_at': datetime.now().isoformat()
                    }
                else:
                    serializable[key] = value
            json.dump(serializable, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Не удалось сохранить таблицы: {e}")


def load_tables_auto() -> Dict:
    """Автозагрузка таблиц"""
    if TABLES_FILE.exists():
        try:
            with open(TABLES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            result = {}
            for key, value in data.items():
                if isinstance(value, dict) and 'data' in value:
                    import pandas as pd
                    result[key] = pd.DataFrame(value['data'])
                else:
                    result[key] = value
            return result
        except Exception as e:
            logger.warning(f"Не удалось загрузить таблицы: {e}")
    return {}


def save_images_metadata_auto(metadata: Dict):
    """Автосохранение метаданных изображений"""
    try:
        with open(IMAGES_METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Не удалось сохранить метаданные изображений: {e}")


def load_images_metadata_auto() -> Dict:
    """Автозагрузка метаданных изображений"""
    if IMAGES_METADATA_FILE.exists():
        try:
            with open(IMAGES_METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось загрузить метаданные изображений: {e}")
    return {}


# ========== ДЕКОРАТОРЫ ==========

def cache_result(ttl_seconds: int = 300):
    """Декоратор для кэширования результатов функций"""
    def decorator(func: Callable):
        cache: Dict[str, Tuple[Any, float]] = {}
        
        def wrapper(*args, **kwargs) -> Any:
            key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            current_time = time.time()
            
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < ttl_seconds:
                    logger.debug(f"Cache hit: {key}")
                    return result
            
            logger.debug(f"Cache miss: {key}, executing function")
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            return result
        
        return wrapper
    return decorator


def handle_errors(default_return: Any = None):
    """Декоратор для обработки исключений с логированием"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Ошибка в {func.__name__}: {str(e)}", exc_info=True)
                st.error(f"⚠️ {func.__name__}: {str(e)}")
                return default_return
        return wrapper
    return decorator


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def format_bytes(size: int) -> str:
    """Форматирует размер в байтах в человекочитаемый вид"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def image_to_base64(image: Image.Image) -> str:
    """Конвертирует PIL Image в base64 строку"""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def base64_to_image(base64_string: str) -> Image.Image:
    """Конвертирует base64 строку в PIL Image"""
    image_data = base64.b64decode(base64_string)
    return Image.open(BytesIO(image_data))


def initialize_session_state():
    """Инициализирует session_state с автозагрузкой данных"""
    defaults = {
        'agent_manager': None,
        'workflow': [],
        'agent_messages': [],
        'history': [],
        'analytics': {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0
        },
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
    
    # Автозагрузка данных при первом запуске
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
