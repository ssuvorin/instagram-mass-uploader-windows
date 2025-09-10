from django.db import models
from django.conf import settings
import json


class Agency(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agencies")

    def __str__(self) -> str:
        return self.name


class Client(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, null=True, blank=True, related_name="clients")
    name = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="clients", null=True, blank=True)

    def __str__(self) -> str:
        return self.name


class ClientHashtag(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="client_hashtags")
    hashtag = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("client", "hashtag")
        indexes = [
            models.Index(fields=["client", "hashtag"]),
        ]

    def __str__(self) -> str:
        return f"{self.client.name} - #{self.hashtag}"


class CalculationHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calculations")
    agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, null=True, blank=True, related_name="calculations")
    
    # Клиент (имя по вводу после сохранения расчета)
    client_name = models.CharField(max_length=255, blank=True, default="")
    
    # Входные параметры
    volume_millions = models.FloatField()
    platforms = models.JSONField(default=list)  # ["instagram", "tiktok"] 
    countries = models.JSONField(default=list)  # [{"code": "USA", "tier": "1"}]
    currency = models.CharField(max_length=3, default="RUB")
    
    # Флаги скидок и надбавок
    own_badge = models.BooleanField(default=False)
    own_content = models.BooleanField(default=False)
    pilot = models.BooleanField(default=False)
    vip_percent = models.FloatField(default=0.0)
    urgent = models.BooleanField(default=False)
    peak_season = models.BooleanField(default=False)
    exclusive_content = models.BooleanField(default=False)
    
    # Результаты расчета
    base_price_per_view = models.FloatField()
    tier_multiplier = models.FloatField()
    platform_multiplier = models.FloatField()
    discounts_percent = models.FloatField()
    surcharges_percent = models.FloatField() 
    market_discount_percent = models.FloatField()
    final_cost_rub = models.FloatField()
    final_cost_usd = models.FloatField()
    
    # Метаданные
    calculation_data = models.JSONField()  # Полные данные расчета
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['agency', '-created_at']),
        ]
    
    def __str__(self) -> str:
        return f"Calculation {self.id} - {self.volume_millions}M views - {self.final_cost_rub:.2f} ₽"


