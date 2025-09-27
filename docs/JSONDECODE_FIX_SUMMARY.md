# Исправление JSONDecodeError при Status 201

## Проблема

В логах наблюдались ошибки:
```
Status 201: JSONDecodeError in public_request (url=https://www.instagram.com/pavelmartynov857/?__a=1&__d=dis)
```

Instagram возвращает Status 201 (Created) вместо ожидаемого JSON, что вызывает JSONDecodeError при попытке парсинга ответа.

## Решение

Исправлен файл `instagrapi_func/instagrapi-master_SOURCE/instagrapi/mixins/public.py`:

### 1. Улучшена обработка JSONDecodeError в `_send_public_request`

```python
except JSONDecodeError as e:
    if "/login/" in response.url:
        raise ClientLoginRequired(e, response=response)

    # Handle Status 201 responses (Created) - Instagram returns HTML instead of JSON
    if response.status_code == 201:
        self.public_request_logger.warning(
            "Status %s: Instagram returned HTML instead of JSON (url=%s) - likely challenge/captcha",
            response.status_code,
            response.url,
        )
        # Return empty dict instead of raising error
        self.last_public_json = {}
        return {}
    
    # Handle other JSON decode errors
    # ... existing error handling
```

### 2. Улучшена обработка в `public_a1_request`

```python
try:
    response = self.public_request(
        url, data=data, params=params, headers=headers, return_json=True
    )
    return response.get("graphql") or response
except ClientJSONDecodeError:
    # If JSON decode failed (likely Status 201), return empty dict
    self.public_request_logger.warning(
        "public_a1_request failed for %s - returning empty response", url
    )
    return {}
```

### 3. Улучшена обработка в `public_a1_request_user_info_by_username`

```python
try:
    response = self.public_request(
        url, data=data, params=params, headers=headers, return_json=True
    )
    return response.get("user") or response
except ClientJSONDecodeError:
    # If JSON decode failed (likely Status 201), return empty dict
    self.public_request_logger.warning(
        "public_a1_request_user_info_by_username failed for %s - returning empty response", username
    )
    return {}
```

### 4. Улучшена обработка в `public_graphql_request`

```python
try:
    body_json = self.public_request(...)
    
    # Handle empty response (Status 201 case)
    if not body_json:
        self.public_request_logger.warning(
            "public_graphql_request returned empty response - likely challenge/captcha"
        )
        return {}
    
    # ... rest of processing
except ClientJSONDecodeError:
    # If JSON decode failed (likely Status 201), return empty dict
    self.public_request_logger.warning(
        "public_graphql_request failed due to JSON decode error - returning empty response"
    )
    return {}
```

### 5. Улучшена обработка в `top_search`

```python
try:
    response = self.public_request(url, params=params, return_json=True)
    return response
except ClientJSONDecodeError:
    # If JSON decode failed (likely Status 201), return empty dict
    self.public_request_logger.warning(
        "top_search failed for query '%s' - returning empty response", query
    )
    return {}
```

## Результат

Теперь вместо критических ошибок JSONDecodeError система будет:

1. **Логировать предупреждения** вместо ошибок при Status 201
2. **Возвращать пустые словари** вместо падения с исключением
3. **Продолжать работу** даже при проблемах с парсингом JSON
4. **Предоставлять информативные сообщения** о причинах проблем

## Ожидаемые изменения в логах

Вместо:
```
[ERROR] Status 201: JSONDecodeError in public_request (url=...) >>> 
```

Теперь будет:
```
[WARNING] Status 201: Instagram returned HTML instead of JSON (url=...) - likely challenge/captcha
[WARNING] public_a1_request failed for ... - returning empty response
```

Это позволит системе продолжать работу даже при проблемах с Instagram API, которые часто возникают из-за challenge/captcha или других защитных механизмов.
