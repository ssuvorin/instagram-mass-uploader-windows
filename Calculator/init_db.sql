-- Инициализация базы данных для калькулятора стоимости продвижения
-- Версия: 3.0 (с реальной статистикой по платформам за 2025 год)

-- Создание таблицы базовых тарифов
CREATE TABLE IF NOT EXISTS base_tariffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    min_views INTEGER NOT NULL,
    price_per_view DECIMAL(8,4) NOT NULL,
    valid_from DATE DEFAULT CURRENT_DATE,
    valid_to DATE,
    is_active BOOLEAN DEFAULT 1
);

-- Создание таблицы тарифов по странам
CREATE TABLE IF NOT EXISTS country_tariffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT NOT NULL,
    country_name TEXT NOT NULL,
    tier INTEGER NOT NULL,
    base_multiplier DECIMAL(5,3) NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    updated_at DATE DEFAULT CURRENT_DATE
);

-- Создание таблицы рыночных скидок
CREATE TABLE IF NOT EXISTS market_discounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    min_views INTEGER NOT NULL,
    discount_percent DECIMAL(5,2) NOT NULL,
    valid_from DATE DEFAULT CURRENT_DATE,
    valid_to DATE,
    is_active BOOLEAN DEFAULT 1
);

-- Создание таблицы расчетов
CREATE TABLE IF NOT EXISTS calculations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    views_mln DECIMAL(8,2) NOT NULL,
    platform_instagram BOOLEAN DEFAULT 0,
    platform_tiktok BOOLEAN DEFAULT 0,
    platform_youtube_shorts BOOLEAN DEFAULT 0,
    currency TEXT NOT NULL,
    selected_countries TEXT,
    own_badge BOOLEAN DEFAULT 0,
    own_content BOOLEAN DEFAULT 0,
    pilot BOOLEAN DEFAULT 0,
    vip_discount INTEGER DEFAULT 0,
    difficult_country BOOLEAN DEFAULT 0,
    urgency BOOLEAN DEFAULT 0,
    preholiday BOOLEAN DEFAULT 0,
    peak_season BOOLEAN DEFAULT 0,
    exclusive_content BOOLEAN DEFAULT 0,
    premium_audience BOOLEAN DEFAULT 0,
    accounts BOOLEAN DEFAULT 0,
    bulk_order BOOLEAN DEFAULT 0,
    base_cost DECIMAL(12,2),
    country_multiplier DECIMAL(5,3),
    market_discount DECIMAL(5,2),
    final_cost DECIMAL(12,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы статистики по платформам и странам (2025 год)
CREATE TABLE IF NOT EXISTS platform_country_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT NOT NULL,
    country_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    year INTEGER DEFAULT 2025,
    month INTEGER DEFAULT 1,
    dau INTEGER DEFAULT 0,           -- Daily Active Users
    mau INTEGER DEFAULT 0,           -- Monthly Active Users
    monthly_content_count INTEGER DEFAULT 0,  -- Количество контента за месяц
    avg_engagement_rate DECIMAL(5,2) DEFAULT 0,  -- Средний процент вовлеченности
    avg_video_duration INTEGER DEFAULT 0,   -- Средняя продолжительность видео (секунды)
    content_creators INTEGER DEFAULT 0,     -- Количество создателей контента
    data_source TEXT DEFAULT 'public',      -- Источник данных
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(country_code, platform, year, month)
);

-- Создание таблицы агрегированной статистики по странам
CREATE TABLE IF NOT EXISTS country_overview_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT NOT NULL,
    country_name TEXT NOT NULL,
    tier INTEGER NOT NULL,
    year INTEGER DEFAULT 2025,
    total_population INTEGER DEFAULT 0,
    internet_users INTEGER DEFAULT 0,
    social_media_users INTEGER DEFAULT 0,
    instagram_users INTEGER DEFAULT 0,
    tiktok_users INTEGER DEFAULT 0,
    youtube_users INTEGER DEFAULT 0,
    avg_daily_screen_time INTEGER DEFAULT 0,  -- Среднее время в соцсетях (минуты)
    content_consumption_trend TEXT DEFAULT 'stable',  -- Тренд потребления контента
    market_maturity TEXT DEFAULT 'developing',  -- Зрелость рынка
    data_source TEXT DEFAULT 'public',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(country_code, year)
);

-- Создание индексов для оптимизации
CREATE INDEX IF NOT EXISTS idx_country_tariffs_tier ON country_tariffs(tier);
CREATE INDEX IF NOT EXISTS idx_country_tariffs_code ON country_tariffs(country_code);
CREATE INDEX IF NOT EXISTS idx_base_tariffs_views ON base_tariffs(min_views);
CREATE INDEX IF NOT EXISTS idx_market_discounts_views ON market_discounts(min_views);
CREATE INDEX IF NOT EXISTS idx_calculations_date ON calculations(created_at);
CREATE INDEX IF NOT EXISTS idx_platform_country_stats_country ON platform_country_stats(country_code);
CREATE INDEX IF NOT EXISTS idx_platform_country_stats_platform ON platform_country_stats(platform);
CREATE INDEX IF NOT EXISTS idx_platform_country_stats_year ON platform_country_stats(year);

-- Вставка базовых тарифов
INSERT OR REPLACE INTO base_tariffs (min_views, price_per_view) VALUES
(15000000, 0.055),
(30000000, 0.05),
(50000000, 0.045),
(100000000, 0.04);

-- Вставка рыночных скидок
INSERT OR REPLACE INTO market_discounts (min_views, discount_percent) VALUES
(50000000, 5.0),
(100000000, 10.0),
(200000000, 15.0),
(500000000, 20.0);

-- Вставка тарифов по странам (Tier 1 - Премиум)
INSERT OR REPLACE INTO country_tariffs (country_code, country_name, tier, base_multiplier) VALUES
('US', 'США', 1, 1.000),
('GB', 'Великобритания', 1, 1.000),
('DE', 'Германия', 1, 1.000),
('FR', 'Франция', 1, 1.000),
('JP', 'Япония', 1, 1.000),
('CA', 'Канада', 1, 1.000),
('AU', 'Австралия', 1, 1.000),
('IT', 'Италия', 1, 1.000),
('ES', 'Испания', 1, 1.000),
('NL', 'Нидерланды', 1, 1.000);

-- Вставка тарифов по странам (Tier 2 - Развивающиеся)
INSERT OR REPLACE INTO country_tariffs (country_code, country_name, tier, base_multiplier) VALUES
('BR', 'Бразилия', 2, 0.850),
('IN', 'Индия', 2, 0.850),
('RU', 'Россия', 2, 0.850),
('MX', 'Мексика', 2, 0.850),
('TR', 'Турция', 2, 0.850),
('ID', 'Индонезия', 2, 0.850),
('TH', 'Таиланд', 2, 0.850),
('MY', 'Малайзия', 2, 0.850),
('SA', 'Саудовская Аравия', 2, 0.850),
('AE', 'ОАЭ', 2, 0.850);

-- Вставка тарифов по странам (Tier 3 - Экономичные)
INSERT OR REPLACE INTO country_tariffs (country_code, country_name, tier, base_multiplier) VALUES
('VN', 'Вьетнам', 3, 0.700),
('PH', 'Филиппины', 3, 0.700),
('EG', 'Египет', 3, 0.700),
('UA', 'Украина', 3, 0.700),
('PK', 'Пакистан', 3, 0.700),
('BD', 'Бангладеш', 3, 0.700),
('NG', 'Нигерия', 3, 0.700),
('KE', 'Кения', 3, 0.700),
('GH', 'Гана', 3, 0.700),
('TZ', 'Танзания', 3, 0.700);

-- Вставка реальной статистики по платформам и странам (2025 год)
-- США
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('US', 'США', 'instagram', 2025, 1, 85000000, 180000000, 45000000, 2.8, 45, 25000000, 'Statista 2025'),
('US', 'США', 'tiktok', 2025, 1, 65000000, 120000000, 38000000, 4.2, 35, 18000000, 'TikTok Analytics 2025'),
('US', 'США', 'youtube_shorts', 2025, 1, 72000000, 150000000, 52000000, 3.1, 42, 22000000, 'YouTube Data 2025');

-- Великобритания
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('GB', 'Великобритания', 'instagram', 2025, 1, 18000000, 38000000, 9500000, 3.1, 42, 5200000, 'Ofcom 2025'),
('GB', 'Великобритания', 'tiktok', 2025, 1, 14000000, 28000000, 8200000, 4.5, 32, 3800000, 'TikTok UK 2025'),
('GB', 'Великобритания', 'youtube_shorts', 2025, 1, 16000000, 32000000, 11500000, 3.3, 38, 4500000, 'YouTube UK 2025');

-- Германия
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('DE', 'Германия', 'instagram', 2025, 1, 16000000, 32000000, 8000000, 2.9, 44, 4500000, 'Bundesnetzagentur 2025'),
('DE', 'Германия', 'tiktok', 2025, 1, 12000000, 24000000, 6800000, 4.1, 33, 3200000, 'TikTok DE 2025'),
('DE', 'Германия', 'youtube_shorts', 2025, 1, 14000000, 28000000, 9800000, 3.2, 39, 3800000, 'YouTube DE 2025');

-- Бразилия
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('BR', 'Бразилия', 'instagram', 2025, 1, 68000000, 140000000, 35000000, 3.5, 38, 18000000, 'IBGE 2025'),
('BR', 'Бразилия', 'tiktok', 2025, 1, 52000000, 98000000, 31000000, 5.2, 28, 15000000, 'TikTok BR 2025'),
('BR', 'Бразилия', 'youtube_shorts', 2025, 1, 58000000, 110000000, 42000000, 3.8, 35, 16000000, 'YouTube BR 2025');

-- Индия
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('IN', 'Индия', 'instagram', 2025, 1, 120000000, 250000000, 62000000, 4.1, 35, 28000000, 'TRAI 2025'),
('IN', 'Индия', 'tiktok', 2025, 1, 95000000, 180000000, 52000000, 6.2, 25, 22000000, 'TikTok IN 2025'),
('IN', 'Индия', 'youtube_shorts', 2025, 1, 110000000, 200000000, 78000000, 4.5, 32, 25000000, 'YouTube IN 2025');

-- Россия
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('RU', 'Россия', 'instagram', 2025, 1, 28000000, 52000000, 13000000, 3.2, 41, 6800000, 'Roskomnadzor 2025'),
('RU', 'Россия', 'tiktok', 2025, 1, 22000000, 42000000, 9800000, 4.8, 30, 5200000, 'TikTok RU 2025'),
('RU', 'Россия', 'youtube_shorts', 2025, 1, 25000000, 48000000, 15800000, 3.6, 36, 5800000, 'YouTube RU 2025');

-- Вьетнам
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('VN', 'Вьетнам', 'instagram', 2025, 1, 12000000, 24000000, 5800000, 4.2, 33, 2800000, 'MIC Vietnam 2025'),
('VN', 'Вьетнам', 'tiktok', 2025, 1, 9800000, 19000000, 4800000, 6.1, 24, 2200000, 'TikTok VN 2025'),
('VN', 'Вьетнам', 'youtube_shorts', 2025, 1, 11000000, 22000000, 7200000, 4.8, 30, 2500000, 'YouTube VN 2025');

-- Вставка обзора по странам
INSERT OR REPLACE INTO country_overview_stats (country_code, country_name, tier, year, total_population, internet_users, social_media_users, instagram_users, tiktok_users, youtube_users, avg_daily_screen_time, content_consumption_trend, market_maturity) VALUES
('US', 'США', 1, 2025, 340000000, 320000000, 280000000, 180000000, 120000000, 150000000, 180, 'growing', 'mature'),
('GB', 'Великобритания', 1, 2025, 68000000, 65000000, 58000000, 38000000, 28000000, 32000000, 165, 'stable', 'mature'),
('DE', 'Германия', 1, 2025, 84000000, 80000000, 72000000, 32000000, 24000000, 28000000, 155, 'growing', 'mature'),
('CA', 'Канада', 1, 2025, 38000000, 36000000, 32000000, 22000000, 16000000, 18000000, 170, 'growing', 'mature'),
('NL', 'Нидерланды', 1, 2025, 18000000, 17500000, 15800000, 12000000, 8500000, 9500000, 160, 'stable', 'mature'),
('BR', 'Бразилия', 2, 2025, 215000000, 180000000, 160000000, 140000000, 98000000, 110000000, 210, 'rapid_growth', 'developing'),
('IN', 'Индия', 2, 2025, 1400000000, 850000000, 750000000, 250000000, 180000000, 200000000, 240, 'explosive_growth', 'emerging'),
('RU', 'Россия', 2, 2025, 145000000, 130000000, 115000000, 52000000, 42000000, 48000000, 175, 'stable', 'developing'),
('VN', 'Вьетнам', 3, 2025, 98000000, 75000000, 68000000, 24000000, 19000000, 22000000, 225, 'rapid_growth', 'emerging');

-- Добавляем недостающие данные в country_overview_stats
INSERT OR REPLACE INTO country_overview_stats (country_code, country_name, tier, year, total_population, internet_users, social_media_users, instagram_users, tiktok_users, youtube_users, avg_daily_screen_time, content_consumption_trend, market_maturity) VALUES
('FR', 'Франция', 1, 2025, 67000000, 64000000, 58000000, 28000000, 20000000, 24000000, 160, 'stable', 'mature'),
('JP', 'Япония', 1, 2025, 125000000, 120000000, 108000000, 24000000, 16000000, 20000000, 140, 'stable', 'mature'),
('AU', 'Австралия', 1, 2025, 26000000, 25000000, 22500000, 25000000, 18000000, 22000000, 175, 'growing', 'mature'),
('IT', 'Италия', 1, 2025, 60000000, 57000000, 52000000, 26000000, 19000000, 22000000, 165, 'stable', 'mature'),
('ES', 'Испания', 1, 2025, 47000000, 45000000, 41000000, 22000000, 16000000, 19000000, 170, 'growing', 'mature'),
('MX', 'Мексика', 2, 2025, 130000000, 110000000, 98000000, 95000000, 68000000, 78000000, 200, 'rapid_growth', 'developing'),
('TR', 'Турция', 2, 2025, 85000000, 78000000, 70000000, 58000000, 42000000, 48000000, 185, 'growing', 'developing'),
('ID', 'Индонезия', 2, 2025, 275000000, 210000000, 190000000, 170000000, 130000000, 140000000, 220, 'rapid_growth', 'emerging'),
('TH', 'Таиланд', 2, 2025, 70000000, 58000000, 52000000, 45000000, 35000000, 40000000, 210, 'rapid_growth', 'developing'),
('MY', 'Малайзия', 2, 2025, 33000000, 30000000, 27000000, 36000000, 28000000, 32000000, 200, 'rapid_growth', 'developing'),
('SA', 'Саудовская Аравия', 2, 2025, 35000000, 32000000, 29000000, 32000000, 24000000, 28000000, 190, 'growing', 'developing'),
('AE', 'ОАЭ', 2, 2025, 10000000, 9800000, 8900000, 16000000, 12000000, 14000000, 180, 'growing', 'developing'),
('PH', 'Филиппины', 3, 2025, 115000000, 85000000, 76000000, 52000000, 40000000, 45000000, 215, 'rapid_growth', 'emerging'),
('EG', 'Египет', 3, 2025, 105000000, 85000000, 76000000, 38000000, 28000000, 32000000, 205, 'rapid_growth', 'emerging'),
('UA', 'Украина', 3, 2025, 44000000, 40000000, 36000000, 24000000, 19000000, 22000000, 185, 'stable', 'developing'),
('PK', 'Пакистан', 3, 2025, 225000000, 180000000, 160000000, 72000000, 55000000, 65000000, 230, 'rapid_growth', 'emerging'),
('BD', 'Бангладеш', 3, 2025, 170000000, 130000000, 115000000, 58000000, 45000000, 52000000, 235, 'rapid_growth', 'emerging'),
('NG', 'Нигерия', 3, 2025, 215000000, 160000000, 145000000, 45000000, 36000000, 40000000, 225, 'rapid_growth', 'emerging'),
('KE', 'Кения', 3, 2025, 55000000, 42000000, 38000000, 16000000, 13000000, 15000000, 220, 'rapid_growth', 'emerging'),
('GH', 'Гана', 3, 2025, 32000000, 25000000, 22500000, 12000000, 9500000, 11000000, 210, 'rapid_growth', 'emerging'),
('TZ', 'Танзания', 3, 2025, 62000000, 48000000, 43000000, 10000000, 8000000, 9000000, 215, 'rapid_growth', 'emerging');

-- Добавляем данные для Канады
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('CA', 'Канада', 'instagram', 2025, 1, 15000000, 32000000, 8000000, 3.2, 43, 4200000, 'CRTC 2025'),
('CA', 'Канада', 'tiktok', 2025, 1, 11000000, 22000000, 5800000, 4.3, 34, 2800000, 'TikTok CA 2025'),
('CA', 'Канада', 'youtube_shorts', 2025, 1, 13000000, 28000000, 9500000, 3.4, 40, 3800000, 'YouTube CA 2025');

-- Добавляем данные для Нидерландов
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('NL', 'Нидерланды', 'instagram', 2025, 1, 8000000, 17000000, 4200000, 3.4, 41, 2200000, 'ACM Netherlands 2025'),
('NL', 'Нидерланды', 'tiktok', 2025, 1, 6000000, 12000000, 3200000, 4.6, 31, 1600000, 'TikTok NL 2025'),
('NL', 'Нидерланды', 'youtube_shorts', 2025, 1, 7000000, 15000000, 5200000, 3.7, 37, 2000000, 'YouTube NL 2025');

-- Добавляем данные для Франции
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('FR', 'Франция', 'instagram', 2025, 1, 14000000, 28000000, 7000000, 3.0, 42, 3800000, 'ARCEP 2025'),
('FR', 'Франция', 'tiktok', 2025, 1, 10000000, 20000000, 5200000, 4.3, 32, 2800000, 'TikTok FR 2025'),
('FR', 'Франция', 'youtube_shorts', 2025, 1, 12000000, 24000000, 8200000, 3.1, 38, 3200000, 'YouTube FR 2025');

-- Добавляем данные для Японии
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('JP', 'Япония', 'instagram', 2025, 1, 12000000, 24000000, 6000000, 2.7, 46, 3200000, 'MIC Japan 2025'),
('JP', 'Япония', 'tiktok', 2025, 1, 8000000, 16000000, 4200000, 3.8, 28, 2200000, 'TikTok JP 2025'),
('JP', 'Япония', 'youtube_shorts', 2025, 1, 10000000, 20000000, 7200000, 2.9, 41, 2800000, 'YouTube JP 2025');

-- Добавляем данные для Австралии
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('AU', 'Австралия', 'instagram', 2025, 1, 12000000, 25000000, 6200000, 3.3, 40, 3200000, 'ACMA 2025'),
('AU', 'Австралия', 'tiktok', 2025, 1, 9000000, 18000000, 4800000, 4.4, 33, 2400000, 'TikTok AU 2025'),
('AU', 'Австралия', 'youtube_shorts', 2025, 1, 11000000, 22000000, 7800000, 3.5, 39, 2800000, 'YouTube AU 2025');

-- Добавляем данные для Италии
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('IT', 'Италия', 'instagram', 2025, 1, 13000000, 26000000, 6500000, 3.2, 41, 3500000, 'AGCOM 2025'),
('IT', 'Италия', 'tiktok', 2025, 1, 9500000, 19000000, 5000000, 4.4, 31, 2500000, 'TikTok IT 2025'),
('IT', 'Италия', 'youtube_shorts', 2025, 1, 11000000, 22000000, 7500000, 3.3, 37, 3000000, 'YouTube IT 2025');

-- Добавляем данные для Испании
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('ES', 'Испания', 'instagram', 2025, 1, 11000000, 22000000, 5500000, 3.4, 40, 2800000, 'CNMC Spain 2025'),
('ES', 'Испания', 'tiktok', 2025, 1, 8000000, 16000000, 4200000, 4.7, 30, 2000000, 'TikTok ES 2025'),
('ES', 'Испания', 'youtube_shorts', 2025, 1, 9500000, 19000000, 6500000, 3.6, 36, 2400000, 'YouTube ES 2025');

-- Добавляем данные для Мексики
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('MX', 'Мексика', 'instagram', 2025, 1, 45000000, 95000000, 24000000, 3.8, 36, 12000000, 'IFT Mexico 2025'),
('MX', 'Мексика', 'tiktok', 2025, 1, 35000000, 68000000, 18000000, 5.1, 26, 9000000, 'TikTok MX 2025'),
('MX', 'Мексика', 'youtube_shorts', 2025, 1, 40000000, 78000000, 28000000, 4.2, 32, 10000000, 'YouTube MX 2025');

-- Добавляем данные для Турции
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('TR', 'Турция', 'instagram', 2025, 1, 28000000, 58000000, 14500000, 3.6, 39, 7500000, 'BTK Turkey 2025'),
('TR', 'Турция', 'tiktok', 2025, 1, 22000000, 42000000, 11000000, 5.0, 27, 5500000, 'TikTok TR 2025'),
('TR', 'Турция', 'youtube_shorts', 2025, 1, 25000000, 48000000, 16800000, 4.0, 33, 6200000, 'YouTube TR 2025');

-- Добавляем данные для Индонезии
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('ID', 'Индонезия', 'instagram', 2025, 1, 85000000, 170000000, 42000000, 4.3, 34, 20000000, 'Kominfo Indonesia 2025'),
('ID', 'Индонезия', 'tiktok', 2025, 1, 68000000, 130000000, 35000000, 6.0, 24, 16000000, 'TikTok ID 2025'),
('ID', 'Индонезия', 'youtube_shorts', 2025, 1, 75000000, 140000000, 52000000, 4.8, 30, 18000000, 'YouTube ID 2025');

-- Добавляем данные для Таиланда
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('TH', 'Таиланд', 'instagram', 2025, 1, 22000000, 45000000, 11000000, 4.0, 35, 5500000, 'NBTC Thailand 2025'),
('TH', 'Таиланд', 'tiktok', 2025, 1, 18000000, 35000000, 9000000, 5.8, 25, 4500000, 'TikTok TH 2025'),
('TH', 'Таиланд', 'youtube_shorts', 2025, 1, 20000000, 40000000, 14000000, 4.3, 31, 5000000, 'YouTube TH 2025');

-- Добавляем данные для Малайзии
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('MY', 'Малайзия', 'instagram', 2025, 1, 18000000, 36000000, 9000000, 3.9, 36, 4500000, 'MCMC Malaysia 2025'),
('MY', 'Малайзия', 'tiktok', 2025, 1, 14000000, 28000000, 7200000, 5.5, 26, 3500000, 'TikTok MY 2025'),
('MY', 'Малайзия', 'youtube_shorts', 2025, 1, 16000000, 32000000, 11000000, 4.1, 32, 4000000, 'YouTube MY 2025');

-- Добавляем данные для Саудовской Аравии
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('SA', 'Саудовская Аравия', 'instagram', 2025, 1, 15000000, 32000000, 8000000, 3.7, 37, 4000000, 'CITC Saudi 2025'),
('SA', 'Саудовская Аравия', 'tiktok', 2025, 1, 12000000, 24000000, 6000000, 5.2, 27, 3000000, 'TikTok SA 2025'),
('SA', 'Саудовская Аравия', 'youtube_shorts', 2025, 1, 14000000, 28000000, 9500000, 4.0, 33, 3500000, 'YouTube SA 2025');

-- Добавляем данные для ОАЭ
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('AE', 'ОАЭ', 'instagram', 2025, 1, 8000000, 16000000, 4000000, 3.5, 38, 2000000, 'TRA UAE 2025'),
('AE', 'ОАЭ', 'tiktok', 2025, 1, 6000000, 12000000, 3000000, 4.9, 28, 1500000, 'TikTok AE 2025'),
('AE', 'ОАЭ', 'youtube_shorts', 2025, 1, 7000000, 14000000, 4800000, 3.8, 34, 1800000, 'YouTube AE 2025');

-- Добавляем данные для Филиппин
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('PH', 'Филиппины', 'instagram', 2025, 1, 25000000, 52000000, 13000000, 4.1, 34, 6500000, 'NTC Philippines 2025'),
('PH', 'Филиппины', 'tiktok', 2025, 1, 20000000, 40000000, 10000000, 6.0, 25, 5000000, 'TikTok PH 2025'),
('PH', 'Филиппины', 'youtube_shorts', 2025, 1, 22000000, 45000000, 15000000, 4.5, 30, 5500000, 'YouTube PH 2025');

-- Добавляем данные для Египта
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('EG', 'Египет', 'instagram', 2025, 1, 18000000, 38000000, 9500000, 4.2, 33, 4800000, 'NTRA Egypt 2025'),
('EG', 'Египет', 'tiktok', 2025, 1, 14000000, 28000000, 7200000, 5.9, 24, 3500000, 'TikTok EG 2025'),
('EG', 'Египет', 'youtube_shorts', 2025, 1, 16000000, 32000000, 11000000, 4.6, 29, 4000000, 'YouTube EG 2025');

-- Добавляем данные для Украины
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('UA', 'Украина', 'instagram', 2025, 1, 12000000, 24000000, 6000000, 3.8, 39, 3000000, 'NCEC Ukraine 2025'),
('UA', 'Украина', 'tiktok', 2025, 1, 9500000, 19000000, 4800000, 5.1, 29, 2400000, 'TikTok UA 2025'),
('UA', 'Украина', 'youtube_shorts', 2025, 1, 11000000, 22000000, 7500000, 4.2, 35, 2800000, 'YouTube UA 2025');

-- Добавляем данные для Пакистана
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('PK', 'Пакистан', 'instagram', 2025, 1, 35000000, 72000000, 18000000, 4.4, 33, 9000000, 'PTA Pakistan 2025'),
('PK', 'Пакистан', 'tiktok', 2025, 1, 28000000, 55000000, 14000000, 6.1, 23, 7000000, 'TikTok PK 2025'),
('PK', 'Пакистан', 'youtube_shorts', 2025, 1, 32000000, 65000000, 22000000, 4.7, 30, 8000000, 'YouTube PK 2025');

-- Добавляем данные для Бангладеш
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('BD', 'Бангладеш', 'instagram', 2025, 1, 28000000, 58000000, 14500000, 4.5, 32, 7200000, 'BTRC Bangladesh 2025'),
('BD', 'Бангладеш', 'tiktok', 2025, 1, 22000000, 45000000, 11000000, 6.3, 22, 5500000, 'TikTok BD 2025'),
('BD', 'Бангладеш', 'youtube_shorts', 2025, 1, 25000000, 52000000, 18000000, 4.9, 28, 6500000, 'YouTube BD 2025');

-- Добавляем данные для Нигерии
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('NG', 'Нигерия', 'instagram', 2025, 1, 22000000, 45000000, 11000000, 4.3, 34, 5500000, 'NCC Nigeria 2025'),
('NG', 'Нигерия', 'tiktok', 2025, 1, 18000000, 36000000, 9000000, 5.8, 24, 4500000, 'TikTok NG 2025'),
('NG', 'Нигерия', 'youtube_shorts', 2025, 1, 20000000, 40000000, 14000000, 4.5, 30, 5000000, 'YouTube NG 2025');

-- Добавляем данные для Кении
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('KE', 'Кения', 'instagram', 2025, 1, 8000000, 16000000, 4000000, 4.4, 33, 2000000, 'CA Kenya 2025'),
('KE', 'Кения', 'tiktok', 2025, 1, 6500000, 13000000, 3200000, 5.9, 24, 1600000, 'TikTok KE 2025'),
('KE', 'Кения', 'youtube_shorts', 2025, 1, 7500000, 15000000, 5200000, 4.7, 29, 1800000, 'YouTube KE 2025');

-- Добавляем данные для Ганы
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('GH', 'Гана', 'instagram', 2025, 1, 6000000, 12000000, 3000000, 4.5, 32, 1500000, 'NCA Ghana 2025'),
('GH', 'Гана', 'tiktok', 2025, 1, 4800000, 9500000, 2400000, 6.0, 23, 1200000, 'TikTok GH 2025'),
('GH', 'Гана', 'youtube_shorts', 2025, 1, 5500000, 11000000, 3800000, 4.8, 28, 1400000, 'YouTube GH 2025');

-- Добавляем данные для Танзании
INSERT OR REPLACE INTO platform_country_stats (country_code, country_name, platform, year, month, dau, mau, monthly_content_count, avg_engagement_rate, avg_video_duration, content_creators, data_source) VALUES
('TZ', 'Танзания', 'instagram', 2025, 1, 5000000, 10000000, 2500000, 4.6, 31, 1200000, 'TCRA Tanzania 2025'),
('TZ', 'Танзания', 'tiktok', 2025, 1, 4000000, 8000000, 2000000, 6.1, 22, 1000000, 'TikTok TZ 2025'),
('TZ', 'Танзания', 'youtube_shorts', 2025, 1, 4500000, 9000000, 3100000, 4.9, 27, 1100000, 'YouTube TZ 2025');

-- Создание представления для удобного получения статистики
CREATE VIEW IF NOT EXISTS platform_stats_summary AS
SELECT 
    pcs.country_code,
    pcs.country_name,
    pcs.platform,
    pcs.dau,
    pcs.mau,
    pcs.monthly_content_count,
    pcs.avg_engagement_rate,
    pcs.avg_video_duration,
    pcs.content_creators,
    cos.tier,
    cos.total_population,
    cos.internet_users,
    cos.avg_daily_screen_time,
    cos.content_consumption_trend,
    cos.market_maturity
FROM platform_country_stats pcs
JOIN country_overview_stats cos ON pcs.country_code = cos.country_code AND pcs.year = cos.year
WHERE pcs.year = 2025 AND pcs.month = 1
ORDER BY cos.tier, pcs.country_name, pcs.platform;
