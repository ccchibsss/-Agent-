"""
Конфигурация приложения, ENUMs и константы
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional
from enum import Enum, auto


class NodeType(Enum):
    """Типы узлов workflow"""
    # Чтение/запись данных
    GOOGLE_SHEETS_READ = "google_sheets_read"
    GOOGLE_SHEETS_WRITE = "google_sheets_write"
    EXCEL_READ = "excel_read"
    EXCEL_WRITE = "excel_write"
    EXCEL_FORMAT = "excel_format"
    EXCEL_CHART = "excel_chart"
    
    # ИИ и обработка
    DEEPSEEK_AI = "deepseek"
    AI_AGENT = "ai_agent"
    DATA_CLEAN = "data_clean"
    PIVOT_TABLE = "pivot_table"
    FILTER = "filter"
    TRANSFORM = "transform"
    
    # Логика и управление
    CONDITION = "condition"
    LOOP = "loop"
    BRANCH = "branch"
    SCHEDULE = "schedule"
    
    # Сетевые операции
    HTTP_GET = "http_get"
    HTTP_POST = "http_post"
    WEBHOOK = "webhook"
    
    # Уведомления
    EMAIL = "email"
    TELEGRAM = "telegram"
    SMS = "sms"
    PUSH_NOTIFICATION = "push_notification"
    
    # Файлы и медиа
    FILE_UPLOAD = "file_upload"
    IMAGE_PROCESS = "image_process"


class ConditionType(Enum):
    """Типы условий для парсинга"""
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
    VARIABLE = "variable"
    PREVIOUS_SUCCESS = "previous_success"


class MemoryImportance(Enum):
    """Уровни важности памяти агента"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowStatus(Enum):
    """Статусы выполнения workflow"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    PAUSED = "paused"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class ImageEditOperation(Enum):
    """Операции редактирования изображений"""
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
    OCR_EXTRACT = "ocr_extract"
    FACE_BLUR = "face_blur"


class SMSProvider(Enum):
    """Провайдеры SMS"""
    TWILIO = "twilio"
    SMSRU = "smsru"
    CUSTOM_WEBHOOK = "custom_webhook"
    SIMULATED = "simulated"


class EmailProvider(Enum):
    """Провайдеры email"""
    SMTP = "smtp"
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"
    CUSTOM = "custom"


class TriggerType(Enum):
    """Типы триггеров для автоматизации"""
    MANUAL = "manual"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    FILE_CHANGE = "file_change"
    DATA_UPDATE = "data_update"
    CONDITION_MET = "condition_met"


class RetryStrategy(Enum):
    """Стратегии повторных попыток"""
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


@dataclass
class APIConfig:
    """Настройки API"""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    API_TIMEOUT: int = 120
    MAX_TOKENS: int = 4096
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    
    # SMS провайдеры
    TWILIO_API_URL: str = "https://api.twilio.com/2010-04-01/Accounts"
    SMSRU_API_URL: str = "https://sms.ru/sms/send"
    
    # Email настройки
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    
    # Telegram
    TELEGRAM_BOT_URL: str = "https://api.telegram.org/bot"


@dataclass
class TableConfig:
    """Настройки работы с таблицами"""
    MAX_ROWS_GOOGLE: int = 10000
    MAX_ROWS_EXCEL: int = 100000
    SUPPORTED_EXCEL_FORMATS: Tuple[str, ...] = ("xlsx", "xlsm", "xls", "csv")
    DEFAULT_SHEET_NAME: str = "Sheet1"
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 300


@dataclass
class ImageConfig:
    """Настройки работы с изображениями"""
    MAX_IMAGE_UPLOAD: int = 100
    SUPPORTED_IMAGE_FORMATS: Tuple[str, ...] = ("jpg", "jpeg", "png", "webp", "bmp", "gif")
    MAX_IMAGE_SIZE_MB: int = 50
    MAX_BATCH_SIZE: int = 50
    COMPRESSION_QUALITY: int = 85


@dataclass
class WorkflowConfig:
    """Настройки workflow"""
    MAX_NODES: int = 100
    MAX_EXECUTION_TIME_SECONDS: int = 3600
    DEFAULT_RETRY_COUNT: int = 3
    ENABLE_CONDITIONAL_BRANCHING: bool = True
    ENABLE_PARALLEL_EXECUTION: bool = False
    LOG_LEVEL: str = "INFO"


@dataclass
class UIConfig:
    """Настройки интерфейса"""
    DEFAULT_LANGUAGE: str = "ru"
    MOBILE_BREAKPOINT: int = 768
    ITEMS_PER_PAGE: int = 10
    THEME: str = "light"
    ENABLE_VOICE: bool = True
    ENABLE_AUTO_SAVE: bool = True
    AUTO_SAVE_INTERVAL_SECONDS: int = 30


@dataclass
class AppConfig:
    """Глобальная конфигурация приложения"""
    # Основное
    APP_TITLE: str = "Workflow Builder Pro — Голосовой помощник"
    APP_ICON: str = "🧠"
    APP_VERSION: str = "9.3.1"
    APP_DESCRIPTION: str = "Платформа для создания ИИ-агентов и автоматизации рабочих процессов"
    
    # Пути и файлы
    DATA_DIR: str = ".workflow_data"
    LOG_FILE: str = "app.log"
    
    # Подконфигурации
    api: APIConfig = field(default_factory=APIConfig)
    tables: TableConfig = field(default_factory=TableConfig)
    images: ImageConfig = field(default_factory=ImageConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    # Цветовая схема
    COLORS: Dict[str, str] = field(default_factory=lambda: {
        'primary': '#6974dc',
        'primary_dark': '#764ba2',
        'primary_light': '#a3b1ff',
        'success': '#00ff88',
        'success_dark': '#00cc6a',
        'error': '#ff4444',
        'error_dark': '#cc0000',
        'warning': '#ffa500',
        'warning_dark': '#cc8400',
        'accent': '#4ECDC4',
        'accent_dark': '#3ba8a0',
        'dark_bg': '#1a1a2e',
        'dark_bg_2': '#16213e',
        'card_bg': '#ffffff',
        'card_bg_dark': '#2a2a4e',
        'text_primary': '#000000',
        'text_secondary': '#4a4a6a',
        'text_on_dark': '#ffffff',
        'border_light': '#e0e0e0',
        'border_dark': '#404060',
    })
    
    # Градиенты
    GRADIENTS: Dict[str, str] = field(default_factory=lambda: {
        'primary': 'linear-gradient(135deg, #6974dc 0%, #764ba2 100%)',
        'success': 'linear-gradient(135deg, #00ff88 0%, #00cc6a 100%)',
        'warning': 'linear-gradient(135deg, #ffa500 0%, #cc8400 100%)',
        'error': 'linear-gradient(135deg, #ff4444 0%, #cc0000 100%)',
        'accent': 'linear-gradient(135deg, #4ECDC4 0%, #3ba8a0 100%)',
    })
    
    # Иконки для типов узлов
    NODE_ICONS: Dict[str, str] = field(default_factory=lambda: {
        'google_sheets_read': '📖',
        'google_sheets_write': '📗',
        'excel_read': '📊',
        'excel_write': '💾',
        'deepseek': '🧠',
        'condition': '🔀',
        'loop': '🔄',
        'http_get': '🌐',
        'http_post': '📤',
        'email': '📧',
        'telegram': '✈️',
        'sms': '📱',
        'ai_agent': '🤖',
        'data_clean': '🧹',
        'pivot_table': '📈',
        'filter': '🔍',
        'transform': '⚙️',
        'webhook': '🔗',
        'schedule': '⏰',
        'file_upload': '📁',
        'image_process': '🖼️',
    })
    
    # Поддерживаемые языки
    SUPPORTED_LANGUAGES: Tuple[str, ...] = ("ru", "en", "zh", "es", "fr", "de")
    
    # Ограничения
    MAX_AGENTS: int = 50
    MAX_TRAINING_EXAMPLES: int = 1000
    MAX_MEMORY_ITEMS: int = 500
    MAX_WORKFLOW_HISTORY: int = 100
    
    # Безопасность
    ALLOWED_FILE_EXTENSIONS: Tuple[str, ...] = ("xlsx", "xls", "csv", "json", "txt", "pdf")
    MAX_FILE_SIZE_MB: int = 100
    ENABLE_SANDBOX: bool = True
    DANGEROUS_OPERATIONS: Tuple[str, ...] = (
        'os.system', 'subprocess', '__import__', 'eval(', 'exec(', 
        'open(', 'file(', 'compile(', 'getattr(', 'setattr('
    )


# Глобальный экземпляр конфигурации
CONFIG = AppConfig()


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_node_icon(node_type: str) -> str:
    """Возвращает иконку для типа узла"""
    return CONFIG.NODE_ICONS.get(node_type, '📦')


def get_status_color(status: str) -> str:
    """Возвращает цвет для статуса"""
    colors = {
        'pending': CONFIG.COLORS['warning'],
        'running': CONFIG.COLORS['accent'],
        'success': CONFIG.COLORS['success'],
        'error': CONFIG.COLORS['error'],
        'paused': CONFIG.COLORS['text_secondary'],
        'skipped': CONFIG.COLORS['text_secondary'],
    }
    return colors.get(status, CONFIG.COLORS['text_primary'])


def validate_api_key(api_key: Optional[str]) -> bool:
    """Проверяет валидность API ключа"""
    if not api_key:
        return False
    # DeepSeek ключи обычно начинаются с 'sk-'
    return api_key.startswith('sk-') and len(api_key) >= 32


def format_duration(seconds: float) -> str:
    """Форматирует длительность в человекочитаемый вид"""
    if seconds < 60:
        return f"{seconds:.1f}с"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}мин"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}ч"


def sanitize_filename(filename: str) -> str:
    """Очищает имя файла от опасных символов"""
    import re
    # Оставляем только безопасные символы
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Убираем пробелы в начале/конце
    return cleaned.strip()
