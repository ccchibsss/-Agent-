# condition_parser.py
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
    ]
    
    @classmethod
    def parse(cls, condition_text: str) -> Dict[str, Any]:
        # [Вставьте оригинальный код метода parse из вашего файла]
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
        # [Вставьте оригинальный код]
        text = re.sub(r'^если\s+', '', text)
        # ... остальной код
        return result
    
    @classmethod
    def _generate_code(cls, pattern_type: str, groups: tuple) -> Optional[str]:
        # [Вставьте оригинальный код]
        templates = {
            'greater': lambda g: f"if {g[0].strip()} > {g[2].strip()}:",
            # ... остальные
        }
        return templates.get(pattern_type, lambda g: None)(groups)
    
    @classmethod
    def _to_python_expr(cls, pattern_type: str, groups: tuple) -> str:
        # [Вставьте оригинальный код]
        pass
    
    @classmethod
    def _extract_variables(cls, text: str) -> List[str]:
        # [Вставьте оригинальный код]
        pass
    
    @classmethod
    def _fallback_parse(cls, text: str) -> Tuple[Optional[str], List[str]]:
        # [Вставьте оригинальный код]
        pass
