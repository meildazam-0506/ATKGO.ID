
from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('login/', views.login_page, name='login'),

    # Logout
    path('logout/', views.logout_page, name='logout'),

    # Halaman utama konsumen
    path('beranda/', views.beranda, name='beranda'),

    # Halaman e-commerce
    path('produk/', views.produk, name='produk'),
    path('kategori/', views.kategori, name='kategori'),
    path('tentang/', views.tentang, name='tentang'),
    path('kontak/', views.kontak, name='kontak'),
    path('pembayaran/', views.pembayaran, name='pembayaran'),
]

