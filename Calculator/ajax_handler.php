<?php
/**
 * Обработчик AJAX запросов для калькулятора
 */

require_once 'config.php';
require_once 'db_operations.php';
require_once 'language_manager.php';

// Проверяем, что это POST запрос
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    die(json_encode(['success' => false, 'message' => 'Метод не разрешен']));
}

// Проверяем размер POST данных
if (!checkPostSize()) {
    http_response_code(413);
    die(json_encode(['success' => false, 'message' => 'Слишком большой объем данных']));
}

$action = $_POST['action'] ?? '';

if (!validateAction($action)) {
    http_response_code(400);
    die(json_encode(['success' => false, 'message' => 'Неверное действие']));
}

$db = new DatabaseOperations();

switch ($action) {
    case 'save':
        $calculationData = json_decode($_POST['calculation_data'] ?? '{}', true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            die(json_encode(['success' => false, 'message' => 'Ошибка формата данных']));
        }
        
        $result = $db->saveCalculation($calculationData);
        echo json_encode($result);
        break;
        
    case 'get_countries':
        $countries = $db->getCountriesList();
        echo json_encode(['success' => true, 'countries' => $countries]);
        break;
        
    case 'get_country_stats':
        $countryCode = $_POST['country_code'] ?? '';
        if (empty($countryCode)) {
            echo json_encode(['success' => false, 'message' => 'Код страны не указан']);
            break;
        }
        
        $platformStats = $db->getCountryPlatformStats($countryCode);
        $overview = $db->getCountryOverview($countryCode);
        
        echo json_encode([
            'success' => true,
            'platform_stats' => $platformStats,
            'overview' => $overview
        ]);
        break;
        
    case 'get_platform_summary':
        $summary = $db->getPlatformStatsSummary();
        echo json_encode(['success' => true, 'summary' => $summary]);
        break;
        
    case 'get_global_platform_stats':
        $stats = $db->getGlobalPlatformStats();
        echo json_encode(['success' => true, 'stats' => $stats]);
        break;
        
    case 'get_top_countries':
        $platform = $_POST['platform'] ?? 'instagram';
        $limit = $_POST['limit'] ?? 10;
        $topCountries = $db->getTopCountriesByPlatform($platform, $limit);
        echo json_encode(['success' => true, 'countries' => $topCountries]);
        break;
        
    case 'export_csv':
        $type = $_POST['type'] ?? 'platform_stats';
        $result = $db->exportToCSV($type);
        echo json_encode($result);
        break;
        
    case 'change_language':
        $language = $_POST['language'] ?? '';
        if (empty($language)) {
            echo json_encode(['success' => false, 'message' => 'Язык не указан']);
            break;
        }
        
        $languageManager = getLanguageManager();
        if ($languageManager->setLanguage($language)) {
            echo json_encode(['success' => true, 'message' => 'Язык изменен']);
        } else {
            echo json_encode(['success' => false, 'message' => 'Неверный язык']);
        }
        break;
        
    default:
        echo json_encode(['success' => false, 'message' => 'Неизвестное действие']);
}
?>
