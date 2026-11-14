from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Uniform error shape: {"ok": false, "detail": "...", "errors": {...}}."""
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    if isinstance(data, dict) and 'detail' in data and len(data) == 1:
        response.data = {'ok': False, 'detail': str(data['detail'])}
    else:
        response.data = {'ok': False, 'detail': 'Please correct the errors below.', 'errors': data}
    return response
