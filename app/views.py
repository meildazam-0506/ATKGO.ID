
import secrets
import uuid

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction, IntegrityError
from django.contrib.auth import logout


# =====================================
# PENGATURAN OTP
# =====================================

OTP_DURATION = 300
OTP_MAX_ATTEMPTS = 5


def clear_otp_session(request):
    keys = [
        'otp_email',
        'otp_hash',
        'otp_expiry',
        'otp_attempts',
        'otp_flow',
        'otp_user_id',
        'pending_registration',
        'otp_last_sent',
    ]

    for key in keys:
        request.session.pop(key, None)


def send_otp_email(request, email):
    otp = str(secrets.randbelow(900000) + 100000)

    send_mail(
        subject='Kode Verifikasi ATKGO.ID',
        message=(
            f'Halo!\n\n'
            f'Kode OTP ATKGO.ID kamu adalah: {otp}\n\n'
            f'Kode berlaku selama 5 menit.\n'
            f'Jangan bagikan kode ini kepada siapa pun.\n\n'
            f'Terima kasih,\nATKGO.ID'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

    request.session['otp_email'] = email
    request.session['otp_hash'] = make_password(otp)
    request.session['otp_expiry'] = (
        timezone.now().timestamp() + OTP_DURATION
    )
    request.session['otp_attempts'] = 0
    request.session['otp_last_sent'] = timezone.now().timestamp()


# =====================================
# HALAMAN PUBLIK
# =====================================

def landing(request):
    return render(request, 'app/landing.html')


# =====================================
# LOGIN DAN PENDAFTARAN
# =====================================

def login_page(request):

    if request.user.is_authenticated:
        return redirect('beranda')

    if request.method == 'POST':

        action = request.POST.get('action')
        User = get_user_model()

        # ---------------------------------
        # BATAL VERIFIKASI OTP
        # ---------------------------------

        if action == 'cancel_otp':
            clear_otp_session(request)
            messages.info(request, 'Proses verifikasi dibatalkan.')
            return redirect('login')

        # ---------------------------------
        # PENDAFTARAN KONSUMEN
        # ---------------------------------

        elif action == 'register_send_otp':

            full_name = request.POST.get(
                'full_name', ''
            ).strip()

            email = request.POST.get(
                'email', ''
            ).strip().lower()

            password = request.POST.get('password', '')
            confirm_password = request.POST.get(
                'confirm_password', ''
            )

            if not full_name or not email or not password:
                messages.error(
                    request,
                    'Semua data pendaftaran wajib diisi.'
                )
                return render(
                    request,
                    'app/login.html',
                    {'mode': 'register'}
                )

            try:
                validate_email(email)
            except ValidationError:
                messages.error(
                    request,
                    'Format email tidak valid.'
                )
                return render(
                    request,
                    'app/login.html',
                    {'mode': 'register'}
                )

            if password != confirm_password:
                messages.error(
                    request,
                    'Konfirmasi password tidak cocok.'
                )
                return render(
                    request,
                    'app/login.html',
                    {'mode': 'register'}
                )

            if User.objects.filter(email__iexact=email).exists():
                messages.error(
                    request,
                    'Email sudah terdaftar. Silakan login.'
                )
                return render(
                    request,
                    'app/login.html',
                    {'mode': 'login'}
                )

            try:
                validate_password(password)
            except ValidationError as errors:
                for error in errors.messages:
                    messages.error(request, error)

                return render(
                    request,
                    'app/login.html',
                    {'mode': 'register'}
                )

            try:
                send_otp_email(request, email)

                request.session['otp_flow'] = 'register'

                request.session['pending_registration'] = {
                    'full_name': full_name,
                    'email': email,
                    'password_hash': make_password(password),
                }

                messages.success(
                    request,
                    'Kode OTP pendaftaran telah dikirim ke email kamu.'
                )

            except Exception as e:
                print('ERROR SMTP:', repr(e))

                clear_otp_session(request)

                messages.error(
                    request,
                    'Gagal mengirim OTP. Periksa konfigurasi email.'
                )

                return render(
                    request,
                    'app/login.html',
                    {'mode': 'register'}
                )

            return redirect('login')

        # ---------------------------------
        # LOGIN KONSUMEN
        # ---------------------------------

        elif action == 'login_send_otp':

            email = request.POST.get(
                'email', ''
            ).strip().lower()

            password = request.POST.get('password', '')

            if not email or not password:
                messages.error(
                    request,
                    'Email dan password wajib diisi.'
                )
                return render(
                    request,
                    'app/login.html',
                    {'mode': 'login'}
                )

            try:
                validate_email(email)
            except ValidationError:
                messages.error(
                    request,
                    'Format email tidak valid.'
                )
                return render(
                    request,
                    'app/login.html',
                    {'mode': 'login'}
                )

            users = User.objects.filter(email__iexact=email)

            if users.count() != 1:
                messages.error(
                    request,
                    'Akun tidak ditemukan.'
                )
                return render(
                    request,
                    'app/login.html',
                    {'mode': 'login'}
                )

            user = users.first()

            if (
                not user.is_active
                or user.is_staff
                or user.is_superuser
                or not user.check_password(password)
                ):
                messages.error(
                    request,
                    'Email atau password salah.'
                    )
                return render(
                    request,
                    'app/login.html',
                    {'mode': 'login'}
                )

            try:
                send_otp_email(request, email)

                request.session['otp_flow'] = 'login'
                request.session['otp_user_id'] = user.pk

                messages.success(
                    request,
                    'Password benar. OTP telah dikirim ke email kamu.'
                )

            except Exception as e:
                print('ERROR SMTP:', repr(e))

                clear_otp_session(request)

                messages.error(
                    request,
                    'Gagal mengirim OTP. Periksa konfigurasi email.'
                )

                return render(
                    request,
                    'app/login.html',
                    {'mode': 'login'}
                )

            return redirect('login')

        # ---------------------------------
        # KIRIM ULANG OTP
        # ---------------------------------

        elif action == 'resend_otp':

            email = request.session.get('otp_email')
            flow = request.session.get('otp_flow')

            if not email or not flow:
                clear_otp_session(request)

                messages.error(
                    request,
                    'Silakan ulangi proses login atau pendaftaran.'
                )
                return redirect('login')

            last_sent = request.session.get('otp_last_sent', 0)

            if timezone.now().timestamp() - last_sent < 60:
                messages.warning(
                    request,
                    'Tunggu 60 detik sebelum meminta OTP baru.'
                )
                return redirect('login')

            try:
                send_otp_email(request, email)

                messages.success(
                    request,
                    'Kode OTP baru berhasil dikirim.'
                )

            except Exception as e:
                print('ERROR SMTP:', repr(e))

                messages.error(
                    request,
                    'Gagal mengirim ulang OTP.'
                )

            return redirect('login')

        # ---------------------------------
        # VERIFIKASI OTP
        # ---------------------------------

        elif action == 'verify_otp':

            email = request.session.get('otp_email')
            otp_hash = request.session.get('otp_hash')
            expiry = request.session.get('otp_expiry')
            attempts = request.session.get('otp_attempts', 0)
            flow = request.session.get('otp_flow')

            entered_otp = request.POST.get(
                'otp', ''
            ).strip()

            if not email or not otp_hash or not expiry or not flow:
                clear_otp_session(request)

                messages.error(
                    request,
                    'Silakan ulangi proses login atau pendaftaran.'
                )
                return redirect('login')

            if timezone.now().timestamp() > expiry:
                clear_otp_session(request)

                messages.error(
                    request,
                    'OTP kedaluwarsa. Silakan mulai kembali.'
                )
                return redirect('login')

            if attempts >= OTP_MAX_ATTEMPTS:
                clear_otp_session(request)

                messages.error(
                    request,
                    'Terlalu banyak percobaan OTP.'
                )
                return redirect('login')

            if not entered_otp.isdigit() or len(entered_otp) != 6:
                request.session['otp_attempts'] = attempts + 1

                messages.error(
                    request,
                    'Masukkan kode OTP enam digit.'
                )
                return redirect('login')

            if not check_password(entered_otp, otp_hash):
                request.session['otp_attempts'] = attempts + 1

                messages.error(
                    request,
                    'Kode OTP salah.'
                )
                return redirect('login')

            # ---------------------------------
            # OTP BENAR: PROSES PENDAFTARAN
            # ---------------------------------

            if flow == 'register':

                pending = request.session.get(
                    'pending_registration'
                )

                if not pending:
                    clear_otp_session(request)

                    messages.error(
                        request,
                        'Data pendaftaran tidak ditemukan.'
                    )
                    return redirect('login')

                try:
                    with transaction.atomic():

                        if User.objects.filter(
                            email__iexact=email
                        ).exists():
                            clear_otp_session(request)

                            messages.error(
                                request,
                                'Email sudah digunakan akun lain.'
                            )
                            return redirect('login')

                        username = (
                            'konsumen_' + uuid.uuid4().hex[:12]
                        )

                        user = User(
                            username=username,
                            email=email,
                            first_name=pending['full_name'],
                            is_active=True,
                        )

                        # Password sudah di-hash sebelum disimpan
                        user.password = pending['password_hash']
                        user.save()

                except IntegrityError:
                    clear_otp_session(request)

                    messages.error(
                        request,
                        'Pendaftaran gagal. Silakan coba kembali.'
                    )
                    return redirect('login')

            # ---------------------------------
            # OTP BENAR: PROSES LOGIN
            # ---------------------------------

            elif flow == 'login':

                user_id = request.session.get('otp_user_id')

                user = User.objects.filter(
                    pk=user_id,
                    email__iexact=email,
                    is_active=True
                ).first()

                if user is None:
                    clear_otp_session(request)

                    messages.error(
                        request,
                        'Akun tidak ditemukan atau sudah tidak aktif.'
                    )
                    return redirect('login')

            else:
                clear_otp_session(request)

                messages.error(
                    request,
                    'Proses autentikasi tidak valid.'
                )
                return redirect('login')

            # ---------------------------------
            # LOGIN OTOMATIS
            # ---------------------------------

            clear_otp_session(request)

            login(
                request,
                user,
                backend='django.contrib.auth.backends.ModelBackend'
            )

            messages.success(
                request,
                'Selamat datang di ATKGO.ID!'
            )

            return redirect('beranda')

    # ---------------------------------
    # TAMPILKAN HALAMAN LOGIN
    # ---------------------------------

    mode = request.GET.get('mode', 'login')

    if mode not in ['login', 'register']:
        mode = 'login'

    return render(
        request,
        'app/login.html',
        {'mode': mode}
    )


# =====================================
# BERANDA KONSUMEN
# =====================================

@login_required(login_url='login')
def beranda(request):
    return render(request, 'app/index.html')


# =====================================
# HALAMAN KONSUMEN LAINNYA
# =====================================

@login_required(login_url='login')
def produk(request):
    return render(request, 'app/produk.html')


@login_required(login_url='login')
def kategori(request):
    return render(request, 'app/kategori.html')


@login_required(login_url='login')
def tentang(request):
    return render(request, 'app/tentang.html')


@login_required(login_url='login')
def kontak(request):
    return render(request, 'app/kontak.html')


@login_required(login_url='login')
def pembayaran(request):
    return render(request, 'app/pembayaran.html')

from django.contrib.auth import logout

# =====================================
# LOGOUT PENGGUNA
# =====================================

@login_required(login_url='login')
def logout_page(request):

    if request.method == 'POST':
        logout(request)

        messages.success(
            request,
            'Kamu berhasil keluar dari akun ATKGO.ID.'
        )

        return redirect('landing')

    return redirect('beranda')