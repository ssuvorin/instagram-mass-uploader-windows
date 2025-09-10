from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from django.utils import timezone
from django.db.models.functions import TruncDate
from django.db.models import Sum
from openpyxl import Workbook
from django.http import HttpResponse
import csv
from django.views.decorators.csrf import csrf_exempt
from .models import Agency, Client, ClientHashtag, CalculationHistory
from django.utils.text import slugify
from uploader.models import HashtagAnalytics
from uploader.models import InstagramAccount, AccountAnalytics
from .forms import AgencyForm, ClientForm, ClientHashtagForm
from django.contrib.auth import get_user_model
from .services import AnalyticsService
from .services import AgencyCalculatorService


@login_required
def dashboard(request):
    if request.user.is_superuser:
        agencies = Agency.objects.select_related("owner").all()
        clients = Client.objects.select_related("agency", "user").all()
        return render(request, "cabinet/admin_dashboard.html", {"agencies": agencies, "clients": clients})

    # Non-superusers must be redirected to their specific cabinet only
    client = Client.objects.filter(user=request.user).select_related("agency").first()
    if client:
        return redirect("cabinet_agency_dashboard")  # client sees agency dashboard scoped via query params if needed

    agency = Agency.objects.filter(owner=request.user).first()
    if agency:
        return redirect("cabinet_agency_dashboard")

    messages.info(request, "No cabinet role assigned.")
    return redirect("/")


@login_required
def manage_agencies(request):
    if not request.user.is_superuser:
        return redirect("/")
    if request.method == "POST":
        form = AgencyForm(request.POST)
        if form.is_valid():
            # Create dedicated owner user for the agency (never use current admin)
            from django.contrib.auth import get_user_model
            import secrets
            User = get_user_model()
            agency_name = form.cleaned_data.get("name") or "agency"
            base_username = slugify(agency_name) or "agency"
            username = base_username
            suffix = 1
            while User.objects.filter(username=username).exists():
                suffix += 1
                username = f"{base_username}{suffix}"
            password = secrets.token_urlsafe(9)

            owner_user = User.objects.create_user(username=username, password=password)

            agency = form.save(commit=False)
            agency.owner = owner_user
            agency.save()

            messages.success(
                request,
                f"Agency created. Credentials — Login: {username} | Password: {password}"
            )
            return redirect("cabinet_manage_agencies")
    else:
        form = AgencyForm()
    agencies = Agency.objects.select_related("owner").all()
    return render(request, "cabinet/manage_agencies.html", {"form": form, "agencies": agencies})


@login_required
def manage_clients(request):
    if not request.user.is_superuser:
        return redirect("/")
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            # Create client and dedicated user for login
            client: Client = form.save(commit=False)
            client.save()

            from django.contrib.auth import get_user_model
            import secrets
            User = get_user_model()
            client_name = client.name or "client"
            base_username = slugify(client_name) or "client"
            username = base_username
            suffix = 1
            while User.objects.filter(username=username).exists():
                suffix += 1
                username = f"{base_username}{suffix}"
            password = secrets.token_urlsafe(9)

            login_user = User.objects.create_user(username=username, password=password)
            client.user = login_user
            client.save(update_fields=["user"])

            messages.success(
                request,
                f"Client created. Credentials — Login: {username} | Password: {password}"
            )
            return redirect("cabinet_manage_clients")
    else:
        form = ClientForm()
    clients = Client.objects.select_related("agency", "user").all()
    return render(request, "cabinet/manage_clients.html", {"form": form, "clients": clients})


@login_required
@require_http_methods(["POST"])
def api_admin_reset_agency_owner(request, agency_id: int):
    # Only superusers
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "Forbidden"}, status=403)
    agency = Agency.objects.filter(id=agency_id).first()
    if not agency:
        return JsonResponse({"success": False, "error": "Agency not found"}, status=404)
    from django.contrib.auth import get_user_model
    from django.utils.text import slugify
    import secrets
    User = get_user_model()
    password = secrets.token_urlsafe(9)
    base_username = slugify(agency.name) or f"agency{agency.id}"
    username = base_username
    suffix = 1
    owner_id = getattr(agency.owner, "id", None)
    while User.objects.filter(username=username).exclude(id=owner_id).exists():
        suffix += 1
        username = f"{base_username}{suffix}"
    # If current owner is a superuser, DO NOT modify it. Create a dedicated non-admin owner.
    if agency.owner and agency.owner.is_superuser:
        user = User.objects.create_user(username=username, password=password)
        agency.owner = user
        agency.save(update_fields=["owner"])
    elif agency.owner:
        user = agency.owner
        if user.username != username:
            user.username = username
        user.set_password(password)
        user.save(update_fields=["username", "password"])
    else:
        user = User.objects.create_user(username=username, password=password)
        agency.owner = user
        agency.save(update_fields=["owner"])
    return JsonResponse({"success": True, "username": username, "password": password})


@login_required
def manage_hashtags(request):
    if not request.user.is_superuser:
        return redirect("/")
    if request.method == "POST":
        form = ClientHashtagForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Hashtag added to client")
            return redirect("cabinet_manage_hashtags")
    else:
        form = ClientHashtagForm()
    items = ClientHashtag.objects.select_related("client", "client__agency").all()
    return render(request, "cabinet/manage_hashtags.html", {"form": form, "items": items})


@login_required
def delete_agency(request, agency_id: int):
    if not request.user.is_superuser:
        return redirect("cabinet_dashboard")
    agency = get_object_or_404(Agency, id=agency_id)
    if request.method == "POST":
        agency.delete()
        messages.success(request, "Agency deleted")
        return redirect("cabinet_manage_agencies")
    return render(request, "cabinet/confirm_delete.html", {"object": agency, "type": "Agency"})


@login_required
def delete_client(request, client_id: int):
    if not request.user.is_superuser:
        return redirect("cabinet_dashboard")
    client = get_object_or_404(Client, id=client_id)
    if request.method == "POST":
        client.delete()
        messages.success(request, "Client deleted")
        return redirect("cabinet_manage_clients")
    return render(request, "cabinet/confirm_delete.html", {"object": client, "type": "Client"})


@login_required
def delete_client_hashtag(request, item_id: int):
    if not request.user.is_superuser:
        return redirect("cabinet_dashboard")
    item = get_object_or_404(ClientHashtag, id=item_id)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Hashtag unassigned from client")
        return redirect("cabinet_manage_hashtags")
    return render(request, "cabinet/confirm_delete.html", {"object": item, "type": "Client Hashtag"})


@login_required
def reset_client_user_password(request, client_id: int):
    if not request.user.is_superuser:
        return redirect("cabinet_dashboard")
    client = get_object_or_404(Client, id=client_id)
    if request.method == "POST":
        new_password = request.POST.get("new_password", "").strip()
        # If no password provided or too short, generate a safe one
        generate = False
        if not new_password or len(new_password) < 6:
            import secrets
            new_password = secrets.token_urlsafe(9)
            generate = True

        from django.contrib.auth import get_user_model
        User = get_user_model()

        # If no user or current user is superuser, create dedicated non-admin user
        if not client.user or client.user.is_superuser:
            base_username = slugify(client.name or "client") or "client"
            username = base_username
            suffix = 1
            while User.objects.filter(username=username).exists():
                suffix += 1
                username = f"{base_username}{suffix}"
            login_user = User.objects.create_user(username=username, password=new_password)
            client.user = login_user
            client.save(update_fields=["user"])
            messages.success(
                request,
                f"Client login created. Credentials — Login: {username} | Password: {new_password}"
            )
        else:
            user = client.user
            user.set_password(new_password)
            user.save(update_fields=["password"])
            if generate:
                messages.success(request, f"Password reset. New Password: {new_password}")
            else:
                messages.success(request, f"Password reset for {user.username}")
        return redirect("cabinet_manage_clients")
    return render(request, "cabinet/reset_password.html", {"client": client})


@login_required
def admin_dashboard(request):
    # Restrict direct access: only superusers
    if not request.user.is_superuser:
        return redirect("cabinet_dashboard")
    agencies = Agency.objects.select_related("owner").all()
    clients = Client.objects.select_related("agency", "user").all()
    # Top hashtags by latest snapshot views
    top_analytics = (
        HashtagAnalytics.objects.order_by("hashtag", "-created_at")
    )
    # Deduplicate to latest per hashtag
    seen = set()
    latest_unique: list[HashtagAnalytics] = []
    for row in top_analytics:
        if row.hashtag not in seen:
            latest_unique.append(row)
            seen.add(row.hashtag)
        if len(latest_unique) >= 20:
            break
    # Defaults for KPIs/analytics to avoid NameError on edge branches
    kpi_total_views = 0
    kpi_total_videos = 0
    kpi_avg_per_video = 0.0
    hashtags_breakdown = []
    clients_breakdown = []
    accounts_analytics = []

    # Daily stats for last 7 days (views and videos)
    end = timezone.now()
    start = end - timezone.timedelta(days=7)
    qs = (
        HashtagAnalytics.objects.filter(created_at__gte=start, created_at__lte=end)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            total_views=Sum("total_views"),
            total_videos=Sum("analyzed_medias"),
            total_likes=Sum("total_likes"),
            total_comments=Sum("total_comments"),
        )
        .order_by("day")
    )
    daily_stats = [
        {
            "date": row["day"].strftime("%Y-%m-%d") if row["day"] else "",
            "day_name": row["day"].strftime("%b %d") if row["day"] else "",
            "total_views": int(row.get("total_views") or 0),
            "total_videos": int(row.get("total_videos") or 0),
            "total_likes": int(row.get("total_likes") or 0),
            "total_comments": int(row.get("total_comments") or 0),
        }
        for row in qs
    ]

    # KPI: totals and avg per video (last 7 days)
    kpi_total_views = sum(d["total_views"] for d in daily_stats)
    kpi_total_videos = sum(d["total_videos"] for d in daily_stats)
    kpi_avg_per_video = (kpi_total_views / kpi_total_videos) if kpi_total_videos > 0 else 0.0

    return render(
        request,
        "cabinet/admin_dashboard.html",
        {
            "agencies": agencies,
            "clients": clients,
            "top_hashtags": latest_unique,
            "daily_stats": daily_stats,
        },
    )


@login_required
def agency_dashboard(request):
    # Defaults for KPIs/analytics to avoid NameError on edge branches
    kpi_total_views = 0
    kpi_total_videos = 0
    kpi_avg_per_video = 0.0
    hashtags_breakdown = []
    clients_breakdown = []
    accounts_analytics = []

    agency = Agency.objects.filter(owner=request.user).first()
    client_scope = False
    client_for_scope = None
    if not agency:
        # Allow clients to open this page only for specific agency and client
        client_for_scope = Client.objects.filter(user=request.user).select_related("agency").first()
        if not client_for_scope:
            return render(request, "cabinet/error.html", {"message": "No agency found for this user."})
        q_agency_id = request.GET.get("agency_id")
        q_client_id = request.GET.get("client_id")
        if not q_agency_id or not q_client_id:
            return render(request, "cabinet/error.html", {"message": "agency_id and client_id are required for client access."})
        try:
            q_agency_id_int = int(q_agency_id)
            q_client_id_int = int(q_client_id)
        except ValueError:
            return render(request, "cabinet/error.html", {"message": "Invalid agency_id or client_id."})
        if client_for_scope.agency_id != q_agency_id_int or client_for_scope.id != q_client_id_int:
            return render(request, "cabinet/error.html", {"message": "Access denied for this agency/client."})
        client_scope = True
        agency = client_for_scope.agency

    # Build client list (single client for client scope, all for agency owner)
    if client_scope and client_for_scope:
        clients_list = [client_for_scope]
    else:
        clients_list = list(agency.clients.select_related("user").all())

    client_rows = []
    for c in clients_list:
        hashtags = ClientHashtag.objects.filter(client=c).values_list("hashtag", flat=True)
        total_views = 0
        total_videos = 0
        average_views = 0.0
        count = 0
        for h in hashtags:
            last = HashtagAnalytics.objects.filter(hashtag=h).order_by("-created_at").first()
            if last:
                total_views += int(last.total_views or 0)
                total_videos += int(getattr(last, "analyzed_medias", 0) or 0)
                average_views += float(last.average_views or 0.0)
                count += 1
        avg_avg = (average_views / count) if count > 0 else 0.0
        client_rows.append({"client": c, "total_views": total_views, "total_videos": total_videos, "avg_views": avg_avg})

    # Daily stats for last 7 days (views and videos)
    end = timezone.now()
    start = end - timezone.timedelta(days=7)
    if client_scope and client_for_scope:
        agency_hashtags = ClientHashtag.objects.filter(client=client_for_scope).values_list("hashtag", flat=True)
    else:
        agency_hashtags = ClientHashtag.objects.filter(client__agency=agency).values_list("hashtag", flat=True)
    # Daily stats aggregated by day
    qs = (
        HashtagAnalytics.objects.filter(hashtag__in=agency_hashtags, created_at__gte=start, created_at__lte=end)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            total_views=Sum("total_views"),
            total_videos=Sum("analyzed_medias"),
            total_likes=Sum("total_likes"),
            total_comments=Sum("total_comments"),
        )
        .order_by("day")
    )
    daily_stats = [
        {
            "date": row["day"].strftime("%Y-%m-%d") if row["day"] else "",
            "day_name": row["day"].strftime("%b %d") if row["day"] else "",
            "total_views": int(row.get("total_views") or 0),
            "total_videos": int(row.get("total_videos") or 0),
            "total_likes": int(row.get("total_likes") or 0),
            "total_comments": int(row.get("total_comments") or 0),
        }
        for row in qs
    ]

    # Daily stats with hashtag breakdown for tooltips
    qs_detailed = (
        HashtagAnalytics.objects.filter(hashtag__in=agency_hashtags, created_at__gte=start, created_at__lte=end)
        .annotate(day=TruncDate("created_at"))
        .values("day", "hashtag")
        .annotate(
            views=Sum("total_views"),
            videos=Sum("analyzed_medias"),
            likes=Sum("total_likes"),
            comments=Sum("total_comments"),
        )
        .order_by("day", "hashtag")
    )
    
    # Group by day with hashtag details for tooltips
    daily_stats_detailed = {}
    for row in qs_detailed:
        day_str = row["day"].strftime("%Y-%m-%d") if row["day"] else ""
        if day_str not in daily_stats_detailed:
            daily_stats_detailed[day_str] = {
                "date": day_str,
                "day_name": row["day"].strftime("%b %d") if row["day"] else "",
                "hashtags": []
            }
        daily_stats_detailed[day_str]["hashtags"].append({
            "hashtag": row["hashtag"],
            "views": int(row.get("views") or 0),
            "videos": int(row.get("videos") or 0),
            "likes": int(row.get("likes") or 0),
            "comments": int(row.get("comments") or 0),
        })

    # KPIs
    kpi_total_views = sum(d.get("total_views", 0) for d in daily_stats)
    kpi_total_videos = sum(d.get("total_videos", 0) for d in daily_stats)
    kpi_avg_per_video = (kpi_total_views / kpi_total_videos) if kpi_total_videos > 0 else 0.0

    # Hashtag breakdown for last 7 days (top 10 by views)
    hb_qs = (
        HashtagAnalytics.objects.filter(hashtag__in=agency_hashtags, created_at__gte=start, created_at__lte=end)
        .values("hashtag")
        .annotate(
            views=Sum("total_views"),
            videos=Sum("analyzed_medias"),
            likes=Sum("total_likes"),
            comments=Sum("total_comments"),
        )
        .order_by("-views")[:10]
    )
    hashtags_breakdown = [
        {
            "hashtag": row["hashtag"],
            "views": int(row.get("views") or 0),
            "videos": int(row.get("videos") or 0),
            "likes": int(row.get("likes") or 0),
            "comments": int(row.get("comments") or 0),
            "avg_views": (int(row.get("views") or 0) / int(row.get("videos") or 0)) if int(row.get("videos") or 0) > 0 else 0.0,
            "er": ((int(row.get("likes") or 0) + int(row.get("comments") or 0)) / max(int(row.get("views") or 0), 1)),
        }
        for row in hb_qs
    ]

    # Client breakdown by latest snapshot totals (sum of last snapshot per client's hashtags)
    clients_breakdown = []
    for c in clients_list:
        c_hashtags = ClientHashtag.objects.filter(client=c).values_list("hashtag", flat=True)
        latest_views = 0
        latest_videos = 0
        for h in c_hashtags:
            last = HashtagAnalytics.objects.filter(hashtag=h).order_by("-created_at").first()
            if last:
                latest_views += int(last.total_views or 0)
                latest_videos += int(getattr(last, "analyzed_medias", 0) or 0)
        clients_breakdown.append({
            "client": c.name,
            "views": latest_views,
            "videos": latest_videos,
        })
    # Account analytics (last 7 days) for accounts under agency's clients
    accounts_qs = (
        AccountAnalytics.objects.filter(
            account__client__in=clients_list, created_at__gte=start, created_at__lte=end
        )
        .values("account__id", "account__username")
        .annotate(
            views=Sum("total_views"),
            videos=Sum("total_videos"),
        )
        .order_by("-views")[:15]
    )
    accounts_analytics = [
        {
            "account_id": row["account__id"],
            "username": row["account__username"] or f"#{row['account__id']}",
            "views": int(row.get("views") or 0),
            "videos": int(row.get("videos") or 0),
            "avg_views": (int(row.get("views") or 0) / int(row.get("videos") or 0)) if int(row.get("videos") or 0) > 0 else 0.0,
        }
        for row in accounts_qs
    ]
    # Sort and keep top 10 by views
    clients_breakdown = sorted(clients_breakdown, key=lambda x: x["views"], reverse=True)[:10]

    # Get recent calculations for this agency
    recent_calculations = CalculationHistory.objects.filter(
        agency=agency
    ).select_related('user', 'agency').order_by('-created_at')[:10]

    return render(
        request,
        "cabinet/agency_dashboard.html",
        {
            "agency": agency,
            "client_rows": client_rows,
            "daily_stats": daily_stats,
            "daily_stats_detailed": daily_stats_detailed,
            "hashtags_breakdown": hashtags_breakdown,
            "clients_breakdown": clients_breakdown,
            "kpi_total_views": kpi_total_views,
            "kpi_total_videos": kpi_total_videos,
            "kpi_avg_per_video": kpi_avg_per_video,
            "accounts_analytics": accounts_analytics,
            "recent_calculations": recent_calculations,
        },
    )


@login_required
def export_excel(request):
    """Export analytics to Excel based on role (admin/agency/client)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"

    user = request.user
    filename = f"cabinet_analytics_{user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    if user.is_superuser:
        # Admin summary of latest hashtag snapshots
        ws.append(["Hashtag", "Total Videos", "Total Views", "Avg Views", "Likes", "Comments", "ER", "Created At"])
        rows = (
            HashtagAnalytics.objects.order_by("hashtag", "-created_at")
        )
        seen = set()
        for r in rows:
            if r.hashtag in seen:
                continue
            seen.add(r.hashtag)
            ws.append([
                f"#{r.hashtag}",
                int(getattr(r, "analyzed_medias", 0) or 0),
                int(getattr(r, "total_views", 0) or 0),
                float(getattr(r, "average_views", 0.0) or 0.0),
                int(getattr(r, "total_likes", 0) or 0),
                int(getattr(r, "total_comments", 0) or 0),
                float(getattr(r, "engagement_rate", 0.0) or 0.0),
                r.created_at.strftime("%Y-%m-%d %H:%M"),
            ])
    else:
        client = Client.objects.filter(user=user).first()
        if client:
            service = AnalyticsService(client)
            ws.append(["Hashtag", "Total Videos", "Total Views", "Avg Views", "Likes", "Comments", "ER"]) 
            for d in service.get_hashtag_details():
                ws.append([
                    f"#{d.hashtag}",
                    d.total_videos,
                    d.total_views,
                    round(d.average_views, 2),
                    d.total_likes,
                    d.total_comments,
                    round(d.engagement_rate, 4),
                ])
        else:
            agency = Agency.objects.filter(owner=user).first()
            if agency:
                ws.append(["Client", "Total Views", "Avg Views"])
                clients = agency.clients.all()
                for c in clients:
                    hashtags = ClientHashtag.objects.filter(client=c).values_list("hashtag", flat=True)
                    total_views = 0
                    avg_sum = 0.0
                    cnt = 0
                    for h in hashtags:
                        last = HashtagAnalytics.objects.filter(hashtag=h).order_by("-created_at").first()
                        if last:
                            total_views += int(last.total_views or 0)
                            avg_sum += float(last.average_views or 0.0)
                            cnt += 1
                    ws.append([c.name, total_views, round((avg_sum / cnt) if cnt else 0.0, 2)])

    from io import BytesIO
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f"attachment; filename={filename}"
    return resp


@login_required
def search_view(request):
    query = request.GET.get("q", "").strip()
    if request.user.is_superuser:
        agencies = Agency.objects.filter(name__icontains=query) if query else Agency.objects.none()
        clients = Client.objects.filter(name__icontains=query) if query else Client.objects.none()
        hashtag_qs = ClientHashtag.objects.filter(hashtag__icontains=query) if query else ClientHashtag.objects.none()
    else:
        # Scope by role
        my_client = Client.objects.filter(user=request.user).first()
        if my_client:
            agencies = Agency.objects.none()
            clients = Client.objects.none()
            hashtag_qs = ClientHashtag.objects.filter(client=my_client, hashtag__icontains=query) if query else ClientHashtag.objects.none()
        else:
            my_agency = Agency.objects.filter(owner=request.user).first()
            if my_agency:
                agencies = Agency.objects.filter(id=my_agency.id, name__icontains=query) if query else Agency.objects.filter(id=my_agency.id)
                clients = my_agency.clients.filter(name__icontains=query) if query else my_agency.clients.all()
                hashtag_qs = ClientHashtag.objects.filter(client__agency=my_agency, hashtag__icontains=query) if query else ClientHashtag.objects.filter(client__agency=my_agency)
            else:
                agencies = Agency.objects.none()
                clients = Client.objects.none()
                hashtag_qs = ClientHashtag.objects.none()
    hashtags = sorted({ch.hashtag for ch in hashtag_qs})
    return JsonResponse({
        "query": query,
        "results": {
            "agencies": [{"id": a.id, "name": a.name} for a in agencies],
            "clients": [{"id": c.id, "name": c.name} for c in clients],
            "hashtags": [{"name": h} for h in hashtags],
        },
    })


@login_required
def client_data_view(request):
    client_id = request.GET.get("client_id")
    # Resolve client under role restrictions
    if request.user.is_superuser:
        if not client_id:
            return JsonResponse({"error": "Client ID required"}, status=400)
        client = Client.objects.filter(id=client_id).first()
    else:
        my_client = Client.objects.filter(user=request.user).first()
        if my_client:
            client = my_client
        else:
            my_agency = Agency.objects.filter(owner=request.user).first()
            if not my_agency:
                return JsonResponse({"error": "No cabinet role"}, status=403)
            if not client_id:
                return JsonResponse({"error": "Client ID required"}, status=400)
            client = Client.objects.filter(id=client_id, agency=my_agency).first()
    if not client:
        return JsonResponse({"error": "Client not found or not allowed"}, status=404)
    hashtags = list(ClientHashtag.objects.filter(client=client).values_list("hashtag", flat=True))
    # Aggregate by day for last 7 days
    end = timezone.now()
    start = end - timezone.timedelta(days=7)
    qs = (
        HashtagAnalytics.objects.filter(hashtag__in=hashtags, created_at__gte=start, created_at__lte=end)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total_views=Sum("total_views"))
        .order_by("day")
    )
    daily_stats = [
        {
            "date": row["day"].strftime("%Y-%m-%d") if row["day"] else "",
            "day_name": row["day"].strftime("%b %d") if row["day"] else "",
            "total_views": int(row["total_views"] or 0),
        }
        for row in qs
    ]
    return JsonResponse({"client_name": client.name, "daily_stats": daily_stats})


@login_required
def agency_clients_view(request):
    agency_id = request.GET.get("agency_id")
    if not agency_id:
        return JsonResponse({"error": "Agency ID required"}, status=400)
    agency = Agency.objects.filter(id=agency_id).first()
    if not agency:
        return JsonResponse({"error": "Agency not found"}, status=404)
    # Authorization: only superuser or the owner of the agency
    if not request.user.is_superuser and agency.owner_id != request.user.id:
        return JsonResponse({"error": "Forbidden"}, status=403)
    clients = agency.clients.all()
    return JsonResponse({
        "agency_name": agency.name,
        "clients": [{"id": c.id, "name": c.name} for c in clients],
    })


@login_required
def dashboard_data_view(request):
    # Restrict counts and stats by role
    if request.user.is_superuser:
        agencies_count = Agency.objects.count()
        clients_count = Client.objects.count()
        tracked_hashtags_qs = ClientHashtag.objects.values_list("hashtag", flat=True).distinct()
        filter_kwargs = {}
    else:
        my_client = Client.objects.filter(user=request.user).first()
        if my_client:
            agencies_count = 1
            clients_count = 1
            tracked_hashtags_qs = ClientHashtag.objects.filter(client=my_client).values_list("hashtag", flat=True).distinct()
            filter_kwargs = {"hashtag__in": list(tracked_hashtags_qs)}
        else:
            my_agency = Agency.objects.filter(owner=request.user).first()
            if my_agency:
                agencies_count = 1
                clients_count = my_agency.clients.count()
                tracked_hashtags_qs = ClientHashtag.objects.filter(client__agency=my_agency).values_list("hashtag", flat=True).distinct()
                filter_kwargs = {"hashtag__in": list(tracked_hashtags_qs)}
            else:
                agencies_count = 0
                clients_count = 0
                tracked_hashtags_qs = ClientHashtag.objects.none()
                filter_kwargs = {"id__isnull": True}
    hashtags_count = len(list(tracked_hashtags_qs))

    end = timezone.now()
    start = end - timezone.timedelta(days=7)
    qs = (
        HashtagAnalytics.objects.filter(created_at__gte=start, created_at__lte=end, **filter_kwargs)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total_views=Sum("total_views"))
        .order_by("day")
    )
    daily_stats = [
        {
            "date": row["day"].strftime("%Y-%m-%d") if row["day"] else "",
            "day_name": row["day"].strftime("%b %d") if row["day"] else "",
            "total_views": int(row["total_views"] or 0),
        }
        for row in qs
    ]
    return JsonResponse({
        "agencies_count": agencies_count,
        "clients_count": clients_count,
        "hashtags_count": hashtags_count,
        "daily_stats": daily_stats,
    })


@login_required
def hashtag_detail(request, hashtag: str):
    hashtag = (hashtag or "").lstrip("#").strip()
    # Access control: superuser sees all; client sees only own; agency sees own clients
    if not request.user.is_superuser:
        my_client = Client.objects.filter(user=request.user).first()
        if my_client:
            if not ClientHashtag.objects.filter(client=my_client, hashtag=hashtag).exists():
                return render(request, "cabinet/error.html", {"message": "Access denied for this hashtag."})
        else:
            my_agency = Agency.objects.filter(owner=request.user).first()
            if my_agency:
                if not ClientHashtag.objects.filter(client__agency=my_agency, hashtag=hashtag).exists():
                    return render(request, "cabinet/error.html", {"message": "Access denied for this hashtag."})
            else:
                return render(request, "cabinet/error.html", {"message": "No cabinet role assigned."})
    qs = HashtagAnalytics.objects.filter(hashtag=hashtag).order_by("created_at")
    # Build daily aggregates
    end = timezone.now()
    start = end - timezone.timedelta(days=30)
    agg = (
        HashtagAnalytics.objects.filter(hashtag=hashtag, created_at__gte=start, created_at__lte=end)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total_views=Sum("total_views"), total_videos=Sum("analyzed_medias"))
        .order_by("day")
    )
    daily_stats = [
        {
            "date": row["day"].strftime("%Y-%m-%d") if row["day"] else "",
            "day_name": row["day"].strftime("%b %d") if row["day"] else "",
            "total_views": int(row.get("total_views") or 0),
            "total_videos": int(row.get("total_videos") or 0),
        }
        for row in agg
    ]
    latest = qs.order_by("-created_at").first()
    return render(
        request,
        "cabinet/hashtag_detail.html",
        {
            "hashtag": hashtag,
            "latest": latest,
            "daily_stats": daily_stats,
        },
    )


@login_required
def account_detail_analytics(request, account_id: int):
    account = get_object_or_404(InstagramAccount, id=account_id)
    # Access control for account ownership
    if not request.user.is_superuser:
        my_client = Client.objects.filter(user=request.user).first()
        if my_client:
            if account.client_id != my_client.id:
                return render(request, "cabinet/error.html", {"message": "Access denied for this account."})
        else:
            my_agency = Agency.objects.filter(owner=request.user).first()
            if my_agency:
                if not account.client or account.client.agency_id != my_agency.id:
                    return render(request, "cabinet/error.html", {"message": "Access denied for this account."})
            else:
                return render(request, "cabinet/error.html", {"message": "No cabinet role assigned."})
    # Last 30 days snapshots if any (we create AccountAnalytics periodically)
    end = timezone.now()
    start = end - timezone.timedelta(days=30)
    agg = (
        AccountAnalytics.objects.filter(account=account, created_at__gte=start, created_at__lte=end)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total_views=Sum("total_views"), total_videos=Sum("total_videos"))
        .order_by("day")
    )
    daily_stats = [
        {
            "date": row["day"].strftime("%Y-%m-%d") if row["day"] else "",
            "day_name": row["day"].strftime("%b %d") if row["day"] else "",
            "total_views": int(row.get("total_views") or 0),
            "total_videos": int(row.get("total_videos") or 0),
        }
        for row in agg
    ]
    latest = AccountAnalytics.objects.filter(account=account).order_by("-created_at").first()
    return render(
        request,
        "cabinet/account_detail.html",
        {
            "account": account,
            "latest": latest,
            "daily_stats": daily_stats,
        },
    )


@login_required
def agency_calculator(request):
    # Only superuser or agency owner
    if not request.user.is_superuser:
        my_agency = Agency.objects.filter(owner=request.user).first()
        if not my_agency:
            return redirect("cabinet_dashboard")
    return render(request, "cabinet/agency_calculator.html", {})


@login_required
@require_http_methods(["POST"])
def agency_calc_quote(request):
    # Only superuser or agency owner
    user_agency = None
    if not request.user.is_superuser:
        user_agency = Agency.objects.filter(owner=request.user).first()
        if not user_agency:
            return JsonResponse({"error": "Forbidden"}, status=403)
    
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        data = {}
    
    service = AgencyCalculatorService()
    result = service.calculate(data)
    
    if "error" not in result:
        # Сохраняем расчет в базу данных
        try:
            inputs = result.get("inputs", {})
            totals = result.get("totals", {})
            percents = result.get("percents", {})
            
            # Конвертируем в USD для сохранения
            usd_to_rub = 92.5
            final_cost_usd = totals.get("rub_total", 0) / usd_to_rub
            
            calculation = CalculationHistory.objects.create(
                user=request.user,
                agency=user_agency,
                volume_millions=inputs.get("volume_millions", 0),
                platforms=inputs.get("platforms", []),
                countries=inputs.get("countries", []),
                currency=data.get("currency", "RUB"),
                own_badge=inputs.get("flags", {}).get("own_badge", False),
                own_content=inputs.get("flags", {}).get("own_content", False),
                pilot=inputs.get("flags", {}).get("pilot", False),
                vip_percent=inputs.get("vip_percent", 0),
                urgent=inputs.get("flags", {}).get("urgent", False),
                peak_season=inputs.get("flags", {}).get("peak_season", False),
                exclusive_content=inputs.get("flags", {}).get("exclusive_content", False),
                base_price_per_view=result.get("unit_prices", {}).get("rub_per_view", 0),
                tier_multiplier=result.get("tier", {}).get("multiplier", 1.0),
                platform_multiplier=result.get("platform_multiplier", 1.0),
                discounts_percent=percents.get("discounts", 0),
                surcharges_percent=percents.get("surcharges", 0),
                market_discount_percent=percents.get("market_discount", 0),
                final_cost_rub=totals.get("rub_total", 0),
                final_cost_usd=final_cost_usd,
                calculation_data=result,
                notes=data.get("notes", "")
            )
            result["calculation_id"] = calculation.id
            result["saved"] = True
        except Exception as e:
            result["save_error"] = str(e)
    
    status = 200 if "error" not in result else 400
    return JsonResponse(result, status=status)


@login_required
def export_calculations_csv(request):
    """Export calculation history to CSV"""
    user = request.user
    
    # Получаем расчеты в зависимости от роли
    if user.is_superuser:
        calculations = CalculationHistory.objects.all()
        filename = f"all_calculations_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    else:
        my_agency = Agency.objects.filter(owner=user).first()
        if my_agency:
            calculations = CalculationHistory.objects.filter(agency=my_agency)
            filename = f"agency_{my_agency.name}_calculations_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            calculations = CalculationHistory.objects.filter(user=user)
            filename = f"user_calculations_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Добавляем BOM для корректного отображения кириллицы в Excel
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # Заголовки
    writer.writerow([
        'ID',
        'Дата создания',
        'Пользователь',
        'Агентство',
        'Объем (млн)',
        'Платформы',
        'Страны',
        'Валюта',
        'Базовая цена за просмотр',
        'Множитель по стране',
        'Множитель платформы',
        'Скидки (%)',
        'Надбавки (%)',
        'Рыночная скидка (%)',
        'Итого RUB',
        'Итого USD',
        'Свой бейдж',
        'Свой контент',
        'Пилотный проект',
        'VIP скидка (%)',
        'Срочность',
        'Пиковый сезон',
        'Эксклюзивный контент',
        'Заметки'
    ])
    
    # Данные
    for calc in calculations.select_related('user', 'agency'):
        platforms_str = ', '.join(calc.platforms) if calc.platforms else '-'
        countries_str = ', '.join([c.get('code', '') for c in calc.countries]) if calc.countries else '-'
        
        writer.writerow([
            calc.id,
            calc.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            calc.user.username if calc.user else '-',
            calc.agency.name if calc.agency else '-',
            calc.volume_millions,
            platforms_str,
            countries_str,
            calc.currency,
            f"{calc.base_price_per_view:.6f}",
            f"{calc.tier_multiplier:.3f}",
            f"{calc.platform_multiplier:.3f}",
            f"{calc.discounts_percent:.1f}",
            f"{calc.surcharges_percent:.1f}",
            f"{calc.market_discount_percent:.1f}",
            f"{calc.final_cost_rub:.2f}",
            f"{calc.final_cost_usd:.2f}",
            'Да' if calc.own_badge else 'Нет',
            'Да' if calc.own_content else 'Нет',
            'Да' if calc.pilot else 'Нет',
            f"{calc.vip_percent * 100:.1f}",
            'Да' if calc.urgent else 'Нет',
            'Да' if calc.peak_season else 'Нет',
            'Да' if calc.exclusive_content else 'Нет',
            calc.notes or '-'
        ])
    
    return response


@login_required
def download_calculation_excel(request, calculation_id):
    """Download specific calculation as Excel"""
    calculation = CalculationHistory.objects.filter(id=calculation_id).first()
    if not calculation:
        return HttpResponse("Расчет не найден", status=404)
    
    # Проверка доступа
    if not request.user.is_superuser:
        if calculation.user != request.user:
            my_agency = Agency.objects.filter(owner=request.user).first()
            if not my_agency or calculation.agency != my_agency:
                return HttpResponse("Доступ запрещен", status=403)
    
    wb = Workbook()
    ws = wb.active
    ws.title = f"Расчет {calculation.id}"
    
    # Заголовок
    ws.append([f"Расчет стоимости продвижения #{calculation.id}"])
    ws.append([f"Дата: {calculation.created_at.strftime('%Y-%m-%d %H:%M:%S')}"])
    ws.append([])
    
    # Входные параметры
    ws.append(["ВХОДНЫЕ ПАРАМЕТРЫ"])
    ws.append(["Объем просмотров (млн):", calculation.volume_millions])
    ws.append(["Платформы:", ', '.join(calculation.platforms)])
    ws.append(["Страны:", ', '.join([c.get('code', '') for c in calculation.countries])])
    ws.append(["Валюта:", calculation.currency])
    ws.append([])
    
    # Скидки и надбавки
    ws.append(["СКИДКИ И НАДБАВКИ"])
    ws.append(["Свой бейдж:", "Да" if calculation.own_badge else "Нет"])
    ws.append(["Свой контент:", "Да" if calculation.own_content else "Нет"])
    ws.append(["Пилотный проект:", "Да" if calculation.pilot else "Нет"])
    ws.append(["VIP скидка (%):", f"{calculation.vip_percent * 100:.1f}"])
    ws.append(["Срочность:", "Да" if calculation.urgent else "Нет"])
    ws.append(["Пиковый сезон:", "Да" if calculation.peak_season else "Нет"])
    ws.append(["Эксклюзивный контент:", "Да" if calculation.exclusive_content else "Нет"])
    ws.append([])
    
    # Результаты расчета
    ws.append(["РЕЗУЛЬТАТЫ РАСЧЕТА"])
    ws.append(["Базовая цена за просмотр:", f"{calculation.base_price_per_view:.6f} ₽"])
    ws.append(["Множитель по стране:", f"{calculation.tier_multiplier:.3f}"])
    ws.append(["Множитель платформы:", f"{calculation.platform_multiplier:.3f}"])
    ws.append(["Скидки (%):", f"{calculation.discounts_percent:.1f}"])
    ws.append(["Надбавки (%):", f"{calculation.surcharges_percent:.1f}"])
    ws.append(["Рыночная скидка (%):", f"{calculation.market_discount_percent:.1f}"])
    ws.append([])
    ws.append(["ИТОГОВАЯ СТОИМОСТЬ"])
    ws.append(["В рублях:", f"{calculation.final_cost_rub:.2f} ₽"])
    ws.append(["В долларах:", f"{calculation.final_cost_usd:.2f} $"])
    
    if calculation.notes:
        ws.append([])
        ws.append(["ЗАМЕТКИ"])
        ws.append([calculation.notes])
    
    from io import BytesIO
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    
    filename = f"calculation_{calculation.id}_{calculation.created_at.strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    response = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@login_required
def calculation_details_api(request, calculation_id):
    """API endpoint to get calculation details"""
    calculation = CalculationHistory.objects.filter(id=calculation_id).first()
    if not calculation:
        return JsonResponse({"success": False, "error": "Calculation not found"}, status=404)
    
    # Check access
    if not request.user.is_superuser:
        if calculation.user != request.user:
            my_agency = Agency.objects.filter(owner=request.user).first()
            if not my_agency or calculation.agency != my_agency:
                return JsonResponse({"success": False, "error": "Access denied"}, status=403)
    
    data = {
        "success": True,
        "calculation": {
            "id": calculation.id,
            "volume_millions": calculation.volume_millions,
            "platforms": calculation.platforms,
            "countries": calculation.countries,
            "currency": calculation.currency,
            "own_badge": calculation.own_badge,
            "own_content": calculation.own_content,
            "pilot": calculation.pilot,
            "vip_percent": calculation.vip_percent,
            "urgent": calculation.urgent,
            "peak_season": calculation.peak_season,
            "exclusive_content": calculation.exclusive_content,
            "base_price_per_view": calculation.base_price_per_view,
            "tier_multiplier": calculation.tier_multiplier,
            "platform_multiplier": calculation.platform_multiplier,
            "discounts_percent": calculation.discounts_percent,
            "surcharges_percent": calculation.surcharges_percent,
            "market_discount_percent": calculation.market_discount_percent,
            "final_cost_rub": calculation.final_cost_rub,
            "final_cost_usd": calculation.final_cost_usd,
            "notes": calculation.notes,
            "created_at": calculation.created_at.isoformat(),
            "user_name": calculation.user.username if calculation.user else "Unknown",
        }
    }
    
    return JsonResponse(data)


@login_required
def calculations_list_api(request):
    """API endpoint to get more calculations with pagination"""
    offset = int(request.GET.get('offset', 0))
    limit = 10
    
    user = request.user
    
    # Filter calculations based on user role
    if user.is_superuser:
        calculations = CalculationHistory.objects.all()
    else:
        my_agency = Agency.objects.filter(owner=user).first()
        if my_agency:
            calculations = CalculationHistory.objects.filter(agency=my_agency)
        else:
            calculations = CalculationHistory.objects.filter(user=user)
    
    calculations = calculations.select_related('user', 'agency').order_by('-created_at')[offset:offset+limit]
    
    data = {
        "success": True,
        "calculations": [
            {
                "id": calc.id,
                "volume_millions": calc.volume_millions,
                "platforms": calc.platforms,
                "countries": calc.countries,
                "currency": calc.currency,
                "final_cost_rub": calc.final_cost_rub,
                "final_cost_usd": calc.final_cost_usd,
                "created_at": calc.created_at.isoformat(),
                "user_name": calc.user.username if calc.user else "Unknown",
            }
            for calc in calculations
        ]
    }
    
    return JsonResponse(data)
