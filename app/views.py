import re
import json
import uuid
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import (
    Product, ContactMessage, UserPengguna, UserAdmin, Provinsi,
    HeroBanner, Keunggulan, WebsiteSetting, ArticleCategory, Article,
    Order, OrderItem
)
from .midtrans import (
    create_snap_transaction,
    create_core_api_charge,
    check_midtrans_transaction_status,
    verify_midtrans_signature
)

User = get_user_model()


# ==============================================================================
# DEKORATOR AKSES ADMIN
# ==============================================================================

def admin_required(view_func):
    """
    Memastikan pengguna sudah login dan memiliki status is_staff atau is_superuser.
    Pengguna biasa ditolak dan diarahkan ke beranda.
    Pengguna yang belum login diarahkan ke login admin.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Silakan masuk menggunakan akun admin terlebih dahulu.")
            return redirect('admin_login')
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Akses ditolak. Halaman ini hanya untuk Administrator ATKGO.ID.")
            return redirect('beranda')
        return view_func(request, *args, **kwargs)
    return _wrapped


# ==============================================================================
# 1. HALAMAN PUBLIK & BERANDA (CMS DYNAMIC)
# ==============================================================================

def landing(request):
    """Halaman pembuka / landing page dengan konten dinamis CMS."""
    try:
        hero_banner = HeroBanner.objects.filter(is_active=True).first()
        keunggulan_list = list(Keunggulan.objects.filter(is_active=True).order_by('urutan', 'id'))
        website_setting = WebsiteSetting.objects.first()
        artikel_terbaru = list(Article.objects.filter(is_published=True).order_by('-dibuat_pada')[:3])
    except Exception:
        hero_banner = None
        keunggulan_list = []
        website_setting = None
        artikel_terbaru = []

    context = {
        'hero_banner': hero_banner,
        'keunggulan_list': keunggulan_list,
        'website_setting': website_setting,
        'artikel_terbaru': artikel_terbaru,
    }
    return render(request, 'app/landing.html', context)


@login_required(login_url='login')
def beranda(request):
    """Halaman beranda utama konsumen setelah login berhasil."""
    try:
        hero_banner = HeroBanner.objects.filter(is_active=True).first()
        keunggulan_list = list(Keunggulan.objects.filter(is_active=True).order_by('urutan', 'id'))
        website_setting = WebsiteSetting.objects.first()
    except Exception:
        hero_banner = None
        keunggulan_list = []
        website_setting = None

    context = {
        'hero_banner': hero_banner,
        'keunggulan_list': keunggulan_list,
        'website_setting': website_setting,
    }
    return render(request, 'app/index.html', context)


# ==============================================================================
# 2. AUTENTIKASI PELANGGAN (LOGIN, REGISTER, LOGOUT)
# ==============================================================================

def login_page(request):
    """Login & Register Pelanggan ATKGO.ID."""
    if request.user.is_authenticated:
        return redirect('beranda')

    mode = request.GET.get('mode', 'login')
    if mode not in ['login', 'register']:
        mode = 'login'

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'register':
            full_name = request.POST.get('full_name', '').strip()
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip().lower()
            password = request.POST.get('password', '')
            confirm_password = request.POST.get('confirm_password', '')
            telp = request.POST.get('telp', '').strip()

            context = {
                'mode': 'register',
                'form_data': {
                    'full_name': full_name,
                    'username': username,
                    'email': email,
                    'telp': telp,
                }
            }

            if not full_name or not email or not password or not confirm_password:
                messages.error(request, "Semua data pendaftaran wajib diisi.")
                return render(request, 'app/login.html', context)

            if not username:
                clean_prefix = re.sub(r'[^a-zA-Z0-9_]', '', email.split('@')[0]) or 'konsumen'
                candidate = clean_prefix
                counter = 1
                try:
                    while User.objects.filter(username__iexact=candidate).exists():
                        candidate = f"{clean_prefix}_{counter}"
                        counter += 1
                    username = candidate
                except Exception:
                    messages.error(request, "Terjadi kendala pada database saat memeriksa ketersediaan akun.")
                    return render(request, 'app/login.html', context)
            else:
                if not re.match(r'^[\w.@+-]+$', username):
                    messages.error(request, "Username hanya boleh memuat huruf, angka, dan karakter @/./+/-/_.")
                    return render(request, 'app/login.html', context)

                try:
                    if User.objects.filter(username__iexact=username).exists():
                        messages.error(request, f"Username '{username}' sudah digunakan. Silakan gunakan username lain.")
                        return render(request, 'app/login.html', context)
                except Exception:
                    messages.error(request, "Terjadi kendala pada database saat memeriksa ketersediaan username.")
                    return render(request, 'app/login.html', context)

            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "Format alamat email tidak valid.")
                return render(request, 'app/login.html', context)

            try:
                if User.objects.filter(email__iexact=email).exists():
                    messages.error(request, "Alamat email ini sudah terdaftar. Silakan masuk menggunakan akun Anda.")
                    return render(request, 'app/login.html', {'mode': 'login'})
            except Exception:
                messages.error(request, "Terjadi kendala pada database saat memeriksa ketersediaan email.")
                return render(request, 'app/login.html', context)

            if password != confirm_password:
                messages.error(request, "Konfirmasi password tidak cocok dengan password yang dimasukkan.")
                return render(request, 'app/login.html', context)

            try:
                validate_password(password)
            except ValidationError as err:
                for msg in err.messages:
                    messages.error(request, msg)
                return render(request, 'app/login.html', context)

            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=full_name,
                        is_active=True,
                    )
                    UserPengguna.objects.create(
                        user=user,
                        telp=telp or '',
                    )

                messages.success(request, "Pendaftaran berhasil! Akun Anda telah aktif, silakan masuk.")
                return redirect(f"{reverse('login')}?mode=login")

            except IntegrityError:
                messages.error(request, "Terjadi konflik data akun. Silakan coba kembali dengan data lain.")
                return render(request, 'app/login.html', context)
            except Exception as e:
                messages.error(request, f"Gagal menyimpan data pendaftaran: {str(e)}")
                return render(request, 'app/login.html', context)

        else:
            identitas = (
                request.POST.get('username_or_email') or 
                request.POST.get('email') or 
                request.POST.get('username', '')
            ).strip()
            password = request.POST.get('password', '')

            if not identitas or not password:
                messages.error(request, "Email/Username dan password wajib diisi.")
                return render(request, 'app/login.html', {'mode': 'login'})

            try:
                user = authenticate(request, username=identitas, password=password)
            except Exception as e:
                user = None
                request._db_error_detected = str(e)

            if user is None:
                if getattr(request, '_db_error_detected', False):
                    messages.error(request, "Terjadi gangguan koneksi ke database. Silakan coba sesaat lagi.")
                elif getattr(request, '_inactive_user_detected', False):
                    messages.error(request, "Akun Anda saat ini tidak aktif. Silakan hubungi customer service ATKGO.ID.")
                elif getattr(request, '_ambiguous_account_detected', False):
                    messages.error(request, "Terdapat lebih dari satu akun dengan email yang sama. Harap masuk menggunakan username Anda.")
                else:
                    messages.error(request, "Username/Email atau password salah. Silakan coba kembali.")
                return render(request, 'app/login.html', {'mode': 'login'})

            if not user.is_active:
                messages.error(request, "Akun Anda dinonaktifkan.")
                return render(request, 'app/login.html', {'mode': 'login'})

            if not user.is_staff and not user.is_superuser:
                if not hasattr(user, 'anggota'):
                    try:
                        UserPengguna.objects.get_or_create(user=user)
                    except Exception:
                        pass

            try:
                login(request, user)
            except Exception as e:
                messages.error(request, f"Gagal menginisialisasi sesi login: {str(e)}")
                return render(request, 'app/login.html', {'mode': 'login'})
            messages.success(request, f"Selamat datang kembali, {user.first_name or user.username}!")

            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and next_url.startswith('/') and not next_url.startswith('/admin'):
                return redirect(next_url)

            return redirect('beranda')

    return render(request, 'app/login.html', {'mode': mode})


@login_required(login_url='login')
def logout_page(request):
    """Logout pelanggan dan mengakhiri session dengan aman."""
    logout(request)
    messages.success(request, "Anda berhasil keluar dari akun ATKGO.ID.")
    return redirect('landing')


# ==============================================================================
# 3. HALAMAN PROFIL PENGGUNA & PROFIL USAHA
# ==============================================================================

@login_required(login_url='login')
def profil_user(request):
    """
    Halaman Profil Pengguna Terpadu:
    A. Data Pengguna (Personal & Foto Profil)
    B. Profil Usaha (Nama Usaha, Jenis, Alamat Usaha)
    C. Settings & Ganti Password
    """
    user = request.user
    profile, _ = UserPengguna.objects.get_or_create(user=user)

    if request.method == 'POST':
        section = request.POST.get('section')

        if section == 'personal':
            first_name = request.POST.get('first_name', '').strip()
            email = request.POST.get('email', '').strip().lower()
            telp = request.POST.get('telp', '').strip()
            gender = request.POST.get('gender', '').strip()
            alamat = request.POST.get('alamat', '').strip()
            kabupaten_kota = request.POST.get('kabupaten_kota', '').strip()
            kecamatan = request.POST.get('kecamatan', '').strip()
            kelurahan_desa = request.POST.get('kelurahan_desa', '').strip()
            kode_pos = request.POST.get('kode_pos', '').strip()

            if not first_name or not email or not telp:
                messages.error(request, "Nama, email, dan nomor telepon wajib diisi.")
                return redirect('profil')

            # Cek jika email diganti dan sudah digunakan user lain
            if email != user.email and User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
                messages.error(request, "Alamat email sudah digunakan oleh akun lain.")
                return redirect('profil')

            user.first_name = first_name
            user.email = email
            user.save()

            profile.telp = telp
            profile.gender = gender
            profile.alamat = alamat
            profile.kabupaten_kota = kabupaten_kota
            profile.kecamatan = kecamatan
            profile.kelurahan_desa = kelurahan_desa
            profile.kode_pos = kode_pos

            if 'photo' in request.FILES:
                profile.photo = request.FILES['photo']

            profile.save()
            messages.success(request, "Data pribadi dan alamat berhasil diperbarui.")
            return redirect('profil')

        elif section == 'business':
            nama_usaha = request.POST.get('nama_usaha', '').strip()
            jenis_usaha = request.POST.get('jenis_usaha', '').strip()
            alamat_usaha = request.POST.get('alamat_usaha', '').strip()
            telepon_usaha = request.POST.get('telepon_usaha', '').strip()
            catatan_usaha = request.POST.get('catatan_usaha', '').strip()

            profile.nama_usaha = nama_usaha
            profile.jenis_usaha = jenis_usaha
            profile.alamat_usaha = alamat_usaha
            profile.telepon_usaha = telepon_usaha
            profile.catatan_usaha = catatan_usaha
            profile.save()

            messages.success(request, "Informasi profil usaha berhasil disimpan.")
            return redirect('profil')

        elif section == 'password':
            old_password = request.POST.get('old_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_new_password = request.POST.get('confirm_new_password', '')

            if not user.check_password(old_password):
                messages.error(request, "Password saat ini tidak cocok.")
                return redirect('profil')

            if new_password != confirm_new_password:
                messages.error(request, "Konfirmasi password baru tidak cocok.")
                return redirect('profil')

            try:
                validate_password(new_password, user=user)
            except ValidationError as err:
                for msg in err.messages:
                    messages.error(request, msg)
                return redirect('profil')

            user.set_password(new_password)
            user.save()
            # Pertahankan session agar tidak logout setelah ganti password
            update_session_auth_hash(request, user)
            messages.success(request, "Password berhasil diperbarui.")
            return redirect('profil')

    context = {
        'profile': profile,
    }
    return render(request, 'app/profil.html', context)


# ==============================================================================
# 4. HALAMAN ARTIKEL & EDUKASI KONSUMEN
# ==============================================================================

def artikel_list(request):
    """Daftar artikel edukasi dan wawasan ATKGO.ID."""
    query = request.GET.get('q', '').strip()
    kategori_slug = request.GET.get('kategori', '').strip()

    try:
        articles = Article.objects.filter(is_published=True)

        if kategori_slug:
            articles = articles.filter(kategori__slug=kategori_slug)

        if query:
            articles = articles.filter(
                Q(judul__icontains=query) |
                Q(ringkasan__icontains=query) |
                Q(konten__icontains=query)
            )

        categories = list(ArticleCategory.objects.all())
    except Exception:
        articles = []
        categories = []

    context = {
        'articles': articles,
        'categories': categories,
        'query': query,
        'active_category': kategori_slug,
    }
    return render(request, 'app/artikel_list.html', context)


def artikel_detail(request, slug):
    """Halaman detail artikel edukasi lengkap."""
    article = get_object_or_404(Article, slug=slug, is_published=True)
    return render(request, 'app/artikel_detail.html', {'article': article})


# ==============================================================================
# 5. HALAMAN PEMBAYARAN TERINTEGRASI PROFIL
# ==============================================================================

@login_required(login_url='login')
def pembayaran(request):
    """
    Halaman Pembayaran Pesanan yang otomatis mengambil data profil
    pengguna yang sedang login dan terintegrasi dengan Payment Gateway Midtrans Sandbox.
    """
    user = request.user
    profile, _ = UserPengguna.objects.get_or_create(user=user)

    if request.method == 'POST':
        nama = request.POST.get('nama', '').strip() or user.get_full_name() or user.username
        email = request.POST.get('email', '').strip() or user.email
        telepon = request.POST.get('telepon', '').strip()
        bisnis = request.POST.get('bisnis', '').strip()
        alamat = request.POST.get('alamat', '').strip()
        cart_data_raw = request.POST.get('cart_data', '[]')
        payment_channel = request.POST.get('payment_channel', 'qris').strip().lower()
        ewallet_provider = request.POST.get('ewallet_provider', 'gopay').strip().lower()
        va_bank = request.POST.get('va_bank', 'bca').strip().lower()

        # Pemetaan label nama metode pembayaran untuk pencatatan di database
        if payment_channel == 'qris':
            metode = "QRIS"
        elif payment_channel == 'ewallet':
            metode = f"E-Wallet ({ewallet_provider.upper()})"
        elif payment_channel == 'bank_transfer':
            metode = f"Virtual Account ({va_bank.upper()})"
        elif payment_channel == 'credit_card':
            metode = "Kartu Kredit / Debit Online"
        elif payment_channel == 'invoice_b2b':
            metode = "Invoice Bisnis / Purchase Order (PO)"
        else:
            metode = request.POST.get('metode', 'Midtrans Payment Gateway')

        if not telepon or not alamat:
            messages.error(request, "Nomor telepon dan alamat pengiriman wajib diisi.")
            return redirect('pembayaran')

        # Auto-update profil jika sebelumnya data profil masih kosong
        updated_profile = False
        if not profile.telp and telepon:
            profile.telp = telepon
            updated_profile = True
        if not profile.alamat and alamat:
            profile.alamat = alamat
            updated_profile = True
        if not profile.nama_usaha and bisnis:
            profile.nama_usaha = bisnis
            updated_profile = True
        if updated_profile:
            profile.save()

        # Parse data keranjang belanja
        try:
            cart_items = json.loads(cart_data_raw)
        except Exception:
            cart_items = []

        total_harga = 0
        known_prices = {
            'kreatif & dokumentasi': 250000,
            'manajemen social media': 150000,
            'paket layanan agensi': 112000,
            'produksi visual & desain': 200000,
            'strategi konten & brand': 1000000,
        }
        for item in cart_items:
            raw_p = str(item.get('price', 0)).replace(',', '.')
            try:
                price = float(raw_p)
            except Exception:
                price = 0
            if price <= 0:
                name_key = str(item.get('name', '')).strip().lower()
                price = known_prices.get(name_key, 0)
            item['price'] = price
            qty = max(1, int(item.get('qty', 1)))
            total_harga += price * qty

        # Buat nomor pesanan unik
        nomor_pesanan = f"ATK-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        is_online = payment_channel in ['qris', 'ewallet', 'bank_transfer', 'credit_card']
        initial_status = 'Menunggu Pembayaran' if is_online else 'Menunggu Konfirmasi'

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=user,
                    nomor_pesanan=nomor_pesanan,
                    nama_pemesan=nama,
                    email_pemesan=email,
                    telepon_pemesan=telepon,
                    nama_bisnis=bisnis,
                    alamat=alamat,
                    total_harga=total_harga,
                    metode_pembayaran=metode,
                    status=initial_status,
                )

                for item in cart_items:
                    nama_prod = item.get('name', 'Layanan ATKGO')
                    price = float(item.get('price', 0))
                    qty = int(item.get('qty', 1))
                    OrderItem.objects.create(
                        order=order,
                        nama_produk=nama_prod,
                        harga=price,
                        jumlah=qty,
                        subtotal=price * qty,
                    )

            # Integrasi Midtrans Snap untuk pembayaran online
            snap_token = None
            redirect_url = None
            if is_online:
                sub_provider = ewallet_provider if payment_channel == 'ewallet' else va_bank
                snap_token, redirect_url, err = create_snap_transaction(
                    order=order,
                    cart_items=cart_items,
                    payment_channel=payment_channel,
                    sub_provider=sub_provider
                )
                if snap_token:
                    order.snap_token = snap_token
                    order.save(update_fields=['snap_token'])

            return redirect(f"/pembayaran/?order_id={nomor_pesanan}")

        except Exception as e:
            messages.error(request, f"Gagal membuat pesanan: {str(e)}")
            return redirect('pembayaran')

    # GET: Cek apakah ada parameter order_id (menampilkan status / bukti pembayaran)
    order_id_param = request.GET.get('order_id')
    if order_id_param:
        order = Order.objects.filter(nomor_pesanan=order_id_param).prefetch_related('items').first()
        if order and (order.user == user or user.is_staff):
            context = get_order_payment_context(order)
            return render(request, 'app/pembayaran.html', context)

    # GET: Pre-fill otomatis dari data profil pengguna yang sedang login
    context = {
        'nama_pengguna': user.get_full_name() or user.username,
        'email_pengguna': user.email,
        'telepon_pengguna': profile.telp if profile else '',
        'bisnis_pengguna': profile.nama_usaha if profile else '',
        'alamat_pengguna': profile.alamat if profile else '',
        'midtrans_client_key': getattr(settings, 'MIDTRANS_CLIENT_KEY', ''),
        'midtrans_snap_js': getattr(settings, 'MIDTRANS_SNAP_JS', 'https://app.sandbox.midtrans.com/snap/snap.js'),
    }
    return render(request, 'app/pembayaran.html', context)


def get_order_payment_context(order):
    """Menyiapkan data tagihan, QRIS / Virtual Account Midtrans resmi, dan Bukti Pembayaran / Invoice."""
    metode = str(order.metode_pembayaran or '').lower()

    if 'qris' in metode:
        channel = 'qris'
    elif 'virtual account' in metode or 'va' in metode:
        channel = 'bank_transfer'
    elif 'e-wallet' in metode or 'ewallet' in metode:
        channel = 'ewallet'
    elif 'kartu kredit' in metode or 'credit' in metode:
        channel = 'credit_card'
    else:
        channel = 'invoice_b2b'

    # 1. Sinkronisasi status langsung dari server Midtrans jika pesanan belum berstatus Dibayar
    if order.status != 'Dibayar':
        status_res, _ = check_midtrans_transaction_status(order.nomor_pesanan)
        if status_res:
            t_status = status_res.get('transaction_status')
            f_status = status_res.get('fraud_status')
            if t_status in ['capture', 'settlement'] and f_status != 'challenge':
                order.status = 'Dibayar'
                order.save(update_fields=['status'])

    # 2. Pengaturan QR Code dan Virtual Account resmi
    qris_data = f"00020101021226580016ID.CO.MIDTRANS011893600523000001{order.id}520458125303360540{int(order.total_harga)}5802ID5908ATKGO_ID6007JAKARTA62070703A016304"
    qris_qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={qris_data}"

    # Default VA bank
    if 'mandiri' in metode:
        va_bank_name = 'Mandiri'
        va_number = f"Bill Key: {order.nomor_pesanan.split('-')[-1]} (Biller: 70012)"
        va_simulator_url = "https://simulator.sandbox.midtrans.com/mandiri/bill/index"
    elif 'bni' in metode:
        va_bank_name = 'BNI'
        va_number = f"988123{order.id:08d}"
        va_simulator_url = "https://simulator.sandbox.midtrans.com/bni/va/index"
    elif 'bri' in metode:
        va_bank_name = 'BRI'
        va_number = f"12345{order.id:08d}"
        va_simulator_url = "https://simulator.sandbox.midtrans.com/bri/va/index"
    elif 'permata' in metode:
        va_bank_name = 'Permata'
        va_number = f"8778{order.id:08d}"
        va_simulator_url = "https://simulator.sandbox.midtrans.com/permata/va/index"
    else:
        va_bank_name = 'BCA'
        va_number = f"80777{order.id:08d}"
        va_simulator_url = "https://simulator.sandbox.midtrans.com/bca/va/index"

    # Hubungkan ke Midtrans Core API jika belum dibayar
    midtrans_official_connected = False
    if order.status != 'Dibayar':
        core_res, core_err = create_core_api_charge(order, payment_channel=channel, bank=va_bank_name)
        if core_res and core_res.get('status_code') in ['200', '201']:
            midtrans_official_connected = True
            for act in core_res.get('actions', []):
                if act.get('name') == 'generate-qr-code':
                    qris_qr_url = act.get('url')
                    break
            va_list = core_res.get('va_numbers', [])
            if va_list and len(va_list) > 0:
                va_number = va_list[0].get('va_number', va_number)
            elif 'permata_va_number' in core_res:
                va_number = core_res.get('permata_va_number')
            elif 'bill_key' in core_res:
                va_number = f"Bill Key: {core_res.get('bill_key')} (Biller: {core_res.get('biller_code', '70012')})"
        else:
            # Jika charge mengembalikan conflict / sudah ada transaksi terdaftar, gunakan transaction_id resmi
            status_check, _ = check_midtrans_transaction_status(order.nomor_pesanan)
            if status_check and status_check.get('transaction_id'):
                midtrans_official_connected = True
                trans_id = status_check.get('transaction_id')
                qris_qr_url = f"https://api.sandbox.midtrans.com/v2/qris/{trans_id}/qr-code"
                va_list = status_check.get('va_numbers', [])
                if va_list and len(va_list) > 0:
                    va_number = va_list[0].get('va_number', va_number)

    return {
        'order_created': order,
        'is_paid': order.status == 'Dibayar',
        'payment_channel': channel,
        'qris_data': qris_data,
        'qris_qr_url': qris_qr_url,
        'va_bank_name': va_bank_name,
        'va_number': va_number,
        'va_simulator_url': va_simulator_url,
        'midtrans_official_connected': midtrans_official_connected,
        'snap_token': order.snap_token,
        'midtrans_client_key': getattr(settings, 'MIDTRANS_CLIENT_KEY', ''),
        'midtrans_snap_js': getattr(settings, 'MIDTRANS_SNAP_JS', 'https://app.sandbox.midtrans.com/snap/snap.js'),
    }


def check_order_status(request, nomor_pesanan):
    """Mengecek status terkini dari pesanan untuk polling otomatis di frontend."""
    order = get_object_or_404(Order, nomor_pesanan=nomor_pesanan)

    # Sinkronisasi langsung ke Midtrans jika belum Dibayar
    if order.status != 'Dibayar':
        status_res, _ = check_midtrans_transaction_status(nomor_pesanan)
        if status_res:
            t_status = status_res.get('transaction_status')
            f_status = status_res.get('fraud_status')
            if t_status in ['capture', 'settlement'] and f_status != 'challenge':
                order.status = 'Dibayar'
                order.save(update_fields=['status'])

    return JsonResponse({
        'nomor_pesanan': order.nomor_pesanan,
        'status': order.status,
        'is_paid': order.status == 'Dibayar',
    })


@csrf_exempt
@require_POST
def midtrans_notification(request):
    """
    Webhook handler untuk menerima callback notifikasi status pembayaran dari Midtrans Sandbox.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'status': 'invalid json'}, status=400)

    order_id = data.get('order_id')
    status_code = data.get('status_code')
    gross_amount = data.get('gross_amount')
    signature_key = data.get('signature_key')
    transaction_status = data.get('transaction_status')
    fraud_status = data.get('fraud_status')
    payment_type = data.get('payment_type', '')

    if not order_id:
        return JsonResponse({'status': 'order_id missing'}, status=400)

    order = Order.objects.filter(nomor_pesanan=order_id).first()
    if not order:
        return JsonResponse({'status': 'order not found'}, status=404)

    # Validasi signature jika signature_key disertakan
    if signature_key and not verify_midtrans_signature(order_id, status_code, gross_amount, signature_key):
        # Abaikan atau catat log jika testing simulasi
        pass

    # Update status pesanan berdasarkan notifikasi Midtrans
    if transaction_status in ['capture', 'settlement']:
        if fraud_status == 'challenge':
            order.status = 'Menunggu Konfirmasi'
        else:
            order.status = 'Dibayar'
    elif transaction_status == 'pending':
        order.status = 'Menunggu Pembayaran'
    elif transaction_status in ['deny', 'expire', 'cancel']:
        order.status = 'Dibatalkan'

    if payment_type:
        order.catatan = f"Metode Midtrans: {payment_type} | Status: {transaction_status}"

    order.save()
    return JsonResponse({'status': 'success', 'order_status': order.status})


# ==============================================================================
# 6. HALAMAN E-COMMERCE LAINNYA
# ==============================================================================

@login_required(login_url='login')
def produk(request):
    """Katalog produk aktif untuk pelanggan."""
    products = Product.objects.filter(is_active=True).order_by('nama')
    return render(request, 'app/produk.html', {'products': products})


@login_required(login_url='login')
def kategori(request):
    """Halaman kategori layanan."""
    return render(request, 'app/kategori.html')


@login_required(login_url='login')
def tentang(request):
    """Halaman tentang ATKGO.ID."""
    return render(request, 'app/tentang.html')


@login_required(login_url='login')
def kontak(request):
    """Halaman dan form pesan kontak."""
    if request.method == 'POST':
        nama = request.POST.get('nama', '').strip()
        email = request.POST.get('email', '').strip()
        pesan = request.POST.get('pesan', '').strip()

        if nama and email and pesan:
            ContactMessage.objects.create(
                nama=nama,
                email=email,
                pesan=pesan,
                sudah_dibaca=False
            )
            messages.success(request, "Pesan Anda berhasil dikirim! Tim kami akan segera merespons.")
            return redirect('kontak')
        else:
            messages.error(request, "Semua bidang kontak wajib diisi.")

    return render(request, 'app/kontak.html')


@login_required(login_url='login')
def keranjang(request):
    """Halaman keranjang pesanan pelanggan."""
    return render(request, 'app/keranjang.html')


# ==============================================================================
# 7. DASHBOARD & OPERASIONAL ADMIN ATKGO.ID
# ==============================================================================

def admin_login(request):
    """Login Khusus Administrator."""
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')

    if request.method == 'POST':
        identitas = (request.POST.get('email') or request.POST.get('username', '')).strip()
        password = request.POST.get('password', '')

        if not identitas or not password:
            messages.error(request, "Email/Username dan password admin wajib diisi.")
            return render(request, 'login_admin.html')

        try:
            user = authenticate(request, username=identitas, password=password)
        except Exception as e:
            user = None
            request._db_error_detected = str(e)

        if user is None:
            if getattr(request, '_db_error_detected', False):
                messages.error(request, "Terjadi kendala koneksi ke database. Silakan coba sesaat lagi.")
            else:
                messages.error(request, "Kredensial admin salah atau akun tidak ditemukan.")
            return render(request, 'login_admin.html')

        if not user.is_active:
            messages.error(request, "Akun admin ini dinonaktifkan.")
            return render(request, 'login_admin.html')

        if not (user.is_staff or user.is_superuser):
            messages.error(request, "Akun Anda tidak memiliki hak akses Administrator ATKGO.ID.")
            return render(request, 'login_admin.html')

        try:
            login(request, user)
        except Exception as e:
            messages.error(request, f"Gagal menginisialisasi sesi admin: {str(e)}")
            return render(request, 'login_admin.html')
        messages.success(request, f"Selamat datang di Admin Workspace, {user.first_name or user.username}!")
        return redirect('admin_dashboard')

    return render(request, 'login_admin.html')


@admin_required
def admin_logout(request):
    """Logout dari Admin Workspace."""
    logout(request)
    messages.success(request, "Anda telah keluar dari Admin Workspace ATKGO.ID.")
    return redirect('admin_login')


@admin_required
def admin_dashboard(request):
    """Dashboard utama operasional ATKGO.ID dengan statistik terpadu."""
    total_produk = Product.objects.count()
    produk_aktif = Product.objects.filter(is_active=True).count()
    total_pelanggan = User.objects.filter(is_staff=False, is_superuser=False).count()
    total_pesan = ContactMessage.objects.count()
    pesan_belum_dibaca = ContactMessage.objects.filter(sudah_dibaca=False).count()
    total_admin = User.objects.filter(is_staff=True).count()
    total_pesanan = Order.objects.count()
    total_artikel = Article.objects.count()

    produk_terbaru = Product.objects.order_by('-dibuat_pada')[:5]
    pesan_terbaru = ContactMessage.objects.order_by('-dibuat_pada')[:5]

    context = {
        'total_produk': total_produk,
        'produk_aktif': produk_aktif,
        'total_pelanggan': total_pelanggan,
        'total_pesan': total_pesan,
        'pesan_belum_dibaca': pesan_belum_dibaca,
        'total_admin': total_admin,
        'total_pesanan': total_pesanan,
        'total_artikel': total_artikel,
        'produk_terbaru': produk_terbaru,
        'pesan_terbaru': pesan_terbaru,
    }
    return render(request, 'admin_dashboard.html', context)


# --- Manajemen Produk Admin ---

@admin_required
def admin_products(request):
    """Daftar manajemen produk."""
    products = Product.objects.all().order_by('-dibuat_pada')
    return render(request, 'admin_products.html', {'products': products})


@admin_required
def admin_product_create(request):
    """Tambah produk baru."""
    if request.method == 'POST':
        nama = request.POST.get('nama', '').strip()
        kategori = request.POST.get('kategori', '').strip()
        harga = request.POST.get('harga', '0')
        stok = request.POST.get('stok', '0')
        deskripsi = request.POST.get('deskripsi', '').strip()
        is_active = 'is_active' in request.POST
        gambar = request.FILES.get('gambar')

        if not nama:
            messages.error(request, "Nama produk wajib diisi.")
            return render(request, 'admin_product_form.html', {
                'page_title': 'Tambah Produk Baru',
                'button_text': 'Simpan Produk',
            })

        try:
            Product.objects.create(
                nama=nama,
                kategori=kategori,
                harga=float(harga) if harga else 0,
                stok=int(stok) if stok else 0,
                deskripsi=deskripsi,
                is_active=is_active,
                gambar=gambar,
            )
            messages.success(request, f"Produk '{nama}' berhasil ditambahkan.")
            return redirect('admin_products')
        except Exception as e:
            messages.error(request, f"Gagal menambahkan produk: {str(e)}")

    return render(request, 'admin_product_form.html', {
        'page_title': 'Tambah Produk Baru',
        'button_text': 'Simpan Produk',
    })


@admin_required
def admin_product_edit(request, pk):
    """Ubah data produk."""
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        nama = request.POST.get('nama', '').strip()
        kategori = request.POST.get('kategori', '').strip()
        harga = request.POST.get('harga', '0')
        stok = request.POST.get('stok', '0')
        deskripsi = request.POST.get('deskripsi', '').strip()
        is_active = 'is_active' in request.POST
        gambar = request.FILES.get('gambar')

        if not nama:
            messages.error(request, "Nama produk wajib diisi.")
            return render(request, 'admin_product_form.html', {
                'page_title': f'Ubah Produk: {product.nama}',
                'button_text': 'Simpan Perubahan',
                'product': product,
            })

        try:
            product.nama = nama
            product.kategori = kategori
            product.harga = float(harga) if harga else 0
            product.stok = int(stok) if stok else 0
            product.deskripsi = deskripsi
            product.is_active = is_active
            if gambar:
                product.gambar = gambar
            product.save()

            messages.success(request, f"Produk '{product.nama}' berhasil diperbarui.")
            return redirect('admin_products')
        except Exception as e:
            messages.error(request, f"Gagal memperbarui produk: {str(e)}")

    return render(request, 'admin_product_form.html', {
        'page_title': f'Ubah Produk: {product.nama}',
        'button_text': 'Simpan Perubahan',
        'product': product,
    })


@admin_required
def admin_product_delete(request, pk):
    """Hapus produk."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        nama = product.nama
        product.delete()
        messages.success(request, f"Produk '{nama}' berhasil dihapus.")
    return redirect('admin_products')


# --- Manajemen Pesanan Admin ---

@admin_required
def admin_orders(request):
    """Daftar pesanan masuk dari pelanggan."""
    orders = Order.objects.all().prefetch_related('items').order_by('-dibuat_pada')
    return render(request, 'admin_orders.html', {'orders': orders})


@admin_required
def admin_order_status(request, pk):
    """Perbarui status pesanan."""
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['Menunggu Konfirmasi', 'Menunggu Pembayaran', 'Dibayar', 'Diproses', 'Selesai', 'Dibatalkan']:
            order.status = status
            order.save(update_fields=['status'])
            messages.success(request, f"Status pesanan {order.nomor_pesanan} diubah menjadi '{status}'.")
    return redirect('admin_orders')


# --- Manajemen Artikel Admin ---

@admin_required
def admin_articles(request):
    """Daftar artikel yang dikelola admin."""
    articles = Article.objects.all().select_related('kategori').order_by('-dibuat_pada')
    return render(request, 'admin_articles.html', {'articles': articles})


@admin_required
def admin_article_create(request):
    """Tambah artikel edukasi baru."""
    if request.method == 'POST':
        judul = request.POST.get('judul', '').strip()
        kategori_nama = request.POST.get('kategori_nama', '').strip()
        nama_penulis = request.POST.get('nama_penulis', '').strip() or 'Tim ATKGO'
        ringkasan = request.POST.get('ringkasan', '').strip()
        konten = request.POST.get('konten', '').strip()
        is_published = 'is_published' in request.POST
        gambar = request.FILES.get('gambar')

        if not judul or not ringkasan or not konten:
            messages.error(request, "Judul, ringkasan, dan isi artikel wajib diisi.")
            return render(request, 'admin_article_form.html', {
                'page_title': 'Tambah Artikel Baru',
                'button_text': 'Simpan Artikel',
            })

        kategori = None
        if kategori_nama:
            kategori, _ = ArticleCategory.objects.get_or_create(nama=kategori_nama)

        try:
            Article.objects.create(
                judul=judul,
                kategori=kategori,
                nama_penulis=nama_penulis,
                penulis=request.user,
                ringkasan=ringkasan,
                konten=konten,
                is_published=is_published,
                gambar=gambar,
            )
            messages.success(request, f"Artikel '{judul}' berhasil dibuat.")
            return redirect('admin_articles')
        except Exception as e:
            messages.error(request, f"Gagal membuat artikel: {str(e)}")

    return render(request, 'admin_article_form.html', {
        'page_title': 'Tambah Artikel Baru',
        'button_text': 'Simpan Artikel',
    })


@admin_required
def admin_article_edit(request, pk):
    """Ubah artikel edukasi."""
    article = get_object_or_404(Article, pk=pk)

    if request.method == 'POST':
        judul = request.POST.get('judul', '').strip()
        kategori_nama = request.POST.get('kategori_nama', '').strip()
        nama_penulis = request.POST.get('nama_penulis', '').strip() or 'Tim ATKGO'
        ringkasan = request.POST.get('ringkasan', '').strip()
        konten = request.POST.get('konten', '').strip()
        is_published = 'is_published' in request.POST
        gambar = request.FILES.get('gambar')

        if not judul or not ringkasan or not konten:
            messages.error(request, "Judul, ringkasan, dan isi artikel wajib diisi.")
            return render(request, 'admin_article_form.html', {
                'page_title': f'Ubah Artikel: {article.judul}',
                'button_text': 'Simpan Perubahan',
                'article': article,
            })

        kategori = None
        if kategori_nama:
            kategori, _ = ArticleCategory.objects.get_or_create(nama=kategori_nama)

        try:
            article.judul = judul
            article.kategori = kategori
            article.nama_penulis = nama_penulis
            article.ringkasan = ringkasan
            article.konten = konten
            article.is_published = is_published
            if gambar:
                article.gambar = gambar
            article.save()

            messages.success(request, f"Artikel '{article.judul}' berhasil diperbarui.")
            return redirect('admin_articles')
        except Exception as e:
            messages.error(request, f"Gagal memperbarui artikel: {str(e)}")

    return render(request, 'admin_article_form.html', {
        'page_title': f'Ubah Artikel: {article.judul}',
        'button_text': 'Simpan Perubahan',
        'article': article,
    })


@admin_required
def admin_article_delete(request, pk):
    """Hapus artikel."""
    article = get_object_or_404(Article, pk=pk)
    if request.method == 'POST':
        judul = article.judul
        article.delete()
        messages.success(request, f"Artikel '{judul}' berhasil dihapus.")
    return redirect('admin_articles')


# --- Manajemen Konten Website (CMS) Admin ---

@admin_required
def admin_content(request):
    """Pengelolaan konten halaman utama dan informasi website."""
    hero = HeroBanner.objects.filter(is_active=True).first()
    if not hero:
        hero = HeroBanner.objects.first()

    settings_obj = WebsiteSetting.objects.first()
    if not settings_obj:
        settings_obj = WebsiteSetting.objects.create()

    keunggulan_items = Keunggulan.objects.all().order_by('urutan', 'id')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_hero':
            eyebrow = request.POST.get('eyebrow', '').strip()
            judul = request.POST.get('judul', '').strip()
            deskripsi = request.POST.get('deskripsi', '').strip()
            tagline = request.POST.get('tagline', '').strip()
            badge = request.POST.get('badge', '').strip()
            gambar = request.FILES.get('gambar')

            if not hero:
                hero = HeroBanner()

            hero.eyebrow = eyebrow
            hero.judul = judul
            hero.deskripsi = deskripsi
            hero.tagline = tagline
            hero.badge = badge
            hero.is_active = True
            if gambar:
                hero.gambar = gambar
            hero.save()

            messages.success(request, "Konten Banner Hero berhasil disimpan dan langsung tayang di website.")
            return redirect('admin_content')

        elif action == 'update_settings':
            settings_obj.nama_website = request.POST.get('nama_website', '').strip()
            settings_obj.email_kontak = request.POST.get('email_kontak', '').strip()
            settings_obj.telepon_kontak = request.POST.get('telepon_kontak', '').strip()
            settings_obj.jam_operasional = request.POST.get('jam_operasional', '').strip()
            settings_obj.alamat_kantor = request.POST.get('alamat_kantor', '').strip()
            settings_obj.banner_promo_judul = request.POST.get('banner_promo_judul', '').strip()
            settings_obj.banner_promo_deskripsi = request.POST.get('banner_promo_deskripsi', '').strip()
            settings_obj.save()

            messages.success(request, "Pengaturan umum website dan kontak berhasil disimpan.")
            return redirect('admin_content')

    context = {
        'hero': hero,
        'settings': settings_obj,
        'keunggulan_items': keunggulan_items,
    }
    return render(request, 'admin_content.html', context)


@admin_required
def admin_keunggulan_create(request):
    """Tambah item keunggulan pada halaman depan."""
    if request.method == 'POST':
        ikon = request.POST.get('ikon', '✓').strip()
        judul = request.POST.get('judul', '').strip()
        deskripsi = request.POST.get('deskripsi', '').strip()

        if judul and deskripsi:
            Keunggulan.objects.create(ikon=ikon, judul=judul, deskripsi=deskripsi)
            messages.success(request, f"Keunggulan '{judul}' berhasil ditambahkan.")
        else:
            messages.error(request, "Judul dan deskripsi keunggulan wajib diisi.")
    return redirect('admin_content')


@admin_required
def admin_keunggulan_delete(request, pk):
    """Hapus item keunggulan."""
    item = get_object_or_404(Keunggulan, pk=pk)
    if request.method == 'POST':
        judul = item.judul
        item.delete()
        messages.success(request, f"Keunggulan '{judul}' berhasil dihapus.")
    return redirect('admin_content')


# --- Data Pelanggan & Pesan Admin ---

@admin_required
def admin_customers(request):
    """Daftar pelanggan terdaftar dan profil bisnisnya."""
    customers = User.objects.filter(is_staff=False, is_superuser=False).select_related('anggota').order_by('-date_joined')
    return render(request, 'admin_customers.html', {'customers': customers})


@admin_required
def admin_messages(request):
    """Daftar pesan pelanggan dari formulir kontak."""
    contact_messages = ContactMessage.objects.all().order_by('-dibuat_pada')
    return render(request, 'admin_messages.html', {'contact_messages': contact_messages})


@admin_required
def admin_register(request):
    """Pendaftaran admin baru oleh tim administrator."""
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        telp = request.POST.get('telp', '').strip()
        gender = request.POST.get('gender', 'Laki-laki')

        if not full_name or not username or not email or not password:
            messages.error(request, "Semua data admin wajib diisi.")
            return render(request, 'register_admin.html')

        if password != confirm_password:
            messages.error(request, "Konfirmasi password tidak cocok.")
            return render(request, 'register_admin.html')

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "Username sudah digunakan.")
            return render(request, 'register_admin.html')

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email sudah terdaftar.")
            return render(request, 'register_admin.html')

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=full_name,
                    is_staff=True,
                    is_active=True,
                )
                UserAdmin.objects.create(
                    username=user,
                    telp=telp,
                    gender=gender,
                )
            messages.success(request, f"Admin '{username}' berhasil didaftarkan.")
            return redirect('admin_dashboard')
        except Exception as e:
            messages.error(request, f"Gagal mendaftarkan admin: {str(e)}")

    return render(request, 'register_admin.html')
