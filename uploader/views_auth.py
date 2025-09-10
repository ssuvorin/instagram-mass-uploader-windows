from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """Logout handler that accepts GET and POST, then redirects to login."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("login")


