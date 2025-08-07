"""
Crop and Aspect Ratio Handler for Instagram Upload
Handles all crop-related operations during video upload
"""

import time
import random
from .selectors_config import InstagramSelectors, SelectorUtils
from .logging_utils import log_info, log_error, log_warning, log_success, log_debug


class CropHandler:
    """Handles crop and aspect ratio operations for Instagram uploads"""
    
    def __init__(self, page, human_behavior):
        self.page = page
        self.human_behavior = human_behavior
        self.selectors = InstagramSelectors()
    
    def handle_crop_settings(self):
        """Handle crop settings and aspect ratio selection with human behavior"""
        log_info("🖼️ Handling crop settings and aspect ratio selection with human behavior...")
        
        # First, look for the crop/size selection button
        crop_button_found = self._find_and_click_crop_button()
        
        if crop_button_found:
            # Now look for "Оригинал" (Original) aspect ratio option
            aspect_ratio_found = self._select_original_aspect_ratio()
            
            if not aspect_ratio_found:
                log_warning("[WARN] 'Оригинал' aspect ratio option not found, trying fallback options...")
                self._try_fallback_aspect_ratios()
        else:
            log_warning("[WARN] Crop/size selection button not found, trying fallback crop logic")
            self._fallback_crop_logic()
        
        return True
    
    def _find_and_click_crop_button(self):
        """Find and click the crop/size selection button - ADAPTIVE VERSION"""
        log_info("📐 [CROP_BTN] Starting ADAPTIVE crop button search...")
        
        # [TARGET] Адаптивная стратегия поиска (независимо от CSS-классов)
        search_strategies = [
            self._find_by_semantic_attributes,
            self._find_by_svg_content,
            self._find_by_context_analysis,
            self._find_by_fallback_patterns
        ]
        
        for strategy_index, strategy in enumerate(search_strategies, 1):
            log_info(f"📐 [CROP_BTN] Trying strategy {strategy_index}: {strategy.__name__}")
            
            try:
                crop_button = strategy()
                if crop_button:
                    log_success(f"📐 [CROP_BTN] [OK] Found crop button using strategy {strategy_index}")
                    
                    # Клик с человеческим поведением
                    self._human_click_crop_button(crop_button)
                    return True
                    
            except Exception as e:
                log_warning(f"📐 [CROP_BTN] Strategy {strategy_index} failed: {str(e)}")
                continue
        
        log_error("📐 [CROP_BTN] [FAIL] All strategies failed - crop button not found")
        return False
    
    def _find_by_semantic_attributes(self):
        """Поиск по семантическим атрибутам (самый устойчивый)"""
        log_info("📐 [SEMANTIC] Searching by semantic attributes...")
        
        # Семантические селекторы (не зависят от CSS-классов)
        semantic_selectors = [
            'svg[aria-label="Выбрать размер и обрезать"]',
            'svg[aria-label*="Выбрать размер"]',
            'svg[aria-label*="обрезать"]',
            '[aria-label*="Выбрать размер и обрезать"]',
            '[aria-label*="Select crop"]',
            '[aria-label*="Crop"]',
        ]
        
        for selector in semantic_selectors:
            try:
                log_info(f"📐 [SEMANTIC] Trying: {selector}")
                
                # Прямой поиск элемента
                element = self.page.locator(selector).first
                if element.is_visible(timeout=1000):
                    log_success(f"📐 [SEMANTIC] [OK] Found direct element: {selector}")
                    return element
                
                # Поиск родительского элемента
                parent_selectors = [
                    f'button:has({selector})',
                    f'div[role="button"]:has({selector})',
                    f'[role="button"]:has({selector})'
                ]
                
                for parent_selector in parent_selectors:
                    parent_element = self.page.locator(parent_selector).first
                    if parent_element.is_visible(timeout=1000):
                        log_success(f"📐 [SEMANTIC] [OK] Found parent element: {parent_selector}")
                        return parent_element
                    
            except Exception as e:
                log_debug(f"📐 [SEMANTIC] Selector {selector} failed: {str(e)}")
                continue
        
        return None
    
    def _find_by_svg_content(self):
        """Поиск по содержимому SVG (анализ путей и форм)"""
        log_info("📐 [SVG] Searching by SVG content analysis...")
        
        try:
            # Находим все SVG элементы на странице
            svg_elements = self.page.locator('svg').all()
            log_info(f"📐 [SVG] Found {len(svg_elements)} SVG elements")
            
            for svg in svg_elements:
                try:
                    # Проверяем aria-label
                    aria_label = svg.get_attribute('aria-label') or ""
                    if any(keyword in aria_label.lower() for keyword in ['crop', 'обрез', 'размер', 'выбрать']):
                        log_success(f"📐 [SVG] [OK] Found by aria-label: {aria_label}")
                        
                        # Найти родительскую кнопку
                        parent_button = svg.locator('xpath=ancestor::button[1] | xpath=ancestor::div[@role="button"][1]').first
                        if parent_button.is_visible():
                            return parent_button
                        return svg
                    
                    # Анализ SVG paths (ищем характерные пути для иконки кропа)
                    paths = svg.locator('path').all()
                    for path in paths:
                        path_data = path.get_attribute('d') or ""
                        # Характерные пути для иконки кропа (углы, рамки)
                        if any(pattern in path_data for pattern in ['M10 20H4v-6', 'M20.999 2H14', 'L', 'H', 'V']):
                            log_success(f"📐 [SVG] [OK] Found by SVG path pattern")
                            
                            # Найти родительскую кнопку
                            parent_button = svg.locator('xpath=ancestor::button[1] | xpath=ancestor::div[@role="button"][1]').first
                            if parent_button.is_visible():
                                return parent_button
                            return svg
                            
                except Exception as e:
                    log_debug(f"📐 [SVG] SVG analysis failed: {str(e)}")
                    continue
                    
        except Exception as e:
            log_warning(f"📐 [SVG] SVG content analysis failed: {str(e)}")
        
        return None
    
    def _find_by_context_analysis(self):
        """Поиск по контекстному анализу (где обычно находится кнопка кропа)"""
        log_info("📐 [CONTEXT] Searching by context analysis...")
        
        try:
            # Ищем кнопки в контексте редактирования видео
            context_selectors = [
                'button[type="button"]:has(svg)',  # Кнопки с SVG
                'div[role="button"]:has(svg)',     # Div-кнопки с SVG
                '[role="button"]:has(svg)',       # Любые кнопки с SVG
            ]
            
            for selector in context_selectors:
                try:
                    buttons = self.page.locator(selector).all()
                    log_info(f"📐 [CONTEXT] Found {len(buttons)} buttons with selector: {selector}")
                    
                    for button in buttons:
                        # Проверяем размер и позицию (кнопка кропа обычно небольшая)
                        bbox = button.bounding_box()
                        if bbox and 10 <= bbox['width'] <= 50 and 10 <= bbox['height'] <= 50:
                            # Проверяем наличие SVG внутри
                            svg_inside = button.locator('svg').first
                            if svg_inside.is_visible():
                                log_success(f"📐 [CONTEXT] [OK] Found candidate button by context")
                                return button
                                
                except Exception as e:
                    log_debug(f"📐 [CONTEXT] Context selector {selector} failed: {str(e)}")
                    continue
                    
        except Exception as e:
            log_warning(f"📐 [CONTEXT] Context analysis failed: {str(e)}")
        
        return None
    
    def _find_by_fallback_patterns(self):
        """Поиск по резервным паттернам (последний resort)"""
        log_info("📐 [FALLBACK] Using fallback patterns...")
        
        try:
            # XPath селекторы (самые мощные)
            xpath_selectors = [
                '//svg[contains(@aria-label, "Выбрать размер")]',
                '//svg[contains(@aria-label, "обрезать")]',
                '//svg[contains(@aria-label, "Select crop")]',
                '//svg[contains(@aria-label, "Crop")]',
                '//button[.//svg[contains(@aria-label, "Выбрать размер")]]',
                '//div[@role="button" and .//svg[contains(@aria-label, "Выбрать размер")]]',
                '//button[.//svg[contains(@aria-label, "Select crop")]]',
                '//div[@role="button" and .//svg[contains(@aria-label, "Select crop")]]',
            ]
            
            for xpath in xpath_selectors:
                try:
                    log_info(f"📐 [FALLBACK] Trying XPath: {xpath}")
                    element = self.page.locator(f'xpath={xpath}').first
                    if element.is_visible(timeout=1000):
                        log_success(f"📐 [FALLBACK] [OK] Found by XPath: {xpath}")
                        return element
                        
                except Exception as e:
                    log_debug(f"📐 [FALLBACK] XPath {xpath} failed: {str(e)}")
                    continue
                    
        except Exception as e:
            log_warning(f"📐 [FALLBACK] Fallback patterns failed: {str(e)}")
        
        return None
    
    def _human_click_crop_button(self, crop_button):
        """Человеческий клик по кнопке кропа"""
        try:
            log_info("📐 [CLICK] Performing human-like click on crop button...")
            
            # Убеждаемся что элемент видим
            crop_button.wait_for(state='visible', timeout=5000)
            
            # Человеческая задержка перед кликом
            time.sleep(random.uniform(0.5, 1.2))
            
            # Двигаем мышь к элементу
            crop_button.hover()
            time.sleep(random.uniform(0.2, 0.5))
            
            # Клик
            crop_button.click()
            
            # Человеческая задержка после клика
            time.sleep(random.uniform(0.8, 1.5))
            
            log_success("📐 [CLICK] [OK] Successfully clicked crop button")
            
        except Exception as e:
            log_error(f"📐 [CLICK] [FAIL] Failed to click crop button: {str(e)}")
            raise
    
    def _debug_available_buttons(self):
        """Debug function to show available crop-related buttons"""
        try:
            log_info("[SEARCH] [CROP_DEBUG] Searching for all buttons with crop-related content...")
            
            # Find all buttons
            all_buttons = self.page.query_selector_all('button, div[role="button"]')
            crop_related = []
            
            for button in all_buttons[:15]:  # Limit to first 15 buttons
                try:
                    if button.is_visible():
                        # Check button text
                        text = button.text_content() or ""
                        aria_label = button.get_attribute('aria-label') or ""
                        classes = button.get_attribute('class') or ""
                        
                        # Look for crop-related content
                        crop_keywords = ['crop', 'обрез', 'размер', 'size', 'оригинал', 'original', 'выбрать']
                        combined_text = (text + " " + aria_label).lower()
                        
                        if any(keyword in combined_text for keyword in crop_keywords):
                            crop_related.append({
                                'text': text.strip(),
                                'aria_label': aria_label,
                                'classes': classes[:80]  # Limit class length
                            })
                        
                        # Also check if button has SVG with crop-related aria-label
                        try:
                            svg = button.query_selector('svg')
                            if svg:
                                svg_label = svg.get_attribute('aria-label') or ""
                                if any(keyword in svg_label.lower() for keyword in crop_keywords):
                                    crop_related.append({
                                        'text': f"Button with SVG: {svg_label}",
                                        'aria_label': aria_label,
                                        'classes': classes[:80]
                                    })
                        except:
                            pass
                            
                except Exception as e:
                    continue
            
            if crop_related:
                log_info(f"[SEARCH] [CROP_DEBUG] Found {len(crop_related)} crop-related buttons:")
                for i, btn in enumerate(crop_related):
                    log_info(f"[SEARCH] [CROP_DEBUG] Button {i+1}: text='{btn['text']}', aria='{btn['aria_label']}', classes='{btn['classes'][:50]}...'")
            else:
                log_warning("[SEARCH] [CROP_DEBUG] No crop-related buttons found")
                
        except Exception as e:
            log_warning(f"[SEARCH] [CROP_DEBUG] Debug failed: {str(e)}")
    
    def _select_original_aspect_ratio(self):
        """Select the 'Оригинал' (Original) aspect ratio option - IMPROVED for dynamic selectors"""
        log_info("📐 Looking for 'Оригинал' (Original) aspect ratio option...")
        
        # [TARGET] АДАПТИВНАЯ СТРАТЕГИЯ: Поиск по семантическим признакам
        search_strategies = [
            self._find_original_by_text_content,
            self._find_original_by_svg_icon,
            self._find_original_by_first_position,
            self._find_any_available_option
        ]
        
        for strategy_index, strategy in enumerate(search_strategies, 1):
            log_info(f"📐 [ORIGINAL] Trying strategy {strategy_index}: {strategy.__name__}")
            
            try:
                original_element = strategy()
                if original_element:
                    log_success(f"📐 [ORIGINAL] [OK] Found 'Оригинал' using strategy {strategy_index}")
                    
                    # Human-like interaction with aspect ratio selection
                    _human_click_with_timeout(self.page, original_element, self.human_behavior, "ASPECT_RATIO")
                    
                    # Wait for aspect ratio to be applied
                    aspect_ratio_wait = self.human_behavior.get_human_delay(2.0, 0.5) if self.human_behavior else random.uniform(1.5, 2.5)
                    log_info(f"[WAIT] Waiting {aspect_ratio_wait:.1f}s for 'Оригинал' aspect ratio to be applied...")
                    time.sleep(aspect_ratio_wait)
                    
                    return True
                    
            except Exception as e:
                log_warning(f"📐 [ORIGINAL] Strategy {strategy_index} failed: {str(e)}")
                continue
        
        log_warning("📐 [ORIGINAL] [WARN] All strategies failed to find 'Оригинал' option")
        return False
    
    def _find_original_by_text_content(self):
        """Поиск 'Оригинал' по текстовому содержимому"""
        log_info("📐 [TEXT] Searching for 'Оригинал' by text content...")
        
        # Семантические селекторы по тексту (независимы от CSS-классов)
        text_selectors = [
            # Прямой поиск span с текстом "Оригинал"
            'span:has-text("Оригинал")',
            'span:has-text("Original")',
            
            # Поиск родительских элементов
            'div[role="button"]:has(span:has-text("Оригинал"))',
            'button:has(span:has-text("Оригинал"))',
            'div[role="button"]:has(span:has-text("Original"))',
            'button:has(span:has-text("Original"))',
            
            # Прямой поиск по тексту в кнопках
            'button:has-text("Оригинал")',
            'div[role="button"]:has-text("Оригинал")',
            'button:has-text("Original")',
            'div[role="button"]:has-text("Original")',
            
            # XPath селекторы (самые точные)
            '//span[text()="Оригинал"]',
            '//span[text()="Original"]',
            '//div[@role="button" and .//span[text()="Оригинал"]]',
            '//button[.//span[text()="Оригинал"]]',
            '//div[@role="button" and .//span[text()="Original"]]',
            '//button[.//span[text()="Original"]]',
        ]
        
        for selector in text_selectors:
            try:
                log_info(f"📐 [TEXT] Trying: {selector}")
                
                if selector.startswith('//'):
                    element = self.page.query_selector(f"xpath={selector}")
                else:
                    element = self.page.query_selector(selector)
                
                if element and element.is_visible():
                    # Если найден span, найти родительскую кнопку
                    if selector.startswith('span:'):
                        parent_button = element.query_selector('xpath=ancestor::*[@role="button"][1] | xpath=ancestor::button[1]')
                        if parent_button and parent_button.is_visible():
                            log_success(f"📐 [TEXT] [OK] Found 'Оригинал' parent button")
                            return parent_button
                    
                    log_success(f"📐 [TEXT] [OK] Found 'Оригинал' element: {selector}")
                    return element
                    
            except Exception as e:
                log_debug(f"📐 [TEXT] Selector {selector} failed: {str(e)}")
                continue
        
        return None
    
    def _find_original_by_svg_icon(self):
        """Поиск 'Оригинал' по SVG иконке"""
        log_info("📐 [SVG] Searching for 'Оригинал' by SVG icon...")
        
        try:
            # Поиск SVG с характерными aria-label для "Оригинал"
            svg_selectors = [
                # Из предоставленного HTML
                'svg[aria-label="Значок контура фото"]',
                'svg[aria-label*="контур"]',
                'svg[aria-label*="фото"]',
                'svg[aria-label*="photo"]',
                'svg[aria-label*="outline"]',
                'svg[aria-label*="original"]',
                'svg[aria-label*="Оригинал"]',
                
                # XPath для более точного поиска
                '//svg[@aria-label="Значок контура фото"]',
                '//svg[contains(@aria-label, "контур")]',
                '//svg[contains(@aria-label, "фото")]',
                '//svg[contains(@aria-label, "photo")]',
                '//svg[contains(@aria-label, "outline")]',
            ]
            
            for selector in svg_selectors:
                try:
                    if selector.startswith('//'):
                        svg_element = self.page.query_selector(f"xpath={selector}")
                    else:
                        svg_element = self.page.query_selector(selector)
                    
                    if svg_element and svg_element.is_visible():
                        log_success(f"📐 [SVG] [OK] Found SVG icon: {selector}")
                        
                        # Найти родительскую кнопку
                        parent_button = svg_element.query_selector('xpath=ancestor::*[@role="button"][1] | xpath=ancestor::button[1]')
                        if parent_button and parent_button.is_visible():
                            log_success("📐 [SVG] [OK] Found parent button for SVG")
                            return parent_button
                        
                        return svg_element
                        
                except Exception as e:
                    log_debug(f"📐 [SVG] SVG selector {selector} failed: {str(e)}")
                    continue
                    
        except Exception as e:
            log_warning(f"📐 [SVG] SVG search failed: {str(e)}")
        
        return None
    
    def _find_original_by_first_position(self):
        """Поиск 'Оригинал' по позиции (обычно первый элемент)"""
        log_info("📐 [POS] Searching for 'Оригинал' by position...")
        
        try:
            # Найти все кнопки опций кропа
            position_selectors = [
                'div[role="button"][tabindex="0"]',
                'button[tabindex="0"]',
                '[role="button"][tabindex="0"]',
                'div[role="button"]:has(span)',
                'button:has(span)',
            ]
            
            for selector in position_selectors:
                try:
                    buttons = self.page.query_selector_all(selector)
                    
                    if buttons:
                        log_info(f"📐 [POS] Found {len(buttons)} buttons with selector: {selector}")
                        
                        # Проверить первые несколько кнопок
                        for i, button in enumerate(buttons[:4]):
                            try:
                                if button.is_visible():
                                    button_text = button.text_content() or ""
                                    
                                    # Если содержит "Оригинал" - точное совпадение
                                    if 'Оригинал' in button_text or 'Original' in button_text:
                                        log_success(f"📐 [POS] [OK] Found 'Оригинал' at position {i+1}: '{button_text.strip()}'")
                                        return button
                                    
                                    # Если первая кнопка - возможно это "Оригинал"
                                    if i == 0:
                                        log_info(f"📐 [POS] [OK] Using first button as potential 'Оригинал': '{button_text.strip()}'")
                                        return button
                                        
                            except Exception as e:
                                log_debug(f"📐 [POS] Button {i+1} check failed: {str(e)}")
                                continue
                                
                except Exception as e:
                    log_debug(f"📐 [POS] Position selector {selector} failed: {str(e)}")
                    continue
                    
        except Exception as e:
            log_warning(f"📐 [POS] Position search failed: {str(e)}")
        
        return None
    
    def _find_any_available_option(self):
        """Поиск любой доступной опции кропа (fallback)"""
        log_info("📐 [ANY] Searching for any available crop option...")
        
        try:
            # Самые широкие селекторы
            fallback_selectors = [
                # XPath для первой доступной кнопки
                '(//div[@role="button" and @tabindex="0"])[1]',
                '(//button[@tabindex="0"])[1]',
                '(//div[@role="button"])[1]',
                '(//button)[1]',
                
                # CSS селекторы
                'div[role="button"][tabindex="0"]:first-child',
                'button[tabindex="0"]:first-child',
                'div[role="button"]:first-child',
                'button:first-child',
            ]
            
            for selector in fallback_selectors:
                try:
                    if selector.startswith('(//') or selector.startswith('//'):
                        element = self.page.query_selector(f"xpath={selector}")
                    else:
                        element = self.page.query_selector(selector)
                    
                    if element and element.is_visible():
                        element_text = element.text_content() or ""
                        log_info(f"📐 [ANY] [OK] Found fallback option: '{element_text.strip()}' with selector: {selector}")
                        return element
                        
                except Exception as e:
                    log_debug(f"📐 [ANY] Fallback selector {selector} failed: {str(e)}")
                    continue
                    
        except Exception as e:
            log_warning(f"📐 [ANY] Fallback search failed: {str(e)}")
        
        return None
    
    def _try_fallback_aspect_ratios(self):
        """Try fallback aspect ratio options"""
        for selector in self.selectors.FALLBACK_ASPECT_RATIOS:
            try:
                if selector.startswith('//'):
                    fallback_button = self.page.query_selector(f"xpath={selector}")
                else:
                    fallback_button = self.page.query_selector(selector)
                
                if fallback_button and fallback_button.is_visible():
                    button_text = fallback_button.text_content() or ""
                    log_info(f"📐 Found fallback aspect ratio option: '{button_text.strip()}'")
                    _human_click_with_timeout(self.page, fallback_button, self.human_behavior, "FALLBACK_ASPECT")
                    time.sleep(2)
                    break
                    
            except Exception as e:
                continue
    
    def _fallback_crop_logic(self):
        """Fallback to original crop logic"""
        original_selectors = [
            'button:has-text("Оригинал")',
            'button:has-text("Original")',
        ]
        
        for selector in original_selectors:
            try:
                original_button = self.page.query_selector(selector)
                if original_button and original_button.is_visible():
                    log_info(f"📐 Found fallback 'Оригинал' button: {selector}")
                    _human_click_with_timeout(self.page, original_button, self.human_behavior, "ORIGINAL_FALLBACK")
                    time.sleep(2)
                    break
            except Exception as e:
                continue


def handle_crop_and_aspect_ratio(page, human_behavior):
    """
    Standalone function to handle crop and aspect ratio selection
    Maintains backward compatibility with existing code
    """
    try:
        crop_handler = CropHandler(page, human_behavior)
        return crop_handler.handle_crop_settings()
    except Exception as e:
        log_error(f"Error in crop handling: {str(e)}")
        return False


def _quick_click(page, element, log_prefix="QUICK_CLICK"):
    """Quick click without verbose Playwright logs"""
    try:
        # Try force click first (fastest)
        element.click(force=True, timeout=3000)
        log_info(f"[{log_prefix}] [OK] Quick click successful")
        return True
    except Exception as e:
        try:
            # Fallback to JavaScript click
            page.evaluate('(element) => element.click()', element)
            log_info(f"[{log_prefix}] [OK] JavaScript click successful")
            return True
        except Exception as e2:
            # Last resort: standard click with short timeout
            try:
                element.click(timeout=2000)
                log_info(f"[{log_prefix}] [OK] Standard click successful")
                return True
            except Exception as e3:
                log_warning(f"[{log_prefix}] [WARN] All click methods failed: {str(e3)[:100]}")
                return False 


def _human_click_with_timeout(page, element, human_behavior, log_prefix="HUMAN_CLICK"):
    """Human-like click with short timeout to avoid verbose logs"""
    try:
        if human_behavior:
            # Set shorter timeout to avoid long retry loops
            original_timeout = page._timeout_settings.default_timeout if hasattr(page, '_timeout_settings') else 30000
            page.set_default_timeout(5000)  # 5 seconds max
            
            try:
                human_behavior.advanced_element_interaction(element, 'click')
                log_info(f"[{log_prefix}] [OK] Human click successful")
                
                # Restore original timeout
                page.set_default_timeout(original_timeout)
                return True
                
            except Exception as e:
                # Restore timeout even if failed
                page.set_default_timeout(original_timeout)
                log_warning(f"[{log_prefix}] Human behavior failed: {str(e)[:100]}")
                
                # Fallback to quick click
                return _quick_click(page, element, log_prefix)
        else:
            # No human behavior available, use quick click
            return _quick_click(page, element, log_prefix)
            
    except Exception as e:
        log_error(f"[{log_prefix}] Error in human click: {str(e)[:100]}")
        return False 