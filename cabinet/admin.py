from django.contrib import admin
from .models import Agency, Client, ClientHashtag


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner")
    search_fields = ("name", "owner__username")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "agency", "user")
    list_filter = ("agency",)
    search_fields = ("name", "user__username", "agency__name")


@admin.register(ClientHashtag)
class ClientHashtagAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "hashtag", "created_at")
    list_filter = ("client",)
    search_fields = ("hashtag", "client__name")


