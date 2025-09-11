<?php
/**
 * Конфигурация калькулятора стоимости продвижения
 */

// Настройки базы данных
define('DB_PATH', 'db.sqlite');

// Курсы валют по ЦБ РФ (актуальные на 2025 год)
define('DEFAULT_USD_RUB', 92.5);  // 1 USD = 92.5 RUB
define('DEFAULT_EUR_RUB', 100.8); // 1 EUR = 100.8 RUB

// Агентские тарифы по объему просмотров (цена за 1 просмотр в рублях)
// Уже с 25% скидкой от розничных цен
define('BASE_TARIFFS', [
    15000000 => 0.041,   // 15-30 млн - 0.041 руб (агентская цена)
    30000000 => 0.038,   // 30-50 млн - 0.038 руб (агентская цена)
    50000000 => 0.034,   // 50-100 млн - 0.034 руб (агентская цена)
    100000000 => 0.030   // 100+ млн - 0.030 руб (агентская цена)
]);

// Множители стоимости по странам (Tier)
define('COUNTRY_MULTIPLIERS', [
    1 => 1.0,    // Tier1 - базовая цена
    2 => 0.85,   // Tier2 - скидка 15%
    3 => 0.7     // Tier3 - скидка 30%
]);

// Множители стоимости по платформам
define('PLATFORM_MULTIPLIERS', [
    'instagram' => 1.0,      // Instagram - базовая цена
    'tiktok' => 1.0,         // TikTok - базовая цена
    'youtube_shorts' => 1.15 // YouTube Shorts - наценка 15%
]);

// Скидки (в процентах)
define('DISCOUNTS', [
    'own_badge' => 3,        // Свой бейдж
    'own_content' => 15,     // Свой контент
    'pilot' => 10,           // Пилотный проект
    'vip_max' => 15,         // Максимальная VIP скидка
    'accounts' => 30,        // Ведение своих аккаунтов
    'bulk_order' => 20       // Массовый заказ (от 5 проектов)
]);

// Надбавки (в процентах)
define('MARKUPS', [
    'difficult_country' => 30,   // Сложная страна
    'urgency' => 40,             // Срочность
    'preholiday' => 15,          // Предпраздничные дни
    'peak_season' => 25,         // Пиковый сезон (декабрь-январь, май-июнь)
    'exclusive_content' => 35,   // Эксклюзивный контент
    'premium_audience' => 20     // Премиум аудитория
]);

// Рыночные скидки по объему (арбитраж)
define('MARKET_DISCOUNTS', [
    50000000 => 5,      // 50 млн+ - скидка 5%
    100000000 => 10,    // 100 млн+ - скидка 10%
    200000000 => 15,    // 200 млн+ - скидка 15%
    500000000 => 20     // 500 млн+ - скидка 20%
]);

// Минимальный объем просмотров
define('MIN_VIEWS_MLN', 15);

// Максимальный объем просмотров для обычного расчета
define('MAX_VIEWS_MLN', 1000);

// Настройки уведомлений
define('NOTIFICATION_TIMEOUT', 5000); // 5 секунд

// Настройки экспорта
define('EXPORT_LIMIT', 10000); // Максимальное количество записей для экспорта

// Настройки статистики
define('STATS_LIMIT', 50); // Количество последних расчетов для отображения

// Цвета для платформ
define('PLATFORM_COLORS', [
    'instagram' => '#E4405F',
    'tiktok' => '#000000',
    'youtube_shorts' => '#FF0000'
]);

// Настройки безопасности
define('ALLOWED_ACTIONS', ['save', 'get_countries', 'get_country_stats', 'get_platform_summary', 'get_global_platform_stats', 'get_top_countries', 'export_csv', 'change_language']);
define('MAX_POST_SIZE', 1048576); // 1MB

// Настройки логирования
define('LOG_ENABLED', true);
define('LOG_FILE', 'calculator.log');

/**
 * Функция логирования
 */
function logMessage($message, $level = 'INFO') {
    if (!LOG_ENABLED) return;
    
    $timestamp = date('Y-m-d H:i:s');
    $logEntry = "[$timestamp] [$level] $message" . PHP_EOL;
    
    file_put_contents(LOG_FILE, $logEntry, FILE_APPEND | LOCK_EX);
}

/**
 * Функция валидации действия
 */
function validateAction($action) {
    return in_array($action, ALLOWED_ACTIONS);
}

/**
 * Функция получения тарифа по объему просмотров
 */
function getTariffByViews($views) {
    foreach (BASE_TARIFFS as $minViews => $price) {
        if ($views >= $minViews) {
            return $price;
        }
    }
    return end(BASE_TARIFFS); // Возвращаем минимальный тариф
}

/**
 * Функция получения рыночной скидки по объему
 */
function getMarketDiscount($views) {
    foreach (MARKET_DISCOUNTS as $minViews => $discount) {
        if ($views >= $minViews) {
            return $discount;
        }
    }
    return 0;
}

/**
 * Функция получения множителя по стране
 */
function getCountryMultiplier($tier) {
    return COUNTRY_MULTIPLIERS[$tier] ?? 1.0;
}

/**
 * Функция получения множителя по платформе
 */
function getPlatformMultiplier($platform) {
    return PLATFORM_MULTIPLIERS[$platform] ?? 1.0;
}

/**
 * Функция форматирования валюты
 */
function formatCurrency($amount, $currency = 'RUB') {
    $symbols = [
        'RUB' => '₽',
        'USD' => '$',
        'EUR' => '€'
    ];
    
    $symbol = $symbols[$currency] ?? $currency;
    
    return number_format($amount, 2, '.', ' ') . ' ' . $symbol;
}

/**
 * Функция проверки размера POST данных
 */
function checkPostSize() {
    if (isset($_SERVER['CONTENT_LENGTH']) && $_SERVER['CONTENT_LENGTH'] > MAX_POST_SIZE) {
        return false;
    }
    return true;
}
?>
