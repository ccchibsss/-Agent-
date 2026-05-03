"""
Менеджер для массовой обработки изображений с ИИ.
"""
import streamlit as st
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Tuple
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
from io import BytesIO
import re
import json
import logging
from openai import OpenAI
from config import CONFIG, IMAGES_DIR
from utils import handle_errors, image_to_base64, ImageEditOperation

# Попытка импорта rembg
try:
    from rembg import remove
except ImportError:
    remove = None

logger = logging.getLogger(__name__)


class ImageManager:
    """Менеджер для массовой обработки изображений с ИИ"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.processed_count = 0
        self.total_count = 0
        
    def remove_background(self, image: Image.Image) -> Image.Image:
        """Удаляет фон с изображения используя rembg"""
        if remove is None:
            raise ImportError("Установите rembg: pip install rembg")
        
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        output = remove(img_byte_arr.read())
        return Image.open(BytesIO(output))
    
    def remove_watermark_basic(self, image: Image.Image) -> Image.Image:
        """Базовое удаление водяного знака (инпейнтинг)"""
        img_array = np.array(image)
        
        if image.mode == 'RGBA':
            alpha = img_array[:, :, 3]
            watermark_mask = (alpha < 200) & (alpha > 50)
        else:
            gray = np.mean(img_array, axis=2)
            watermark_mask = (gray > 240) | (gray < 20)
        
        result_array = img_array.copy()
        
        if np.any(watermark_mask):
            avg_color = np.mean(img_array[~watermark_mask], axis=0)
            result_array[watermark_mask] = avg_color
        
        return Image.fromarray(result_array.astype(np.uint8))
    
    def resize_image(self, image: Image.Image, width: Optional[int] = None, 
                     height: Optional[int] = None, maintain_aspect: bool = True) -> Image.Image:
        """Изменяет размер изображения"""
        if width is None and height is None:
            return image
        
        if maintain_aspect:
            img_width, img_height = image.size
            if width and height:
                ratio = min(width / img_width, height / img_height)
            elif width:
                ratio = width / img_width
            else:
                ratio = height / img_height
            
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
        else:
            new_width = width or image.size[0]
            new_height = height or image.size[1]
        
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def crop_image(self, image: Image.Image, left: int, top: int, 
                   right: int, bottom: int) -> Image.Image:
        """Обрезает изображение"""
        return image.crop((left, top, right, bottom))
    
    def rotate_image(self, image: Image.Image, angle: float, expand: bool = True) -> Image.Image:
        """Поворачивает изображение"""
        return image.rotate(angle, expand=expand, resample=Image.Resampling.BICUBIC)
    
    def enhance_image(self, image: Image.Image, brightness: float = 1.0, 
                      contrast: float = 1.0, sharpness: float = 1.0) -> Image.Image:
        """Улучшает изображение"""
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(brightness)
        
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(contrast)
        
        if sharpness != 1.0:
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(sharpness)
        
        return image
    
    def apply_filter(self, image: Image.Image, filter_type: str) -> Image.Image:
        """Применяет фильтр к изображению"""
        filters = {
            'blur': ImageFilter.BLUR,
            'sharpen': ImageFilter.SHARPEN,
            'edge_enhance': ImageFilter.EDGE_ENHANCE,
            'contour': ImageFilter.CONTOUR,
            'emboss': ImageFilter.EMBOSS,
            'smooth': ImageFilter.SMOOTH,
            'detail': ImageFilter.DETAIL,
        }
        
        if filter_type in filters:
            return image.filter(filters[filter_type])
        return image
    
    def add_text_watermark(self, image: Image.Image, text: str, position: str = "bottom-right",
                           font_size: int = 40, opacity: int = 128, 
                           color: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
        """Добавляет текстовый водяной знак"""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        txt_layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        draw = ImageDraw.Draw(txt_layer)
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        img_width, img_height = image.size
        padding = 20
        
        if position == "top-left":
            x, y = padding, padding
        elif position == "top-right":
            x, y = img_width - text_width - padding, padding
        elif position == "bottom-left":
            x, y = padding, img_height - text_height - padding
        else:  # bottom-right
            x, y = img_width - text_width - padding, img_height - text_height - padding
        
        draw.text((x, y), text, font=font, fill=(*color, opacity))
        return Image.alpha_composite(image, txt_layer)
    
    def convert_format(self, image: Image.Image, format: str) -> Image.Image:
        """Конвертирует изображение в другой формат"""
        if format.upper() in ['JPEG', 'JPG']:
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                return background
            return image.convert('RGB')
        return image
    
    def ai_edit_image(self, image: Image.Image, instruction: str) -> Dict[str, Any]:
        """Использует ИИ для редактирования изображения"""
        if not self.api_key:
            return {'error': 'API ключ не указан'}
        
        try:
            client = OpenAI(api_key=self.api_key, base_url=CONFIG.DEEPSEEK_BASE_URL)
            
            img_base64 = image_to_base64(image)
            
            prompt = f"""
Ты эксперт по редактированию изображений.

Инструкция: {instruction}

Предложи параметры для редактирования в формате JSON:
{{
    "operations": [
        {{
            "type": "resize|crop|enhance|filter",
            "params": {{...}}
        }}
    ],
    "description": "что будет сделано"
}}
"""
            
            response = client.chat.completions.create(
                model=CONFIG.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "Ты эксперт по обработке изображений."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                timeout=CONFIG.API_TIMEOUT,
                max_tokens=CONFIG.MAX_TOKENS
            )
            
            content = response.choices[0].message.content
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
            
            return {'error': 'Не удалось получить ответ от ИИ'}
            
        except Exception as e:
            return {'error': f'Ошибка ИИ: {str(e)}'}
    
    def process_batch(self, images: List[Tuple[str, Image.Image]], 
                      operation: ImageEditOperation, 
                      params: Dict[str, Any],
                      progress_callback: Optional[Callable] = None) -> List[Tuple[str, Image.Image]]:
        """Обрабатывает пакет изображений"""
        self.total_count = len(images)
        self.processed_count = 0
        results = []
        
        for filename, image in images:
            try:
                processed = self._apply_operation(image, operation, params)
                results.append((filename, processed))
                
                self.processed_count += 1
                if progress_callback:
                    progress_callback(self.processed_count, self.total_count, filename)
                    
            except Exception as e:
                logger.error(f"Ошибка обработки {filename}: {e}")
                results.append((filename, None))
        
        return results
    
    def _apply_operation(self, image: Image.Image, operation: ImageEditOperation, 
                         params: Dict[str, Any]) -> Image.Image:
        """Применяет операцию к изображению"""
        if operation == ImageEditOperation.REMOVE_BACKGROUND:
            return self.remove_background(image)
        elif operation == ImageEditOperation.REMOVE_WATERMARK:
            return self.remove_watermark_basic(image)
        elif operation == ImageEditOperation.RESIZE:
            return self.resize_image(
                image, 
                width=params.get('width'),
                height=params.get('height'),
                maintain_aspect=params.get('maintain_aspect', True)
            )
        elif operation == ImageEditOperation.CROP:
            return self.crop_image(
                image,
                params.get('left', 0),
                params.get('top', 0),
                params.get('right', image.size[0]),
                params.get('bottom', image.size[1])
            )
        elif operation == ImageEditOperation.ROTATE:
            return self.rotate_image(
                image, 
                params.get('angle', 0),
                params.get('expand', True)
            )
        elif operation == ImageEditOperation.ENHANCE:
            return self.enhance_image(
                image,
                brightness=params.get('brightness', 1.0),
                contrast=params.get('contrast', 1.0),
                sharpness=params.get('sharpness', 1.0)
            )
        elif operation == ImageEditOperation.FILTER:
            return self.apply_filter(image, params.get('filter_type', 'blur'))
        elif operation == ImageEditOperation.ADD_WATERMARK:
            return self.add_text_watermark(
                image,
                text=params.get('text', 'Watermark'),
                position=params.get('position', 'bottom-right'),
                font_size=params.get('font_size', 40),
                opacity=params.get('opacity', 128),
                color=tuple(params.get('color', [255, 255, 255]))
            )
        elif operation == ImageEditOperation.CONVERT_FORMAT:
            return self.convert_format(image, params.get('format', 'PNG'))
        return image
