"""
CSS стили приложения.
"""

def get_app_styles() -> str:
    """Возвращает CSS стили приложения"""
    return """
    <style>
        /* ========== БАЗОВЫЕ СТИЛИ ========== */
        :root {
            --primary-gradient: linear-gradient(135deg, #6974dc 0%, #764ba2 100%);
            --dark-gradient: linear-gradient(135deg, #ffffff 0%, #f0f2f6 100%);
            --success-color: #00ff88;
            --error-color: #ff4444;
            --warning-color: #ffa500;
            --accent-color: #4ECDC4;
            --card-bg: #ffffff;
            --text-on-dark: #000000;
            --text-on-light: #000000;
            --text-secondary: #4a4a6a;
            --border-light: #e0e0e0;
            --border-dark: #e0e0e0;
            --block-bg: #ffffff;
        }
        
        /* ========== БАЗОВЫЙ ТЕКСТ ========== */
        body, .stApp, .main, .block-container {
            color: var(--text-on-light) !important;
            background-color: #f0f2f6 !important;
        }
        
        p, span, div, li, a, label, h1, h2, h3, h4, h5, h6 {
            color: var(--text-on-light) !important;
        }
        
        strong, b {
            color: var(--text-on-light) !important;
            font-weight: 600 !important;
        }
        
        small, .caption {
            color: var(--text-secondary) !important;
        }
        
        /* ========== ПОЛЯ ВВОДА ========== */
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stSelectbox select,
        .stMultiselect select,
        input[type="text"],
        input[type="number"],
        input[type="password"],
        textarea {
            color: #000000 !important;
            background-color: #ffffff !important;
            border: none !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
        }
        
        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder,
        input::placeholder,
        textarea::placeholder {
            color: #888888 !important;
            opacity: 1 !important;
        }
        
        .stTextInput input:focus,
        .stTextArea textarea:focus,
        input:focus,
        textarea:focus {
            box-shadow: 0 2px 12px rgba(105, 116, 220, 0.3) !important;
            outline: none !important;
        }
        
        /* ========== MARKDOWN И СООБЩЕНИЯ ЧАТА ========== */
        .stMarkdown p, .stMarkdown div, .stMarkdown span, .stMarkdown label {
            color: #000000 !important;
        }
        
        .stMarkdown strong, .stMarkdown b {
            color: #000000 !important;
        }
        
        .stChatMessage {
            border: none !important;
            border-radius: 12px !important;
            padding: 0.8rem !important;
            margin: 0.5rem 0 !important;
            background-color: #ffffff !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
        }
        
        .stChatMessage p, .stChatMessage div, .stChatMessage span {
            color: #000000 !important;
        }
        
        /* ========== ЭЛЕМЕНТЫ УПРАВЛЕНИЯ ========== */
        .stButton button {
            border-radius: 12px !important; 
            font-weight: 600 !important;
            transition: all 0.2s ease;
            border: none !important;
            background-color: #ffffff !important;
            color: #000000 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
        }
        
        .stButton button:hover { 
            transform: scale(1.03); 
            box-shadow: 0 4px 12px rgba(0,0,0,0.12) !important;
            background-color: #f8f9fa !important;
        }
        
        .stButton button:active {
            transform: scale(0.98);
        }
        
        /* ========== БОКОВАЯ ПАНЕЛЬ ========== */
        [data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border: none !important;
            box-shadow: 2px 0 10px rgba(0,0,0,0.05) !important;
        }
        
        [data-testid="stSidebar"] .stButton button {
            border: none !important;
            background-color: #ffffff !important;
            color: #000000 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
        }
        
        [data-testid="stSidebar"] .stButton button:hover {
            background-color: #f0f2f6 !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.12) !important;
        }
        
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4,
        [data-testid="stSidebar"] h5,
        [data-testid="stSidebar"] h6,
        [data-testid="stSidebar"] div {
            color: #000000 !important;
        }
        
        [data-testid="stSidebar"] div[data-testid="stExpander"] details {
            background-color: #ffffff !important;
            border: none !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
        }
        
        [data-testid="stSidebar"] div[data-testid="stExpander"] summary {
            color: #000000 !important;
            font-weight: 600 !important;
        }
        
        [data-testid="stSidebar"] div[data-testid="stExpander"] details * {
            color: #000000 !important;
        }
        
        /* ========== ЗАГОЛОВОК ========== */
        .main-header {
            background: var(--primary-gradient);
            padding: 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
            text-align: center;
            animation: fadeIn 1s ease-in;
            box-shadow: 0 10px 40px rgba(105, 116, 220, 0.3);
            border: none !important;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .main-header h1 { 
            color: white !important; 
            margin: 0; 
            font-size: 2.5rem; 
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .main-header p { 
            color: rgba(255,255,255,0.95) !important; 
            margin: 0.5rem 0 0 0; 
            font-size: 1.1rem;
        }
        
        .version-badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.85rem;
            margin-top: 0.5rem;
            color: white !important;
            border: none !important;
        }
        
        /* ========== КАРТОЧКИ АГЕНТОВ — БЕЛЫЙ ФОН ========== */
        .agent-card {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border-radius: 15px; 
            padding: 1rem; 
            margin: 0.5rem 0;
            border: none !important;
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
            overflow: hidden;
            color: #000000 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
        }
        
        .agent-card *, .agent-card p, .agent-card span, .agent-card div {
            color: #000000 !important;
        }
        
        .agent-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(135deg, rgba(105, 116, 220, 0.05), transparent);
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .agent-card:hover { 
            transform: translateX(5px); 
            box-shadow: 0 8px 25px rgba(105, 116, 220, 0.2);
        }
        
        .agent-card:hover::before { opacity: 1; }
        
        .agent-card-selected {
            background: linear-gradient(135deg, #f0fff4 0%, #e6ffed 100%) !important;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.15);
            border-left: 4px solid var(--success-color) !important;
        }
        
        .agent-stats {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
            font-size: 0.8rem;
            opacity: 0.9;
            color: #4a4a6a !important;
        }
        
        /* ========== ЦЕНТРИРОВАНИЕ КОРЗИНЫ В КАРТОЧКЕ АГЕНТА ========== */
        [data-testid="stSidebar"] .stColumn:has([key^="del_"]) {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            flex: 0 0 auto !important;
            max-width: 50px !important;
        }
        
        [data-testid="stSidebar"] [key^="del_"] {
            width: 36px !important;
            height: 36px !important;
            min-width: 36px !important;
            border-radius: 50% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 !important;
            margin: auto !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1) !important;
        }
        
        [data-testid="stSidebar"] [key^="del_"] svg {
            width: 16px !important;
            height: 16px !important;
        }
        
        [data-testid="stSidebar"] [key^="del_"]:hover {
            background-color: #fff0f0 !important;
            box-shadow: 0 4px 12px rgba(255, 68, 68, 0.2) !important;
        }
        
        /* ========== СТАТИСТИКА — БЕЛЫЙ ФОН ========== */
        .stat-card {
            background: #ffffff !important;
            background-color: #ffffff !important;
            padding: 1.2rem; 
            border-radius: 15px; 
            text-align: center; 
            color: #000000 !important;
            transition: transform 0.3s, box-shadow 0.3s;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
            border: none !important;
        }
        
        .stat-card *, .stat-card p, .stat-card span, .stat-card div {
            color: #000000 !important;
        }
        
        .stat-card:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 10px 30px rgba(105, 116, 220, 0.15);
        }
        
        .stat-card h3 { 
            margin: 0; 
            font-size: 2rem; 
            font-weight: bold;
            color: #6974dc !important;
        }
        
        .stat-card p { 
            margin: 0.3rem 0 0 0; 
            opacity: 0.9;
            font-size: 0.9rem;
            color: #4a4a6a !important;
        }
        
        /* ========== БЛОКИ ПАМЯТИ И УСЛОВИЙ — БЕЛЫЙ ФОН ========== */
        .memory-box, .condition-box, .info-box {
            background: #ffffff !important;
            background-color: #ffffff !important;
            padding: 1rem; 
            border-radius: 12px;
            margin: 0.5rem 0;
            border: none !important;
            color: #000000 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
        }
        
        .memory-box *, .condition-box *, .info-box *,
        .memory-box p, .condition-box p, .info-box p,
        .memory-box span, .condition-box span, .info-box span {
            color: #000000 !important;
        }
        
        .memory-box strong, .memory-box b,
        .condition-box strong, .condition-box b,
        .info-box strong, .info-box b {
            color: #000000 !important;
            font-weight: 600 !important;
        }
        
        .memory-box small, .condition-box small, .info-box small {
            color: #4a4a6a !important;
        }
        
        .memory-box { border-left: 4px solid var(--warning-color) !important; }
        .condition-box { 
            border-left: 4px solid var(--warning-color) !important; 
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
        }
        .info-box { border-left: 4px solid var(--accent-color) !important; }
        
        /* ========== УЗЛЫ WORKFLOW — БЕЛЫЙ ФОН ========== */
        .workflow-node {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border-radius: 15px; 
            padding: 1rem; 
            margin: 0.5rem 0; 
            color: #000000 !important;
            border: none !important;
            transition: all 0.3s ease;
            position: relative;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
        }
        
        .workflow-node *, .workflow-node p, .workflow-node span, .workflow-node div {
            color: #000000 !important;
        }
        
        .workflow-node small {
            color: #4a4a6a !important;
        }
        
        .workflow-node::after {
            content: '';
            position: absolute;
            bottom: -10px; left: 50%;
            width: 2px; height: 10px;
            background: var(--accent-color);
            transform: translateX(-50%);
        }
        
        .workflow-node:hover { 
            transform: translateX(5px); 
            box-shadow: 0 8px 25px rgba(105, 116, 220, 0.15);
        }
        
        .workflow-node-success {
            background: linear-gradient(135deg, #f0fff4 0%, #e6ffed 100%) !important;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.15);
        }
        
        .workflow-node-error {
            background: linear-gradient(135deg, #fff5f5 0%, #ffe6e6 100%) !important;
            box-shadow: 0 0 20px rgba(255, 68, 68, 0.15);
        }
        
        .workflow-connector {
            text-align: center;
            font-size: 1.2rem;
            color: var(--accent-color) !important;
            margin: 0.3rem 0;
        }
        
        /* ========== EXPANDER — БЕЛЫЙ ФОН ========== */
        div[data-testid="stExpander"] details {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border-radius: 12px; 
            border: none !important;
            margin: 0.5rem 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
        }
        
        div[data-testid="stExpander"] summary { 
            color: #000000 !important; 
            font-weight: 600;
            padding: 0.8rem 1rem;
        }
        
        div[data-testid="stExpander"] details *,
        div[data-testid="stExpander"] details p,
        div[data-testid="stExpander"] details span,
        div[data-testid="stExpander"] details div {
            color: #000000 !important;
        }
        
        /* ========== ТАБЛИЦЫ ========== */
        .dataframe {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            border: none !important;
            background-color: #ffffff !important;
        }
        
        /* ========== МОБИЛЬНАЯ АДАПТАЦИЯ ========== */
        @media (max-width: 768px) {
            .main-header { padding: 1.5rem; border-radius: 15px; }
            .main-header h1 { font-size: 1.8rem !important; }
            .main-header p { font-size: 0.95rem !important; }
            
            .stat-card { padding: 1rem; }
            .stat-card h3 { font-size: 1.5rem !important; }
            .stat-card p { font-size: 0.85rem !important; }
            
            .stButton button { 
                padding: 0.8rem 1.5rem !important; 
                font-size: 1rem !important;
                width: 100%;
            }
            
            .stTextArea textarea, 
            .stTextInput input { 
                font-size: 1rem !important; 
                padding: 0.9rem !important;
            }
            
            div[data-testid="column"] {
                flex: 1 1 100% !important;
                max-width: 100% !important;
            }
            
            .agent-card, .workflow-node, .memory-box {
                padding: 0.9rem !important;
                margin: 0.5rem 0 !important;
            }
            
            .desktop-only { display: none !important; }
            .mobile-only { display: block !important; }
        }
        
        @media (min-width: 769px) {
            div[data-testid="column"] {
                flex: 1 1 48% !important;
            }
            .mobile-only { display: none !important; }
        }
        
        /* ========== АНИМАЦИИ ========== */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        .loading { animation: pulse 1.5s infinite; }
        
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        /* ========== ПРОГРЕСС БАР ========== */
        .progress-container {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border-radius: 10px;
            padding: 0.5rem;
            margin: 0.5rem 0;
            color: #000000 !important;
            border: none !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
        }
        
        .progress-bar {
            height: 8px;
            background: var(--primary-gradient);
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        
        /* ========== TAGS ========== */
        .tag {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
            margin: 0.2rem;
            border: none !important;
        }
        .tag-success { background: rgba(0,255,136,0.15); color: #00cc6a !important; }
        .tag-error { background: rgba(255,68,68,0.15); color: #ff4444 !important; }
        .tag-warning { background: rgba(255,165,0,0.15); color: #ffa500 !important; }
        .tag-info { background: rgba(78,205,196,0.15); color: #3bb4a8 !important; }
        
        /* ========== CODE И СПИСКИ ========== */
        code, pre, .stCode {
            color: var(--accent-color) !important;
            background-color: rgba(78, 205, 196, 0.1) !important;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-weight: 500;
            border: none !important;
        }
        
        ul, ol, li {
            color: #000000 !important;
        }
        
        /* ========== ALERTS ========== */
        .stAlert, .stInfo, .stSuccess, .stWarning, .stError {
            color: #000000 !important;
            border: none !important;
            border-radius: 12px !important;
            background-color: #ffffff !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
        }
        
        .stAlert *, .stInfo *, .stSuccess *, .stWarning *, .stError * {
            color: #000000 !important;
        }
        
        /* ========== ОБЩИЕ БЛОКИ ========== */
        .stContainer, .stVerticalBlock, .stHorizontalBlock {
            border: none !important;
            border-radius: 10px;
            padding: 0.5rem;
            margin: 0.3rem 0;
        }
        
        /* Скрытие стандартных бордюров Streamlit */
        .stApp [data-testid="stVerticalBlockBorderWrapper"] {
            border: none !important;
        }
        
        /* ========== СТИЛИ ДЛЯ КНОПКИ ЗАГРУЗКИ ========== */
        .stFileUploader {
            background-color: #ffffff !important;
            border: none !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
        }
        
        /* ========== TABS ========== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: #ffffff !important;
            border: none !important;
            border-radius: 10px !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06) !important;
            color: #000000 !important;
        }
        
        .stTabs [aria-selected="true"] {
            background: var(--primary-gradient) !important;
            color: white !important;
        }
        
        .stTabs [aria-selected="true"] p {
            color: white !important;
        }
        
        /* ========== ЧАТ-ИНТЕРФЕЙС ========== */
        .chat-container {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            max-height: 60vh;
            overflow-y: auto;
            padding: 0.5rem;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        
        .chat-message-user {
            background: linear-gradient(135deg, #6974dc, #764ba2);
            color: white !important;
            padding: 0.8rem 1.2rem;
            border-radius: 18px 18px 4px 18px;
            margin-left: auto;
            max-width: 80%;
            box-shadow: 0 2px 8px rgba(105, 116, 220, 0.3);
        }
        
        .chat-message-agent {
            background: #f0f2f6;
            color: #000000 !important;
            padding: 0.8rem 1.2rem;
            border-radius: 18px 18px 18px 4px;
            margin-right: auto;
            max-width: 80%;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        
        .chat-message-user *, .chat-message-agent * {
            color: inherit !important;
        }
        
        .chat-input-container {
            position: sticky;
            top: 0;
            background: #ffffff;
            padding: 1rem 0;
            border-bottom: 1px solid #e0e0e0;
            z-index: 100;
            margin-bottom: 1rem;
        }
        
        /* ========== РЕДАКТИРУЕМЫЕ ТАБЛИЦЫ ========== */
        .table-editor {
            background: #ffffff;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            margin: 0.5rem 0;
        }
        
        .table-editor-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .table-actions {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        
        .saved-table-card {
            background: #ffffff;
            border-radius: 12px;
            padding: 1rem;
            margin: 0.5rem 0;
            border-left: 4px solid var(--accent-color);
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        
        .saved-table-card * {
            color: #000000 !important;
        }
        
        /* ========== КАРТОЧКИ ИЗОБРАЖЕНИЙ ========== */
        .image-card {
            background: #ffffff;
            border-radius: 12px;
            padding: 0.8rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            margin: 0.5rem;
            text-align: center;
        }
        
        .image-card img {
            max-width: 100%;
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }
        
        .image-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1rem;
            padding: 1rem;
        }
        
        .image-preview-container {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 1rem;
            margin: 0.5rem 0;
        }
        
        /* ========== ПРОГРЕСС ЗАГРУЗКИ ========== */
        .upload-progress {
            background: linear-gradient(135deg, #6974dc, #764ba2);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            text-align: center;
        }
    </style>
    """
