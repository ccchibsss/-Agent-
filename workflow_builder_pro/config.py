"""
Конфигурация приложения, ENUMs и константы
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional
from enum import Enum


class NodeType(Enum):
    """Типы узлов workflow"""
    # Данные
    GOOGLE_SHEETS_READ = "google_sheets_read"
    GOOGLE_SHEETS_WRITE = "google_sheets_write"
    EXCEL_READ = "excel_read"
    EXCEL_WRITE = "excel_write"
    
    # ИИ и логика
    DEEPSEEK_AI = "deepseek"
    AI_AGENT = "ai_agent"
    DATA_CLEAN = "data_clean"
    PIVOT_TABLE = "pivot_table"
    CONDITION = "condition"
    LOOP = "loop"
    TRANSFORM = "transform"
    
    # Связь и API (Добавлены новые типы)
    HTTP_GET = "http_get"
    HTTP_POST = "http_post"
    EMAIL = "email"
    TELEGRAM = "telegram"
    SMS = "sms"          
    WEBHOOK = "webhook" 
    
    # Система
    SCHEDULE = "schedule"


class ConditionType(Enum):
    """Типы условий"""
    GREATER = "greater"
    LESS = "less"
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    CONTAINS = "contains"
    CUSTOM = "custom"
    VARIABLE = "variable"


class WorkflowStatus(Enum):
    """Статусы workflow"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


class ImageEditOperation(Enum):
    """Операции с изображениями"""
    REMOVE_BACKGROUND = "remove_background"
    REMOVE_WATERMARK = "remove_watermark"
    RESIZE = "resize"
    CROP = "crop"
    ROTATE = "rotate"
    ENHANCE = "enhance"
    CONVERT_FORMAT = "convert_format"


@dataclass
class AppConfig:
    """Глобальная конфигурация"""
    APP_TITLE: str = "Workflow Builder Pro"
    APP_ICON: str = ""
    APP_VERSION: str = "9.4.0"
    
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    API_TIMEOUT: int = 120
    MAX_TOKENS: int = 4096
    
    MAX_ROWS_GOOGLE: int = 10000
    MAX_ROWS_EXCEL: int = 100000
    SUPPORTED_EXCEL_FORMATS: Tuple[str, ...] = ("xlsx", "xls", "csv")
    
    COLORS: Dict[str, str] = field(default_factory=lambda: {
        'primary': '#6974dc', 'primary_dark': '#764ba2',
        'success': '#00ff88', 'error': '#ff4444',
        'warning': '#ffa500', 'accent': '#4ECDC4',
        'dark_bg': '#1a1a2e', 'card_bg': '#ffffff'
    })

CONFIG = AppConfig()
