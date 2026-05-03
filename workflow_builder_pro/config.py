"""
Конфигурация приложения, ENUMs и константы
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple
from enum import Enum, auto


class NodeType(Enum):
    GOOGLE_SHEETS_READ = "google_sheets_read"
    GOOGLE_SHEETS_WRITE = "google_sheets_write"
    EXCEL_READ = "excel_read"
    EXCEL_WRITE = "excel_write"
    EXCEL_FORMAT = "excel_format"
    EXCEL_CHART = "excel_chart"
    DEEPSEEK_AI = "deepseek"
    CONDITION = "condition"
    LOOP = "loop"
    HTTP_GET = "http_get"
    HTTP_POST = "http_post"
    EMAIL = "email"
    TELEGRAM = "telegram"
    AI_AGENT = "ai_agent"
    DATA_CLEAN = "data_clean"
    PIVOT_TABLE = "pivot_table"
    FILTER = "filter"
    TRANSFORM = "transform"


class ConditionType(Enum):
    GREATER = "greater"
    LESS = "less"
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    BETWEEN = "between"
    IN_LIST = "in_list"
    CUSTOM = "custom"


class MemoryImportance(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    PAUSED = "paused"


class ImageEditOperation(Enum):
    REMOVE_BACKGROUND = "remove_background"
    REMOVE_WATERMARK = "remove_watermark"
    RESIZE = "resize"
    CROP = "crop"
    ROTATE = "rotate"
    ENHANCE = "enhance"
    FILTER = "filter"
    ADD_TEXT = "add_text"
    ADD_WATERMARK = "add_watermark"
    CONVERT_FORMAT = "convert_format"


@dataclass
class AppConfig:
    APP_TITLE: str = "Workflow Builder Pro -- Голосовой помощник"
    APP_ICON: str = "🧠"
    APP_VERSION: str = "9.3.0"
    
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    API_TIMEOUT: int = 120
    MAX_TOKENS: int = 4096
    
    MAX_ROWS_GOOGLE: int = 10000
    MAX_ROWS_EXCEL: int = 100000
    SUPPORTED_EXCEL_FORMATS: Tuple[str, ...] = ("xlsx", "xlsm", "xls")
    DEFAULT_SHEET_NAME: str = "Sheet1"
    
    MAX_IMAGE_UPLOAD: int = 10000
    SUPPORTED_IMAGE_FORMATS: Tuple[str, ...] = ("jpg", "jpeg", "png", "webp", "bmp", "gif")
    MAX_IMAGE_SIZE_MB: int = 50
    
    CACHE_TTL_SECONDS: int = 300
    DEFAULT_LANGUAGE: str = "ru"
    MOBILE_BREAKPOINT: int = 768
    ITEMS_PER_PAGE: int = 10
    
    COLORS: Dict[str, str] = field(default_factory=lambda: {
        'primary': '#6974dc',
        'primary_dark': '#764ba2',
        'success': '#00ff88',
        'error': '#ff4444',
        'warning': '#ffa500',
        'accent': '#4ECDC4',
        'dark_bg': '#1a1a2e',
        'dark_bg_2': '#16213e',
        'card_bg': '#ffffff'
    })


CONFIG = AppConfig()
