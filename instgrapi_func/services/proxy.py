from typing import Optional, Dict


def build_proxy_url(proxy: Dict) -> Optional[str]:
    if not proxy:
        return None
    proto = (proxy.get('type') or 'http').lower()
    host = proxy.get('host')
    port = proxy.get('port')
    user = proxy.get('user')
    pwd = proxy.get('pass')
    if not (host and port):
        return None
    if user and pwd:
        return f"{proto}://{user}:{pwd}@{host}:{port}"
    return f"{proto}://{host}:{port}" 