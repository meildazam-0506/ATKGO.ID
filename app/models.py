from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone
from django.utils.text import slugify
import os
from django.conf import settings

User.add_to_class("__str__", lambda self: f"{self.username} - {self.first_name}")

class Provinsi(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nama_provinsi = models.CharField(max_length=100, unique=True, verbose_name='Nama Provinsi')
    aktif = models.BooleanField(default=True, verbose_name='Aktif')

    class Meta:
        verbose_name = 'Provinsi'
        verbose_name_plural = 'Provinsi'
        ordering = ['nama_provinsi']

    def __str__(self):
        return f"{self.nama_provinsi}"

def rename_photo_anggota(instance, filename):
    ext = filename.split('.')[-1]
    username = instance.user.username
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    new_filename = f"{username}_{timestamp}.{ext}"
    return os.path.join('img_profile/anggota/', new_filename)

class UserPengguna(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)    
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name="anggota")
    telp = models.CharField(max_length=15)
    gender = models.CharField(max_length=15, null=True, blank=True, choices=[
        ('Laki-laki', 'Laki-laki'),
        ('Perempuan', 'Perempuan'),
    ]) 
    alamat = models.TextField(null=True, blank=True)
    kabupaten_kota = models.CharField(max_length=100, null=True, blank=True)
    kecamatan = models.CharField(max_length=100, null=True, blank=True)
    kelurahan_desa = models.CharField(max_length=100, null=True, blank=True)
    kode_pos = models.CharField(max_length=10, null=True, blank=True)
    photo = models.ImageField(upload_to=rename_photo_anggota, null=True, blank=True)
    provinsi_anggota = models.ForeignKey(Provinsi, on_delete=models.SET_NULL, null=True, blank=True)
    jafung = models.CharField(max_length=100, null=True, blank=True)
    nuptk = models.CharField(max_length=20, null=True, blank=True, verbose_name='NUPTK')
    bidang_keahlian = models.CharField(max_length=100, null=True, blank=True)
    link_sinta = models.URLField(blank=True)
    link_scopus = models.URLField(blank=True, null=True)
    link_google_scholar = models.URLField(blank=True, null=True)
    link_orcid = models.URLField(blank=True, null=True)

    # Profil Usaha Pelanggan
    nama_usaha = models.CharField(max_length=150, null=True, blank=True, verbose_name='Nama Usaha / Brand')
    jenis_usaha = models.CharField(max_length=100, null=True, blank=True, verbose_name='Jenis Usaha / Bidang')
    alamat_usaha = models.TextField(null=True, blank=True, verbose_name='Alamat Usaha')
    telepon_usaha = models.CharField(max_length=20, null=True, blank=True, verbose_name='Nomor Telepon Usaha')
    catatan_usaha = models.TextField(null=True, blank=True, verbose_name='Catatan / Deskripsi Usaha')

    class Meta:
        verbose_name = 'Anggota'
        verbose_name_plural = 'Anggota'

    def save(self, *args, **kwargs):
        try:
            old_instance = UserPengguna.objects.get(pk=self.pk)
            if old_instance.photo and old_instance.photo != self.photo:
                old_photo_path = os.path.join(
                    settings.MEDIA_ROOT,
                    old_instance.photo.name
                )
                if os.path.isfile(old_photo_path):
                    os.remove(old_photo_path)
        except UserPengguna.DoesNotExist:
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.user.get_full_name() or self.user.email}"

def rename_photo_admin(instance, filename):
    ext = filename.split('.')[-1]
    username = instance.username
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S') 
    new_filename = f"{username}_{timestamp}.{ext}"
    return os.path.join('img_profile/admin/', new_filename)  

class UserAdmin(models.Model):
    username = models.OneToOneField(User, on_delete=models.CASCADE, to_field="username", primary_key=True)
    telp = models.CharField(max_length=15)
    gender = models.CharField(max_length=15, choices=[
        ('Laki-laki', 'Laki-laki'),
        ('Perempuan', 'Perempuan'),
    ])
    photo = models.ImageField(upload_to=rename_photo_admin)

    def save(self, *args, **kwargs):
        try:
            old_instance = UserAdmin.objects.get(pk=self.pk)
            if old_instance.photo and old_instance.photo != self.photo:
                old_photo_path = os.path.join(settings.MEDIA_ROOT, old_instance.photo.name)
                if os.path.isfile(old_photo_path):
                    os.remove(old_photo_path)
        except UserAdmin.DoesNotExist:
            pass  

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username}"


class Product(models.Model):
    nama = models.CharField(max_length=150)
    deskripsi = models.TextField(blank=True)
    kategori = models.CharField(max_length=100, blank=True)
    harga = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stok = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    gambar = models.ImageField(upload_to='produk/', blank=True, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Produk'
        verbose_name_plural = 'Produk'
        ordering = ['nama']

    def __str__(self):
        return self.nama


class ContactMessage(models.Model):
    nama = models.CharField(max_length=120)
    email = models.EmailField(max_length=254)
    pesan = models.TextField()
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    sudah_dibaca = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Pesan Kontak'
        verbose_name_plural = 'Pesan Kontak'
        ordering = ['-dibuat_pada']

    def __str__(self):
        return f"{self.nama} ({self.email})"


# ==============================================================================
# MODEL PENGELOLAAN KONTEN WEBSITE (CMS ADMIN)
# ==============================================================================

class HeroBanner(models.Model):
    """Pengelolaan banner dan teks utama pada halaman depan website."""
    eyebrow = models.CharField(max_length=150, default='Agensi Strategi & Produksi Visual Kreatif')
    judul = models.CharField(max_length=200, default='Lebih cepat, hemat, dan Berdampak.')
    deskripsi = models.TextField(default='ATKGO.ID membantu kebutuhan strategi pemasaran, manajemen media sosial, dan produksi visual Anda dengan proses yang praktis, kreatif, dan profesional.')
    tagline = models.CharField(max_length=200, default='Satu Agensi untuk seluruh solusi kreatif brand anda.')
    badge = models.CharField(max_length=100, default='Kreatif • Strategis • Terpercaya')
    gambar = models.ImageField(upload_to='banners/', blank=True, null=True)
    tombol_teks = models.CharField(max_length=100, default='Lihat Layanan')
    tombol_url = models.CharField(max_length=200, default='/produk/')
    is_active = models.BooleanField(default=True, verbose_name='Aktif Ditampilkan')
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Banner Utama (Hero)'
        verbose_name_plural = 'Banner Utama (Hero)'

    def __str__(self):
        return self.judul


class Keunggulan(models.Model):
    """Keunggulan layanan yang tampil pada halaman depan (Kenapa ATKGO.ID)."""
    ikon = models.CharField(max_length=50, default='✓', help_text='Contoh: ✓, ♡, ↗, ✎, ▣')
    judul = models.CharField(max_length=150)
    deskripsi = models.TextField()
    urutan = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Keunggulan Website'
        verbose_name_plural = 'Keunggulan Website'
        ordering = ['urutan', 'id']

    def __str__(self):
        return self.judul


class WebsiteSetting(models.Model):
    """Pengaturan umum konten website (kontak, footer, jam operasional)."""
    nama_website = models.CharField(max_length=100, default='ATKGO.ID')
    tagline = models.CharField(max_length=255, default='Mitra cerdas pengadaan alat tulis dan perlengkapan kantor.')
    email_kontak = models.EmailField(default='hello@atkgo.id')
    telepon_kontak = models.CharField(max_length=30, default='081234567890')
    alamat_kantor = models.TextField(default='Jakarta, Indonesia')
    jam_operasional = models.CharField(max_length=150, default='Senin - Jumat: 08.00 - 17.00 WIB')
    banner_promo_judul = models.CharField(max_length=200, default='Butuh rekomendasi produk atau layanan?')
    banner_promo_deskripsi = models.TextField(default='Hubungi ATKGO.ID untuk mendiskusikan kebutuhan paket visual dan operasional Anda.')

    class Meta:
        verbose_name = 'Pengaturan Konten Website'
        verbose_name_plural = 'Pengaturan Konten Website'

    def __str__(self):
        return self.nama_website


# ==============================================================================
# MODEL ARTIKEL DAN EDUKASI
# ==============================================================================

class ArticleCategory(models.Model):
    """Kategori artikel edukasi."""
    nama = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name = 'Kategori Artikel'
        verbose_name_plural = 'Kategori Artikel'
        ordering = ['nama']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nama)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nama


class Article(models.Model):
    """Artikel dan konten edukasi seputar layanan ATKGO.ID."""
    judul = models.CharField(max_length=250)
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    kategori = models.ForeignKey(ArticleCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='artikel')
    ringkasan = models.TextField(help_text='Ringkasan singkat yang tampil di daftar artikel.')
    konten = models.TextField(help_text='Isi lengkap artikel.')
    gambar = models.ImageField(upload_to='artikel/', blank=True, null=True)
    penulis = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='artikel_ditulis')
    nama_penulis = models.CharField(max_length=150, default='Tim ATKGO.ID')
    is_published = models.BooleanField(default=True, verbose_name='Dipublikasikan')
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Artikel'
        verbose_name_plural = 'Artikel'
        ordering = ['-dibuat_pada']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.judul) or 'artikel'
            candidate = base_slug
            counter = 1
            while Article.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.judul


# ==============================================================================
# MODEL PESANAN DAN PEMBAYARAN
# ==============================================================================

class Order(models.Model):
    """Pesanan yang dibuat oleh pelanggan."""
    STATUS_CHOICES = [
        ('Menunggu Pembayaran', 'Menunggu Pembayaran'),
        ('Dibayar', 'Dibayar'),
        ('Menunggu Konfirmasi', 'Menunggu Konfirmasi'),
        ('Diproses', 'Diproses'),
        ('Selesai', 'Selesai'),
        ('Dibatalkan', 'Dibatalkan'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pesanan')
    nomor_pesanan = models.CharField(max_length=50, unique=True)
    nama_pemesan = models.CharField(max_length=150)
    email_pemesan = models.EmailField()
    telepon_pemesan = models.CharField(max_length=30)
    nama_bisnis = models.CharField(max_length=150, blank=True, null=True)
    alamat = models.TextField()
    total_harga = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    metode_pembayaran = models.CharField(max_length=100, default='Konsultasi Pembayaran')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Menunggu Konfirmasi')
    snap_token = models.CharField(max_length=255, blank=True, null=True)
    catatan = models.TextField(blank=True, null=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pesanan Pelanggan'
        verbose_name_plural = 'Pesanan Pelanggan'
        ordering = ['-dibuat_pada']

    def __str__(self):
        return f"{self.nomor_pesanan} - {self.nama_pemesan}"


class OrderItem(models.Model):
    """Item detail dari setiap pesanan."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    nama_produk = models.CharField(max_length=150)
    harga = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    jumlah = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Item Pesanan'
        verbose_name_plural = 'Item Pesanan'

    def __str__(self):
        return f"{self.nama_produk} x {self.jumlah}"
