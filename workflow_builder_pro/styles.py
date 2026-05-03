"""
CSS стили приложения (расширенная версия)
"""


def get_app_styles() -> str:
    return """
<style>
:root {
    --primary-gradient: linear-gradient(135deg, #6974dc 0%, #764ba2 100%);
    --success-color: #00ff88;
    --error-color: #ff4444;
    --warning-color: #ffa500;
    --accent-color: #4ECDC4;
    --card-bg: #ffffff;
    --text-dark: #000000;
    --text-secondary: #4a4a6a;
    --border-light: #e0e0e0;
}

body, .stApp, .main, .block-container {
    color: var(--text-dark) !important;
    background-color: #f0f2f6 !important;
}

[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid var(--border-light) !important;
    box-shadow: 2px 0 10px rgba(0,0,0,0.05) !important;
}

.agent-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 0.8rem;
    margin: 0.5rem 0;
    border: 1px solid var(--border-light);
    transition: all 0.2s ease;
    cursor: pointer;
}
.agent-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.1);
}
.agent-card-selected {
    background: linear-gradient(135deg, #f0fff4, #e6ffed);
    border-left: 4px solid var(--success-color);
    box-shadow: 0 4px 12px rgba(0,255,136,0.2);
}
.agent-stats {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.5rem;
    font-size: 0.75rem;
    color: var(--text-secondary);
}

.workflow-node {
    background: #ffffff;
    border-radius: 12px;
    padding: 1rem;
    margin: 0.5rem 0;
    border-left: 4px solid var(--accent-color);
    transition: all 0.2s;
}
.workflow-node:hover {
    transform: translateX(4px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.workflow-connector {
    text-align: center;
    font-size: 1.2rem;
    color: var(--accent-color);
    margin: 0.2rem 0;
}

.chat-message-user {
    background: linear-gradient(135deg, #6974dc, #764ba2);
    color: white;
    padding: 0.8rem 1.2rem;
    border-radius: 18px 18px 4px 18px;
    margin-left: auto;
    max-width: 80%;
    margin-bottom: 0.5rem;
}
.chat-message-agent {
    background: #f0f2f6;
    color: #000;
    padding: 0.8rem 1.2rem;
    border-radius: 18px 18px 18px 4px;
    margin-right: auto;
    max-width: 80%;
    margin-bottom: 0.5rem;
}
.chat-input-container {
    position: sticky;
    top: 0;
    background: #ffffff;
    padding: 1rem 0;
    border-bottom: 1px solid var(--border-light);
    z-index: 100;
}

.memory-box, .condition-box, .info-box {
    background: #ffffff;
    padding: 1rem;
    border-radius: 12px;
    margin: 0.5rem 0;
    border-left: 4px solid var(--warning-color);
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.stButton button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease;
    background: #ffffff;
    border: 1px solid var(--border-light);
}
.stButton button:hover {
    transform: scale(1.02);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.stButton button[kind="primary"] {
    background: var(--primary-gradient);
    color: white;
    border: none;
}

.main-header {
    background: var(--primary-gradient);
    padding: 2rem;
    border-radius: 20px;
    margin-bottom: 2rem;
    text-align: center;
    box-shadow: 0 10px 30px rgba(105,116,220,0.3);
}
.main-header h1 {
    color: white !important;
    margin: 0;
}
.version-badge {
    background: rgba(255,255,255,0.2);
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.8rem;
    color: white;
}

@media (max-width: 768px) {
    .main-header { padding: 1rem; }
    .chat-message-user, .chat-message-agent { max-width: 95%; }
    .stButton button { width: 100%; }
}
</style>
"""
