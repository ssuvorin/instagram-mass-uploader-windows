import requests
import time
import logging

logger = logging.getLogger('bot.instagram_uploader.tfa_api')

class TFAAPI:
    def __init__(self):
        self.base_url = "https://2fa.fb.rip/api/otp"
    
    def get_otp(self, secret_key):
        """
        Получает OTP код для указанного секретного ключа
        """
        try:
            url = f"{self.base_url}/{secret_key}"
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
            if data.get("ok"):
                otp = data["data"]["otp"]
                time_remaining = data["data"]["timeRemaining"]
                logger.info(f"Получен OTP код: {otp}, время жизни: {time_remaining} сек")
                return otp
            else:
                logger.error(f"Ошибка получения OTP: {data}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении OTP: {str(e)}")
            return None
    
    def wait_for_new_otp(self, secret_key, current_otp):
        """
        Ожидает новый OTP код, если текущий скоро истечет
        """
        try:
            url = f"{self.base_url}/{secret_key}"
            while True:
                response = requests.get(url)
                data = response.json()
                
                if data.get("ok"):
                    new_otp = data["data"]["otp"]
                    time_remaining = data["data"]["timeRemaining"]
                    
                    if new_otp != current_otp or time_remaining < 10:
                        logger.info(f"Получен новый OTP код: {new_otp}")
                        return new_otp
                    
                    time.sleep(1)
                else:
                    logger.error(f"Ошибка получения OTP: {data}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка при ожидании нового OTP: {str(e)}")
            return None 