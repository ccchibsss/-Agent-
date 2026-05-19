from dataclasses import dataclass, field
from typing import Dict, Tuple
from pathlib import Path

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


@dataclass
class AppConfig:
    APP_TITLE: str = "Workflow Builder Pro – Голосовой помощник"
    APP_ICON: str = "🧠"
    APP_VERSION: str = "9.2.0"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    API_TIMEOUT: int = 120
    MAX_TOKENS: int = 4096
    MAX_ROWS_GOOGLE: int = 10000
    MAX_ROWS_EXCEL: int = 100000
    SUPPORTED_EXCEL_FORMATS: Tuple[str, ...] = ("xlsx", "xlsm", "xls", "csv")
    DEFAULT_SHEET_NAME: str = "Sheet1"
    MAX_IMAGE_UPLOAD: int = 10000
    SUPPORTED_IMAGE_FORMATS: Tuple[str, ...] = ("jpg", "jpeg", "png", "webp", "bmp", "gif")
    MAX_IMAGE_SIZE_MB: int = 50
    CACHE_TTL_SECONDS: int = 300
    DEFAULT_LANGUAGE: str = "ru"
    MOBILE_BREAKPOINT: int = 768
    ITEMS_PER_PAGE: int = 10
    COLORS: Dict[str, str] = field(default_factory=lambda: {
        'primary': '#6974dc', 'primary_dark': '#764ba2',
        'success': '#00ff88', 'error': '#ff4444',
        'warning': '#ffa500', 'accent': '#4ECDC4',
        'dark_bg': '#1a1a2e', 'dark_bg_2': '#16213e',
        'card_bg': '#ffffff'
    })
    AGENTS_GSHEET_URL: str = ""


CONFIG = AppConfig()
