from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from app.models import UserPengguna, UserAdmin, Product, ContactMessage

User = get_user_model()


class AuthenticationAndSecurityTests(TestCase):
    """
    Rangkaian pengujian komprehensif sistem autentikasi, session,
    redirect, dan database ATKGO.ID.
    """

    def setUp(self):
        self.client = Client()

        # Buat akun pelanggan uji
        self.customer = User.objects.create_user(
            username='budi_santoso',
            email='budi@example.com',
            password='Password123#',
            first_name='Budi Santoso',
            is_staff=False,
            is_superuser=False
        )
        self.customer_profile = UserPengguna.objects.create(
            user=self.customer,
            telp='081234567890'
        )

        # Buat akun admin uji
        self.admin_user = User.objects.create_user(
            username='admin_atkgo',
            email='admin@atkgo.id',
            password='AdminPassword123#',
            first_name='Admin Utama',
            is_staff=True,
            is_superuser=False
        )
        self.admin_profile = UserAdmin.objects.create(
            username=self.admin_user,
            telp='089876543210',
            gender='Laki-laki'
        )

    def test_01_customer_registration_success(self):
        """1. Registrasi pelanggan baru berhasil dan membuat profil UserPengguna secara atomik."""
        response = self.client.post(
            reverse('login') + '?mode=register',
            {
                'action': 'register',
                'full_name': 'Siti Rahma',
                'username': 'siti_rahma',
                'email': 'siti@example.com',
                'password': 'SitiPassword123#',
                'confirm_password': 'SitiPassword123#',
                'telp': '081345678901',
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Verifikasi auth_user tersimpan
        new_user = User.objects.filter(username='siti_rahma').first()
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.email, 'siti@example.com')
        self.assertEqual(new_user.first_name, 'Siti Rahma')
        self.assertFalse(new_user.is_staff)

        # Verifikasi password di-hash (bukan teks biasa)
        self.assertNotEqual(new_user.password, 'SitiPassword123#')
        self.assertTrue(new_user.check_password('SitiPassword123#'))

        # Verifikasi app_userpengguna terhubung
        self.assertTrue(hasattr(new_user, 'anggota'))
        self.assertEqual(new_user.anggota.telp, '081345678901')

    def test_02_registration_duplicate_username_rejected(self):
        """2. Registrasi dengan username yang sudah terdaftar ditolak."""
        response = self.client.post(
            reverse('login') + '?mode=register',
            {
                'action': 'register',
                'full_name': 'Budi Duplikat',
                'username': 'budi_santoso',  # Duplikat
                'email': 'budi_baru@example.com',
                'password': 'Password123#',
                'confirm_password': 'Password123#',
            }
        )
        self.assertEqual(response.status_code, 200)
        # Akun baru tidak boleh terbentuk
        self.assertEqual(User.objects.filter(email='budi_baru@example.com').count(), 0)

    def test_03_registration_duplicate_email_rejected(self):
        """3. Registrasi dengan email yang sudah terdaftar ditolak."""
        response = self.client.post(
            reverse('login') + '?mode=register',
            {
                'action': 'register',
                'full_name': 'Email Duplikat',
                'username': 'user_unik_123',
                'email': 'budi@example.com',  # Duplikat email
                'password': 'Password123#',
                'confirm_password': 'Password123#',
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='user_unik_123').count(), 0)

    def test_04_wrong_password_rejected(self):
        """4. Login pelanggan dengan password salah ditolak."""
        response = self.client.post(
            reverse('login') + '?mode=login',
            {
                'action': 'login',
                'username_or_email': 'budi_santoso',
                'password': 'SalahPassword#',
            }
        )
        self.assertEqual(response.status_code, 200)
        # Pastikan session belum terautentikasi
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_05_customer_login_success_with_username_and_email(self):
        """5. Pelanggan dapat login menggunakan username ATAU email."""
        # Login dengan username
        resp_username = self.client.post(
            reverse('login') + '?mode=login',
            {
                'action': 'login',
                'username_or_email': 'budi_santoso',
                'password': 'Password123#',
            }
        )
        self.assertRedirects(resp_username, reverse('beranda'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.customer.pk)

        # Logout
        self.client.logout()

        # Login dengan email
        resp_email = self.client.post(
            reverse('login') + '?mode=login',
            {
                'action': 'login',
                'username_or_email': 'budi@example.com',
                'password': 'Password123#',
            }
        )
        self.assertRedirects(resp_email, reverse('beranda'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.customer.pk)

    def test_06_customer_login_not_redirected_to_django_admin(self):
        """6. Login pelanggan tidak boleh diarahkan ke /admin/ atau Django Administration."""
        response = self.client.post(
            reverse('login') + '?mode=login',
            {
                'action': 'login',
                'username_or_email': 'budi_santoso',
                'password': 'Password123#',
                'next': '/admin/'  # Coba bypass ke admin
            }
        )
        # Harus dicegah dan diarahkan ke beranda
        self.assertRedirects(response, reverse('beranda'))

    def test_07_ordinary_customer_cannot_access_admin_dashboard(self):
        """7. Pelanggan biasa ditolak saat mencoba membuka Admin Workspace (/admin-area/)."""
        self.client.force_login(self.customer)
        response = self.client.get(reverse('admin_dashboard'), follow=True)
        # Harus diarahkan ke beranda dengan pesan peringatan/error
        self.assertRedirects(response, reverse('beranda'))

    def test_08_admin_login_success(self):
        """8. Login admin menggunakan kredensial yang valid berhasil."""
        response = self.client.post(
            reverse('admin_login'),
            {
                'email': 'admin@atkgo.id',
                'password': 'AdminPassword123#',
            }
        )
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.admin_user.pk)

    def test_09_admin_login_redirected_to_atkgo_dashboard(self):
        """9. Login admin diarahkan ke dashboard internal ATKGO.ID, bukan Django Administration."""
        response = self.client.post(
            reverse('admin_login'),
            {
                'email': 'admin_atkgo',
                'password': 'AdminPassword123#',
            }
        )
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertNotIn('/admin/', response.url)

    def test_10_customer_logout_success(self):
        """10. Logout pelanggan berhasil mengakhiri session dan diarahkan ke landing page."""
        self.client.force_login(self.customer)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('landing'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_11_admin_logout_success(self):
        """11. Logout admin berhasil mengakhiri session dan diarahkan ke login admin."""
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('admin_logout'))
        self.assertRedirects(response, reverse('admin_login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_12_unauthenticated_access_blocked(self):
        """12. Pengguna yang belum login tidak dapat membuka halaman yang memerlukan autentikasi."""
        # Akses beranda pelanggan tanpa login -> redirect ke login
        resp_beranda = self.client.get(reverse('beranda'))
        self.assertRedirects(resp_beranda, f"{reverse('login')}?next={reverse('beranda')}")

        # Akses admin area tanpa login -> redirect ke login admin
        resp_admin = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(resp_admin, reverse('admin_login'))

    def test_13_session_persistence(self):
        """13. Session Django tetap berfungsi di beberapa request berturut-turut."""
        self.client.post(
            reverse('login') + '?mode=login',
            {
                'action': 'login',
                'username_or_email': 'budi_santoso',
                'password': 'Password123#',
            }
        )
        # Buka beranda
        r1 = self.client.get(reverse('beranda'))
        self.assertEqual(r1.status_code, 200)

        # Buka produk
        r2 = self.client.get(reverse('produk'))
        self.assertEqual(r2.status_code, 200)

    def test_14_user_data_persisted_in_database(self):
        """14. Data pengguna dan relasi benar-benar tersimpan di database."""
        user = User.objects.get(username='budi_santoso')
        self.assertTrue(user.is_active)
        self.assertEqual(user.first_name, 'Budi Santoso')

        profile = UserPengguna.objects.get(user=user)
        self.assertEqual(profile.telp, '081234567890')
        self.assertEqual(profile.user.pk, user.pk)

    def test_15_ecommerce_pages_render_without_reverse_errors(self):
        """15. Semua halaman e-commerce terender dengan status 200 tanpa NoReverseMatch."""
        self.client.force_login(self.customer)
        urls_to_test = [
            reverse('beranda'),
            reverse('produk'),
            reverse('kategori'),
            reverse('tentang'),
            reverse('kontak'),
            reverse('keranjang'),
            reverse('pembayaran'),
        ]
        for url in urls_to_test:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Gagal merender URL: {url}")

    def test_16_admin_pages_render_for_admin_user(self):
        """16. Semua halaman Admin Workspace terender dengan status 200 untuk akun admin."""
        self.client.force_login(self.admin_user)
        urls_to_test = [
            reverse('admin_dashboard'),
            reverse('admin_products'),
            reverse('admin_product_create'),
            reverse('admin_orders'),
            reverse('admin_articles'),
            reverse('admin_content'),
            reverse('admin_customers'),
            reverse('admin_messages'),
            reverse('admin_register'),
        ]
        for url in urls_to_test:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Gagal merender URL admin: {url}")

    def test_17_profile_update_and_business(self):
        """17. Pembaruan data diri dan profil usaha pelanggan tersimpan di database."""
        self.client.force_login(self.customer)
        # Update tab data diri
        r1 = self.client.post(
            reverse('profil'),
            {
                'section': 'personal',
                'first_name': 'Budi Santoso Updated',
                'email': 'budi@example.com',
                'telp': '081299998888',
                'alamat': 'Jl. Bisnis Merdeka No. 10',
                'kabupaten_kota': 'Jakarta Selatan',
                'provinsi': 'DKI Jakarta',
                'kode_pos': '12345',
            },
            follow=True
        )
        self.assertEqual(r1.status_code, 200)
        self.customer.refresh_from_db()
        self.customer_profile.refresh_from_db()
        self.assertEqual(self.customer.first_name, 'Budi Santoso Updated')
        self.assertEqual(self.customer_profile.telp, '081299998888')

        # Update tab profil usaha
        r2 = self.client.post(
            reverse('profil'),
            {
                'section': 'business',
                'nama_usaha': 'CV ATK Kreatif Mandiri',
                'jenis_usaha': 'Agency & Retail',
                'alamat_usaha': 'Kawasan Industri Bisnis Blok C2',
                'telepon_usaha': '0215556789',
                'catatan_usaha': 'Kebutuhan pengadaan bulanan 100 rim kertas',
            },
            follow=True
        )
        self.assertEqual(r2.status_code, 200)
        self.customer_profile.refresh_from_db()
        self.assertEqual(self.customer_profile.nama_usaha, 'CV ATK Kreatif Mandiri')
        self.assertEqual(self.customer_profile.jenis_usaha, 'Agency & Retail')

    def test_18_profile_change_password(self):
        """18. Pengaturan keamanan / ganti password di profil pengguna."""
        self.client.force_login(self.customer)
        res = self.client.post(
            reverse('profil'),
            {
                'section': 'password',
                'old_password': 'Password123#',
                'new_password': 'NewPassword123#',
                'confirm_new_password': 'NewPassword123#',
            },
            follow=True
        )
        self.assertEqual(res.status_code, 200)
        # Verifikasi password baru bisa digunakan login
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password('NewPassword123#'))

    def test_19_article_listing_and_detail(self):
        """19. Halaman artikel publik menampilkan artikel terpublikasi."""
        from app.models import ArticleCategory, Article
        cat = ArticleCategory.objects.create(nama='Tips Kantor', slug='tips-kantor')
        art = Article.objects.create(
            judul='Panduan Efisiensi ATK Kantor',
            slug='panduan-efisiensi-atk-kantor',
            kategori=cat,
            ringkasan='Cara menghemat pengadaan kantor.',
            konten='Isi lengkap artikel panduan efisiensi ATK kantor.',
            penulis=self.admin_user,
            is_published=True
        )
        # List view
        r_list = self.client.get(reverse('artikel_list'))
        self.assertEqual(r_list.status_code, 200)
        self.assertContains(r_list, 'Panduan Efisiensi ATK Kantor')

        # Detail view
        r_detail = self.client.get(reverse('artikel_detail', kwargs={'slug': art.slug}))
        self.assertEqual(r_detail.status_code, 200)
        self.assertContains(r_detail, 'Panduan Efisiensi ATK Kantor')

    def test_20_order_creation_at_checkout(self):
        """20. Integrasi checkout / pembayaran membuat order di database dan mengisi profil."""
        from app.models import Order, OrderItem
        self.client.force_login(self.customer)
        import json
        cart_items_json = json.dumps([
            {
                'name': 'Kertas A4 80gr',
                'price': 45000,
                'qty': 2,
                'subtotal': 90000
            }
        ])
        res = self.client.post(
            reverse('pembayaran'),
            {
                'nama': 'Budi Santoso',
                'email': 'budi@example.com',
                'telepon': '081234567890',
                'alamat': 'Gedung Wisma Niaga Lt 4',
                'bisnis': 'CV Sukses Mandiri',
                'metode': 'Transfer Bank (BCA / Mandiri / BRI)',
                'cart_data': cart_items_json,
            },
            follow=True
        )
        self.assertEqual(res.status_code, 200)
        order = Order.objects.filter(user=self.customer).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.nama_pemesan, 'Budi Santoso')
        self.assertEqual(order.total_harga, 90000)
        items = OrderItem.objects.filter(order=order)
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().nama_produk, 'Kertas A4 80gr')

    def test_21_convenience_urls_no_404(self):
        """21. URL shortcut dan ekstensi .html tidak menghasilkan error 404."""
        self.client.force_login(self.customer)
        urls = [
            '/produk.html',
            '/kategori.html',
            '/tentang.html',
            '/kontak.html',
            '/pembayaran.html',
            '/profil.html',
            '/artikel.html',
            '/index.html',
            '/landing.html',
        ]
        for u in urls:
            res = self.client.get(u)
            self.assertEqual(res.status_code, 200, f"URL {u} menghasilkan status {res.status_code}")


