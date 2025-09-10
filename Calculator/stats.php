<?php
/**
 * Статистика калькулятора стоимости продвижения
 * Версия: 4.0 (с поддержкой многоязычности)
 */

require_once 'config.php';
require_once 'db_operations.php';
require_once 'language_manager.php';

$db = new DatabaseOperations();
$countries = $db->getCountriesList();
$globalStats = $db->getGlobalPlatformStats();
$lang = getLanguageManager();
?>

<!DOCTYPE html>
<html lang="<?= $lang->getCurrentLanguage() ?>">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= __('stats_title') ?> - Аналитика 2025</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --primary-color: #1a1a1a;
            --secondary-color: #333333;
            --accent-color: #ff6b35;
            --success-color: #28a745;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
            --dark-color: #1a1a1a;
            --light-color: #f8f9fa;
            --text-color: #333333;
            --border-color: #e9ecef;
        }
        
        body {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: var(--text-color);
        }
        
        .main-container {
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.1);
            margin: 2rem auto;
            max-width: 1400px;
        }
        
        .header-section {
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 2rem;
            border-radius: 20px 20px 0 0;
            text-align: center;
            position: relative;
            min-height: 120px;
        }
        
        .header-section h1 {
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            max-width: 70%;
            margin-left: auto;
            margin-right: auto;
        }
        
        .header-controls {
            position: absolute;
            top: 1rem;
            right: 1rem;
            display: flex;
            gap: 1rem;
            align-items: center;
            z-index: 10;
        }
        
        .language-switcher .dropdown-toggle {
            background: transparent;
            border: 2px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
            transition: all 0.3s ease;
            white-space: nowrap;
        }
        
        .language-switcher .dropdown-toggle:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.5);
        }
        
        .language-switcher .dropdown-menu {
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            border: none;
        }
        
        .language-switcher .dropdown-item.active {
            background-color: var(--accent-color);
            color: white;
        }
        
        .back-btn {
            background: var(--accent-color);
            border: 2px solid var(--accent-color);
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 25px;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .back-btn:hover {
            background: #e55a2b;
            border-color: #e55a2b;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 107, 53, 0.4);
        }
        
        .stats-section {
            padding: 2rem;
        }
        
        .country-selector {
            background: white;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
            text-align: center;
        }
        
        .country-select {
            max-width: 400px;
            margin: 0 auto;
        }
        
        .platform-stats {
            background: white;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
        }
        
        .platform-card {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border-left: 5px solid var(--accent-color);
            transition: transform 0.3s ease;
        }
        
        .platform-card:hover {
            transform: translateY(-3px);
        }
        
        .platform-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: 700;
            color: var(--accent-color);
        }
        
        .stat-label {
            color: var(--dark-color);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 0.5px;
        }
        
        .country-overview {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 15px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }
        
        .overview-item {
            background: white;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
        }
        
        .overview-label {
            font-weight: 600;
            color: var(--dark-color);
            margin-bottom: 0.5rem;
        }
        
        .overview-value {
            font-size: 1.3rem;
            color: var(--accent-color);
        }
        
        .chart-container {
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }
        
        .btn {
            border-radius: 25px;
            padding: 0.75rem 2rem;
            font-weight: 600;
            transition: all 0.3s ease;
            border: none;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--accent-color), #e55a2b);
            box-shadow: 0 5px 15px rgba(255, 107, 53, 0.4);
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(255, 107, 53, 0.6);
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: var(--dark-color);
        }
        
        .no-data {
            text-align: center;
            padding: 2rem;
            color: var(--dark-color);
            font-style: italic;
        }
        
        @media (max-width: 768px) {
            .main-container {
                margin: 1rem;
                border-radius: 15px;
            }
            
            .header-section {
                padding: 1.5rem 1rem;
                min-height: 100px;
            }
            
            .header-section h1 {
                font-size: 1.8rem;
                max-width: 100%;
                margin-bottom: 0.5rem;
            }
            
            .header-controls {
                position: static;
                justify-content: center;
                margin-top: 1rem;
                flex-wrap: wrap;
                gap: 0.5rem;
            }
            
            .language-switcher .dropdown-toggle {
                font-size: 0.8rem;
                padding: 0.4rem 0.8rem;
            }
            
            .stats-btn {
                font-size: 0.9rem;
                padding: 0.6rem 1.2rem;
            }
            
            .form-section {
                padding: 1rem;
            }
        }
        
        @media (max-width: 480px) {
            .header-section h1 {
                font-size: 1.5rem;
            }
            
            .header-controls {
                flex-direction: column;
                gap: 0.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="main-container">
            <!-- Заголовок -->
            <div class="header-section">
                <!-- Элементы управления в шапке -->
                <div class="header-controls">
                    <?= $lang->getLanguageSwitcher() ?>
                    <a href="calc.php" class="back-btn">
                        <i class="bi bi-arrow-left"></i> <?= __('back_to_calculator') ?>
                    </a>
                </div>
                
                <h1><i class="bi bi-graph-up"></i> <?= __('stats_title') ?></h1>
                <p class="lead mb-0"><?= __('stats_subtitle') ?></p>
            </div>

            <!-- Выбор страны -->
            <div class="stats-section">
                <div class="country-selector">
                    <h3 class="mb-3"><i class="bi bi-globe"></i> <?= __('select_country') ?></h3>
                    
                    <select class="form-select country-select" id="countrySelect">
                        <option value=""><?= __('select_country_placeholder') ?></option>
                        <?php foreach ($countries as $country): ?>
                        <option value="<?= $country['country_code'] ?>">
                            <?= $country['country_name'] ?> (Tier <?= $country['tier'] ?>)
                        </option>
                        <?php endforeach; ?>
                    </select>
                </div>

                <!-- Загрузка -->
                <div id="loadingSection" class="loading" style="display:none;">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Загрузка...</span>
                    </div>
                    <p class="mt-2"><?= __('loading_stats') ?></p>
                </div>

                <!-- Обзор страны -->
                <div id="countryOverview" class="country-overview" style="display:none;">
                    <h3 class="text-center mb-4"><i class="bi bi-info-circle"></i> <?= __('country_overview') ?></h3>
                    <div class="row" id="overviewContent">
                        <!-- Содержимое загружается динамически -->
                    </div>
                </div>

                <!-- Статистика по платформам -->
                <div id="platformStats" class="platform-stats" style="display:none;">
                    <h3 class="text-center mb-4"><i class="bi bi-phone"></i> <?= __('platform_stats') ?></h3>
                    <div class="row" id="platformContent">
                        <!-- Содержимое загружается динамически -->
                    </div>
                </div>

                <!-- Графики -->
                <div id="chartsSection" style="display:none;">
                    <div class="row">
                        <div class="col-lg-6">
                            <div class="chart-container">
                                <h4 class="text-center mb-3"><?= __('mau_comparison') ?></h4>
                                <canvas id="mauChart"></canvas>
                            </div>
                        </div>
                        <div class="col-lg-6">
                            <div class="chart-container">
                                <h4 class="text-center mb-3"><?= __('dau_comparison') ?></h4>
                                <canvas id="dauChart"></canvas>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-lg-6">
                            <div class="chart-container">
                                <h4 class="text-center mb-3"><?= __('monthly_content') ?></h4>
                                <canvas id="contentChart"></canvas>
                            </div>
                        </div>
                        <div class="col-lg-6">
                            <div class="chart-container">
                                <h4 class="text-center mb-3"><?= __('engagement_percentage') ?></h4>
                                <canvas id="engagementChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Глобальная статистика -->
                <div class="platform-stats">
                    <h3 class="text-center mb-4"><i class="bi bi-globe2"></i> <?= __('global_platform_stats') ?></h3>
                    
                    <div class="row">
                        <?php foreach ($globalStats as $stat): ?>
                        <div class="col-md-4 mb-3">
                            <div class="platform-card text-center">
                                <div class="platform-icon">
                                    <?php if ($stat['platform'] === 'instagram'): ?>
                                        <i class="bi bi-instagram text-danger"></i>
                                    <?php elseif ($stat['platform'] === 'tiktok'): ?>
                                        <i class="bi bi-tiktok text-dark"></i>
                                    <?php elseif ($stat['platform'] === 'youtube_shorts'): ?>
                                        <i class="bi bi-youtube text-danger"></i>
                                    <?php endif; ?>
                                </div>
                                <h5 class="text-capitalize"><?= ucfirst(str_replace('_', ' ', $stat['platform'])) ?></h5>
                                <div class="row text-center">
                                    <div class="col-6">
                                        <div class="stat-number"><?= number_format($stat['total_mau'] / 1000000, 1) ?>M</div>
                                        <div class="stat-label">MAU</div>
                                    </div>
                                    <div class="col-6">
                                        <div class="stat-number"><?= number_format($stat['total_dau'] / 1000000, 1) ?>M</div>
                                        <div class="stat-label">DAU</div>
                                    </div>
                                </div>
                                <div class="mt-3">
                                    <div class="h6 text-success"><?= number_format($stat['total_monthly_content'] / 1000000, 1) ?>M</div>
                                    <small class="text-muted"><?= __('content_per_month') ?></small>
                                </div>
                                <div class="mt-2">
                                    <div class="h6 text-warning"><?= number_format($stat['total_creators'] / 1000000, 1) ?>M</div>
                                    <small class="text-muted"><?= __('content_creators') ?></small>
                                </div>
                            </div>
                        </div>
                        <?php endforeach; ?>
                    </div>
                </div>

                <!-- Экспорт -->
                <div class="platform-stats text-center">
                    <h4 class="mb-3"><i class="bi bi-download"></i> <?= __('data_export') ?></h4>
                    <div class="d-flex justify-content-center gap-3">
                        <button class="btn btn-primary" onclick="exportData('platform_stats')">
                            <i class="bi bi-file-earmark-text"></i> <?= __('platform_stats_export') ?>
                        </button>
                        <button class="btn btn-primary" onclick="exportData('country_overview')">
                            <i class="bi bi-globe"></i> <?= __('country_overview_export') ?>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <?= $lang->getLanguageSwitcherScript() ?>
    <script>
        let currentCharts = {};
        
        // Обработчик выбора страны
        document.getElementById('countrySelect').addEventListener('change', function() {
            const countryCode = this.value;
            if (countryCode) {
                loadCountryStats(countryCode);
            } else {
                hideAllSections();
            }
        });
        
        // Загрузка статистики по стране
        function loadCountryStats(countryCode) {
            console.log('Загружаем статистику для страны:', countryCode);
            showLoading();
            
            fetch('ajax_handler.php', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `action=get_country_stats&country_code=${countryCode}`
            })
            .then(response => {
                console.log('Ответ получен:', response);
                return response.json();
            })
            .then(data => {
                console.log('Данные получены:', data);
                if (data.success) {
                    displayCountryOverview(data.overview);
                    displayPlatformStats(data.platform_stats);
                    createCharts(data.platform_stats);
                    showAllSections();
                } else {
                    console.error('Ошибка в данных:', data.message);
                    showError('<?= __('loading_error') ?>' + data.message);
                    hideAllSections();
                }
            })
            .catch(error => {
                console.error('Ошибка загрузки:', error);
                showError('<?= __('loading_error_retry') ?>');
                hideAllSections();
            })
            .finally(() => {
                hideLoading();
            });
        }
        
        // Функция для отображения ошибок
        function showError(message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger alert-dismissible fade show';
            errorDiv.innerHTML = `
                <strong><?= __('error') ?>:</strong> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            // Вставляем ошибку после селектора страны
            const countrySelector = document.querySelector('.country-selector');
            countrySelector.parentNode.insertBefore(errorDiv, countrySelector.nextSibling);
            
            // Автоматически скрываем через 5 секунд
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.remove();
                }
            }, 5000);
        }
        
        // Отображение обзора страны
        function displayCountryOverview(overview) {
            if (!overview) return;
            
            const content = document.getElementById('overviewContent');
            content.innerHTML = `
                <div class="col-md-6">
                    <div class="overview-item">
                        <div class="overview-label"><?= __('population') ?></div>
                        <div class="overview-value">${(overview.total_population / 1000000).toFixed(1)}M</div>
                    </div>
                    <div class="overview-item">
                        <div class="overview-label"><?= __('internet_users') ?></div>
                        <div class="overview-value">${(overview.internet_users / 1000000).toFixed(1)}M</div>
                    </div>
                    <div class="overview-item">
                        <div class="overview-label"><?= __('social_media_users') ?></div>
                        <div class="overview-value">${(overview.social_media_users / 1000000).toFixed(1)}M</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="overview-item">
                        <div class="overview-label"><?= __('screen_time') ?></div>
                        <div class="overview-value">${overview.avg_daily_screen_time}</div>
                    </div>
                    <div class="overview-item">
                        <div class="overview-label"><?= __('content_consumption_trend') ?></div>
                        <div class="overview-value">${getTrendText(overview.content_consumption_trend)}</div>
                    </div>
                    <div class="overview-item">
                        <div class="overview-label"><?= __('market_maturity') ?></div>
                        <div class="overview-value">${getMaturityText(overview.market_maturity)}</div>
                    </div>
                </div>
            `;
        }
        
        // Отображение статистики по платформам
        function displayPlatformStats(platformStats) {
            const content = document.getElementById('platformContent');
            let html = '';
            
            platformStats.forEach(stat => {
                const platformName = stat.platform === 'instagram' ? 'Instagram' : 
                                   stat.platform === 'tiktok' ? 'TikTok' : 'YouTube Shorts';
                const platformIcon = stat.platform === 'instagram' ? 'bi-instagram text-danger' : 
                                   stat.platform === 'tiktok' ? 'bi-tiktok text-dark' : 'bi-youtube text-danger';
                
                html += `
                    <div class="col-lg-4 mb-3">
                        <div class="platform-card text-center">
                            <div class="platform-icon">
                                <i class="bi ${platformIcon}"></i>
                            </div>
                            <h5>${platformName}</h5>
                            <div class="row text-center">
                                <div class="col-6">
                                    <div class="stat-number">${(stat.mau / 1000000).toFixed(1)}M</div>
                                    <div class="stat-label">MAU</div>
                                </div>
                                <div class="col-6">
                                    <div class="stat-number">${(stat.dau / 1000000).toFixed(1)}M</div>
                                    <div class="stat-label">DAU</div>
                                </div>
                            </div>
                            <div class="mt-3">
                                <div class="h6 text-success">${(stat.monthly_content_count / 1000000).toFixed(1)}M</div>
                                <small class="text-muted"><?= __('content_per_month') ?></small>
                            </div>
                            <div class="mt-2">
                                <div class="h6 text-warning">${(stat.avg_engagement_rate).toFixed(1)}%</div>
                                <small class="text-muted"><?= __('engagement_rate') ?></small>
                            </div>
                            <div class="mt-2">
                                <div class="h6 text-info">${(stat.content_creators / 1000000).toFixed(1)}M</div>
                                <small class="text-muted"><?= __('content_creators') ?></small>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            content.innerHTML = html;
        }
        
        // Создание графиков
        function createCharts(platformStats) {
            // Уничтожаем предыдущие графики
            Object.values(currentCharts).forEach(chart => {
                if (chart) chart.destroy();
            });
            currentCharts = {};
            
            const platforms = platformStats.map(s => s.platform === 'instagram' ? 'Instagram' : 
                                                   s.platform === 'tiktok' ? 'TikTok' : 'YouTube Shorts');
            const mauData = platformStats.map(s => s.mau / 1000000);
            const dauData = platformStats.map(s => s.dau / 1000000);
            const contentData = platformStats.map(s => s.monthly_content_count / 1000000);
            const engagementData = platformStats.map(s => s.avg_engagement_rate);
            
            // График MAU
            const mauCtx = document.getElementById('mauChart').getContext('2d');
            currentCharts.mau = new Chart(mauCtx, {
                type: 'bar',
                data: {
                    labels: platforms,
                    datasets: [{
                        label: '<?= __('mau_millions') ?>',
                        data: mauData,
                        backgroundColor: ['#E4405F', '#000000', '#FF0000'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
            
            // График DAU
            const dauCtx = document.getElementById('dauChart').getContext('2d');
            currentCharts.dau = new Chart(dauCtx, {
                type: 'bar',
                data: {
                    labels: platforms,
                    datasets: [{
                        label: '<?= __('dau_millions') ?>',
                        data: dauData,
                        backgroundColor: ['#E4405F', '#000000', '#FF0000'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
            
            // График контента
            const contentCtx = document.getElementById('contentChart').getContext('2d');
            currentCharts.content = new Chart(contentCtx, {
                type: 'doughnut',
                data: {
                    labels: platforms,
                    datasets: [{
                        data: contentData,
                        backgroundColor: ['#E4405F', '#000000', '#FF0000'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
            
            // График вовлеченности
            const engagementCtx = document.getElementById('engagementChart').getContext('2d');
            currentCharts.engagement = new Chart(engagementCtx, {
                type: 'radar',
                data: {
                    labels: platforms,
                    datasets: [{
                        label: '<?= __('engagement_percent') ?>',
                        data: engagementData,
                        backgroundColor: 'rgba(255, 107, 53, 0.2)',
                        borderColor: '#ff6b35',
                        borderWidth: 2,
                        pointBackgroundColor: '#ff6b35'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    },
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 10
                        }
                    }
                }
            });
        }
        
        // Вспомогательные функции
        function getTrendText(trend) {
            const trends = {
                'stable': '<?= __('trend_stable') ?>',
                'growing': '<?= __('trend_growing') ?>',
                'rapid_growth': '<?= __('trend_rapid_growth') ?>',
                'explosive_growth': '<?= __('trend_explosive_growth') ?>'
            };
            return trends[trend] || trend;
        }
        
        function getMaturityText(maturity) {
            const maturities = {
                'mature': '<?= __('maturity_mature') ?>',
                'developing': '<?= __('maturity_developing') ?>',
                'emerging': '<?= __('maturity_emerging') ?>'
            };
            return maturities[maturity] || maturity;
        }
        
        // Управление отображением секций
        function showLoading() {
            document.getElementById('loadingSection').style.display = 'block';
        }
        
        function hideLoading() {
            document.getElementById('loadingSection').style.display = 'none';
        }
        
        function showAllSections() {
            document.getElementById('countryOverview').style.display = 'block';
            document.getElementById('platformStats').style.display = 'block';
            document.getElementById('chartsSection').style.display = 'block';
        }
        
        function hideAllSections() {
            document.getElementById('countryOverview').style.display = 'none';
            document.getElementById('platformStats').style.display = 'none';
            document.getElementById('chartsSection').style.display = 'none';
        }
        
        // Функция экспорта данных
        function exportData(type) {
            fetch('ajax_handler.php', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `action=export_csv&type=${type}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Создаем ссылку для скачивания
                    const blob = new Blob([data.data], { type: 'text/csv;charset=utf-8;' });
                    const link = document.createElement('a');
                    const url = URL.createObjectURL(blob);
                    link.setAttribute('href', url);
                    link.setAttribute('download', data.filename);
                    link.style.visibility = 'hidden';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                } else {
                    showError('<?= __('export_error') ?>' + data.message);
                }
            })
            .catch(error => {
                console.error('Ошибка:', error);
                showError('<?= __('export_data_error') ?>');
            });
        }
    </script>
</body>
</html>
