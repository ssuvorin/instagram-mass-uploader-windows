from .common import *

from django.views.decorators.http import require_http_methods

from instgrapi_func.services.hashtag_service import HashtagAnalysisService
from instgrapi_func.services.code_providers import CompositeProvider, TOTPProvider, AutoIMAPEmailProvider


@login_required
@require_http_methods(["GET", "POST"])
def hashtag_analyzer(request):
    """UI: Select account and enter hashtag to compute total views."""
    # Only superusers can access hashtag analyzer
    if not request.user.is_superuser:
        messages.error(request, 'Доступ запрещен. Только администраторы могут использовать анализатор хэштегов.')
        return redirect('dashboard')
    
    accounts = InstagramAccount.objects.all().order_by('username')
    context = {
        'accounts': accounts,
        'active_tab': 'tools',
    }

    if request.method == 'GET':
        return render(request, 'uploader/hashtag/analyzer.html', context)

    account_id = request.POST.get('account_id')
    hashtag = (request.POST.get('hashtag') or '').strip()

    if not account_id or not hashtag:
        messages.error(request, 'Выберите аккаунт и укажите хэштег')
        context['form_account_id'] = account_id
        context['form_hashtag'] = hashtag
        return render(request, 'uploader/hashtag/analyzer.html', context)

    account = get_object_or_404(InstagramAccount, id=account_id)

    # Build composite provider: TOTP (if tfa_secret present) + Email IMAP (if email creds present)
    provider = CompositeProvider([
        TOTPProvider(getattr(account, 'tfa_secret', None)),
        AutoIMAPEmailProvider(getattr(account, 'email_username', None), getattr(account, 'email_password', None), on_log=None),
    ])

    service = HashtagAnalysisService(provider=provider)
    logs: list[str] = []
    console = logging.getLogger('uploader.hashtag')

    def on_log(msg: str):
        logs.append(msg)
        try:
            console.info(msg)
        except Exception:
            pass

    try:
        proxy_dict = None
        proxy = getattr(account, 'current_proxy', None) or getattr(account, 'proxy', None)
        if proxy:
            proxy_dict = proxy.to_dict()

        result = service.analyze_hashtag(
            account_username=account.username,
            account_password=account.password,
            hashtag=hashtag,
            proxy=proxy_dict,
            on_log=on_log,
        )

        context.update({
            'result': result.to_dict(),
            'logs': logs,
            'selected_account': account,
            'form_hashtag': hashtag,
        })
        return render(request, 'uploader/hashtag/analyzer_result.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка анализа: {e}')
        context['logs'] = logs
        context['form_account_id'] = account_id
        context['form_hashtag'] = hashtag
        return render(request, 'uploader/hashtag/analyzer.html', context)


