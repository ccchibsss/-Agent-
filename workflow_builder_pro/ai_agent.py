import streamlit as st
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from openai import OpenAI
import logging
import pandas as pd
import requests
from io import BytesIO
from config import CONFIG
from utils import save_agents_auto, handle_errors, logger

class AIAgent:
    def __init__(self, name: str, role: str, system_prompt: str, agent_id: Optional[str] = None):
        self.id = agent_id or hashlib.md5(f"{name}{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.created_at = datetime.now().isoformat()
        self.training_examples: List[Dict] = []
        self.memory: List[Dict] = []
        self.conversation_history: List[Dict] = []
        self.knowledge_base: Dict[str, Any] = {}
        self.stats: Dict[str, Any] = {
            'total_trainings': 0,
            'total_conversations': 0,
            'success_rate': 0.0,
            'last_trained': None,
            'last_used': None
        }
    
    def add_training_example(self, user_input: str, expected_output: str, context: str = "") -> Dict:
        example = {
            'id': len(self.training_examples) + 1,
            'user_input': user_input,
            'expected_output': expected_output,
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'used_count': 0
        }
        self.training_examples.append(example)
        self.stats['total_trainings'] += 1
        self.stats['last_trained'] = datetime.now().isoformat()
        return example
    
    def add_to_memory(self, key: str, value: Any, importance: str = "normal") -> Dict:
        memory_item = {
            'key': key,
            'value': value,
            'importance': importance,
            'timestamp': datetime.now().isoformat(),
            'access_count': 0
        }
        existing_idx = None
        for i, mem in enumerate(self.memory):
            if mem['key'] == key:
                existing_idx = i
                break
        if existing_idx is not None:
            self.memory[existing_idx] = memory_item
        else:
            self.memory.append(memory_item)
        return memory_item
    
    def get_from_memory(self, key: str) -> Any:
        for mem in self.memory:
            if mem['key'] == key:
                mem['access_count'] += 1
                return mem['value']
        return None
    
    def add_conversation(self, user_message: str, agent_response: str, feedback: Optional[str] = None):
        conversation = {
            'user': user_message,
            'agent': agent_response,
            'feedback': feedback,
            'timestamp': datetime.now().isoformat(),
            'context': self.get_context_summary()
        }
        self.conversation_history.append(conversation)
        self.stats['total_conversations'] += 1
        self.stats['last_used'] = datetime.now().isoformat()
        if feedback == 'positive':
            self.stats['success_rate'] = (
                self.stats['success_rate'] * (self.stats['total_conversations'] - 1) + 100
            ) / self.stats['total_conversations']
        elif feedback == 'negative':
            self.stats['success_rate'] = (
                self.stats['success_rate'] * (self.stats['total_conversations'] - 1)
            ) / self.stats['total_conversations']
    
    def get_context_summary(self) -> str:
        return (
            f"Роль: {self.role}\n"
            f"Память: {len(self.memory)} фактов\n"
            f"Обучен на: {len(self.training_examples)} примерах\n"
            f"Диалогов: {self.stats['total_conversations']}"
        )
    
    def generate_response(self, user_input: str, api_key: str, use_training: bool = True) -> str:
        if not api_key:
            return "❌ API ключ не указан. Получите бесплатно на platform.deepseek.com"
        try:
            client = OpenAI(api_key=api_key, base_url=CONFIG.DEEPSEEK_BASE_URL)
            memory_context = ""
            if self.memory:
                memory_context = "\n\n🧠 ЗНАНИЯ АГЕНТА (из памяти):\n"
                for mem in self.memory[-5:]:
                    memory_context += f"- {mem['key']}: {mem['value']}\n"
            training_context = ""
            if use_training and self.training_examples:
                training_context = "\n\n📚 ПРИМЕРЫ ОБУЧЕНИЯ:\n"
                for ex in self.training_examples[-3:]:
                    training_context += f"Вопрос: {ex['user_input']}\nОтвет: {ex['expected_output']}\n\n"
            history_context = ""
            if self.conversation_history:
                history_context = "\n\n📜 ИСТОРИЯ ДИАЛОГОВ:\n"
                for conv in self.conversation_history[-3:]:
                    history_context += f"Пользователь: {conv['user']}\nАгент: {conv['agent']}\n\n"
            full_prompt = f"""
Ты - ИИ агент с именем "{self.name}" и ролью "{self.role}".

{self.system_prompt}

{memory_context}

{training_context}

{history_context}

Текущий запрос пользователя: "{user_input}"

Ответь, используя полученные знания, примеры обучения и память.
Будь полезным, точным и дружелюбным. Отвечай на русском языке.
"""
            response = client.chat.completions.create(
                model=CONFIG.DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.7,
                timeout=CONFIG.API_TIMEOUT,
                max_tokens=CONFIG.MAX_TOKENS
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return f"⚠️ Ошибка: {str(e)}"
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'system_prompt': self.system_prompt,
            'created_at': self.created_at,
            'training_examples': self.training_examples,
            'memory': self.memory,
            'conversation_history': self.conversation_history[-50:],
            'knowledge_base': self.knowledge_base,
            'stats': self.stats
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AIAgent':
        agent = cls(
            name=data['name'],
            role=data['role'],
            system_prompt=data['system_prompt'],
            agent_id=data['id']
        )
        agent.created_at = data.get('created_at', datetime.now().isoformat())
        agent.training_examples = data.get('training_examples', [])
        agent.memory = data.get('memory', [])
        agent.conversation_history = data.get('conversation_history', [])
        agent.knowledge_base = data.get('knowledge_base', {})
        agent.stats = data.get('stats', {
            'total_trainings': len(agent.training_examples),
            'total_conversations': len(agent.conversation_history),
            'success_rate': 0.0,
            'last_trained': None,
            'last_used': None
        })
        return agent


class AgentManager:
    def __init__(self, api_key: Optional[str] = None):
        self.agents: Dict[str, AIAgent] = {}
        self.current_agent_id: Optional[str] = None
        self.api_key = api_key
        self.load_agents()
    
    def load_agents(self):
        if 'agents' not in st.session_state:
            default_agents = self._create_default_agents()
            st.session_state.agents = {agent.id: agent.to_dict() for agent in default_agents}
            st.session_state.current_agent_id = default_agents[0].id if default_agents else None
            logger.info("Использованы агенты по умолчанию")
        for agent_id, agent_dict in st.session_state.agents.items():
            if agent_id not in self.agents:
                self.agents[agent_id] = AIAgent.from_dict(agent_dict)
        self.current_agent_id = st.session_state.get('current_agent_id')
    
    def _create_default_agents(self) -> List[AIAgent]:
        agents = []
        analyst = AIAgent(
            name="Аналитик Данных",
            role="эксперт по анализу данных и бизнес-метрикам",
            system_prompt="""Ты профессиональный аналитик данных. Твоя задача:
- Анализировать цифры и метрики
- Находить закономерности и тренды
- Давать практические рекомендации
- Объяснять сложные вещи простым языком"""
        )
        agents.append(analyst)
        automation = AIAgent(
            name="Автоматизатор",
            role="специалист по автоматизации бизнес-процессов",
            system_prompt="""Ты эксперт по автоматизации. Твоя задача:
- Предлагать решения для автоматизации
- Оптимизировать рабочие процессы
- Указывать на узкие места
- Давать пошаговые инструкции"""
        )
        agents.append(automation)
        manager = AIAgent(
            name="Менеджер Задач",
            role="помощник по управлению задачами и проектами",
            system_prompt="""Ты менеджер проектов. Твоя задача:
- Помогать планировать задачи
- Приоритезировать дела
- Напоминать о важных вещах
- Отслеживать прогресс"""
        )
        agents.append(manager)
        return agents
    
    def save_agents(self):
        st.session_state.agents = {agent_id: agent.to_dict() for agent_id, agent in self.agents.items()}
        st.session_state.current_agent_id = self.current_agent_id
        save_agents_auto(st.session_state.agents)
    
    def add_agent(self, name: str, role: str, system_prompt: str) -> AIAgent:
        agent = AIAgent(name, role, system_prompt)
        self.agents[agent.id] = agent
        self.save_agents()
        return agent
    
    def delete_agent(self, agent_id: str):
        if agent_id in self.agents:
            del self.agents[agent_id]
            if self.current_agent_id == agent_id:
                self.current_agent_id = next(iter(self.agents.keys())) if self.agents else None
            self.save_agents()
    
    def get_current_agent(self) -> Optional[AIAgent]:
        if self.current_agent_id and self.current_agent_id in self.agents:
            return self.agents[self.current_agent_id]
        return None
    
    def set_current_agent(self, agent_id: str):
        if agent_id in self.agents:
            self.current_agent_id = agent_id
            st.session_state.current_agent_id = agent_id
            self.save_agents()
    
    def export_agent(self, agent_id: str) -> str:
        if agent_id in self.agents:
            return json.dumps(self.agents[agent_id].to_dict(), ensure_ascii=False, indent=2)
        return ""
    
    def import_agent(self, agent_json: str) -> bool:
        try:
            data = json.loads(agent_json)
            agent = AIAgent.from_dict(data)
            self.agents[agent.id] = agent
            self.save_agents()
            return True
        except Exception as e:
            logger.error(f"Ошибка импорта агента: {e}")
            st.error(f"Ошибка импорта: {str(e)}")
            return False
