from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.utils.text import slugify
import secrets
from .models import Agency, Client, ClientHashtag


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner")
    search_fields = ("name", "owner__username")
    actions = ["create_or_reset_owner"]

    @admin.action(description="Create or reset login for selected agencies (owner)")
    def create_or_reset_owner(self, request, queryset):
        User = get_user_model()
        results = []
        for agency in queryset:
            # Generate password
            password = secrets.token_urlsafe(9)
            # Username from agency name
            base_username = slugify(agency.name) or f"agency{agency.id}"
            username = base_username
            suffix = 1
            owner_id = getattr(agency.owner, "id", None)
            while User.objects.filter(username=username).exclude(id=owner_id).exists():
                suffix += 1
                username = f"{base_username}{suffix}"

            if agency.owner:
                user = agency.owner
                if user.username != username:
                    user.username = username
                user.set_password(password)
                user.save(update_fields=["username", "password"])
            else:
                user = User.objects.create_user(username=username, password=password)
                agency.owner = user
                agency.save(update_fields=["owner"])

            results.append(f"Agency #{agency.id} — login: {username} | password: {password}")

        if results:
            self.message_user(request, "\n".join(results), level=messages.SUCCESS)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "agency", "user")
    list_filter = ("agency",)
    search_fields = ("name", "user__username", "agency__name")
    actions = ["create_or_reset_user"]

    @admin.action(description="Create or reset login for selected clients")
    def create_or_reset_user(self, request, queryset):
        User = get_user_model()
        results = []
        for client in queryset:
            # Generate a safe random password (12 chars)
            password = secrets.token_urlsafe(9)

            # Derive a unique username from client name
            base_username = slugify(client.name) or f"client{client.id}"
            username = base_username
            suffix = 1
            while User.objects.filter(username=username).exclude(id=getattr(client.user, "id", None)).exists():
                suffix += 1
                username = f"{base_username}{suffix}"

            if client.user:
                user = client.user
                # If username changed, update it
                if user.username != username:
                    user.username = username
                user.set_password(password)
                user.save(update_fields=["username", "password"])
            else:
                user = User.objects.create_user(username=username, password=password)
                client.user = user
                client.save(update_fields=["user"])

            results.append(f"Client #{client.id} — login: {username} | password: {password}")

        if results:
            self.message_user(request, "\n".join(results), level=messages.SUCCESS)


@admin.register(ClientHashtag)
class ClientHashtagAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "hashtag", "created_at")
    list_filter = ("client",)
    search_fields = ("hashtag", "client__name")


