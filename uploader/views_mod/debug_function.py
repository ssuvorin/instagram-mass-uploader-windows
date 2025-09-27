@csrf_exempt
@login_required
def tiktok_proxy_debug_all_accounts(request):
    """Proxy: debug endpoint to check all accounts in TikTok database."""
    import requests
    if request.method != 'GET':
        return _json_response({'detail': 'Method not allowed'}, status=405)
    
    api_base = _get_tiktok_api_base(request)
    try:
        resp = requests.get(f"{api_base}/proxy/debug/all-accounts", timeout=30)
        
        try:
            data = resp.json()
        except Exception:
            data = {'detail': resp.text}
        
        return _json_response(data, status=resp.status_code)
    except requests.exceptions.RequestException as e:
        return _json_response({'detail': f'Upstream error: {str(e)}'}, status=502)
