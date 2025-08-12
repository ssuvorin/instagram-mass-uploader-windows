"""Views module: cookie_robot (split from monolith)."""
from .common import *
from .misc import run_cookie_robot_task  # ensure available here for background start


def create_cookie_robot_task(request):
    # Deprecated: individual cookie robot replaced by async bulk tool
    from django.http import Http404
    raise Http404("Cookie Robot single-task creation is disabled. Use Bulk Cookie Robot.")
