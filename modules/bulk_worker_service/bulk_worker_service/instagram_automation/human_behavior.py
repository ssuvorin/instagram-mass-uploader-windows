"""
Human Behavior Simulation for Instagram Automation
Provides realistic human-like behavior patterns
"""

import time
import random
import math
from datetime import datetime, timedelta
from .logging_utils import log_info, log_warning, log_error


class AdvancedHumanBehavior:
    """Advanced human behavior simulation for Instagram automation"""
    
    def __init__(self, page):
        self.page = page
        self.typing_speed_base = 0.1  # Base typing speed
        self.typing_speed_variance = 0.05  # Variance in typing speed
        self.mouse_movement_speed = 1.0  # Mouse movement speed multiplier
        
        # Новые параметры для улучшенного поведения
        self.user_profile = self._generate_user_profile()
        self.session_start_time = datetime.now()
        self.action_count = 0
        self.fatigue_level = 0.0
        self.last_error_time = None
        
    def _generate_user_profile(self):
        """Генерируем профиль пользователя для персонализированного поведения"""
        profiles = [
            {
                'type': 'careful',
                'speed_multiplier': 1.3,
                'error_rate': 0.02,
                'pause_probability': 0.15,
                'description': 'Осторожный пользователь'
            },
            {
                'type': 'normal',
                'speed_multiplier': 1.0,
                'error_rate': 0.05,
                'pause_probability': 0.10,
                'description': 'Обычный пользователь'
            },
            {
                'type': 'fast',
                'speed_multiplier': 0.7,
                'error_rate': 0.08,
                'pause_probability': 0.05,
                'description': 'Быстрый пользователь'
            },
            {
                'type': 'distracted',
                'speed_multiplier': 1.5,
                'error_rate': 0.12,
                'pause_probability': 0.25,
                'description': 'Рассеянный пользователь'
            }
        ]
        
        profile = random.choice(profiles)
        log_info(f"[HUMAN_PROFILE] Generated profile: {profile['description']}")
        return profile
    
    def get_time_based_multiplier(self):
        """Получить множитель задержки в зависимости от времени суток"""
        current_hour = datetime.now().hour
        
        # Утренние часы (6-10): более медленное поведение
        if 6 <= current_hour <= 10:
            return random.uniform(1.2, 1.8)
        # Рабочие часы (11-17): нормальное поведение
        elif 11 <= current_hour <= 17:
            return random.uniform(0.8, 1.2)
        # Вечерние часы (18-22): более активное поведение
        elif 18 <= current_hour <= 22:
            return random.uniform(0.6, 1.0)
        # Ночные часы (23-5): очень медленное, сонное поведение
        else:
            return random.uniform(1.5, 2.5)
    
    def calculate_fatigue_level(self):
        """Вычислить уровень усталости на основе времени сессии и количества действий"""
        session_duration = (datetime.now() - self.session_start_time).total_seconds() / 60  # в минутах
        
        # Усталость растет со временем и количеством действий
        time_fatigue = min(session_duration / 30, 2.0)  # Максимум 2x через 30 минут
        action_fatigue = min(self.action_count / 50, 1.5)  # Максимум 1.5x через 50 действий
        
        self.fatigue_level = 1.0 + (time_fatigue * 0.3) + (action_fatigue * 0.2)
        return self.fatigue_level
    
    def get_advanced_human_delay(self, base_delay=1.0, variance=0.5, context='general'):
        """
        Улучшенная генерация человеческих задержек с учетом всех факторов
        
        Args:
            base_delay: Базовая задержка
            variance: Вариативность
            context: Контекст действия ('typing', 'clicking', 'thinking', 'resting')
        """
        self.action_count += 1
        
        # Базовые множители для разных контекстов
        context_multipliers = {
            'typing': 1.0,
            'clicking': 0.7,
            'thinking': 1.5,
            'resting': 2.0,
            'reading': 1.2,
            'general': 1.0
        }
        
        # Применяем все множители
        time_multiplier = self.get_time_based_multiplier()
        fatigue_multiplier = self.calculate_fatigue_level()
        profile_multiplier = self.user_profile['speed_multiplier']
        context_multiplier = context_multipliers.get(context, 1.0)
        
        # Итоговая задержка
        total_multiplier = time_multiplier * fatigue_multiplier * profile_multiplier * context_multiplier
        adjusted_delay = base_delay * total_multiplier
        
        # Добавляем случайную вариативность с нормальным распределением
        final_delay = random.normalvariate(adjusted_delay, variance * adjusted_delay / 3)
        
        # Ограничиваем разумными пределами
        min_delay = base_delay * 0.3
        max_delay = base_delay * 5.0
        final_delay = max(min_delay, min(max_delay, final_delay))
        
        log_info(f"[HUMAN_DELAY] Context: {context}, Base: {base_delay:.2f}s, "
                f"Final: {final_delay:.2f}s (Time: {time_multiplier:.2f}x, "
                f"Fatigue: {fatigue_multiplier:.2f}x, Profile: {profile_multiplier:.2f}x)")
        
        return final_delay
    
    def simulate_break_pattern(self):
        """Симуляция естественных перерывов в активности"""
        break_probability = 0.1 + (self.fatigue_level - 1.0) * 0.2
        
        if random.random() < break_probability:
            # Разные типы перерывов
            break_types = [
                {'type': 'micro', 'duration': (2, 8), 'probability': 0.6},
                {'type': 'short', 'duration': (10, 30), 'probability': 0.3},
                {'type': 'medium', 'duration': (60, 180), 'probability': 0.1}
            ]
            
            break_type = random.choices(
                break_types, 
                weights=[bt['probability'] for bt in break_types]
            )[0]
            
            duration = random.uniform(*break_type['duration'])
            
            log_info(f"[HUMAN_BREAK] Taking {break_type['type']} break for {duration:.1f}s")
            time.sleep(duration)
            
            # Сбрасываем некоторую усталость после перерыва
            if break_type['type'] in ['short', 'medium']:
                self.fatigue_level = max(1.0, self.fatigue_level - 0.3)
    
    def advanced_error_simulation(self, element, text):
        """Улучшенная симуляция ошибок при печати"""
        error_rate = self.user_profile['error_rate']
        
        # Увеличиваем вероятность ошибок при усталости
        adjusted_error_rate = error_rate * self.fatigue_level
        
        # Увеличиваем вероятность ошибок после недавних ошибок (фрустрация)
        if self.last_error_time and (datetime.now() - self.last_error_time).seconds < 30:
            adjusted_error_rate *= 1.5
        
        typed_text = ""
        i = 0
        
        while i < len(text):
            char = text[i]
            
            # Проверяем на ошибку
            if random.random() < adjusted_error_rate and i > 0:
                self.last_error_time = datetime.now()
                
                # Разные типы ошибок
                error_types = ['wrong_char', 'double_char', 'skip_char', 'transpose']
                error_type = random.choice(error_types)
                
                if error_type == 'wrong_char':
                    # Неправильный символ (соседние клавиши)
                    wrong_char = self._get_adjacent_key(char)
                    element.type(wrong_char)
                    typed_text += wrong_char
                    
                    # Пауза для "осознания" ошибки
                    time.sleep(self.get_advanced_human_delay(0.5, 0.3, 'thinking'))
                    
                    # Исправляем
                    element.press('Backspace')
                    typed_text = typed_text[:-1]
                    time.sleep(self.get_advanced_human_delay(0.2, 0.1, 'clicking'))
                
                elif error_type == 'double_char':
                    # Двойной символ
                    element.type(char + char)
                    typed_text += char + char
                    
                    time.sleep(self.get_advanced_human_delay(0.4, 0.2, 'thinking'))
                    
                    # Исправляем лишний символ
                    element.press('Backspace')
                    typed_text = typed_text[:-1]
                    time.sleep(self.get_advanced_human_delay(0.1, 0.05, 'clicking'))
                
                elif error_type == 'transpose' and i < len(text) - 1:
                    # Перестановка символов
                    next_char = text[i + 1]
                    element.type(next_char + char)
                    typed_text += next_char + char
                    
                    time.sleep(self.get_advanced_human_delay(0.6, 0.3, 'thinking'))
                    
                    # Исправляем
                    element.press('Backspace')
                    element.press('Backspace')
                    typed_text = typed_text[:-2]
                    time.sleep(self.get_advanced_human_delay(0.2, 0.1, 'clicking'))
                    
                    # Печатаем правильно
                    element.type(char)
                    typed_text += char
                    i += 1  # Пропускаем следующий символ, так как уже обработали
            
            # Обычная печать
            element.type(char)
            typed_text += char
            
            # Адаптивная скорость печати
            typing_delay = self.get_advanced_human_delay(
                self.typing_speed_base, 
                self.typing_speed_variance, 
                'typing'
            )
            time.sleep(typing_delay)
            
            i += 1
        
        # Пауза после печати
        time.sleep(self.get_advanced_human_delay(0.5, 0.2, 'general'))
    
    def _get_adjacent_key(self, char):
        """Получить соседнюю клавишу для симуляции опечатки"""
        keyboard_layout = {
            'q': ['w', 'a'], 'w': ['q', 'e', 's'], 'e': ['w', 'r', 'd'],
            'r': ['e', 't', 'f'], 't': ['r', 'y', 'g'], 'y': ['t', 'u', 'h'],
            'u': ['y', 'i', 'j'], 'i': ['u', 'o', 'k'], 'o': ['i', 'p', 'l'],
            'p': ['o', 'l'], 'a': ['q', 's', 'z'], 's': ['w', 'a', 'd', 'x'],
            'd': ['e', 's', 'f', 'c'], 'f': ['r', 'd', 'g', 'v'],
            'g': ['t', 'f', 'h', 'b'], 'h': ['y', 'g', 'j', 'n'],
            'j': ['u', 'h', 'k', 'm'], 'k': ['i', 'j', 'l'], 'l': ['o', 'k', 'p'],
            'z': ['a', 's', 'x'], 'x': ['z', 's', 'd', 'c'], 'c': ['x', 'd', 'f', 'v'],
            'v': ['c', 'f', 'g', 'b'], 'b': ['v', 'g', 'h', 'n'],
            'n': ['b', 'h', 'j', 'm'], 'm': ['n', 'j', 'k']
        }
        
        adjacent_keys = keyboard_layout.get(char.lower(), ['x'])
        return random.choice(adjacent_keys)
    
    def simulate_realistic_mouse_behavior(self, target_element):
        """Более реалистичное поведение мыши"""
        try:
            box = target_element.bounding_box()
            if not box:
                return
            
            # Получаем текущую позицию курсора (приблизительно)
            current_x, current_y = self.page.mouse.get_position() if hasattr(self.page.mouse, 'get_position') else (400, 300)
            
            # Целевая позиция с некоторым разбросом
            target_x = box['x'] + box['width'] * random.uniform(0.2, 0.8)
            target_y = box['y'] + box['height'] * random.uniform(0.2, 0.8)
            
            # Вычисляем расстояние
            distance = math.sqrt((target_x - current_x)**2 + (target_y - current_y)**2)
            
            # Время движения зависит от расстояния (закон Фитца)
            movement_time = 0.1 + (distance / 1000) * random.uniform(0.8, 1.2)
            
            # Движение через промежуточные точки для естественности
            steps = max(3, int(distance / 100))
            
            for step in range(steps):
                progress = (step + 1) / steps
                
                # Добавляем небольшие отклонения для естественности
                deviation_x = random.uniform(-5, 5) * (1 - progress)  # Уменьшаем отклонение к концу
                deviation_y = random.uniform(-5, 5) * (1 - progress)
                
                intermediate_x = current_x + (target_x - current_x) * progress + deviation_x
                intermediate_y = current_y + (target_y - current_y) * progress + deviation_y
                
                self.page.mouse.move(intermediate_x, intermediate_y)
                time.sleep(movement_time / steps)
            
            # Финальная позиция
            self.page.mouse.move(target_x, target_y)
            
            # Пауза перед кликом
            time.sleep(self.get_advanced_human_delay(0.1, 0.05, 'clicking'))
            
        except Exception as e:
            log_warning(f"Advanced mouse movement failed: {str(e)}")

    def get_human_delay(self, base_delay=1.0, variance=0.5):
        """
        Generate human-like delay with natural variance
        
        Args:
            base_delay: Base delay in seconds
            variance: Maximum variance as fraction of base_delay
        
        Returns:
            float: Randomized delay time
        """
        min_delay = base_delay * (1 - variance)
        max_delay = base_delay * (1 + variance)
        
        # Use normal distribution for more realistic timing
        delay = random.normalvariate(base_delay, variance * base_delay / 3)
        
        # Clamp to reasonable bounds
        delay = max(min_delay, min(max_delay, delay))
        
        return delay
    
    def simulate_reading_time(self, text_length):
        """
        Simulate time needed to read text (average reading speed: 200-250 WPM)
        
        Args:
            text_length: Length of text to read
            
        Returns:
            float: Reading time in seconds
        """
        words_per_minute = random.uniform(200, 250)
        estimated_words = text_length / 5  # Average word length
        reading_time = (estimated_words / words_per_minute) * 60
        
        # Add some variance and minimum time
        reading_time = max(1.0, reading_time * random.uniform(0.8, 1.2))
        
        return reading_time
    
    def natural_mouse_movement(self, target_element):
        """
        Simulate natural mouse movement to element
        
        Args:
            target_element: Element to move mouse to
        """
        try:
            # Get element position
            box = target_element.bounding_box()
            if not box:
                return
            
            # Calculate target position (slightly randomized within element)
            target_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            target_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
            
            # Move mouse in natural arc
            self.page.mouse.move(target_x, target_y)
            
            # Small pause after movement
            time.sleep(self.get_human_delay(0.1, 0.05))
            
        except Exception as e:
            log_warning(f"Mouse movement simulation failed: {str(e)}")
    
    def human_typing(self, element, text, simulate_mistakes=True):
        """
        Type text with human-like behavior including mistakes and corrections
        
        Args:
            element: Element to type into
            text: Text to type
            simulate_mistakes: Whether to simulate typing mistakes
        """
        try:
            # Click on element first
            element.click()
            time.sleep(self.get_human_delay(0.3, 0.1))
            
            # Clear existing content
            element.fill('')
            time.sleep(self.get_human_delay(0.2, 0.1))
            
            if simulate_mistakes:
                self.advanced_error_simulation(element, text)
            else:
                # Simple typing without errors
                for char in text:
                    element.type(char)
                    typing_delay = self.get_human_delay(self.typing_speed_base, self.typing_speed_variance)
                    time.sleep(typing_delay)
            
        except Exception as e:
            log_warning(f"Human typing simulation failed: {str(e)}")
            # Fallback to simple fill
            element.fill(text)
    
    def simulate_decision_making(self, options_count=1):
        """
        Simulate time needed for decision making
        
        Args:
            options_count: Number of options to consider
        """
        base_time = 0.5 + (options_count * 0.3)
        decision_time = self.get_human_delay(base_time, 0.3)
        time.sleep(decision_time)
    
    def simulate_page_scanning(self):
        """Simulate time spent scanning/reading page content"""
        scan_time = self.get_human_delay(2.0, 1.0)
        time.sleep(scan_time)
    
    def simulate_distraction(self):
        """
        Simulate brief distraction/pause in activity
        """
        if random.random() < 0.1:  # 10% chance of distraction
            distraction_time = self.get_human_delay(2.0, 1.0)
            log_info(f"Simulating brief distraction for {distraction_time:.1f}s")
            time.sleep(distraction_time)
    
    def advanced_element_interaction(self, element, action='click'):
        """
        Perform advanced interaction with element including natural movement
        
        Args:
            element: Element to interact with
            action: Type of interaction ('click', 'hover', etc.)
        """
        try:
            # Ensure element is in viewport
            element.scroll_into_view_if_needed()
            time.sleep(self.get_human_delay(0.2, 0.1))
            
            # Natural mouse movement to element
            self.simulate_realistic_mouse_behavior(element)
            
            # Brief pause before action
            time.sleep(self.get_human_delay(0.1, 0.05))
            
            # Perform action
            if action == 'click':
                element.click()
            elif action == 'hover':
                element.hover()
            
            # Brief pause after action
            time.sleep(self.get_human_delay(0.2, 0.1))
            
        except Exception as e:
            log_warning(f"Advanced element interaction failed: {str(e)}")
            # Fallback to simple action
            if action == 'click':
                element.click()
            elif action == 'hover':
                element.hover()

    def simulate_ui_exploration(self, page):
        """Симулируем естественное изучение интерфейса"""
        log_info("👁️ [HUMAN] Exploring UI naturally...")
        
        try:
            # Получаем видимые элементы для изучения
            clickable_elements = page.query_selector_all('button, a, input, [role="button"]')
            visible_elements = [elem for elem in clickable_elements if elem.is_visible()]
            
            # Случайно выбираем несколько элементов для "рассматривания"
            elements_to_examine = random.sample(visible_elements, min(3, len(visible_elements)))
            
            for element in elements_to_examine:
                try:
                    # Наводим мышь на элемент (как будто рассматриваем)
                    box = element.bounding_box()
                    if box:
                        # Движение к элементу
                        target_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
                        target_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
                        page.mouse.move(target_x, target_y)
                        
                        # Пауза на "чтение" элемента
                        element_text = element.text_content() or ""
                        if element_text:
                            read_time = self.simulate_reading_time(len(element_text))
                            time.sleep(min(read_time, 2.0))  # Максимум 2 секунды на элемент
                        else:
                            time.sleep(self.get_advanced_human_delay(0.5, 0.3, 'reading'))
                            
                except Exception:
                    continue
                    
        except Exception as e:
            log_warning(f"UI exploration failed: {str(e)}")
    
    def simulate_natural_scroll(self, page, direction='down', amount='small'):
        """Симулируем естественный скролл"""
        log_info(f"📜 [HUMAN] Natural scroll {direction} ({amount})")
        
        try:
            # Определяем параметры скролла
            scroll_amounts = {
                'small': random.randint(100, 300),
                'medium': random.randint(400, 800),
                'large': random.randint(900, 1500)
            }
            
            scroll_distance = scroll_amounts.get(amount, 200)
            if direction == 'up':
                scroll_distance = -scroll_distance
            
            # Скроллим с естественными паузами
            steps = random.randint(3, 6)
            step_distance = scroll_distance // steps
            
            for step in range(steps):
                page.mouse.wheel(0, step_distance)
                # Пауза между "толчками" колеса мыши
                step_delay = self.get_advanced_human_delay(0.1, 0.05, 'general')
                time.sleep(step_delay)
            
            # Пауза после скролла для "осмотра" нового контента
            time.sleep(self.get_advanced_human_delay(1.0, 0.5, 'reading'))
            
        except Exception as e:
            log_warning(f"Natural scroll failed: {str(e)}")
    
    def simulate_idle_mouse_movement(self, page, duration=2.0):
        """Симулируем случайные движения мыши во время простоя"""
        log_info(f"🖱️ [HUMAN] Idle mouse movements for {duration:.1f}s")
        
        try:
            start_time = time.time()
            movements = random.randint(2, 5)
            
            for i in range(movements):
                if time.time() - start_time >= duration:
                    break
                
                # Случайные координаты в пределах экрана
                viewport = page.viewport_size
                if viewport:
                    random_x = random.randint(100, viewport['width'] - 100)
                    random_y = random.randint(100, viewport['height'] - 100)
                    
                    # Плавное движение к случайной точке
                    page.mouse.move(random_x, random_y)
                    
                    # Пауза между движениями
                    pause_time = duration / movements
                    time.sleep(pause_time * random.uniform(0.5, 1.5))
                    
        except Exception as e:
            log_warning(f"Idle mouse movement failed: {str(e)}")
    
    def simulate_form_hesitation(self, form_element):
        """Симулируем колебания при заполнении формы"""
        log_info("🤔 [HUMAN] Form filling hesitation...")
        
        try:
            # Наводим мышь на форму несколько раз (как будто колеблемся)
            hesitation_count = random.randint(1, 3)
            
            for _ in range(hesitation_count):
                # Наводим мышь на разные части формы
                box = form_element.bounding_box()
                if box:
                    hover_x = box['x'] + box['width'] * random.uniform(0.2, 0.8)
                    hover_y = box['y'] + box['height'] * random.uniform(0.2, 0.8)
                    form_element.page.mouse.move(hover_x, hover_y)
                    
                    # Пауза "размышления"
                    think_time = self.get_advanced_human_delay(0.5, 0.3, 'thinking')
                    time.sleep(think_time)
                    
        except Exception as e:
            log_warning(f"Form hesitation simulation failed: {str(e)}")
    
    def simulate_attention_shifts(self, page):
        """Симулируем естественные переключения внимания"""
        log_info("[EYES] [HUMAN] Natural attention shifts...")
        
        try:
            # Случайно переключаем внимание между элементами
            attention_targets = [
                'h1', 'h2', 'h3',  # Заголовки
                'button', '[role="button"]',  # Кнопки
                'img', 'svg',  # Изображения
                'input', 'textarea'  # Поля ввода
            ]
            
            selected_targets = random.sample(attention_targets, min(3, len(attention_targets)))
            
            for target_selector in selected_targets:
                try:
                    elements = page.query_selector_all(target_selector)
                    visible_elements = [elem for elem in elements if elem.is_visible()]
                    
                    if visible_elements:
                        target_element = random.choice(visible_elements)
                        
                        # Быстрый взгляд на элемент
                        box = target_element.bounding_box()
                        if box:
                            page.mouse.move(
                                box['x'] + box['width'] / 2,
                                box['y'] + box['height'] / 2
                            )
                            
                            # Короткая пауза "внимания"
                            attention_time = self.get_advanced_human_delay(0.3, 0.2, 'reading')
                            time.sleep(attention_time)
                            
                except Exception:
                    continue
                    
        except Exception as e:
            log_warning(f"Attention shifts simulation failed: {str(e)}")


# Global variable to store human behavior instance
human_behavior = None

class HumanBehaviorMonitor:
    """Мониторинг и анализ человеческого поведения для оптимизации"""
    
    def __init__(self):
        self.action_history = []
        self.error_patterns = []
        self.timing_patterns = []
        self.session_stats = {
            'total_actions': 0,
            'total_errors': 0,
            'average_delay': 0.0,
            'session_duration': 0.0,
            'break_count': 0
        }
    
    def record_action(self, action_type, duration, success=True, context=None):
        """Записать действие для анализа"""
        timestamp = datetime.now()
        
        action_record = {
            'timestamp': timestamp,
            'type': action_type,
            'duration': duration,
            'success': success,
            'context': context or {}
        }
        
        self.action_history.append(action_record)
        self.session_stats['total_actions'] += 1
        
        if not success:
            self.session_stats['total_errors'] += 1
            self.error_patterns.append(action_record)
        
        # Обновляем среднюю задержку
        self.timing_patterns.append(duration)
        self.session_stats['average_delay'] = sum(self.timing_patterns) / len(self.timing_patterns)
        
        # Ограничиваем историю последними 1000 действиями
        if len(self.action_history) > 1000:
            self.action_history = self.action_history[-1000:]
    
    def analyze_behavior_patterns(self):
        """Анализ паттернов поведения для адаптации"""
        if len(self.action_history) < 10:
            return None
        
        analysis = {
            'error_rate': self.session_stats['total_errors'] / self.session_stats['total_actions'],
            'average_action_time': self.session_stats['average_delay'],
            'activity_trend': self._calculate_activity_trend(),
            'optimal_break_intervals': self._suggest_break_intervals(),
            'performance_score': self._calculate_performance_score()
        }
        
        return analysis
    
    def _calculate_activity_trend(self):
        """Вычислить тренд активности"""
        if len(self.timing_patterns) < 20:
            return 'insufficient_data'
        
        recent_times = self.timing_patterns[-10:]
        earlier_times = self.timing_patterns[-20:-10]
        
        recent_avg = sum(recent_times) / len(recent_times)
        earlier_avg = sum(earlier_times) / len(earlier_times)
        
        if recent_avg > earlier_avg * 1.2:
            return 'slowing_down'
        elif recent_avg < earlier_avg * 0.8:
            return 'speeding_up'
        else:
            return 'stable'
    
    def _suggest_break_intervals(self):
        """Предложить оптимальные интервалы перерывов"""
        if len(self.action_history) < 50:
            return 'default'
        
        # Анализируем когда происходят ошибки
        error_positions = []
        for i, action in enumerate(self.action_history):
            if not action['success']:
                error_positions.append(i)
        
        if len(error_positions) >= 3:
            # Вычисляем средний интервал между ошибками
            intervals = [error_positions[i+1] - error_positions[i] for i in range(len(error_positions)-1)]
            avg_error_interval = sum(intervals) / len(intervals) if intervals else 50
            
            # Предлагаем перерывы чаще, чем интервал ошибок
            suggested_interval = max(20, int(avg_error_interval * 0.7))
            return f'every_{suggested_interval}_actions'
        
        return 'standard'
    
    def _calculate_performance_score(self):
        """Вычислить оценку производительности"""
        if self.session_stats['total_actions'] == 0:
            return 0.0
        
        success_rate = 1.0 - (self.session_stats['total_errors'] / self.session_stats['total_actions'])
        
        # Нормализуем среднее время (предполагаем оптимум 1.0 секунда)
        time_efficiency = min(1.0, 1.0 / max(0.1, self.session_stats['average_delay']))
        
        # Комбинируем показатели
        performance_score = (success_rate * 0.7) + (time_efficiency * 0.3)
        
        return min(1.0, performance_score)
    
    def get_recommendations(self):
        """Получить рекомендации по оптимизации поведения"""
        analysis = self.analyze_behavior_patterns()
        if not analysis:
            return ["Недостаточно данных для анализа"]
        
        recommendations = []
        
        if analysis['error_rate'] > 0.1:
            recommendations.append("Слишком высокий уровень ошибок - рекомендуется увеличить задержки")
        
        if analysis['activity_trend'] == 'slowing_down':
            recommendations.append("Обнаружено замедление активности - рекомендуется перерыв")
        
        if analysis['performance_score'] < 0.7:
            recommendations.append("Низкая производительность - рекомендуется оптимизация параметров")
        
        if analysis['average_action_time'] > 3.0:
            recommendations.append("Слишком медленное выполнение - можно ускорить процесс")
        
        return recommendations if recommendations else ["Поведение оптимально"]

# Глобальный монитор поведения
behavior_monitor = HumanBehaviorMonitor()

def init_human_behavior(page):
    """Initialize human behavior for the given page"""
    global human_behavior
    if not human_behavior:
        human_behavior = AdvancedHumanBehavior(page)
        log_info("Human behavior initialized")
    return human_behavior


def get_human_behavior():
    """Get the current human behavior instance"""
    return human_behavior

def get_behavior_monitor():
    """Get the behavior monitoring instance"""
    return behavior_monitor 