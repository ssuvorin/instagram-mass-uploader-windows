from django.db import models
from django.conf import settings


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


