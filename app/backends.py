from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Backend autentikasi Django yang mengizinkan login menggunakan
    username maupun email secara aman dan konsisten.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get('email')

        if not username or not password:
            return None

        username = str(username).strip()

        # 1. Coba cari berdasarkan username (case-insensitive)
        try:
            user = User.objects.get(username__iexact=username)
            if user.check_password(password):
                if not self.user_can_authenticate(user):
                    if request is not None:
                        request._inactive_user_detected = True
                    return None
                return user
        except User.DoesNotExist:
            user = None
        except User.MultipleObjectsReturned:
            # Jika ada duplikasi username (seharusnya unik di Django)
            try:
                candidates = User.objects.filter(username__iexact=username)
                matching = [u for u in candidates if u.check_password(password)]
                if len(matching) == 1:
                    u = matching[0]
                    if self.user_can_authenticate(u):
                        return u
                    if request is not None:
                        request._inactive_user_detected = True
            except Exception as e:
                if request is not None:
                    request._db_error_detected = str(e)
            return None
        except Exception as e:
            if request is not None:
                request._db_error_detected = str(e)
            return None

        # 2. Coba cari berdasarkan email (case-insensitive)
        try:
            email_candidates = User.objects.filter(email__iexact=username)
            count = email_candidates.count()
        except Exception as e:
            if request is not None:
                request._db_error_detected = str(e)
            return None

        if count == 1:
            user = email_candidates.first()
            if user.check_password(password):
                if not self.user_can_authenticate(user):
                    if request is not None:
                        request._inactive_user_detected = True
                    return None
                return user
        elif count > 1:
            # Penanganan email duplikat tanpa menghapus atau menggabungkan akun
            matching = [u for u in email_candidates if u.check_password(password)]
            if len(matching) == 1:
                u = matching[0]
                if self.user_can_authenticate(u):
                    return u
                if request is not None:
                    request._inactive_user_detected = True
            elif len(matching) > 1:
                # Ambigu: lebih dari 1 akun dengan email dan password yang sama
                if request is not None:
                    request._ambiguous_account_detected = True
            return None

        return None
