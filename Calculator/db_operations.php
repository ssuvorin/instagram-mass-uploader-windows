<?php
/**
 * Операции с базой данных для калькулятора
 * Версия: 3.0 (с реальной статистикой по платформам за 2025 год)
 */

require_once 'config.php';

class DatabaseOperations {
    private $pdo;
    
    public function __construct() {
        try {
            $this->pdo = new PDO('sqlite:' . DB_PATH);
            $this->pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            $this->pdo->exec('PRAGMA foreign_keys = ON');
        } catch (PDOException $e) {
            logMessage("Ошибка подключения к БД: " . $e->getMessage(), 'ERROR');
            die('Ошибка подключения к базе данных');
        }
    }
    
    /**
     * Получение базовых тарифов
     */
    public function getTariffs() {
        try {
            $sql = "SELECT * FROM base_tariffs WHERE is_active = 1 ORDER BY min_views";
            $stmt = $this->pdo->prepare($sql);
            $stmt->execute();
            return $stmt->fetchAll(PDO::FETCH_ASSOC);
        } catch (PDOException $e) {
            logMessage("Ошибка получения тарифов: " . $e->getMessage(), 'ERROR');
            return [];
        }
    }
    
    /**
     * Получение тарифов по странам
     */
    public function getCountryTariffs() {
        try {
            $sql = "SELECT * FROM country_tariffs WHERE is_active = 1 ORDER BY tier, country_name";
            $stmt = $this->pdo->prepare($sql);
            $stmt->execute();
            return $stmt->fetchAll(PDO::FETCH_ASSOC);
        } catch (PDOException $e) {
            logMessage("Ошибка получения тарифов по странам: " . $e->getMessage(), 'ERROR');
            return [];
        }
    }
    
    /**
     * Получение рыночных скидок
     */
    public function getMarketDiscounts() {
        try {
            $sql = "SELECT * FROM market_discounts WHERE is_active = 1 ORDER BY min_views";
            $stmt = $this->pdo->prepare($sql);
            $stmt->execute();
            return $stmt->fetchAll(PDO::FETCH_ASSOC);
        } catch (PDOException $e) {
            logMessage("Ошибка получения рыночных скидок: " . $e->getMessage(), 'ERROR');
            return [];
        }
    }
    
    /**
     * Получение списка всех стран
     */
    public function getCountriesList() {
        try {
            $sql = "SELECT DISTINCT country_code, country_name, tier FROM country_tariffs WHERE is_active = 1 ORDER BY tier, country_name";
            error_log("DEBUG: getCountriesList SQL: " . $sql);
            
            $stmt = $this->pdo->prepare($sql);
            $stmt->execute();
            $result = $stmt->fetchAll(PDO::FETCH_ASSOC);
            
            error_log("DEBUG: getCountriesList result count: " . count($result));
            if (count($result) > 0) {
                error_log("DEBUG: First country: " . json_encode($result[0]));
            }
            
            return $result;
        } catch (PDOException $e) {
            error_log("ERROR: getCountriesList failed: " . $e->getMessage());
            logMessage("Ошибка получения списка стран: " . $e->getMessage(), 'ERROR');
            return [];
        }
    }
    
    /**
     * Получение статистики по платформам для конкретной страны
     */
    public function getCountryPlatformStats($countryCode) {
        try {
            $sql = "SELECT * FROM platform_country_stats WHERE country_code = :country_code AND year = 2025 AND month = 1 ORDER BY platform";
            $stmt = $this->pdo->prepare($sql);
            $stmt->bindValue(':country_code', $countryCode);
            $stmt->execute();
            return $stmt->fetchAll(PDO::FETCH_ASSOC);
        } catch (PDOException $e) {
            logMessage("Ошибка получения статистики по платформам: " . $e->getMessage(), 'ERROR');
            return [];
        }
    }
    
    /**
     * Получение обзора по стране
     */
    public function getCountryOverview($countryCode) {
        try {
            $sql = "SELECT * FROM country_overview_stats WHERE country_code = :country_code AND year = 2025";
            $stmt = $this->pdo->prepare($sql);
            $stmt->bindValue(':country_code', $countryCode);
            $stmt->execute();
            return $stmt->fetch(PDO::FETCH_ASSOC);
        } catch (PDOException $e) {
            logMessage("Ошибка получения обзора по стране: " . $e->getMessage(), 'ERROR');
            return null;
        }
    }
    
    /**
     * Получение сводной статистики по всем странам
     */
    public function getPlatformStatsSummary() {
        try {
            $sql = "SELECT * FROM platform_stats_summary ORDER BY tier, country_name, platform";
            $stmt = $this->pdo->prepare($sql);
            $stmt->execute();
            return $stmt->fetchAll(PDO::FETCH_ASSOC);
        } catch (PDOException $e) {
            logMessage("Ошибка получения сводной статистики: " . $e->getMessage(), 'ERROR');
            return [];
        }
    }
    
    /**
     * Получение статистики по платформам (глобально)
     */
    public function getGlobalPlatformStats() {
        try {
            $sql = "SELECT 
                platform,
                SUM(dau) as total_dau,
                SUM(mau) as total_mau,
                SUM(monthly_content_count) as total_monthly_content,
                AVG(avg_engagement_rate) as avg_engagement_rate,
                AVG(avg_video_duration) as avg_video_duration,
                SUM(content_creators) as total_creators
                FROM platform_country_stats 
                WHERE year = 2025 AND month = 1 
                GROUP BY platform 
                ORDER BY total_mau DESC";
            $stmt = $this->pdo->prepare($sql);
            $stmt->execute();
            return $stmt->fetchAll(PDO::FETCH_ASSOC);
        } catch (PDOException $e) {
            logMessage("Ошибка получения глобальной статистики: " . $e->getMessage(), 'ERROR');
            return [];
        }
    }
    
    /**
     * Получение топ стран по платформе
     */
    public function getTopCountriesByPlatform($platform, $limit = 10) {
        try {
            $sql = "SELECT 
                country_code,
                country_name,
                dau,
                mau,
                monthly_content_count,
                avg_engagement_rate,
                content_creators
                FROM platform_country_stats 
                WHERE platform = :platform AND year = 2025 AND month = 1 
                ORDER BY mau DESC 
                LIMIT :limit";
            $stmt = $this->pdo->prepare($sql);
            $stmt->bindValue(':platform', $platform);
            $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
            $stmt->execute();
            return $stmt->fetchAll(PDO::FETCH_ASSOC);
        } catch (PDOException $e) {
            logMessage("Ошибка получения топ стран по платформе: " . $e->getMessage(), 'ERROR');
            return [];
        }
    }
    
    /**
     * Сохранение расчета
     */
    public function saveCalculation($data) {
        try {
            // Валидация данных
            if (!isset($data['views_mln']) || $data['views_mln'] < MIN_VIEWS_MLN) {
                return ['success' => false, 'message' => 'Неверный объем просмотров'];
            }
            
            $sql = "INSERT INTO calculations (
                views_mln, platform_instagram, platform_tiktok, platform_youtube_shorts,
                currency, selected_countries, own_badge, own_content, pilot, vip_discount,
                difficult_country, urgency, preholiday, peak_season, exclusive_content,
                premium_audience, accounts, bulk_order, base_cost,
                country_multiplier, market_discount, final_cost, notes
            ) VALUES (
                :views_mln, :platform_instagram, :platform_tiktok, :platform_youtube_shorts,
                :currency, :selected_countries, :own_badge, :own_content, :pilot, :vip_discount,
                :difficult_country, :urgency, :preholiday, :peak_season, :exclusive_content,
                :premium_audience, :accounts, :bulk_order, :base_cost,
                :country_multiplier, :market_discount, :final_cost, :notes
            )";
            
            $stmt = $this->pdo->prepare($sql);
            
            $stmt->bindValue(':views_mln', $data['views_mln'] ?? 0);
            $stmt->bindValue(':platform_instagram', $data['platform_instagram'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':platform_tiktok', $data['platform_tiktok'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':platform_youtube_shorts', $data['platform_youtube_shorts'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':currency', $data['currency'] ?? 'RUB');
            $stmt->bindValue(':selected_countries', json_encode($data['selected_countries'] ?? []));
            $stmt->bindValue(':own_badge', $data['own_badge'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':own_content', $data['own_content'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':pilot', $data['pilot'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':vip_discount', $data['vip_discount'] ?? 0);
            $stmt->bindValue(':difficult_country', $data['difficult_country'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':urgency', $data['urgency'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':preholiday', $data['preholiday'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':peak_season', $data['peak_season'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':exclusive_content', $data['exclusive_content'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':premium_audience', $data['premium_audience'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':accounts', $data['accounts'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':bulk_order', $data['bulk_order'] ?? 0, PDO::PARAM_BOOL);
            $stmt->bindValue(':base_cost', $data['base_cost'] ?? 0);
            $stmt->bindValue(':country_multiplier', $data['country_multiplier'] ?? 1.0);
            $stmt->bindValue(':market_discount', $data['market_discount'] ?? 0);
            $stmt->bindValue(':final_cost', $data['final_cost'] ?? 0);
            $stmt->bindValue(':notes', $data['notes'] ?? '');
            
            $stmt->execute();
            
            logMessage("Расчет успешно сохранен: ID " . $this->pdo->lastInsertId());
            return ['success' => true, 'message' => 'Расчет сохранен', 'id' => $this->pdo->lastInsertId()];
            
        } catch (PDOException $e) {
            logMessage("Ошибка сохранения расчета: " . $e->getMessage(), 'ERROR');
            return ['success' => false, 'message' => 'Ошибка сохранения: ' . $e->getMessage()];
        }
    }
    
    /**
     * Экспорт данных в CSV
     */
    public function exportToCSV($type = 'platform_stats') {
        try {
            switch ($type) {
                case 'platform_stats':
                    $sql = "SELECT * FROM platform_stats_summary ORDER BY tier, country_name, platform";
                    $filename = 'platform_stats_2025_' . date('Y-m-d_H-i-s') . '.csv';
                    break;
                case 'country_overview':
                    $sql = "SELECT * FROM country_overview_stats WHERE year = 2025 ORDER BY tier, country_name";
                    $filename = 'country_overview_2025_' . date('Y-m-d_H-i-s') . '.csv';
                    break;
                case 'calculations':
                    $sql = "SELECT * FROM calculations ORDER BY created_at DESC LIMIT " . EXPORT_LIMIT;
                    $filename = 'calculations_' . date('Y-m-d_H-i-s') . '.csv';
                    break;
                default:
                    return ['success' => false, 'message' => 'Неверный тип экспорта'];
            }
            
            $stmt = $this->pdo->prepare($sql);
            $stmt->execute();
            $data = $stmt->fetchAll(PDO::FETCH_ASSOC);
            
            if (empty($data)) {
                return ['success' => false, 'message' => 'Нет данных для экспорта'];
            }
            
            // Создаем CSV
            $output = fopen('php://temp', 'r+');
            
            // Заголовки
            fputcsv($output, array_keys($data[0]));
            
            // Данные
            foreach ($data as $row) {
                fputcsv($output, $row);
            }
            
            rewind($output);
            $csv = stream_get_contents($output);
            fclose($output);
            
            return [
                'success' => true,
                'filename' => $filename,
                'data' => $csv,
                'size' => strlen($csv)
            ];
            
        } catch (PDOException $e) {
            logMessage("Ошибка экспорта в CSV: " . $e->getMessage(), 'ERROR');
            return ['success' => false, 'message' => 'Ошибка экспорта: ' . $e->getMessage()];
        }
    }
}
?>
