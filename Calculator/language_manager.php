<?php
/**
 * Менеджер языков для калькулятора
 */

class LanguageManager {
    private static $instance = null;
    private $translations = [];
    private $currentLanguage = 'ru';
    private $availableLanguages = ['ru', 'en', 'es', 'de'];
    private $languageNames = [
        'ru' => 'Русский',
        'en' => 'English', 
        'es' => 'Español',
        'de' => 'Deutsch'
    ];
    
    private function __construct() {
        $this->loadLanguage();
    }
    
    public static function getInstance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    /**
     * Загрузка языка из кеша или файла
     */
    private function loadLanguage() {
        // Проверяем кеш
        if (isset($_COOKIE['calculator_language']) && in_array($_COOKIE['calculator_language'], $this->availableLanguages)) {
            $this->currentLanguage = $_COOKIE['calculator_language'];
        }
        
        // Загружаем переводы
        $this->loadTranslations();
    }
    
    /**
     * Загрузка переводов для текущего языка
     */
    private function loadTranslations() {
        $languageFile = "languages/{$this->currentLanguage}.php";
        
        if (file_exists($languageFile)) {
            $this->translations = include $languageFile;
        } else {
            // Fallback на русский
            $this->currentLanguage = 'ru';
            $this->translations = include 'languages/ru.php';
        }
    }
    
    /**
     * Получение перевода по ключу
     */
    public function get($key, $default = '') {
        return $this->translations[$key] ?? $default;
    }
    
    /**
     * Установка языка
     */
    public function setLanguage($language) {
        if (in_array($language, $this->availableLanguages)) {
            $this->currentLanguage = $language;
            $this->loadTranslations();
            
            // Сохраняем в кеш на 1 год
            setcookie('calculator_language', $language, time() + (365 * 24 * 60 * 60), '/');
            
            return true;
        }
        return false;
    }
    
    /**
     * Получение текущего языка
     */
    public function getCurrentLanguage() {
        return $this->currentLanguage;
    }
    
    /**
     * Получение доступных языков
     */
    public function getAvailableLanguages() {
        return $this->availableLanguages;
    }
    
    /**
     * Получение названий языков
     */
    public function getLanguageNames() {
        return $this->languageNames;
    }
    
    /**
     * Получение названия текущего языка
     */
    public function getCurrentLanguageName() {
        return $this->languageNames[$this->currentLanguage] ?? 'Unknown';
    }
    
    /**
     * Проверка, является ли язык текущим
     */
    public function isCurrentLanguage($language) {
        return $this->currentLanguage === $language;
    }
    
    /**
     * Получение HTML для переключателя языков
     */
    public function getLanguageSwitcher() {
        $html = '<div class="language-switcher dropdown">';
        $html .= '<button class="btn btn-outline-light dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">';
        $html .= '<i class="bi bi-globe"></i> ' . $this->getCurrentLanguageName();
        $html .= '</button>';
        $html .= '<ul class="dropdown-menu">';
        
        foreach ($this->availableLanguages as $lang) {
            $activeClass = $this->isCurrentLanguage($lang) ? 'active' : '';
            $html .= '<li><a class="dropdown-item ' . $activeClass . '" href="#" data-language="' . $lang . '">';
            $html .= $this->languageNames[$lang];
            $html .= '</a></li>';
        }
        
        $html .= '</ul>';
        $html .= '</div>';
        
        return $html;
    }
    
    /**
     * Получение JavaScript для переключения языков
     */
    public function getLanguageSwitcherScript() {
        return "
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Обработчик переключения языков
            document.querySelectorAll('[data-language]').forEach(function(element) {
                element.addEventListener('click', function(e) {
                    e.preventDefault();
                    const language = this.getAttribute('data-language');
                    
                    // AJAX запрос на смену языка
                    fetch('ajax_handler.php', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: 'action=change_language&language=' + language
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Перезагружаем страницу для применения нового языка
                            window.location.reload();
                        }
                    })
                    .catch(error => {
                        console.error('Language change error:', error);
                    });
                });
            });
        });
        </script>";
    }
}

// Глобальная функция для получения перевода
function __($key, $default = '') {
    return LanguageManager::getInstance()->get($key, $default);
}

// Глобальная функция для получения менеджера языков
function getLanguageManager() {
    return LanguageManager::getInstance();
}
?>
