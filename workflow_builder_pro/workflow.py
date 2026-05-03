"""
Workflow: генератор, исполнитель и узлы
"""
import json
import re
import time
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from openai import OpenAI

import pandas as pd
import streamlit as st

from config import CONFIG, NodeType, WorkflowStatus
from utils import logger
from condition_parser import RussianConditionParser
from table_manager import TableManager
from ai_agent import AgentManager


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
   - sms: отправка SMS (config: phone, message, provider)
   - ai_agent: вызов ИИ агента (config: agent_id, question)
   - data_clean: очистка данных (config: rules)
   - pivot_table: сводная таблица (config: index, columns, values)
   - webhook: webhook (config: url, method)
   - schedule: планировщик (config: cron, timezone)
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
            return []
        
        except Exception as e:
            logger.error(f"Ошибка генерации workflow: {e}")
            st.error(f"Ошибка генерации: {str(e)}")
            return []


class WorkflowExecutor:
    """Выполняет workflow с поддержкой условий и расширенной автоматизации"""
    
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
        """Выполняет весь workflow с поддержкой условий"""
        self.start_time = time.time()
        
        while self.current_node_index < len(self.workflow):
            node = self.workflow[self.current_node_index]
            
            # Проверка условий выполнения узла
            if 'condition' in node:
                should_execute = self._check_node_condition(node)
                if not should_execute:
                    logger.info(f"Пропуск узла {node.get('name')} - условие не выполнено")
                    node['status'] = 'skipped'
                    self.current_node_index += 1
                    continue
            
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
                
                # Обработка ошибок по условию
                if 'on_error' in node:
                    error_action = node['on_error']
                    if error_action == 'continue':
                        self.current_node_index += 1
                        continue
                    elif error_action == 'retry':
                        retry_count = node.get('retry_count', 3)
                        if node.get('retries', 0) < retry_count:
                            node['retries'] = node.get('retries', 0) + 1
                            logger.info(f"Повтор узла {node.get('name')} ({node['retries']}/{retry_count})")
                            time.sleep(1) # Небольшая задержка перед повтором
                            continue
                
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
    
    def _check_node_condition(self, node: Dict) -> bool:
        """Проверяет условие выполнения узла"""
        condition = node.get('condition', {})
        condition_type = condition.get('type', 'always')
        
        if condition_type == 'always':
            return True
        
        elif condition_type == 'previous_success':
            prev_node = self.results[-1] if self.results else None
            return prev_node and prev_node.get('result', {}).get('success', False)
        
        elif condition_type == 'variable':
            var_name = condition.get('variable')
            expected_value = condition.get('value')
            operator = condition.get('operator', '==')
            
            actual_value = self.context.get(var_name)
            
            if operator == '==':
                return str(actual_value) == str(expected_value)
            elif operator == '!=':
                return str(actual_value) != str(expected_value)
            elif operator == '>':
                return float(actual_value) > float(expected_value)
            elif operator == '<':
                return float(actual_value) < float(expected_value)
            elif operator == 'contains':
                return str(expected_value) in str(actual_value)
        
        elif condition_type == 'custom':
            custom_condition = condition.get('expression', '')
            return self._evaluate_condition(custom_condition)
        
        return True
    
    def _execute_node(self, node: Dict) -> Any:
        """Выполняет отдельный узел"""
        node_type = node.get('type')
        config = node.get('config', {})
        
        executors = {
            NodeType.GOOGLE_SHEETS_READ.value: lambda: self._execute_google_sheets_read(config),
            NodeType.GOOGLE_SHEETS_WRITE.value: lambda: self._execute_google_sheets_write(config),
            NodeType.EXCEL_READ.value: lambda: self._execute_excel_read(config),
            NodeType.EXCEL_WRITE.value: lambda: self._execute_excel_write(config),
            NodeType.DEEPSEEK_AI.value: lambda: self._execute_deepseek(config),
            NodeType.CONDITION.value: lambda: self._execute_condition(config),
            NodeType.LOOP.value: lambda: self._execute_loop(config),
            NodeType.HTTP_GET.value: lambda: self._execute_http_get(config),
            NodeType.HTTP_POST.value: lambda: self._execute_http_post(config),
            NodeType.EMAIL.value: lambda: self._execute_email(config),
            NodeType.TELEGRAM.value: lambda: self._execute_telegram(config),
            NodeType.SMS.value: lambda: self._execute_sms(config),
            NodeType.AI_AGENT.value: lambda: self._execute_ai_agent(config),
            NodeType.DATA_CLEAN.value: lambda: self._execute_data_clean(config),
            NodeType.PIVOT_TABLE.value: lambda: self._execute_pivot_table(config),
            NodeType.WEBHOOK.value: lambda: self._execute_webhook(config),
            NodeType.SCHEDULE.value: lambda: self._execute_schedule(config),
        }
        
        executor = executors.get(node_type)
        if executor:
            return executor()
        else:
            return {'status': 'unknown_type', 'type': node_type}

    def _execute_sms(self, config: Dict) -> Dict:
        """Отправка SMS (поддержка различных провайдеров)"""
        phone = config.get('phone', '')
        message = config.get('message', '')
        provider = config.get('provider', 'simulated')
        
        if not phone or not message:
            return {'error': 'Телефон или сообщение не указаны'}
        
        try:
            if provider == 'twilio':
                account_sid = config.get('twilio_sid', '')
                auth_token = config.get('twilio_token', '')
                from_number = config.get('from_number', '')
                # Здесь код отправки через Twilio API
                return {'status': 'sent', 'provider': 'twilio', 'phone': phone}
            
            elif provider == 'smsru':
                api_key = config.get('smsru_key', '')
                url = "https://sms.ru/sms/send"
                params = {'api_id': api_key, 'to': phone, 'msg': message, 'json': 1}
                response = requests.post(url, data=params, timeout=30)
                result = response.json()
                return {'status': 'sent' if result.get('status') == 100 else 'failed', 'provider': 'smsru'}
            
            else:
                # Webhook или симуляция
                webhook_url = config.get('webhook_url', '')
                if webhook_url:
                    requests.post(webhook_url, json={'phone': phone, 'message': message}, timeout=30)
                    return {'status': 'sent', 'provider': 'webhook'}
                
                return {'status': 'simulated', 'phone': phone, 'message': message[:50]}
            
        except Exception as e:
            return {'error': str(e), 'status': 'failed'}

    def _execute_webhook(self, config: Dict) -> Dict:
        """Вызов webhook"""
        url = config.get('url', '')
        method = config.get('method', 'POST').upper()
        headers = config.get('headers', {})
        body = config.get('body', {})
        
        if not url:
            return {'error': 'URL webhook не указан'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=CONFIG.API_TIMEOUT)
            elif method == 'POST':
                response = requests.post(url, json=body, headers=headers, timeout=CONFIG.API_TIMEOUT)
            elif method == 'PUT':
                response = requests.put(url, json=body, headers=headers, timeout=CONFIG.API_TIMEOUT)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=CONFIG.API_TIMEOUT)
            else:
                return {'error': f'Неподдерживаемый метод: {method}'}
            
            return {
                'status': response.status_code,
                'data': response.json() if response.status_code == 200 else None,
                'url': url
            }
        except Exception as e:
            return {'error': str(e)}

    def _execute_schedule(self, config: Dict) -> Dict:
        """Планировщик (информационный узел)"""
        cron = config.get('cron', '')
        timezone = config.get('timezone', 'UTC')
        return {
            'status': 'scheduled',
            'cron': cron,
            'timezone': timezone,
            'message': 'Узел планировщика (требует внешней интеграции)'
        }
    
    def _execute_google_sheets_read(self, config: Dict) -> Dict:
        """Чтение из Google Sheets"""
        sheet_url = config.get('sheet_url', '')
        sheet_name = config.get('sheet_name')
        range_a1 = config.get('range_a1')
        
        if not sheet_url:
            return {'error': 'URL Google Sheets не указан'}
        
        try:
            df = self.table_manager.read_google_sheets(sheet_url, sheet_name, range_a1)
            if df is None:
                return {'error': 'Не удалось загрузить данные'}
            
            return {
                'data': df.to_dict('records'),
                'rows': len(df),
                'columns': list(df.columns),
                'df': df
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _execute_google_sheets_write(self, config: Dict) -> Dict:
        """Запись в Google Sheets (заглушка)"""
        return {'status': 'not_implemented', 'message': 'Требуется настройка Google Sheets API'}
    
    def _execute_excel_read(self, config: Dict) -> Dict:
        """Чтение из Excel"""
        file_path = config.get('file_path', '')
        sheet_name = config.get('sheet_name', 0)
        
        if not file_path:
            return {'error': 'Путь к файлу не указан'}
        
        try:
            df = self.table_manager.read_excel(file_path, sheet_name)
            if df is None:
                return {'error': 'Не удалось загрузить данные'}
            
            return {
                'data': df.to_dict('records'),
                'rows': len(df),
                'columns': list(df.columns),
                'df': df
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _execute_excel_write(self, config: Dict) -> Dict:
        """Запись в Excel"""
        df = config.get('df')
        output_path = config.get('output_path', 'output.xlsx')
        apply_formatting = config.get('apply_formatting', True)
        
        if df is None:
            return {'error': 'DataFrame не указан'}
        
        try:
            success = self.table_manager.write_excel(df, output_path, apply_formatting=apply_formatting)
            return {'status': 'success' if success else 'failed', 'path': output_path}
        except Exception as e:
            return {'error': str(e)}
    
    def _execute_deepseek(self, config: Dict) -> Dict:
        """Вызов DeepSeek AI"""
        if not self.api_key:
            return {'error': 'API ключ не указан'}
        
        try:
            client = OpenAI(api_key=self.api_key, base_url=CONFIG.DEEPSEEK_BASE_URL)
            user_prompt = config.get('user_prompt', '')
            
            # Подстановка переменных из контекста
            for key, value in self.context.items():
                if isinstance(value, str):
                    user_prompt = user_prompt.replace(f"{{{{{key}}}}}", value)
            
            response = client.chat.completions.create(
                model=CONFIG.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": config.get('system_prompt', 'Ты полезный ассистент')},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=float(config.get('temperature', 0.3)),
                timeout=CONFIG.API_TIMEOUT,
                max_tokens=CONFIG.MAX_TOKENS
            )
            
            return {
                'response': response.choices[0].message.content,
                'model': CONFIG.DEEPSEEK_MODEL
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _execute_condition(self, config: Dict) -> Dict:
        """Выполнение условия"""
        condition_text = config.get('condition', '')
        parsed = RussianConditionParser.parse(condition_text)
        result = self._evaluate_condition(condition_text)
        
        return {
            'condition': condition_text,
            'result': result,
            'parsed': parsed,
            'code': parsed.get('code')
        }
    
    def _evaluate_condition(self, condition_text: str) -> bool:
        """Оценивает условие"""
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
        """Выполнение цикла"""
        items = config.get('items', '[]')
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except:
                items = []
        
        batch_size = int(config.get('batch_size', 10))
        
        return {
            'items': items,
            'count': len(items),
            'batch_size': batch_size,
            'processed': 0
        }
    
    def _execute_http_get(self, config: Dict) -> Dict:
        """HTTP GET запрос"""
        url = config.get('url', '')
        if not url:
            return {'error': 'URL не указан'}
        
        try:
            response = requests.get(url, timeout=CONFIG.API_TIMEOUT)
            return {
                'status': response.status_code,
                'data': response.json() if response.status_code == 200 else None,
                'url': url
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _execute_http_post(self, config: Dict) -> Dict:
        """HTTP POST запрос"""
        url = config.get('url', '')
        if not url:
            return {'error': 'URL не указан'}
        
        try:
            body = config.get('body', '{}')
            if isinstance(body, str):
                body = json.loads(body)
            
            response = requests.post(url, json=body, timeout=CONFIG.API_TIMEOUT)
            return {
                'status': response.status_code,
                'data': response.json() if response.status_code == 200 else None,
                'url': url
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _execute_email(self, config: Dict) -> Dict:
        """Подготовка email (заглушка)"""
        return {
            'to': config.get('to', ''),
            'subject': config.get('subject', ''),
            'body': config.get('body', ''),
            'status': 'ready'
        }
    
    def _execute_telegram(self, config: Dict) -> Dict:
        """Подготовка Telegram сообщения (заглушка)"""
        return {
            'chat_id': config.get('chat_id', ''),
            'message': config.get('message', ''),
            'status': 'ready'
        }
    
    def _execute_ai_agent(self, config: Dict) -> Dict:
        """Вызов ИИ агента"""
        if not self.agent_manager:
            return {'error': 'Менеджер агентов не инициализирован'}
        
        agent_id = config.get('agent_id')
        if not agent_id or agent_id not in self.agent_manager.agents:
            return {'error': 'Агент не найден'}
        
        agent = self.agent_manager.agents[agent_id]
        question = config.get('question', '')
        use_training = config.get('use_training', True)
        
        response = agent.generate_response(question, self.api_key, use_training)
        
        return {
            'agent': agent.name,
            'question': question,
            'response': response
        }
    
    def _execute_data_clean(self, config: Dict) -> Dict:
        """Очистка данных"""
        df = config.get('df')
        rules = config.get('rules', {})
        
        if df is None:
            return {'error': 'DataFrame не указан'}
        
        try:
            cleaned_df = df.copy()
            
            if rules.get('remove_duplicates'):
                cleaned_df = cleaned_df.drop_duplicates()
            
            if rules.get('remove_empty'):
                cleaned_df = cleaned_df.dropna(how='all')
            
            if rules.get('fill_na'):
                fill_value = rules.get('fill_value', '')
                cleaned_df = cleaned_df.fillna(fill_value)
            
            if rules.get('columns'):
                cleaned_df = cleaned_df[rules['columns']]
            
            return {
                'data': cleaned_df.to_dict('records'),
                'rows': len(cleaned_df),
                'columns': list(cleaned_df.columns),
                'df': cleaned_df,
                'removed_rows': len(df) - len(cleaned_df)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _execute_pivot_table(self, config: Dict) -> Dict:
        """Создание сводной таблицы"""
        df = config.get('df')
        index = config.get('index', [])
        columns = config.get('columns', [])
        values = config.get('values', [])
        aggfunc = config.get('aggfunc', 'sum')
        
        if df is None:
            return {'error': 'DataFrame не указан'}
        
        try:
            pivot = pd.pivot_table(
                df,
                index=index if isinstance(index, list) else [index],
                columns=columns if isinstance(columns, list) else [columns] if columns else None,
                values=values if isinstance(values, list) else [values] if values else None,
                aggfunc=aggfunc,
                fill_value=0
            )
            
            return {
                'data': pivot.to_dict(),
                'df': pivot.reset_index(),
                'type': 'pivot_table'
            }
        except Exception as e:
            return {'error': str(e)}
