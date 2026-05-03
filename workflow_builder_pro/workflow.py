"""
Генератор и исполнитель workflow.
"""
import streamlit as st
import json
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
import pandas as pd
import requests
from openai import OpenAI
from config import CONFIG
from utils import NodeType, WorkflowStatus
from condition_parser import RussianConditionParser
from ai_agent import AgentManager  # для типизации
from table_manager import TableManager  # для типизации
import logging

logger = logging.getLogger(__name__)


class AIWorkflowGenerator:
    """Генерирует workflow из текстового описания на русском"""
    
    @staticmethod
    def generate(description: str, api_key: str) -> List[Dict]:
        """Генерирует workflow из описания"""
        if not api_key:
            return []
        
        try:
            client = OpenAI(api_key=api_key, base_url=CONFIG.DEEPSEEK_BASE_URL)
            
            prompt = f"""
Ты эксперт по созданию workflow автоматизации. На основе описания пользователя создай JSON workflow.

Описание пользователя: "{description}"

Правила:
1. Workflow - это массив блоков (nodes)
2. Каждый блок имеет: name (название), type (тип), config (настройки)
3. Доступные типы блоков:
   - google_sheets_read: чтение из Google таблиц (config: sheet_url)
   - google_sheets_write: запись в Google таблицы
   - excel_read: чтение Excel файла
   - excel_write: запись в Excel
   - deepseek: AI анализ (config: system_prompt, user_prompt)
   - http_get: GET запрос к API (config: url)
   - http_post: POST запрос (config: url, body)
   - condition: условие (config: condition на русском)
   - loop: цикл (config: items)
   - email: отправка email (config: to, subject, body)
   - telegram: отправка в Telegram (config: chat_id, message)
   - ai_agent: вызов ИИ агента (config: agent_id, question)
   - data_clean: очистка данных (config: rules)
   - pivot_table: сводная таблица (config: index, columns, values)

4. Условия пиши на РУССКОМ языке, используя природные фразы

Верни ТОЛЬКО JSON массив блоков, без пояснений.
"""
            response = client.chat.completions.create(
                model=CONFIG.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "Ты генератор workflow автоматизации. Возвращай только JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                timeout=CONFIG.API_TIMEOUT,
                max_tokens=CONFIG.MAX_TOKENS
            )
            
            content = response.choices[0].message.content
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                return json.loads(json_match.group())
            else:
                return []
                
        except Exception as e:
            logger.error(f"Ошибка генерации workflow: {e}")
            st.error(f"Ошибка генерации: {str(e)}")
            return []


class WorkflowExecutor:
    """Выполняет workflow с поддержкой условий на русском"""
    
    def __init__(
        self, 
        workflow: List[Dict], 
        api_key: Optional[str] = None, 
        agent_manager: Optional[AgentManager] = None,
        table_manager: Optional[TableManager] = None
    ):
        self.workflow = workflow
        self.api_key = api_key
        self.agent_manager = agent_manager
        self.table_manager = table_manager or TableManager(api_key)
        self.context: Dict[str, Any] = {}
        self.results: List[Dict] = []
        self.current_node_index: int = 0
        self.start_time: Optional[float] = None
    
    def execute(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Выполняет весь workflow"""
        self.start_time = time.time()
        
        while self.current_node_index < len(self.workflow):
            node = self.workflow[self.current_node_index]
            
            if progress_callback:
                progress_callback(self.current_node_index, node)
            
            try:
                result = self._execute_node(node)
                self.results.append({
                    'node': node.get('name'),
                    'type': node.get('type'),
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                })
                
                if isinstance(result, dict) and 'data' in result:
                    self.context.update(result)
                
                node['status'] = WorkflowStatus.SUCCESS.value
                self.current_node_index += 1
                
            except Exception as e:
                logger.error(f"Ошибка в узле {node.get('name')}: {e}")
                node['status'] = WorkflowStatus.ERROR.value
                node['error'] = str(e)
                return {
                    'success': False,
                    'error': str(e),
                    'error_node': node.get('name'),
                    'results': self.results,
                    'execution_time': time.time() - (self.start_time or time.time())
                }
        
        return {
            'success': True,
            'results': self.results,
            'context': self.context,
            'execution_time': time.time() - (self.start_time or time.time())
        }
    
    def _execute_node(self, node: Dict) -> Any:
        """Выполняет отдельный узел"""
        node_type = node.get('type')
        config = node.get('config', {})
        
        if node_type == NodeType.GOOGLE_SHEETS_READ.value:
            return self._execute_google_sheets_read(config)
        elif node_type == NodeType.EXCEL_READ.value:
            return self._execute_excel_read(config)
        elif node_type == NodeType.DEEPSEEK_AI.value:
            return self._execute_deepseek(config)
        elif node_type == NodeType.CONDITION.value:
            return self._execute_condition(config)
        elif node_type == NodeType.LOOP.value:
            return self._execute_loop(config)
        elif node_type == NodeType.HTTP_GET.value:
            return self._execute_http_get(config)
        elif node_type == NodeType.HTTP_POST.value:
            return self._execute_http_post(config)
        elif node_type == NodeType.EMAIL.value:
            return self._execute_email(config)
        elif node_type == NodeType.TELEGRAM.value:
            return self._execute_telegram(config)
        elif node_type == NodeType.AI_AGENT.value:
            return self._execute_ai_agent(config)
        elif node_type == NodeType.DATA_CLEAN.value:
            return self._execute_data_clean(config)
        elif node_type == NodeType.PIVOT_TABLE.value:
            return self._execute_pivot_table(config)
        else:
            return {'status': 'unknown_type', 'type': node_type}
    
    def _execute_google_sheets_read(self, config: Dict) -> Dict:
        sheet_url = config.get('sheet_url', '')
        if not sheet_url:
            return {'error': 'URL Google Sheets не указан'}
        df = self.table_manager.read_google_sheets(sheet_url, config.get('sheet_name'), config.get('range_a1'))
        if df is None:
            return {'error': 'Не удалось загрузить данные'}
        return {'data': df.to_dict('records'), 'rows': len(df), 'columns': list(df.columns), 'df': df}
    
    def _execute_excel_read(self, config: Dict) -> Dict:
        file_path = config.get('file_path', '')
        if not file_path:
            return {'error': 'Путь к файлу не указан'}
        df = self.table_manager.read_excel(file_path, config.get('sheet_name', 0))
        if df is None:
            return {'error': 'Не удалось загрузить данные'}
        return {'data': df.to_dict('records'), 'rows': len(df), 'columns': list(df.columns), 'df': df}
    
    def _execute_deepseek(self, config: Dict) -> Dict:
        if not self.api_key:
            return {'error': 'API ключ не указан'}
        client = OpenAI(api_key=self.api_key, base_url=CONFIG.DEEPSEEK_BASE_URL)
        user_prompt = config.get('user_prompt', '')
        for key, value in self.context.items():
            if isinstance(value, str):
                user_prompt = user_prompt.replace(f"{{{{{key}}}}}", value)
        response = client.chat.completions.create(
            model=CONFIG.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": config.get('system_prompt', 'Ты полезный ассистент')},
                {"role": "user", "content": user_prompt}
            ],
            temperature=float(config.get('temperature', 0.3))
        )
        return {'response': response.choices[0].message.content}
    
    def _execute_condition(self, config: Dict) -> Dict:
        condition_text = config.get('condition', '')
        parsed = RussianConditionParser.parse(condition_text)
        result = self._evaluate_condition(condition_text)
        return {'condition': condition_text, 'result': result, 'parsed': parsed, 'code': parsed.get('code')}
    
    def _evaluate_condition(self, condition_text: str) -> bool:
        condition_text = condition_text.lower()
        if 'больше' in condition_text:
            match = re.search(r'(\w+)\s+больше\s+(\d+)', condition_text)
            if match:
                var_name = match.group(1)
                value = float(match.group(2))
                context_value = self.context.get(var_name, 0)
                return float(context_value) > value if isinstance(context_value, (int, float)) else False
        elif 'меньше' in condition_text:
            match = re.search(r'(\w+)\s+меньше\s+(\d+)', condition_text)
            if match:
                var_name = match.group(1)
                value = float(match.group(2))
                context_value = self.context.get(var_name, 0)
                return float(context_value) < value if isinstance(context_value, (int, float)) else False
        elif 'равно' in condition_text or 'равняется' in condition_text:
            match = re.search(r'(\w+)\s+равно\s+(.+)', condition_text)
            if match:
                var_name = match.group(1)
                value = match.group(2).strip().strip("'\"")
                context_value = self.context.get(var_name, '')
                return str(context_value) == value
        elif 'содержит' in condition_text:
            match = re.search(r'(\w+)\s+содержит\s+(.+)', condition_text)
            if match:
                var_name = match.group(1)
                value = match.group(2).strip().strip("'\"")
                context_value = str(self.context.get(var_name, ''))
                return value in context_value
        return True
    
    def _execute_loop(self, config: Dict) -> Dict:
        items = config.get('items', '[]')
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except:
                items = []
        return {'items': items, 'count': len(items)}
    
    def _execute_http_get(self, config: Dict) -> Dict:
        url = config.get('url', '')
        if not url:
            return {'error': 'URL не указан'}
        response = requests.get(url, timeout=CONFIG.API_TIMEOUT)
        return {'status': response.status_code, 'data': response.json() if response.status_code == 200 else None}
    
    def _execute_http_post(self, config: Dict) -> Dict:
        url = config.get('url', '')
        if not url:
            return {'error': 'URL не указан'}
        body = config.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        response = requests.post(url, json=body, timeout=CONFIG.API_TIMEOUT)
        return {'status': response.status_code, 'data': response.json() if response.status_code == 200 else None}
    
    def _execute_email(self, config: Dict) -> Dict:
        return {'to': config.get('to', ''), 'subject': config.get('subject', ''), 'body': config.get('body', ''), 'status': 'ready'}
    
    def _execute_telegram(self, config: Dict) -> Dict:
        return {'chat_id': config.get('chat_id', ''), 'message': config.get('message', ''), 'status': 'ready'}
    
    def _execute_ai_agent(self, config: Dict) -> Dict:
        if not self.agent_manager:
            return {'error': 'Менеджер агентов не инициализирован'}
        agent_id = config.get('agent_id')
        if not agent_id or agent_id not in self.agent_manager.agents:
            return {'error': 'Агент не найден'}
        agent = self.agent_manager.agents[agent_id]
        question = config.get('question', '')
        use_training = config.get('use_training', True)
        response = agent.generate_response(question, self.api_key, use_training)
        return {'agent': agent.name, 'question': question, 'response': response}
    
    def _execute_data_clean(self, config: Dict) -> Dict:
        df = config.get('df')
        rules = config.get('rules', {})
        if df is None:
            return {'error': 'DataFrame не указан'}
        cleaned = df.copy()
        if rules.get('remove_duplicates'):
            cleaned = cleaned.drop_duplicates()
        if rules.get('remove_empty'):
            cleaned = cleaned.dropna(how='all')
        if rules.get('fill_na'):
            cleaned = cleaned.fillna(rules.get('fill_value', ''))
        return {'data': cleaned.to_dict('records'), 'rows': len(cleaned), 'columns': list(cleaned.columns)}
    
    def _execute_pivot_table(self, config: Dict) -> Dict:
        df = config.get('df')
        if df is None:
            return {'error': 'DataFrame не указан'}
        pivot = pd.pivot_table(
            df,
            index=config.get('index', []),
            columns=config.get('columns', []),
            values=config.get('values', []),
            aggfunc=config.get('aggfunc', 'sum'),
            fill_value=0
        )
        return {'data': pivot.to_dict()}
