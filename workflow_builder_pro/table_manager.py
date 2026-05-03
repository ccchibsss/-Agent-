"""
Менеджер для работы с таблицами (Google Sheets и Excel)
Расширенная версия с поддержкой ИИ-трансформаций, отката изменений и CSV
"""
import json
import re
import pandas as pd
import requests
from io import BytesIO
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from openai import OpenAI

from config import CONFIG
from utils import handle_errors, cache_result, logger

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False
    openpyxl = None


class TableManager:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._cache: Dict[str, pd.DataFrame] = {}
        self._last_operation: Optional[Dict] = None
        self._history: Dict[str, List[pd.DataFrame]] = {}

    @handle_errors(default_return=None)
    def read_google_sheets(self, url: str, sheet_name: Optional[str] = None,
                           range_a1: Optional[str] = None, use_cache: bool = True) -> Optional[pd.DataFrame]:
        if '/d/' in url:
            sheet_id = url.split('/d/')[1].split('/')[0]
        else:
            sheet_id = url
        cache_key = f"gsheets:{sheet_id}:{sheet_name}:{range_a1}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key].copy()
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export"
        params = {'format': 'csv'}
        if sheet_name:
            params['gid'] = self._get_sheet_gid(url, sheet_name)
        if range_a1:
            params['range'] = range_a1
        response = requests.get(csv_url, params=params, timeout=CONFIG.API_TIMEOUT)
        response.raise_for_status()
        df = pd.read_csv(BytesIO(response.content))
        if use_cache:
            self._cache[cache_key] = df.copy()
        self._last_operation = {'type': 'read', 'source': 'google_sheets', 'rows': len(df),
                                'columns': list(df.columns), 'timestamp': datetime.now().isoformat()}
        return df

    def _get_sheet_gid(self, url: str, sheet_name: str) -> Optional[str]:
        return None

    @handle_errors(default_return=None)
    def read_excel(self, file_path: Union[str, BytesIO], sheet_name: Optional[Union[str, int]] = 0,
                   range_a1: Optional[str] = None, use_cache: bool = True) -> Optional[pd.DataFrame]:
        if not EXCEL_SUPPORT:
            raise ImportError("Установите openpyxl: pip install openpyxl")
        cache_key = f"excel:{hash(str(file_path))}:{sheet_name}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key].copy()
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl',
                           **({'usecols': range_a1} if range_a1 else {}))
        if use_cache:
            self._cache[cache_key] = df.copy()
        self._last_operation = {'type': 'read', 'source': 'excel', 'rows': len(df),
                                'columns': list(df.columns), 'timestamp': datetime.now().isoformat()}
        return df

    @handle_errors(default_return=False)
    def write_excel(self, df: pd.DataFrame, output_path: str, sheet_name: str = 'Sheet1',
                    apply_formatting: bool = True, formatting_rules: Optional[Dict] = None) -> bool:
        if not EXCEL_SUPPORT:
            raise ImportError("Требуется openpyxl")
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            if apply_formatting:
                self._apply_excel_formatting(writer, df, formatting_rules)
        return True

    def _apply_excel_formatting(self, writer, df, rules):
        worksheet = writer.sheets[writer.sheet_names[0]]
        for column in worksheet.columns:
            max_length = max((len(str(cell.value)) if cell.value else 0) for cell in column)
            col_letter = column[0].column_letter
            worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
        header_fill = PatternFill(start_color="667eea", end_color="764ba2", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        if rules:
            self._apply_custom_rules(worksheet, df, rules)

    def _apply_custom_rules(self, worksheet, df, rules):
        if rules.get('conditional_format'):
            for rule in rules['conditional_format']:
                col_name = rule.get('column')
                condition = rule.get('condition')
                format_config = rule.get('format', {})
                if col_name in df.columns:
                    col_idx = df.columns.get_loc(col_name) + 1
                    self._apply_conditional_format(worksheet, col_idx, len(df)+1, condition, format_config)

    def _apply_conditional_format(self, worksheet, col_idx, max_row, condition, format_config):
        fill_color = format_config.get('color', 'FFEB3B')
        for row in range(2, max_row+1):
            cell = worksheet.cell(row=row, column=col_idx)
            value = cell.value
            if condition == 'highlight_negatives' and isinstance(value, (int, float)) and value < 0:
                cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
            elif condition == 'highlight_high' and isinstance(value, (int, float)) and value > 1000:
                cell.fill = PatternFill(start_color='90EE90', end_color='90EE90', fill_type="solid")

    @cache_result()
    def ai_analyze_dataframe(self, df: pd.DataFrame, instruction: str, api_key: str) -> Dict[str, Any]:
        if not api_key:
            return {'error': 'API ключ не указан'}
        df_summary = {
            'shape': df.shape,
            'columns': list(df.columns),
            'dtypes': {str(k): str(v) for k, v in df.dtypes.to_dict().items()},
            'sample': df.head(5).to_dict('records'),
            'null_counts': df.isnull().sum().to_dict(),
            'stats': df.describe(include='all').to_dict() if not df.empty else {}
        }
        client = OpenAI(api_key=api_key, base_url=CONFIG.DEEPSEEK_BASE_URL)
        prompt = f"""
Ты эксперт по анализу данных в Python pandas.

ДАННЫЕ:
{json.dumps(df_summary, ensure_ascii=False, default=str)[:8000]}

ЗАДАЧА: {instruction}

Верни ответ в формате JSON:
{{
    "analysis": "Краткий анализ данных на русском",
    "issues_found": ["список проблем"],
    "recommendations": ["список рекомендаций"],
    "transformations": [
        {{
            "type": "clean|filter|aggregate|pivot|format|drop_rows|drop_columns|merge|groupby",
            "code": "pandas код для выполнения",
            "description": "что делает этот код"
        }}
    ],
    "ready_code": "полный готовый код для копирования"
}}
"""
        try:
            response = client.chat.completions.create(
                model=CONFIG.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "Ты аналитик данных. Отвечай только валидным JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                timeout=CONFIG.API_TIMEOUT,
                max_tokens=CONFIG.MAX_TOKENS
            )
            content = response.choices[0].message.content
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                json_str = json_match.group()
                json_str = re.sub(r'//[^\n]*', '', json_str)
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                return json.loads(json_str)
            return {'error': 'Не удалось извлечь JSON'}
        except Exception as e:
            return {'error': f'Ошибка ИИ: {str(e)}'}

    def execute_transformation(self, df: pd.DataFrame, transformation_code: str) -> pd.DataFrame:
        dangerous_patterns = ['os.', 'subprocess', '__import__', 'eval(', 'exec(', 'open(', 'file(']
        for pattern in dangerous_patterns:
            if pattern in transformation_code:
                raise ValueError(f"Запрещённая операция: {pattern}")
        import numpy as np
        safe_globals = {"pd": pd, "np": np, "df": df.copy()}
        exec(transformation_code, safe_globals)
        return safe_globals.get('df', df)

    def save_to_history(self, table_id: str, df: pd.DataFrame):
        if table_id not in self._history:
            self._history[table_id] = []
        self._history[table_id].append(df.copy())
        if len(self._history[table_id]) > 10:
            self._history[table_id].pop(0)

    def undo_last(self, table_id: str) -> Optional[pd.DataFrame]:
        if table_id in self._history and len(self._history[table_id]) > 1:
            self._history[table_id].pop()
            return self._history[table_id][-1].copy()
        return None

    @handle_errors(default_return=None)
    def ai_edit_excel_file(self, input_file: Union[str, BytesIO], instruction: str,
                           api_key: str, sheet_name: Union[str, int] = 0,
                           file_type: str = "excel") -> Dict[str, Any]:
        result = {
            'success': False,
            'df': None,
            'output_bytes': None,
            'transformations_applied': [],
            'message': '',
            'error': None
        }
        if file_type == "csv":
            if isinstance(input_file, BytesIO):
                df = pd.read_csv(input_file)
            else:
                df = pd.read_csv(input_file)
        else:
            df = self.read_excel(input_file, sheet_name=sheet_name, use_cache=False)
        if df is None:
            result['error'] = "Не удалось прочитать файл"
            return result
        table_id = f"edit_{datetime.now().timestamp()}"
        self.save_to_history(table_id, df)
        ai_res = self.ai_analyze_dataframe(df, instruction, api_key)
        if 'error' in ai_res:
            result['error'] = f"Ошибка ИИ: {ai_res['error']}"
            return result
        current_df = df.copy()
        applied = []
        for trans in ai_res.get('transformations', []):
            code = trans.get('code')
            if not code:
                continue
            try:
                self.save_to_history(table_id, current_df)
                current_df = self.execute_transformation(current_df, code)
                applied.append(trans.get('description', code[:50]))
            except Exception as e:
                result['error'] = f"Ошибка выполнения трансформации: {e}"
                undo_df = self.undo_last(table_id)
                if undo_df is not None:
                    current_df = undo_df
                    result['message'] += f" Откат из-за ошибки: {e}"
                else:
                    return result
        result['df'] = current_df
        result['transformations_applied'] = applied
        output = BytesIO()
        if file_type == "csv":
            current_df.to_csv(output, index=False)
            mime = "text/csv"
        else:
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                current_df.to_excel(writer, sheet_name='Sheet1', index=False)
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        output.seek(0)
        result['output_bytes'] = output
        result['success'] = True
        result['message'] = f"✅ Применено {len(applied)} изменений"
        return result
