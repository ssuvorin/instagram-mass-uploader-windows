from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models.functions import TruncDate
from django.db.models import Sum
from .models import Agency, Client, ClientHashtag
from uploader.models import HashtagAnalytics
from .forms import AgencyForm, ClientForm, ClientHashtagForm
from .services import AnalyticsService


@login_required
def dashboard(request):
    if request.user.is_superuser:
        agencies = Agency.objects.select_related("owner").all()
        clients = Client.objects.select_related("agency", "user").all()
        return render(request, "cabinet/admin_dashboard.html", {"agencies": agencies, "clients": clients})

    client = Client.objects.filter(user=request.user).select_related("agency").first()
    if client:
        service = AnalyticsService(client)
        return render(
            request,
            "cabinet/client_dashboard.html",
            {"client": client, "hashtags": service.get_client_hashtags(), "summaries": service.get_hashtag_summaries()},
        )

    agency = Agency.objects.filter(owner=request.user).first()
    if agency:
        clients = agency.clients.select_related("user").all()
        return render(request, "cabinet/agency_dashboard.html", {"agency": agency, "clients": clients})

    messages.info(request, "No cabinet role assigned.")
    return redirect("/")


@login_required
def manage_agencies(request):
    if not request.user.is_superuser:
        return redirect("/")
    if request.method == "POST":
        form = AgencyForm(request.POST)
        if form.is_valid():
            agency = form.save(commit=False)
            agency.owner = request.user
            agency.save()
            messages.success(request, "Agency created")
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
            form.save()
            messages.success(request, "Client created")
            return redirect("cabinet_manage_clients")
    else:
        form = ClientForm()
    clients = Client.objects.select_related("agency", "user").all()
    return render(request, "cabinet/manage_clients.html", {"form": form, "clients": clients})


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
def admin_dashboard(request):
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
    return render(
        request,
        "cabinet/admin_dashboard.html",
        {
            "agencies": agencies,
            "clients": clients,
            "top_hashtags": latest_unique,
        },
    )


@login_required
def agency_dashboard(request):
    agency = Agency.objects.filter(owner=request.user).first()
    if not agency:
        return render(request, "cabinet/error.html", {"message": "No agency found for this user."})
    clients = agency.clients.select_related("user").all()
    client_rows = []
    for c in clients:
        hashtags = ClientHashtag.objects.filter(client=c).values_list("hashtag", flat=True)
        total_views = 0
        average_views = 0.0
        count = 0
        for h in hashtags:
            last = HashtagAnalytics.objects.filter(hashtag=h).order_by("-created_at").first()
            if last:
                total_views += int(last.total_views or 0)
                average_views += float(last.average_views or 0.0)
                count += 1
        avg_avg = (average_views / count) if count > 0 else 0.0
        client_rows.append({"client": c, "total_views": total_views, "avg_views": avg_avg})
    return render(
        request,
        "cabinet/agency_dashboard.html",
        {"agency": agency, "client_rows": client_rows},
    )


@login_required
def search_view(request):
    query = request.GET.get("q", "").strip()
    agencies = Agency.objects.filter(name__icontains=query) if query else Agency.objects.none()
    clients = Client.objects.filter(name__icontains=query) if query else Client.objects.none()
    hashtag_qs = ClientHashtag.objects.filter(hashtag__icontains=query) if query else ClientHashtag.objects.none()
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
    if not client_id:
        return JsonResponse({"error": "Client ID required"}, status=400)
    client = Client.objects.filter(id=client_id).first()
    if not client:
        return JsonResponse({"error": "Client not found"}, status=404)
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
    clients = agency.clients.all()
    return JsonResponse({
        "agency_name": agency.name,
        "clients": [{"id": c.id, "name": c.name} for c in clients],
    })


@login_required
def dashboard_data_view(request):
    agencies_count = Agency.objects.count()
    clients_count = Client.objects.count()
    # Consider tracked hashtags unique across clients
    tracked_hashtags = ClientHashtag.objects.values_list("hashtag", flat=True).distinct()
    hashtags_count = tracked_hashtags.count()

    end = timezone.now()
    start = end - timezone.timedelta(days=7)
    qs = (
        HashtagAnalytics.objects.filter(created_at__gte=start, created_at__lte=end)
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


