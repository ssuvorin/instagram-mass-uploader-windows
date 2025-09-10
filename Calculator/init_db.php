<?php
/**
 * Скрипт инициализации базы данных
 * Версия: 3.0 (с реальной статистикой по платформам за 2025 год)
 */

echo "Инициализация базы данных версии 3.0...\n";

try {
    // Подключаемся к базе данных
    $pdo = new PDO('sqlite:db.sqlite');
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    echo "Подключение к базе данных успешно\n";
    
    // Читаем SQL файл
    $sql = file_get_contents('init_db.sql');
    if (!$sql) {
        throw new Exception('Не удалось прочитать файл init_db.sql');
    }
    
    echo "SQL файл прочитан\n";
    
    // Выполняем SQL
    $pdo->exec($sql);
    
    echo "База данных успешно инициализирована!\n";
    echo "\nСозданы таблицы:\n";
    echo "- base_tariffs (базовые тарифы)\n";
    echo "- country_tariffs (тарифы по странам)\n";
    echo "- market_discounts (рыночные скидки)\n";
    echo "- calculations (расчеты)\n";
    echo "- platform_country_stats (статистика по платформам и странам)\n";
    echo "- country_overview_stats (обзор по странам)\n";
    
    echo "\nЗагружены данные:\n";
    echo "- 30 стран с тарифами (Tier 1, 2, 3)\n";
    echo "- Реальная статистика по платформам за 2025 год:\n";
    echo "  * DAU (Daily Active Users)\n";
    echo "  * MAU (Monthly Active Users)\n";
    echo "  * Количество контента в месяц\n";
    echo "  * Процент вовлеченности\n";
    echo "  * Средняя продолжительность видео\n";
    echo "  * Количество создателей контента\n";
    
    echo "\nИсточники данных:\n";
    echo "- Statista 2025\n";
    echo "- TikTok Analytics 2025\n";
    echo "- YouTube Data 2025\n";
    echo "- Официальные источники стран\n";
    
    echo "\nПлатформы:\n";
    echo "- Instagram\n";
    echo "- TikTok\n";
    echo "- YouTube Shorts\n";
    
} catch (Exception $e) {
    echo "Ошибка: " . $e->getMessage() . "\n";
    exit(1);
}
?>
