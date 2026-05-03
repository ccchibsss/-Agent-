"""
Workflow: генератор, исполнитель и узлы
Расширенная версия с SMS, условиями и улучшенным ИИ
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
   - sms: отправка SMS (config: phone_number, message, provider="twilio" or "http")
   - telegram: отправка в Telegram (config: chat_id, message)
   - ai_agent: вызов ИИ агента (config: agent_id, question)
   - data_clean: очистка данных (config: rules)
   - pivot_table: сводная таблица (config: index, columns, values)
4. Условия пиши на РУССКОМ языке, используя природные фразы
5. Для отправки сообщений (email, sms, telegram) добавь поле condition (опционально) - условие на русском

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
    def __init__(self, workflow: List[Dict], api_key: Optional[str] = None,
                 agent_manager: Optional[AgentManager] = None, table_manager: Optional[TableManager] = None):
        self.workflow = workflow
        self.api_key = api_key
        self.agent_manager = agent_manager
        self.table_manager = table_manager or TableManager(api_key)
        self.context: Dict[str, Any] = {}
        self.results: List[Dict] = []
        self.current_node_index: int = 0
        self.start_time: Optional[float] = None

    def execute(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        self.start_time = time.time()
        while self.current_node_index < len(self.workflow):
            node = self.workflow[self.current_node_index]
            if progress_callback:
                progress_callback(self.current_node_index, node)
            condition = node.get('condition')
            if condition:
                condition_met = self._evaluate_condition(condition)
                if not condition_met:
                    logger.info(f"Узел {node.get('name')} пропущен по условию: {condition}")
                    self.current_node_index += 1
                    continue
            try:
                result = self._execute_node(node)
                self.results.append({
                    'node': node.get('name'),
                    'type': node.get('type'),
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                })
                if isinstance(result, dict):
                    if 'data' in result:
                        self.context.update(result)
                    for k, v in result.items():
                        if k not in ['df', 'data'] and not isinstance(v, pd.DataFrame):
                            self.context[k] = v
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
            NodeType.AI_AGENT.value: lambda: self._execute_ai_agent(config),
            NodeType.DATA_CLEAN.value: lambda: self._execute_data_clean(config),
            NodeType.PIVOT_TABLE.value: lambda: self._execute_pivot_table(config),
            'sms': lambda: self._execute_sms(config),
        }
        executor = executors.get(node_type)
        if executor:
            return executor()
        else:
            return {'status': 'unknown_type', 'type': node_type}

    def _execute_google_sheets_read(self, config: Dict) -> Dict:
        sheet_url = config.get('sheet_url', '')
        if not sheet_url:
            return {'error': 'URL Google Sheets не указан'}
        try:
            df = self.table_manager.read_google_sheets(sheet_url, config.get('sheet_name'), config.get('range_a1'))
            if df is None:
                return {'error': 'Не удалось загрузить данные'}
            return {'data': df.to_dict('records'), 'rows': len(df), 'columns': list(df.columns), 'df': df}
        except Exception as e:
            return {'error': str(e)}

    def _execute_google_sheets_write(self, config: Dict) -> Dict:
        return {'status': 'not_implemented', 'message': 'Требуется настройка Google Sheets API'}

    def _execute_excel_read(self, config: Dict) -> Dict:
        file_path = config.get('file_path', '')
        if not file_path:
            return {'error': 'Путь к файлу не указан'}
        try:
            df = self.table_manager.read_excel(file_path, config.get('sheet_name', 0))
            if df is None:
                return {'error': 'Не удалось загрузить данные'}
            return {'data': df.to_dict('records'), 'rows': len(df), 'columns': list(df.columns), 'df': df}
        except Exception as e:
            return {'error': str(e)}

    def _execute_excel_write(self, config: Dict) -> Dict:
        df = config.get('df')
        output_path = config.get('output_path', 'output.xlsx')
        if df is None:
            return {'error': 'DataFrame не указан'}
        try:
            success = self.table_manager.write_excel(df, output_path, apply_formatting=config.get('apply_formatting', True))
            return {'status': 'success' if success else 'failed', 'path': output_path}
        except Exception as e:
            return {'error': str(e)}

    def _execute_deepseek(self, config: Dict) -> Dict:
        if not self.api_key:
            return {'error': 'API ключ не указан'}
        try:
            client = OpenAI(api_key=self.api_key, base_url=CONFIG.DEEPSEEK_BASE_URL)
            user_prompt = config.get('user_prompt', '')
            system_prompt = config.get('system_prompt', 'Ты полезный ассистент')
            for key, value in self.context.items():
                if isinstance(value, (str, int, float)):
                    user_prompt = user_prompt.replace(f"{{{{{key}}}}}", str(value))
                    system_prompt = system_prompt.replace(f"{{{{{key}}}}}", str(value))
            response = client.chat.completions.create(
                model=CONFIG.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=float(config.get('temperature', 0.3)),
                timeout=CONFIG.API_TIMEOUT,
                max_tokens=CONFIG.MAX_TOKENS
            )
            ai_response = response.choices[0].message.content
            json_match = re.search(r'\{[\s\S]*\}', ai_response)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return {'response': ai_response, 'parsed_data': data}
                except:
                    pass
            return {'response': ai_response, 'model': CONFIG.DEEPSEEK_MODEL}
        except Exception as e:
            return {'error': str(e)}

    def _execute_condition(self, config: Dict) -> Dict:
        condition_text = config.get('condition', '')
        parsed = RussianConditionParser.parse(condition_text)
        result = self._evaluate_condition(condition_text)
        return {'condition': condition_text, 'result': result, 'parsed': parsed, 'code': parsed.get('code')}

    def _evaluate_condition(self, condition_text: str) -> bool:
        condition_text = condition_text.lower().strip()
        for key, value in self.context.items():
            if isinstance(value, (int, float)):
                condition_text = condition_text.replace(key, str(value))
            elif isinstance(value, str):
                condition_text = condition_text.replace(key, f"'{value}'")
        parsed = RussianConditionParser.parse(condition_text)
        if parsed.get('code'):
            try:
                local_vars = {'data': self.context}
                return eval(parsed['python_expr'], {"__builtins__": {}}, local_vars)
            except:
                pass
        if 'больше' in condition_text:
            match = re.search(r'(\w+)\s+больше\s+(\d+)', condition_text)
            if match:
                var_name = match.group(1)
                value = float(match.group(2))
                context_value = self.context.get(var_name, 0)
                try:
                    return float(context_value) > value
                except:
                    return False
        elif 'меньше' in condition_text:
            match = re.search(r'(\w+)\s+меньше\s+(\d+)', condition_text)
            if match:
                var_name = match.group(1)
                value = float(match.group(2))
                context_value = self.context.get(var_name, 0)
                try:
                    return float(context_value) < value
                except:
                    return False
        elif 'равно' in condition_text:
            match = re.search(r'(\w+)\s+равно\s+(.+)', condition_text)
            if match:
                var_name = match.group(1)
                expected = match.group(2).strip().strip("'\"")
                context_value = str(self.context.get(var_name, ''))
                return context_value == expected
        elif 'содержит' in condition_text:
            match = re.search(r'(\w+)\s+содержит\s+(.+)', condition_text)
            if match:
                var_name = match.group(1)
                substr = match.group(2).strip().strip("'\"")
                context_value = str(self.context.get(var_name, ''))
                return substr in context_value
        return True

    def _execute_loop(self, config: Dict) -> Dict:
        items = config.get('items', [])
        if isinstance(items, str):
            if items in self.context:
                items = self.context[items]
            else:
                try:
                    items = json.loads(items)
                except:
                    items = []
        batch_size = int(config.get('batch_size', 10))
        max_iterations = int(config.get('max_iterations', 1000))
        loop_workflow = config.get('workflow', [])
        processed = 0
        results = []
        for idx, item in enumerate(items[:max_iterations]):
            loop_context = self.context.copy()
            loop_context['loop_item'] = item
            loop_context['loop_index'] = idx
            if loop_workflow:
                sub_executor = WorkflowExecutor(loop_workflow, self.api_key, self.agent_manager, self.table_manager)
                sub_executor.context = loop_context
                sub_result = sub_executor.execute()
                results.append(sub_result)
                if sub_result['success']:
                    self.context.update(sub_executor.context)
            processed += 1
            if processed % batch_size == 0:
                pass
        return {'items': items, 'processed': processed, 'total': len(items), 'batch_size': batch_size, 'results_summary': results}

    def _execute_http_get(self, config: Dict) -> Dict:
        url = config.get('url', '')
        if not url:
            return {'error': 'URL не указан'}
        try:
            response = requests.get(url, timeout=CONFIG.API_TIMEOUT)
            return {'status': response.status_code, 'data': response.json() if response.status_code == 200 else None, 'url': url}
        except Exception as e:
            return {'error': str(e)}

    def _execute_http_post(self, config: Dict) -> Dict:
        url = config.get('url', '')
        if not url:
            return {'error': 'URL не указан'}
        try:
            body = config.get('body', '{}')
            if isinstance(body, str):
                body = json.loads(body)
            response = requests.post(url, json=body, timeout=CONFIG.API_TIMEOUT)
            return {'status': response.status_code, 'data': response.json() if response.status_code == 200 else None, 'url': url}
        except Exception as e:
            return {'error': str(e)}

    def _execute_email(self, config: Dict) -> Dict:
        to = config.get('to', '')
        subject = config.get('subject', '')
        body = config.get('body', '')
        for key, value in self.context.items():
            if isinstance(value, (str, int, float)):
                body = body.replace(f"{{{{{key}}}}}", str(value))
                subject = subject.replace(f"{{{{{key}}}}}", str(value))
        logger.info(f"[EMAIL] To: {to}, Subject: {subject}, Body: {body[:100]}")
        return {'to': to, 'subject': subject, 'body': body, 'status': 'sent (simulated)'}

    def _execute_telegram(self, config: Dict) -> Dict:
        chat_id = config.get('chat_id', '')
        message = config.get('message', '')
        bot_token = config.get('bot_token', st.secrets.get("TELEGRAM_BOT_TOKEN", ""))
        if not bot_token or not chat_id:
            return {'error': 'Не указан bot_token или chat_id'}
        for key, value in self.context.items():
            if isinstance(value, (str, int, float)):
                message = message.replace(f"{{{{{key}}}}}", str(value))
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return {'status': 'sent', 'chat_id': chat_id}
            else:
                return {'error': f"Telegram API ошибка: {response.text}"}
        except Exception as e:
            return {'error': str(e)}

    def _execute_sms(self, config: Dict) -> Dict:
        phone_number = config.get('phone_number', '')
        message = config.get('message', '')
        provider = config.get('provider', 'twilio')
        for key, value in self.context.items():
            if isinstance(value, (str, int, float)):
                message = message.replace(f"{{{{{key}}}}}", str(value))
        if not phone_number or not message:
            return {'error': 'Не указан номер телефона или текст сообщения'}
        if provider == 'twilio':
            try:
                from twilio.rest import Client
                account_sid = config.get('twilio_account_sid', st.secrets.get("TWILIO_ACCOUNT_SID", ""))
                auth_token = config.get('twilio_auth_token', st.secrets.get("TWILIO_AUTH_TOKEN", ""))
                from_number = config.get('twilio_from_number', st.secrets.get("TWILIO_FROM_NUMBER", ""))
                if not account_sid or not auth_token or not from_number:
                    return {'error': 'Не хватает Twilio учетных данных'}
                client = Client(account_sid, auth_token)
                sms = client.messages.create(body=message, from_=from_number, to=phone_number)
                return {'status': 'sent', 'sid': sms.sid, 'provider': 'twilio'}
            except ImportError:
                return {'error': 'Установите twilio: pip install twilio'}
            except Exception as e:
                return {'error': f'Twilio ошибка: {str(e)}'}
        elif provider == 'http':
            api_url = config.get('api_url', 'https://sms.ru/sms/send')
            api_key = config.get('api_key', st.secrets.get("SMS_API_KEY", ""))
            if not api_key:
                return {'error': 'Не указан API ключ для HTTP провайдера'}
            try:
                payload = {'api_id': api_key, 'to': phone_number, 'msg': message, 'json': 1}
                response = requests.post(api_url, data=payload, timeout=10)
                data = response.json()
                if data.get('status_code') == 100:
                    return {'status': 'sent', 'provider': 'http', 'response': data}
                else:
                    return {'error': f"HTTP провайдер вернул ошибку: {data}"}
            except Exception as e:
                return {'error': str(e)}
        else:
            return {'error': f'Неизвестный провайдер: {provider}'}

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
            return {'data': cleaned_df.to_dict('records'), 'rows': len(cleaned_df),
                    'columns': list(cleaned_df.columns), 'df': cleaned_df, 'removed_rows': len(df) - len(cleaned_df)}
        except Exception as e:
            return {'error': str(e)}

    def _execute_pivot_table(self, config: Dict) -> Dict:
        df = config.get('df')
        index = config.get('index', [])
        columns = config.get('columns', [])
        values = config.get('values', [])
        aggfunc = config.get('aggfunc', 'sum')
        if df is None:
            return {'error': 'DataFrame не указан'}
        try:
            pivot = pd.pivot_table(df, index=index if isinstance(index, list) else [index],
                                   columns=columns if isinstance(columns, list) else [columns] if columns else None,
                                   values=values if isinstance(values, list) else [values] if values else None,
                                   aggfunc=aggfunc, fill_value=0)
            return {'data': pivot.to_dict(), 'df': pivot.reset_index(), 'type': 'pivot_table'}
        except Exception as e:
            return {'error': str(e)}
