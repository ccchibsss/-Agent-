"""
Парсер условий на русском языке
"""
import re
from typing import Dict, List, Any, Optional, Tuple
from config import ConditionType


class RussianConditionParser:
    """Преобразует условия на русском языке в исполняемый код."""
    
    PATTERNS: Dict[str, str] = {
        'greater': r'(.+?)\s+(больше|выше|превышает|>)\s+(.+)',
        'less': r'(.+?)\s+(меньше|ниже|<)\s+(.+)',
        'equal': r'(.+?)\s+(равно|равняется|==|=|есть)\s+(.+)',
        'not_equal': r'(.+?)\s+(не равно|не равняется|!=|<>|не есть)\s+(.+)',
        'contains': r'(.+?)\s+(содержит|включает|имеет|в себе)\s+(.+)',
        'not_contains': r'(.+?)\s+(не содержит|не включает)\s+(.+)',
        'starts_with': r'(.+?)\s+(начинается с|начинается)\s+(.+)',
        'ends_with': r'(.+?)\s+(заканчивается на|заканчивается)\s+(.+)',
        'is_empty': r'(.+?)\s+(пусто|не заполнено|отсутствует|пустое|is empty)',
        'is_not_empty': r'(.+?)\s+(не пусто|заполнено|присутствует)',
        'between': r'(.+?)\s+(между|от)\s+(.+?)\s+(и|до)\s+(.+)',
        'in_list': r'(.+?)\s+(в\s+списке|один из|включая)\s+(.+)',
    }
    
    OPERATOR_MAP: Dict[str, str] = {
        'больше': '>', 'выше': '>', 'превышает': '>',
        'меньше': '<', 'ниже': '<',
        'равно': '==', 'равняется': '==', 'есть': '==',
        'не равно': '!=', 'не равняется': '!=', 'не есть': '!=',
        'содержит': 'in', 'включает': 'in',
        'начинается с': '.startswith(', 'заканчивается на': '.endswith(',
    }
    
    EXAMPLES: List[str] = [
        "если цена больше 1000 то отправить уведомление",
        "если статус равно 'успех' иначе отправить ошибку",
        "если количество меньше 5 то пополнить склад",
        "если текст содержит 'срочно' то отметить как важное",
        "если поле пусто то заполнить значением по умолчанию",
        "если сумма между 1000 и 5000 то одобрить заявку",
        "если имя начинается с 'VIP' то применить скидку",
        "если дата заканчивается на '2024' то архивировать",
    ]
    
    @classmethod
    def parse(cls, condition_text: str) -> Dict[str, Any]:
        """Преобразует русское условие в структурированный формат"""
        condition_text = condition_text.lower().strip()
        
        result: Dict[str, Any] = {
            'original': condition_text,
            'type': ConditionType.CUSTOM.value,
            'condition': condition_text,
            'code': None,
            'python_expr': None,
            'variables': [],
            'examples': cls.EXAMPLES.copy(),
            'errors': [],
            'confidence': 0.0
        }
        
        if 'если' in condition_text:
            result = cls._parse_if_statement(condition_text, result)
            return result
        
        for pattern_type, pattern in cls.PATTERNS.items():
            match = re.search(pattern, condition_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                result['type'] = pattern_type
                result['matches'] = groups
                result['code'] = cls._generate_code(pattern_type, groups)
                result['python_expr'] = cls._to_python_expr(pattern_type, groups)
                result['variables'] = cls._extract_variables(condition_text)
                result['confidence'] = 0.9
                break
        
        if result['code'] is None:
            result['code'], result['errors'] = cls._fallback_parse(condition_text)
            result['confidence'] = 0.5 if result['code'] else 0.0
        
        return result
    
    @classmethod
    def _parse_if_statement(cls, text: str, result: Dict) -> Dict:
        """Парсит конструкцию если-то-иначе"""
        text = re.sub(r'^если\s+', '', text)
        
        then_part = None
        else_part = None
        
        if 'иначе' in text:
            parts = re.split(r'\s+иначе\s+', text)
            text = parts[0]
            else_part = parts[1] if len(parts) > 1 else None
        
        if ' то ' in text:
            parts = text.split(' то ', 1)
            condition = parts[0]
            then_part = parts[1] if len(parts) > 1 else None
        else:
            condition = text
        
        result['type'] = 'if_else' if else_part else 'if_then'
        result['condition'] = condition.strip()
        result['then_action'] = then_part.strip() if then_part else None
        result['else_action'] = else_part.strip() if else_part else None
        
        cond_code = cls._to_python_expr('custom', (condition,))
        result['code'] = f"if {cond_code}:\n    # {then_part or 'действие'}"
        if else_part:
            result['code'] += f"\nelse:\n    # {else_part}"
        
        result['variables'] = cls._extract_variables(condition)
        result['confidence'] = 0.85
        
        return result
    
    @classmethod
    def _generate_code(cls, pattern_type: str, groups: tuple) -> Optional[str]:
        """Генерирует Python-код из распознанного паттерна"""
        templates = {
            'greater': lambda g: f"if {g[0].strip()} > {g[2].strip()}:",
            'less': lambda g: f"if {g[0].strip()} < {g[2].strip()}:",
            'equal': lambda g: f"if {g[0].strip()} == {g[2].strip()}:",
            'not_equal': lambda g: f"if {g[0].strip()} != {g[2].strip()}:",
            'contains': lambda g: f"if {g[2].strip()} in {g[0].strip()}:",
            'not_contains': lambda g: f"if {g[2].strip()} not in {g[0].strip()}:",
            'starts_with': lambda g: f"if {g[0].strip()}.startswith({g[2].strip()}):",
            'ends_with': lambda g: f"if {g[0].strip()}.endswith({g[2].strip()}):",
            'is_empty': lambda g: f"if not {g[0].strip()}:",
            'is_not_empty': lambda g: f"if {g[0].strip()}:",
            'between': lambda g: f"if {g[1].strip()} <= {g[0].strip()} <= {g[3].strip()}:",
        }
        return templates.get(pattern_type, lambda g: None)(groups)
    
    @classmethod
    def _to_python_expr(cls, pattern_type: str, groups: tuple) -> str:
        """Преобразует условие в Python-выражение (без if)"""
        exprs = {
            'greater': lambda g: f"{g[0].strip()} > {g[2].strip()}",
            'less': lambda g: f"{g[0].strip()} < {g[2].strip()}",
            'equal': lambda g: f"{g[0].strip()} == {g[2].strip()}",
            'contains': lambda g: f"{g[2].strip()} in {g[0].strip()}",
            'is_empty': lambda g: f"not {g[0].strip()}",
            'between': lambda g: f"{g[1].strip()} <= {g[0].strip()} <= {g[3].strip()}",
        }
        return exprs.get(pattern_type, lambda g: f"# {pattern_type}: {groups}")(groups)
    
    @classmethod
    def _extract_variables(cls, text: str) -> List[str]:
        """Извлекает имена переменных из условия"""
        vars_found = re.findall(r'\{\{(\w+)\}\}', text)
        if not vars_found:
            words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ_][a-zA-Zа-яА-яЁё0-9_]*\b', text)
            keywords = {'если', 'то', 'иначе', 'и', 'или', 'не', 'больше', 'меньше', 'равно'}
            vars_found = [w for w in words if w.lower() not in keywords and len(w) > 2][:5]
        return vars_found
    
    @classmethod
    def _fallback_parse(cls, text: str) -> Tuple[Optional[str], List[str]]:
        """Резервный парсер для нераспознанных условий"""
        errors: List[str] = []
        
        for rus, eng in cls.OPERATOR_MAP.items():
            text = re.sub(rf'\b{rus}\b', eng, text, flags=re.IGNORECASE)
        
        text = re.sub(r'\{\{(\w+)\}\}', r'data.get("\1", None)', text)
        
        try:
            compile(text, '<string>', 'eval')
            return text, errors
        except SyntaxError as e:
            errors.append(f"Синтаксическая ошибка: {e}")
        
        return None, errors
