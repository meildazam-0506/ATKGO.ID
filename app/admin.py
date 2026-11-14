from django.contrib import admin
from .models import (
    Provinsi, UserPengguna, UserAdmin, Product, ContactMessage,
    HeroBanner, Keunggulan, WebsiteSetting, ArticleCategory, Article,
    Order, OrderItem
)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('nama', 'kategori', 'harga', 'stok', 'is_active', 'dibuat_pada')
    list_filter = ('is_active', 'kategori')
    search_fields = ('nama', 'deskripsi', 'kategori')
    list_editable = ('harga', 'stok', 'is_active')

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('nama', 'email', 'dibuat_pada', 'sudah_dibaca')
    list_filter = ('sudah_dibaca', 'dibuat_pada')
    search_fields = ('nama', 'email', 'pesan')
    list_editable = ('sudah_dibaca',)

@admin.register(HeroBanner)
class HeroBannerAdmin(admin.ModelAdmin):
    list_display = ('judul', 'eyebrow', 'badge', 'is_active', 'dibuat_pada')
    list_editable = ('is_active',)

@admin.register(Keunggulan)
class KeunggulanAdmin(admin.ModelAdmin):
    list_display = ('judul', 'ikon', 'urutan', 'is_active')
    list_editable = ('urutan', 'is_active')

@admin.register(WebsiteSetting)
class WebsiteSettingAdmin(admin.ModelAdmin):
    list_display = ('nama_website', 'email_kontak', 'telepon_kontak')

@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ('nama', 'slug')
    prepopulated_fields = {'slug': ('nama',)}

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('judul', 'kategori', 'nama_penulis', 'is_published', 'dibuat_pada')
    list_filter = ('is_published', 'kategori')
    search_fields = ('judul', 'ringkasan', 'konten')
    prepopulated_fields = {'slug': ('judul',)}
    list_editable = ('is_published',)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('nomor_pesanan', 'nama_pemesan', 'telepon_pemesan', 'total_harga', 'status', 'dibuat_pada')
    list_filter = ('status', 'dibuat_pada')
    search_fields = ('nomor_pesanan', 'nama_pemesan', 'email_pemesan', 'telepon_pemesan')
    list_editable = ('status',)
    inlines = [OrderItemInline]

@admin.register(Provinsi)
class ProvinsiAdmin(admin.ModelAdmin):
    list_display = ('nama_provinsi', 'aktif')
    list_filter = ('aktif',)
    search_fields = ('nama_provinsi',)

@admin.register(UserPengguna)
class UserPenggunaAdmin(admin.ModelAdmin):
    list_display = ('user', 'telp', 'nama_usaha', 'jenis_usaha')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'telp', 'nama_usaha')

@admin.register(UserAdmin)
class UserAdminAdmin(admin.ModelAdmin):
    list_display = ('username', 'telp', 'gender')
    search_fields = ('username__username', 'username__email', 'telp')
