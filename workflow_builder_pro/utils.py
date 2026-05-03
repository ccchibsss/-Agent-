# utils.py
import json
import logging
import time
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple
from io import BytesIO
from PIL import Image
import streamlit as st

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Автосохранение
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

# Функции автосохранения
def save_workflow_auto(workflow: List[Dict]):
    try:
        with open(WORKFLOW_FILE, 'w', encoding='utf-8') as f:
            json.dump(workflow, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Не удалось сохранить workflow: {e}")

def load_workflow_auto() -> List[Dict]:
    if WORKFLOW_FILE.exists():
        try:
            with open(WORKFLOW_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось загрузить workflow: {e}")
    return []

def save_agents_auto(agents_data: Dict):
    try:
        with open(AGENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(agents_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Не удалось сохранить агентов: {e}")

def load_agents_auto() -> Optional[Dict]:
    if AGENTS_FILE.exists():
        try:
            with open(AGENTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Не удалось загрузить агентов: {e}")
    return None

# Декораторы
def cache_result(ttl_seconds: int = 300):
    def decorator(func: Callable):
        cache: Dict[str, Tuple[Any, float]] = {}
        def wrapper(*args, **kwargs) -> Any:
            key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            current_time = time.time()
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < ttl_seconds:
                    return result
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            return result
        return wrapper
    return decorator

def handle_errors(default_return: Any = None):
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

def format_bytes(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def image_to_base64(image: Image.Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()
