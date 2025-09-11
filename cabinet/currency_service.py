import requests
import json
from decimal import Decimal
from typing import Dict, Optional, Tuple
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CurrencyService:
    """
    Сервис для получения актуальных курсов валют
    """
    
    # Кэш ключи
    CACHE_KEY_USD_RUB = "currency_usd_rub"
    CACHE_KEY_EUR_RUB = "currency_eur_rub"
    CACHE_KEY_RATES = "currency_rates_all"
    
    # Время кэширования (1 час)
    CACHE_TIMEOUT = 3600
    
    # Резервные значения (если API недоступен)
    FALLBACK_USD_RUB = 92.5
    FALLBACK_EUR_RUB = 100.8
    
    def __init__(self):
        self.timeout = 10  # секунд на запрос
        
    def get_rates_cbr(self) -> Optional[Dict[str, float]]:
        """
        Получить курсы валют с API ЦБ РФ
        """
        try:
            response = requests.get(
                "https://www.cbr-xml-daily.ru/daily_json.js",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            valute = data.get("Valute", {})
            
            # USD к рублю
            usd_data = valute.get("USD", {})
            usd_rub = float(usd_data.get("Value", 0)) if usd_data else 0
            
            # EUR к рублю
            eur_data = valute.get("EUR", {})
            eur_rub = float(eur_data.get("Value", 0)) if eur_data else 0
            
            if usd_rub > 0 and eur_rub > 0:
                logger.info(f"ЦБ РФ: USD/RUB = {usd_rub}, EUR/RUB = {eur_rub}")
                return {
                    "usd_rub": usd_rub,
                    "eur_rub": eur_rub,
                    "source": "cbr"
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения курсов ЦБ РФ: {e}")
            
        return None
    
    def get_rates_exchangerate_api(self) -> Optional[Dict[str, float]]:
        """
        Получить курсы валют с exchangerate-api.com (резервный источник)
        """
        try:
            # Получаем USD к другим валютам
            response = requests.get(
                "https://api.exchangerate-api.com/v4/latest/USD",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            rates = data.get("rates", {})
            
            # USD к RUB
            usd_rub = float(rates.get("RUB", 0))
            
            # Для EUR нужен отдельный запрос или расчет
            eur_usd = 1.0 / float(rates.get("EUR", 1)) if rates.get("EUR") else 0
            eur_rub = eur_usd * usd_rub if eur_usd and usd_rub else 0
            
            if usd_rub > 0 and eur_rub > 0:
                logger.info(f"ExchangeRate API: USD/RUB = {usd_rub}, EUR/RUB = {eur_rub}")
                return {
                    "usd_rub": usd_rub,
                    "eur_rub": eur_rub,
                    "source": "exchangerate-api"
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения курсов ExchangeRate API: {e}")
            
        return None
    
    def get_rates_fixer_io(self) -> Optional[Dict[str, float]]:
        """
        Получить курсы валют с fixer.io (еще один резервный источник)
        """
        try:
            # Бесплатный план fixer.io (ограниченный)
            response = requests.get(
                "https://api.fixer.io/latest?base=USD&symbols=RUB,EUR",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("success"):
                rates = data.get("rates", {})
                usd_rub = float(rates.get("RUB", 0))
                
                # EUR через USD
                eur_usd = 1.0 / float(rates.get("EUR", 1)) if rates.get("EUR") else 0
                eur_rub = eur_usd * usd_rub if eur_usd and usd_rub else 0
                
                if usd_rub > 0 and eur_rub > 0:
                    logger.info(f"Fixer.io: USD/RUB = {usd_rub}, EUR/RUB = {eur_rub}")
                    return {
                        "usd_rub": usd_rub,
                        "eur_rub": eur_rub,
                        "source": "fixer"
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка получения курсов Fixer.io: {e}")
            
        return None
    
    def fetch_fresh_rates(self) -> Dict[str, float]:
        """
        Получить свежие курсы валют из разных источников
        """
        # Пробуем источники по приоритету
        sources = [
            self.get_rates_cbr,           # ЦБ РФ - основной
            self.get_rates_exchangerate_api,  # ExchangeRate API
            self.get_rates_fixer_io,      # Fixer.io
        ]
        
        for source_func in sources:
            rates = source_func()
            if rates:
                return rates
        
        # Если все источники недоступны, используем резервные значения
        logger.warning("Все источники курсов недоступны, используем резервные значения")
        return {
            "usd_rub": self.FALLBACK_USD_RUB,
            "eur_rub": self.FALLBACK_EUR_RUB,
            "source": "fallback"
        }
    
    def get_cached_rates(self) -> Optional[Dict[str, float]]:
        """
        Получить курсы из кэша
        """
        return cache.get(self.CACHE_KEY_RATES)
    
    def cache_rates(self, rates: Dict[str, float]) -> None:
        """
        Сохранить курсы в кэш
        """
        cache.set(self.CACHE_KEY_RATES, rates, self.CACHE_TIMEOUT)
        cache.set(self.CACHE_KEY_USD_RUB, rates["usd_rub"], self.CACHE_TIMEOUT)
        cache.set(self.CACHE_KEY_EUR_RUB, rates["eur_rub"], self.CACHE_TIMEOUT)
    
    def get_current_rates(self) -> Dict[str, float]:
        """
        Получить актуальные курсы валют (с кэшированием)
        """
        # Сначала проверяем кэш
        cached_rates = self.get_cached_rates()
        if cached_rates:
            logger.debug(f"Курсы из кэша: {cached_rates}")
            return cached_rates
        
        # Получаем свежие курсы
        fresh_rates = self.fetch_fresh_rates()
        
        # Кэшируем результат
        self.cache_rates(fresh_rates)
        
        logger.info(f"Обновлены курсы валют: {fresh_rates}")
        return fresh_rates
    
    def get_usd_rub(self) -> float:
        """
        Получить курс USD к RUB
        """
        cached = cache.get(self.CACHE_KEY_USD_RUB)
        if cached:
            return float(cached)
        
        rates = self.get_current_rates()
        return rates["usd_rub"]
    
    def get_eur_rub(self) -> float:
        """
        Получить курс EUR к RUB
        """
        cached = cache.get(self.CACHE_KEY_EUR_RUB)
        if cached:
            return float(cached)
        
        rates = self.get_current_rates()
        return rates["eur_rub"]
    
    def force_update(self) -> Dict[str, float]:
        """
        Принудительно обновить курсы (игнорируя кэш)
        """
        logger.info("Принудительное обновление курсов валют")
        
        # Удаляем из кэша
        cache.delete(self.CACHE_KEY_RATES)
        cache.delete(self.CACHE_KEY_USD_RUB)
        cache.delete(self.CACHE_KEY_EUR_RUB)
        
        # Получаем свежие курсы
        return self.get_current_rates()
    
    def get_rates_info(self) -> Dict[str, any]:
        """
        Получить информацию о курсах и источнике
        """
        rates = self.get_current_rates()
        return {
            "usd_rub": rates["usd_rub"],
            "eur_rub": rates["eur_rub"],
            "source": rates.get("source", "unknown"),
            "cached": cache.get(self.CACHE_KEY_RATES) is not None,
            "fallback_used": rates.get("source") == "fallback"
        }


# Глобальный экземпляр сервиса
currency_service = CurrencyService()
