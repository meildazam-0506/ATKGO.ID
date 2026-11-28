from django.shortcuts import redirect
from django.contrib import messages
from django.middleware.csrf import rotate_token

class FriendlyCsrfMiddleware:
    """
    Middleware pelindung dari layar error 403 CSRF raw.
    Jika terjadi ketidakcocokan token CSRF akibat sesi lama, tab browser tertunda,
    atau server restart, middleware ini secara otomatis merotasi token CSRF baru,
    memberikan pesan informatif ke pengguna, dan mengarahkan kembali ke halaman terkait
    sehingga pengguna dapat langsung mencoba kembali tanpa terhenti di layar 403.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 403:
            content = getattr(response, 'content', b'')
            if b"CSRF" in content or b"csrf" in content:
                try:
                    rotate_token(request)
                except Exception:
                    pass
                try:
                    from django.contrib.messages.storage.fallback import FallbackStorage
                    if not hasattr(request, '_messages'):
                        request._messages = FallbackStorage(request)
                    messages.warning(
                        request,
                        "Sesi keamanan formulir Anda telah diperbarui secara otomatis. Silakan klik submit kembali."
                    )
                except Exception:
                    pass
                referer = request.META.get('HTTP_REFERER') or request.path or '/'
                return redirect(referer)
        return response
