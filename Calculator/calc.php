<?php
/**
 * Калькулятор стоимости продвижения в Instagram и TikTok
 * Версия: 4.0 (с поддержкой многоязычности)
 */

require_once 'config.php';
require_once 'language_manager.php';

$lang = getLanguageManager();
?>
<!DOCTYPE html>
<html lang="<?= $lang->getCurrentLanguage() ?>">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= __('calculator_title') ?> - Instagram и TikTok</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
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
        
        .stats-btn {
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
        
        .stats-btn:hover {
            background: #e55a2b;
            border-color: #e55a2b;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 107, 53, 0.4);
        }
        
        .tariffs-section {
            background: linear-gradient(135deg, #ffffff, #f8f9fa);
            padding: 2rem;
            border-radius: 15px;
            margin: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
        }
        
        .tariffs-section h3 {
            color: var(--dark-color);
            text-align: center;
            margin-bottom: 1.5rem;
            font-weight: 600;
        }
        
        .tariff-card {
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            border-left: 5px solid var(--accent-color);
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        
        .tariff-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.15);
        }
        
        .tier-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .tier-1 { background: linear-gradient(135deg, var(--accent-color), #e55a2b); color: white; }
        .tier-2 { background: linear-gradient(135deg, var(--warning-color), #e0a800); color: white; }
        .tier-3 { background: linear-gradient(135deg, var(--danger-color), #c82333); color: white; }
        .tier-difficult { background: linear-gradient(135deg, var(--dark-color), #495057); color: white; }
        
        .form-section {
            padding: 2rem;
        }
        
        .form-card {
            background: white;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
        }
        
        .form-card h4 {
            color: var(--primary-color);
            margin-bottom: 1.5rem;
            font-weight: 600;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.5rem;
        }
        
        .form-control, .form-select {
            border-radius: 10px;
            border: 2px solid var(--border-color);
            padding: 0.75rem 1rem;
            transition: all 0.3s ease;
        }
        
        .form-control:focus, .form-select:focus {
            border-color: var(--accent-color);
            box-shadow: 0 0 0 0.2rem rgba(255, 107, 53, 0.25);
        }
        
        .form-check-input:checked {
            background-color: var(--accent-color);
            border-color: var(--accent-color);
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
        
        .btn-secondary {
            background: linear-gradient(135deg, #6c757d, #495057);
        }
        
        .result-section {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 15px;
            padding: 2rem;
            margin: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }
        
        .final-cost {
            background: linear-gradient(135deg, var(--accent-color), #e55a2b);
            color: white;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            font-size: 2rem;
            font-weight: 700;
            box-shadow: 0 10px 30px rgba(255, 107, 53, 0.4);
        }
        
        .accordion-button {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border: none;
            border-radius: 10px;
            font-weight: 600;
            color: var(--dark-color);
        }
        
        .accordion-button:not(.collapsed) {
            background: linear-gradient(135deg, var(--accent-color), #e55a2b);
            color: white;
        }
        
        .country-select {
            max-height: 400px;
            overflow-y: auto;
            padding: 1rem;
        }
        
        .country-option {
            padding: 0.5rem 1rem;
            border-radius: 8px;
            margin: 0.25rem 0;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9rem;
        }
        
        .country-option:hover {
            background-color: var(--light-color);
            transform: translateX(5px);
        }
        
        .country-option.selected {
            background-color: var(--accent-color);
            color: white;
            transform: translateX(5px);
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
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
                    <a href="stats.php" class="stats-btn">
                        <i class="bi bi-graph-up"></i> <?= __('stats_button') ?>
                    </a>
                </div>
                
                <h1><i class="bi bi-calculator"></i> <?= __('calculator_title') ?></h1>
                <p class="lead mb-0"><?= __('calculator_subtitle') ?></p>
            </div>

            <!-- Тарифы -->
            <div class="tariffs-section">
                <h3><i class="bi bi-currency-exchange"></i> <?= __('tariffs_title') ?></h3>
                <div class="row">
                    <div class="col-md-3">
                        <div class="tariff-card text-center">
                            <span class="tier-badge tier-1 mb-2">Tier 1</span>
                            <h5><?= __('tier_1_title') ?></h5>
                            <p class="text-muted"><?= __('country_usa') ?>, <?= __('country_uk') ?>, <?= __('country_de') ?>, <?= __('country_fr') ?>, <?= __('country_jp') ?>, <?= __('country_ca') ?>, <?= __('country_au') ?>, <?= __('country_nl') ?>, <?= __('country_se') ?>, <?= __('country_ch') ?>, <?= __('country_no') ?>, <?= __('country_dk') ?>, <?= __('country_fi') ?>, <?= __('country_at') ?>, <?= __('country_be') ?>, <?= __('country_ie') ?>, <?= __('country_sg') ?>, <?= __('country_hk') ?>, <?= __('country_kr') ?>, <?= __('country_nz') ?></p>
                            <div class="h4 text-primary"><?= __('tier_1_price') ?></div>
                            <small><?= __('tier_1_subtitle') ?></small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="tariff-card text-center">
                            <span class="tier-badge tier-2 mb-2">Tier 2</span>
                            <h5><?= __('tier_2_title') ?></h5>
                            <p class="text-muted"><?= __('country_it') ?>, <?= __('country_es') ?>, <?= __('country_pt') ?>, <?= __('country_gr') ?>, <?= __('country_pl') ?>, <?= __('country_cz') ?>, <?= __('country_hu') ?>, <?= __('country_sk') ?>, <?= __('country_si') ?>, <?= __('country_ee') ?>, <?= __('country_lv') ?>, <?= __('country_lt') ?>, <?= __('country_br') ?>, <?= __('country_in') ?>, <?= __('country_ru') ?>, <?= __('country_mx') ?>, <?= __('country_tr') ?>, <?= __('country_ar') ?>, <?= __('country_cl') ?>, <?= __('country_co') ?>, <?= __('country_pe') ?>, <?= __('country_ve') ?>, <?= __('country_uy') ?>, <?= __('country_ec') ?>, <?= __('country_bo') ?>, <?= __('country_py') ?>, <?= __('country_za') ?></p>
                            <div class="h4 text-warning"><?= __('tier_2_price') ?></div>
                            <small><?= __('tier_2_subtitle') ?></small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="tariff-card text-center">
                            <span class="tier-badge tier-3 mb-2">Tier 3</span>
                            <h5><?= __('tier_3_title') ?></h5>
                            <p class="text-muted"><?= __('country_ng') ?>, <?= __('country_ke') ?>, <?= __('country_gh') ?>, <?= __('country_ug') ?>, <?= __('country_tz') ?>, <?= __('country_et') ?>, <?= __('country_mz') ?>, <?= __('country_zw') ?>, <?= __('country_zm') ?>, <?= __('country_mw') ?>, <?= __('country_bw') ?>, <?= __('country_nam') ?>, <?= __('country_vn') ?>, <?= __('country_ph') ?>, <?= __('country_eg') ?>, <?= __('country_pk') ?>, <?= __('country_bd') ?>, <?= __('country_lk') ?>, <?= __('country_np') ?>, <?= __('country_mm') ?>, <?= __('country_kh') ?>, <?= __('country_la') ?>, <?= __('country_mn') ?></p>
                            <div class="h4 text-danger"><?= __('tier_3_price') ?></div>
                            <small><?= __('tier_3_subtitle') ?></small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="tariff-card text-center">
                            <span class="tier-badge tier-difficult mb-2">Сложные</span>
                            <h5><?= __('tier_difficult') ?></h5>
                            <p class="text-muted"><?= __('country_af') ?>, <?= __('country_ir') ?>, <?= __('country_iq') ?>, <?= __('country_sy') ?>, <?= __('country_lb') ?>, <?= __('country_jo') ?>, <?= __('country_ps') ?>, <?= __('country_ye') ?>, <?= __('country_om') ?>, <?= __('country_kw') ?>, <?= __('country_qa') ?>, <?= __('country_bh') ?>, <?= __('country_ae') ?>, <?= __('country_sa') ?>, <?= __('country_ua') ?></p>
                            <div class="h4 text-dark">100%</div>
                            <small>Сложная страна</small>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Форма расчета -->
            <div class="form-section">
                <form id="calcForm" class="form-card">
                    <div class="row">
                        <!-- Левая колонка -->
                        <div class="col-lg-6">
                            <h4><i class="bi bi-eye"></i> <?= __('main_parameters') ?></h4>
                            
                            <div class="mb-3">
                                <label for="views_mln" class="form-label">
                                    <strong><?= __('views_volume') ?></strong>
                                    <i class="bi bi-info-circle text-muted" data-bs-toggle="tooltip" title="<?= __('views_tooltip') ?>"></i>
                                </label>
                                <input type="number" class="form-control" id="views_mln" name="views_mln" min="15" max="1000" step="1" value="15" required>
                                <input type="range" class="form-range mt-2" id="views_slider" min="15" max="1000" step="1" value="15">
                                <small class="text-muted"><?= __('views_range') ?></small>
                            </div>

                            <div class="mb-3">
                                <label class="form-label"><strong><?= __('platforms') ?></strong></label>
                                <div class="d-flex gap-3">
                                    <div class="form-check">
                                        <input type="checkbox" class="form-check-input" id="platform_instagram" name="platform_instagram">
                                        <label class="form-check-label" for="platform_instagram">
                                            <i class="bi bi-instagram text-danger"></i> <?= __('instagram') ?>
                                        </label>
                                    </div>
                                    <div class="form-check">
                                        <input type="checkbox" class="form-check-input" id="platform_tiktok" name="platform_tiktok">
                                        <label class="form-check-label" for="platform_tiktok">
                                            <i class="bi bi-tiktok text-dark"></i> <?= __('tiktok') ?>
                                        </label>
                                    </div>
                                    <div class="form-check">
                                        <input type="checkbox" class="form-check-input" id="platform_youtube_shorts" name="platform_youtube_shorts">
                                        <label class="form-check-label" for="platform_youtube_shorts">
                                            <i class="bi bi-youtube text-danger"></i> <?= __('youtube_shorts') ?> <span class="badge bg-warning"><?= __('youtube_shorts_badge') ?></span>
                                        </label>
                                    </div>
                                </div>
                            </div>

                            <div class="mb-3">
                                <label for="currency" class="form-label"><strong><?= __('currency') ?></strong></label>
                                <select class="form-select" id="currency" name="currency">
                                    <option value="RUB"><?= __('rub') ?></option>
                                    <option value="USD"><?= __('usd') ?></option>
                                    <option value="EUR"><?= __('eur') ?></option>
                                </select>
                            </div>

                            <div class="mb-3">
                                <label for="countries" class="form-label"><strong><?= __('country_selection') ?></strong></label>
                                <div class="country-select border rounded p-2">
                                    <div class="mb-2">
                                        <strong class="text-primary"><?= __('tier_1_premium') ?></strong>
                                        <div class="country-option" data-country="USA" data-tier="1">🇺🇸 <?= __('country_usa') ?></div>
                                        <div class="country-option" data-country="UK" data-tier="1">🇬🇧 <?= __('country_uk') ?></div>
                                        <div class="country-option" data-country="DE" data-tier="1">🇩🇪 <?= __('country_de') ?></div>
                                        <div class="country-option" data-country="FR" data-tier="1">🇫🇷 <?= __('country_fr') ?></div>
                                        <div class="country-option" data-country="JP" data-tier="1">🇯🇵 <?= __('country_jp') ?></div>
                                        <div class="country-option" data-country="CA" data-tier="1">🇨🇦 <?= __('country_ca') ?></div>
                                        <div class="country-option" data-country="AU" data-tier="1">🇦🇺 <?= __('country_au') ?></div>
                                        <div class="country-option" data-country="NL" data-tier="1">🇳🇱 <?= __('country_nl') ?></div>
                                        <div class="country-option" data-country="SE" data-tier="1">🇸🇪 <?= __('country_se') ?></div>
                                        <div class="country-option" data-country="CH" data-tier="1">🇨🇭 <?= __('country_ch') ?></div>
                                        <div class="country-option" data-country="NO" data-tier="1">🇳🇴 <?= __('country_no') ?></div>
                                        <div class="country-option" data-country="DK" data-tier="1">🇩🇰 <?= __('country_dk') ?></div>
                                        <div class="country-option" data-country="FI" data-tier="1">🇫🇮 <?= __('country_fi') ?></div>
                                        <div class="country-option" data-country="AT" data-tier="1">🇦🇹 <?= __('country_at') ?></div>
                                        <div class="country-option" data-country="BE" data-tier="1">🇧🇪 <?= __('country_be') ?></div>
                                        <div class="country-option" data-country="IE" data-tier="1">🇮🇪 <?= __('country_ie') ?></div>
                                        <div class="country-option" data-country="SG" data-tier="1">🇸🇬 <?= __('country_sg') ?></div>
                                        <div class="country-option" data-country="HK" data-tier="1">🇭🇰 <?= __('country_hk') ?></div>
                                        <div class="country-option" data-country="KR" data-tier="1">🇰🇷 <?= __('country_kr') ?></div>
                                        <div class="country-option" data-country="NZ" data-tier="1">🇳🇿 <?= __('country_nz') ?></div>
                                    </div>
                                    <div class="mb-2">
                                        <strong class="text-warning"><?= __('tier_2_developing') ?></strong>
                                        <div class="country-option" data-country="IT" data-tier="2">🇮🇹 <?= __('country_it') ?></div>
                                        <div class="country-option" data-country="ES" data-tier="2">🇪🇸 <?= __('country_es') ?></div>
                                        <div class="country-option" data-country="PT" data-tier="2">🇵🇹 <?= __('country_pt') ?></div>
                                        <div class="country-option" data-country="GR" data-tier="2">🇬🇷 <?= __('country_gr') ?></div>
                                        <div class="country-option" data-country="PL" data-tier="2">🇵🇱 <?= __('country_pl') ?></div>
                                        <div class="country-option" data-country="CZ" data-tier="2">🇨🇿 <?= __('country_cz') ?></div>
                                        <div class="country-option" data-country="HU" data-tier="2">🇭🇺 <?= __('country_hu') ?></div>
                                        <div class="country-option" data-country="SK" data-tier="2">🇸🇰 <?= __('country_sk') ?></div>
                                        <div class="country-option" data-country="SI" data-tier="2">🇸🇮 <?= __('country_si') ?></div>
                                        <div class="country-option" data-country="EE" data-tier="2">🇪🇪 <?= __('country_ee') ?></div>
                                        <div class="country-option" data-country="LV" data-tier="2">🇱🇻 <?= __('country_lv') ?></div>
                                        <div class="country-option" data-country="LT" data-tier="2">🇱🇹 <?= __('country_lt') ?></div>
                                        <div class="country-option" data-country="BR" data-tier="2">🇧🇷 <?= __('country_br') ?></div>
                                        <div class="country-option" data-country="IN" data-tier="2">🇮🇳 <?= __('country_in') ?></div>
                                        <div class="country-option" data-country="RU" data-tier="2">🇷🇺 <?= __('country_ru') ?></div>
                                        <div class="country-option" data-country="MX" data-tier="2">🇲🇽 <?= __('country_mx') ?></div>
                                        <div class="country-option" data-country="TR" data-tier="2">🇹🇷 <?= __('country_tr') ?></div>
                                        <div class="country-option" data-country="AR" data-tier="2">🇦🇷 <?= __('country_ar') ?></div>
                                        <div class="country-option" data-country="CL" data-tier="2">🇨🇱 <?= __('country_cl') ?></div>
                                        <div class="country-option" data-country="CO" data-tier="2">🇨🇴 <?= __('country_co') ?></div>
                                        <div class="country-option" data-country="PE" data-tier="2">🇵🇪 <?= __('country_pe') ?></div>
                                        <div class="country-option" data-country="VE" data-tier="2">🇻🇪 <?= __('country_ve') ?></div>
                                        <div class="country-option" data-country="UY" data-tier="2">🇺🇾 <?= __('country_uy') ?></div>
                                        <div class="country-option" data-country="EC" data-tier="2">🇪🇨 <?= __('country_ec') ?></div>
                                        <div class="country-option" data-country="BO" data-tier="2">🇧🇴 <?= __('country_bo') ?></div>
                                        <div class="country-option" data-country="PY" data-tier="2">🇵🇾 <?= __('country_py') ?></div>
                                        <div class="country-option" data-country="ZA" data-tier="2">🇿🇦 <?= __('country_za') ?></div>
                                    </div>
                                    <div class="mb-2">
                                        <strong class="text-danger"><?= __('tier_3_economic') ?></strong>
                                        <div class="country-option" data-country="NG" data-tier="3">🇳🇬 <?= __('country_ng') ?></div>
                                        <div class="country-option" data-country="KE" data-tier="3">🇰🇪 <?= __('country_ke') ?></div>
                                        <div class="country-option" data-country="GH" data-tier="3">🇬🇭 <?= __('country_gh') ?></div>
                                        <div class="country-option" data-country="UG" data-tier="3">🇺🇬 <?= __('country_ug') ?></div>
                                        <div class="country-option" data-country="TZ" data-tier="3">🇹🇿 <?= __('country_tz') ?></div>
                                        <div class="country-option" data-country="ET" data-tier="3">🇪🇹 <?= __('country_et') ?></div>
                                        <div class="country-option" data-country="MZ" data-tier="3">🇲🇿 <?= __('country_mz') ?></div>
                                        <div class="country-option" data-country="ZW" data-tier="3">🇿🇼 <?= __('country_zw') ?></div>
                                        <div class="country-option" data-country="ZM" data-tier="3">🇿🇲 <?= __('country_zm') ?></div>
                                        <div class="country-option" data-country="MW" data-tier="3">🇲🇼 <?= __('country_mw') ?></div>
                                        <div class="country-option" data-country="BW" data-tier="3">🇧🇼 <?= __('country_bw') ?></div>
                                        <div class="country-option" data-country="NAM" data-tier="3">🇳🇦 <?= __('country_nam') ?></div>
                                        <div class="country-option" data-country="VN" data-tier="3">🇻🇳 <?= __('country_vn') ?></div>
                                        <div class="country-option" data-country="PH" data-tier="3">🇵🇭 <?= __('country_ph') ?></div>
                                        <div class="country-option" data-country="EG" data-tier="3">🇪🇬 <?= __('country_eg') ?></div>
                                        <div class="country-option" data-country="PK" data-tier="3">🇵🇰 <?= __('country_pk') ?></div>
                                        <div class="country-option" data-country="BD" data-tier="3">🇧🇩 <?= __('country_bd') ?></div>
                                        <div class="country-option" data-country="LK" data-tier="3">🇱🇰 <?= __('country_lk') ?></div>
                                        <div class="country-option" data-country="NP" data-tier="3">🇳🇵 <?= __('country_np') ?></div>
                                        <div class="country-option" data-country="MM" data-tier="3">🇲🇲 <?= __('country_mm') ?></div>
                                        <div class="country-option" data-country="KH" data-tier="3">🇰🇭 <?= __('country_kh') ?></div>
                                        <div class="country-option" data-country="LA" data-tier="3">🇱🇦 <?= __('country_la') ?></div>
                                        <div class="country-option" data-country="MN" data-tier="3">🇲🇳 <?= __('country_mn') ?></div>
                                    </div>
                                    <div class="mb-2">
                                        <strong class="text-dark"><?= __('tier_difficult') ?></strong>
                                        <div class="country-option" data-country="AF" data-tier="difficult">🇦🇫 <?= __('country_af') ?></div>
                                        <div class="country-option" data-country="IR" data-tier="difficult">🇮🇷 <?= __('country_ir') ?></div>
                                        <div class="country-option" data-country="IQ" data-tier="difficult">🇮🇶 <?= __('country_iq') ?></div>
                                        <div class="country-option" data-country="SY" data-tier="difficult">🇸🇾 <?= __('country_sy') ?></div>
                                        <div class="country-option" data-country="LB" data-tier="difficult">🇱🇧 <?= __('country_lb') ?></div>
                                        <div class="country-option" data-country="JO" data-tier="difficult">🇯🇴 <?= __('country_jo') ?></div>
                                        <div class="country-option" data-country="PS" data-tier="difficult">🇵🇸 <?= __('country_ps') ?></div>
                                        <div class="country-option" data-country="YE" data-tier="difficult">🇾🇪 <?= __('country_ye') ?></div>
                                        <div class="country-option" data-country="OM" data-tier="difficult">🇴🇲 <?= __('country_om') ?></div>
                                        <div class="country-option" data-country="KW" data-tier="difficult">🇰🇼 <?= __('country_kw') ?></div>
                                        <div class="country-option" data-country="QA" data-tier="difficult">🇶🇦 <?= __('country_qa') ?></div>
                                        <div class="country-option" data-country="BH" data-tier="difficult">🇧🇭 <?= __('country_bh') ?></div>
                                        <div class="country-option" data-country="AE" data-tier="difficult">🇦🇪 <?= __('country_ae') ?></div>
                                        <div class="country-option" data-country="SA" data-tier="difficult">🇸🇦 <?= __('country_sa') ?></div>
                                        <div class="country-option" data-country="UA" data-tier="difficult">🇺🇦 <?= __('country_ua') ?></div>
                                    </div>
                                </div>
                                <small class="text-muted"><?= __('country_selection_tip') ?></small>
                            </div>
                        </div>

                        <!-- Правая колонка -->
                        <div class="col-lg-6">
                            <h4><i class="bi bi-tags"></i> <?= __('discounts_and_markups') ?></h4>
                            
                            <div class="mb-3">
                                <label class="form-label"><strong><?= __('discounts') ?></strong></label>
                                <div class="form-check">
                                    <input type="checkbox" class="form-check-input" id="own_badge" name="own_badge">
                                    <label class="form-check-label" for="own_badge"><?= __('own_badge') ?></label>
                                </div>
                                <div class="form-check">
                                    <input type="checkbox" class="form-check-input" id="own_content" name="own_content">
                                    <label class="form-check-label" for="own_content"><?= __('own_content') ?></label>
                                </div>
                                <div class="form-check">
                                    <input type="checkbox" class="form-check-input" id="pilot" name="pilot">
                                    <label class="form-check-label" for="pilot"><?= __('pilot_project') ?></label>
                                </div>
                            </div>

                            <div class="mb-3">
                                <label for="vip_discount" class="form-label"><strong><?= __('vip_discount') ?></strong></label>
                                <select class="form-select" id="vip_discount" name="vip_discount">
                                    <option value="0">0%</option>
                                    <option value="3">3%</option>
                                    <option value="5">5%</option>
                                    <option value="10">10%</option>
                                    <option value="15">15%</option>
                                </select>
                            </div>

                            <h4><i class="bi bi-plus-circle"></i> <?= __('additional_services') ?></h4>
                            <div class="form-check">
                                <input type="checkbox" class="form-check-input" id="difficult_country" name="difficult_country">
                                <label class="form-check-label" for="difficult_country"><?= __('difficult_country') ?></label>
                            </div>
                            <div class="form-check">
                                <input type="checkbox" class="form-check-input" id="urgency" name="urgency">
                                <label class="form-check-label" for="urgency"><?= __('urgency') ?></label>
                            </div>
                            <div class="form-check">
                                <input type="checkbox" class="form-check-input" id="peak_season" name="peak_season">
                                <label class="form-check-label" for="peak_season"><?= __('peak_season') ?></label>
                            </div>
                            <div class="form-check">
                                <input type="checkbox" class="form-check-input" id="exclusive_content" name="exclusive_content">
                                <label class="form-check-label" for="exclusive_content"><?= __('exclusive_content') ?></label>
                            </div>
                        </div>
                    </div>

                    <div class="d-flex justify-content-between mt-4">
                        <button type="button" class="btn btn-primary" id="calculateBtn">
                            <i class="bi bi-calculator"></i> <?= __('calculate') ?>
                        </button>
                        <button type="button" class="btn btn-secondary" id="resetForm">
                            <i class="bi bi-arrow-clockwise"></i> <?= __('reset') ?>
                        </button>
                    </div>
                </form>
            </div>

            <!-- Результаты -->
            <div class="result-section" id="resultBlock" style="display:none;">
                <h3 class="text-center mb-4"><i class="bi bi-graph-up"></i> <?= __('calculation_results') ?></h3>
                
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="text-center">
                            <div class="h5 text-primary"><?= __('views_volume_result') ?></div>
                            <div class="h3" id="res_views">-</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <div class="h5 text-success"><?= __('price_per_view') ?></div>
                            <div class="h3" id="res_cpv">-</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <div class="h5 text-warning"><?= __('country_multiplier') ?></div>
                            <div class="h3" id="res_multiplier">-</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <div class="h5 text-info"><?= __('market_discount') ?></div>
                            <div class="h3" id="res_market_discount">-</div>
                        </div>
                    </div>
                </div>
                
                <!-- Новая секция с ценами по CPM и итоговыми ценами -->
                <div class="row mb-4">
                    <div class="col-md-4">
                        <div class="text-center">
                            <div class="h5 text-primary"><?= __('cpm_price') ?></div>
                            <div class="h3" id="res_cpm">-</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center">
                            <div class="h5 text-success"><?= __('price_per_view_with_discounts') ?></div>
                            <div class="h3" id="res_cpv_final">-</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center">
                            <div class="h5 text-warning"><?= __('cpm_with_discounts') ?></div>
                            <div class="h3" id="res_cpm_final">-</div>
                        </div>
                    </div>
                </div>
                
                <div class="row mb-4" id="platform_multiplier_row" style="display:none;">
                    <div class="col-md-6 offset-md-3">
                        <div class="text-center">
                            <div class="h5 text-danger" id="res_platform_multiplier_label"><?= __('platform_multiplier') ?></div>
                            <div class="h3" id="res_platform_multiplier">-</div>
                        </div>
                    </div>
                </div>

                <div class="accordion mb-4" id="resultAccordion">
                    <div class="accordion-item">
                        <h2 class="accordion-header">
                            <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#collapseMarkups">
                                <i class="bi bi-plus-circle"></i> <?= __('markups') ?>
                            </button>
                        </h2>
                        <div id="collapseMarkups" class="accordion-collapse collapse show">
                            <div class="accordion-body">
                                <div id="res_markups"></div>
                                <div class="mt-2">
                                    <strong><?= __('markups_sum') ?>: <span id="res_markup_amount">-</span></strong>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="accordion-item">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseDiscounts">
                                <i class="bi bi-dash-circle"></i> <?= __('discounts_result') ?>
                            </button>
                        </h2>
                        <div id="collapseDiscounts" class="accordion-collapse collapse">
                            <div class="accordion-body">
                                <div id="res_discounts"></div>
                                <div class="mt-2">
                                    <strong><?= __('discounts_sum') ?>: <span id="res_discount_amount">-</span></strong>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="final-cost">
                    <div class="h4 mb-2"><?= __('final_cost') ?></div>
                    <div class="h1" id="res_final_cost">-</div>
                </div>

                <div class="text-center mt-4">
                    <button class="btn btn-success me-2" id="saveCalc">
                        <i class="bi bi-save"></i> <?= __('save_calculation') ?>
                    </button>
                    <button class="btn btn-info" id="copySummary">
                        <i class="bi bi-clipboard"></i> <?= __('copy_summary') ?>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <?= $lang->getLanguageSwitcherScript() ?>
    <script>
        // Константы
        const BASE_TARIFFS = {
            15000000: 0.055,
            30000000: 0.050,
            50000000: 0.045,
            100000000: 0.040
        };
        
        const COUNTRY_MULTIPLIERS = {
            1: 1.0,    // Tier1 - базовая цена
            2: 0.85,   // Tier2 - скидка 15%
            3: 0.7,    // Tier3 - скидка 30%
            'difficult': 1.0  // Сложные страны - базовая цена (100%)
        };
        
        const MARKET_DISCOUNTS = {
            50000000: 5,      // 50 млн+ - скидка 5%
            100000000: 10,    // 100 млн+ - скидка 10%
            200000000: 15,    // 200 млн+ - скидка 15%
            500000000: 20     // 500 млн+ - скидка 20%
        };
        
        const DISCOUNTS = {
            'own_badge': 3,
            'own_content': 15,
            'pilot': 10
        };
        
        const MARKUPS = {
            'difficult_country': 30,
            'urgency': 40,
            'peak_season': 25,
            'exclusive_content': 35
        };
        
        // Курсы валют по ЦБ РФ (актуальные на 2025 год)
        const usdToRub = 92.5;  // 1 USD = 92.5 RUB
        const eurToRub = 100.8; // 1 EUR = 100.8 RUB
        
        // Выбранные страны
        let selectedCountries = [];
        
        // Инициализация
        $(document).ready(function() {
            initializeCountrySelection();
            initializeEventHandlers();
            calculate();
        });
        
        function initializeCountrySelection() {
            $('.country-option').click(function() {
                const country = $(this).data('country');
                const tier = $(this).data('tier');
                
                if ($(this).hasClass('selected')) {
                    $(this).removeClass('selected');
                    selectedCountries = selectedCountries.filter(c => c.code !== country);
                } else {
                    $(this).addClass('selected');
                    selectedCountries.push({ code: country, tier: tier });
                }
                
                calculate();
            });
        }
        
        function initializeEventHandlers() {
            // Синхронизация слайдера и поля ввода
            $('#views_mln').on('input', function() {
                $('#views_slider').val($(this).val());
                calculate();
            });
            
            $('#views_slider').on('input', function() {
                $('#views_mln').val($(this).val());
                calculate();
            });
            
            // Пересчет при изменении любых полей
            $('#calcForm input, #calcForm select').on('change', calculate);
            
            // Кнопки
            $('#calculateBtn').click(calculate);
            $('#resetForm').click(resetForm);
            $('#saveCalc').click(saveCalculation);
            $('#copySummary').click(copySummary);
        }
        
        function calculate() {
            const views_mln = parseFloat($('#views_mln').val()) || 0;
            const views = views_mln * 1000000;
            
            if (views_mln < 15) {
                $('#resultBlock').hide();
                return;
            }
            
            if (!$('#platform_instagram').is(':checked') && !$('#platform_tiktok').is(':checked') && !$('#platform_youtube_shorts').is(':checked')) {
                return;
            }
            
            // Базовый расчет
            const basePrice = getBasePrice(views);
            const baseCost = views * basePrice;
            
            // Множитель по странам
            const countryMultiplier = getCountryMultiplier();
            const adjustedCost = baseCost * countryMultiplier;
            
            // Рыночная скидка
            const marketDiscount = getMarketDiscount(views);
            const marketDiscountAmount = adjustedCost * (marketDiscount / 100);
            const costAfterMarketDiscount = adjustedCost - marketDiscountAmount;
            
            // Множитель по платформам
            const platformMultiplier = getPlatformMultiplier();
            const costAfterPlatform = costAfterMarketDiscount * platformMultiplier;
            
            // Скидки
            const { discountPercent, discountList } = calculateDiscounts();
            const discountAmount = costAfterPlatform * (discountPercent / 100);
            const costAfterDiscounts = costAfterPlatform - discountAmount;
            
            // Надбавки
            const { markupPercent, markupList } = calculateMarkups();
            const markupAmount = costAfterDiscounts * (markupPercent / 100);
            const finalCost = costAfterDiscounts + markupAmount;
            
            // Конвертация валюты
            const currency = $('#currency').val();
            const { symbol, convertedCost } = convertCurrency(finalCost, currency);
            
            // Отображение результатов
            displayResults(views_mln, basePrice, countryMultiplier, marketDiscount, 
                         platformMultiplier, discountAmount, markupAmount, convertedCost, symbol, 
                         discountList, markupList, currency);
        }
        
        function getBasePrice(views) {
            if (views >= 100000000) return 0.040;
            if (views >= 50000000) return 0.045;
            if (views >= 30000000) return 0.050;
            if (views >= 15000000) return 0.055;
            return 0.055;
        }
        
        function getCountryMultiplier() {
            if (selectedCountries.length === 0) return 1.0;
            
            const avgTier = selectedCountries.reduce((sum, country) => {
                // Обрабатываем как числовые, так и строковые тиры
                if (country.tier === 'difficult') return sum + 4; // Присваиваем числовое значение для сложных стран
                return sum + country.tier;
            }, 0) / selectedCountries.length;
            
            const tier = Math.round(avgTier);
            
            // Маппинг для числовых тиров
            if (tier === 4) return COUNTRY_MULTIPLIERS['difficult']; // Сложные страны
            return COUNTRY_MULTIPLIERS[tier] || 1.0;
        }
        
        function getMarketDiscount(views) {
            for (const [minViews, discount] of Object.entries(MARKET_DISCOUNTS)) {
                if (views >= parseInt(minViews)) {
                    return discount;
                }
            }
            return 0;
        }
        
        function getPlatformMultiplier() {
            let multiplier = 1.0;
            
            if ($('#platform_youtube_shorts').is(':checked')) {
                multiplier = 1.15; // YouTube Shorts +15%
            }
            
            return multiplier;
        }
        
        function calculateDiscounts() {
            let totalDiscount = 0;
            let discountList = [];
            
            for (const [key, discount] of Object.entries(DISCOUNTS)) {
                if ($(`#${key}`).is(':checked')) {
                    totalDiscount += discount;
                    discountList.push(`<div class="d-flex justify-content-between"><span>${getDiscountName(key)}</span><span class="text-success">-${discount}%</span></div>`);
                }
            }
            
            const vipDiscount = parseFloat($('#vip_discount').val()) || 0;
            if (vipDiscount > 0) {
                totalDiscount += vipDiscount;
                discountList.push(`<div class="d-flex justify-content-between"><span>VIP скидка</span><span class="text-success">-${vipDiscount}%</span></div>`);
            }
            
            return { discountPercent: totalDiscount, discountList };
        }
        
        function calculateMarkups() {
            let totalMarkup = 0;
            let markupList = [];
            
            for (const [key, markup] of Object.entries(MARKUPS)) {
                if ($(`#${key}`).is(':checked')) {
                    totalMarkup += markup;
                    markupList.push(`<div class="d-flex justify-content-between"><span>${getMarkupName(key)}</span><span class="text-danger">+${markup}%</span></div>`);
                }
            }
            
            return { markupPercent: totalMarkup, markupList };
        }
        
        function getDiscountName(key) {
            const names = {
                'own_badge': 'Свой бейдж',
                'own_content': 'Свой контент',
                'pilot': 'Пилотный проект'
            };
            return names[key] || key;
        }
        
        function getMarkupName(key) {
            const names = {
                'difficult_country': 'Сложная страна',
                'urgency': 'Срочность',
                'peak_season': 'Пиковый сезон',
                'exclusive_content': 'Эксклюзивный контент'
            };
            return names[key] || key;
        }
        
        function convertCurrency(amount, currency) {
            let symbol = ' ₽';
            let convertedAmount = amount;
            
            if (currency === 'USD') {
                convertedAmount = amount / usdToRub;
                symbol = ' $';
            } else if (currency === 'EUR') {
                convertedAmount = amount / eurToRub;
                symbol = ' €';
            }
            
            return { symbol, convertedCost: convertedAmount };
        }
        
        function displayResults(views_mln, basePrice, countryMultiplier, marketDiscount, 
                               platformMultiplier, discountAmount, markupAmount, finalCost, symbol, 
                               discountList, markupList, currency) {
            
            $('#res_views').text(views_mln.toLocaleString('ru-RU') + ' млн');
            
            // Конвертируем цену за просмотр в выбранную валюту
            const { symbol: cpvSymbol, convertedCost: cpvCost } = convertCurrency(basePrice, currency);
            $('#res_cpv').text(cpvCost.toFixed(4) + cpvSymbol);
            
            // Рассчитываем CPM (цена за 1000 просмотров)
            const cpm = cpvCost * 1000;
            $('#res_cpm').text(cpm.toFixed(2) + cpvSymbol);
            
            // Рассчитываем итоговую цену за 1 просмотр со всеми скидками и надбавками
            const finalCostPerView = finalCost / (views_mln * 1000000);
            $('#res_cpv_final').text(finalCostPerView.toFixed(4) + symbol);
            
            // Рассчитываем итоговый CPM со скидками
            const finalCpm = finalCostPerView * 1000;
            $('#res_cpm_final').text(finalCpm.toFixed(2) + symbol);
            
            $('#res_multiplier').text((countryMultiplier * 100).toFixed(0) + '%');
            $('#res_market_discount').text(marketDiscount + '%');
            
            // Добавляем информацию о множителе платформы
            if (platformMultiplier > 1.0) {
                $('#res_platform_multiplier').text('+' + ((platformMultiplier - 1) * 100).toFixed(0) + '%');
                $('#platform_multiplier_row').show();
            } else {
                $('#platform_multiplier_row').hide();
            }
            
            // Конвертируем суммы надбавок и скидок в выбранную валюту
            const { symbol: markupSymbol, convertedCost: markupConverted } = convertCurrency(markupAmount, currency);
            const { symbol: discountSymbol, convertedCost: discountConverted } = convertCurrency(discountAmount, currency);
            
            $('#res_markup_amount').text(markupConverted.toFixed(2) + markupSymbol);
            $('#res_discount_amount').text(discountConverted.toFixed(2) + discountSymbol);
            $('#res_final_cost').text(finalCost.toFixed(2) + symbol);
            
            $('#res_markups').html(markupList.length > 0 ? markupList.join('') : '<div class="text-muted"><?= __('no_markups') ?></div>');
            $('#res_discounts').html(discountList.length > 0 ? discountList.join('') : '<div class="text-muted"><?= __('no_discounts') ?></div>');
            
            $('#resultBlock').show();
        }
        
        function resetForm() {
            $('#calcForm')[0].reset();
            $('#views_slider').val(15);
            $('.country-option').removeClass('selected');
            selectedCountries = [];
            $('#resultBlock').hide();
            calculate();
        }
        
        function saveCalculation() {
            const calculationData = {
                views_mln: parseFloat($('#views_mln').val()) || 0,
                platform_instagram: $('#platform_instagram').is(':checked'),
                platform_tiktok: $('#platform_tiktok').is(':checked'),
                platform_youtube_shorts: $('#platform_youtube_shorts').is(':checked'),
                currency: $('#currency').val(),
                selected_countries: selectedCountries,
                own_badge: $('#own_badge').is(':checked'),
                own_content: $('#own_content').is(':checked'),
                pilot: $('#pilot').is(':checked'),
                vip_discount: parseInt($('#vip_discount').val()) || 0,
                difficult_country: $('#difficult_country').is(':checked'),
                urgency: $('#urgency').is(':checked'),
                peak_season: $('#peak_season').is(':checked'),
                exclusive_content: $('#exclusive_content').is(':checked'),
                
                notes: 'Расчет сохранен автоматически'
            };
            
            $.ajax({
                url: 'ajax_handler.php',
                method: 'POST',
                data: {
                    action: 'save',
                    calculation_data: JSON.stringify(calculationData)
                },
                success: function(response) {
                    try {
                        const result = JSON.parse(response);
                        if (result.success) {
                            showNotification('<?= __('calculation_saved') ?>', 'success');
                        } else {
                            showNotification('<?= __('save_error') ?>' + result.message, 'error');
                        }
                    } catch (e) {
                        showNotification('<?= __('response_error') ?>', 'error');
                    }
                },
                error: function() {
                    showNotification('<?= __('connection_error') ?>', 'error');
                }
            });
        }
        
        function copySummary() {
            const summary = `Расчет стоимости продвижения: ${$('#res_views').text()} просмотров, итоговая стоимость: ${$('#res_final_cost').text()}`;
            navigator.clipboard.writeText(summary);
            showNotification('<?= __('summary_copied') ?>', 'success');
        }
        
        function showNotification(message, type = 'info') {
            const alertClass = type === 'success' ? 'alert-success' : 
                              type === 'error' ? 'alert-danger' : 'alert-info';
            
            const notification = $(`
                <div class="alert ${alertClass} alert-dismissible fade show notification" role="alert">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `);
            
            $('body').append(notification);
            
            setTimeout(function() {
                notification.alert('close');
            }, 5000);
        }
    </script>
</body>
</html>