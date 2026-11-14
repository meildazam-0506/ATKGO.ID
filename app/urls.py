from django.urls import path
from . import views

urlpatterns = [
    # Halaman Publik & Pelanggan
    path('', views.landing, name='landing'),
    path('beranda/', views.beranda, name='beranda'),
    path('home/', views.beranda, name='home'),

    # Autentikasi Pelanggan
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_page, name='logout'),

    # Halaman E-Commerce Pelanggan
    path('produk/', views.produk, name='produk'),
    path('kategori/', views.kategori, name='kategori'),
    path('tentang/', views.tentang, name='tentang'),
    path('kontak/', views.kontak, name='kontak'),
    path('keranjang/', views.keranjang, name='keranjang'),
    path('pembayaran/', views.pembayaran, name='pembayaran'),

    # Halaman Profil Pengguna & Usaha
    path('profil/', views.profil_user, name='profil'),

    # Halaman Artikel & Edukasi
    path('artikel/', views.artikel_list, name='artikel_list'),
    path('artikel/<slug:slug>/', views.artikel_detail, name='artikel_detail'),

    # Autentikasi & Dashboard Admin ATKGO.ID
    path('admin-area/login/', views.admin_login, name='admin_login'),
    path('admin-area/logout/', views.admin_logout, name='admin_logout'),
    path('admin-area/', views.admin_dashboard, name='admin_dashboard'),

    # Manajemen Produk Admin
    path('admin-area/products/', views.admin_products, name='admin_products'),
    path('admin-area/products/create/', views.admin_product_create, name='admin_product_create'),
    path('admin-area/products/<int:pk>/edit/', views.admin_product_edit, name='admin_product_edit'),
    path('admin-area/products/<int:pk>/delete/', views.admin_product_delete, name='admin_product_delete'),

    # Manajemen Pesanan Pelanggan Admin
    path('admin-area/orders/', views.admin_orders, name='admin_orders'),
    path('admin-area/orders/<int:pk>/status/', views.admin_order_status, name='admin_order_status'),

    # Manajemen Artikel & Edukasi Admin
    path('admin-area/articles/', views.admin_articles, name='admin_articles'),
    path('admin-area/articles/create/', views.admin_article_create, name='admin_article_create'),
    path('admin-area/articles/<int:pk>/edit/', views.admin_article_edit, name='admin_article_edit'),
    path('admin-area/articles/<int:pk>/delete/', views.admin_article_delete, name='admin_article_delete'),

    # Manajemen Konten Website (CMS) Admin
    path('admin-area/content/', views.admin_content, name='admin_content'),
    path('admin-area/keunggulan/create/', views.admin_keunggulan_create, name='admin_keunggulan_create'),
    path('admin-area/keunggulan/<int:pk>/delete/', views.admin_keunggulan_delete, name='admin_keunggulan_delete'),

    # Manajemen Data Pelanggan & Pesan Admin
    path('admin-area/customers/', views.admin_customers, name='admin_customers'),
    path('admin-area/messages/', views.admin_messages, name='admin_messages'),

    # Tambah Admin
    path('admin-area/register/', views.admin_register, name='admin_register'),

    # URL Convenience Aliases (mencegah 404 jika diakses dengan .html atau shortcut URL)
    path('dashboard/', views.admin_dashboard),
    path('admin-dashboard/', views.admin_dashboard),
    path('admin_dashboard/', views.admin_dashboard),
    path('admin-area/dashboard/', views.admin_dashboard),

    path('landing.html', views.landing),
    path('index.html', views.beranda),
    path('beranda.html', views.beranda),
    path('home.html', views.beranda),
    path('produk.html', views.produk),
    path('kategori.html', views.kategori),
    path('tentang.html', views.tentang),
    path('kontak.html', views.kontak),
    path('keranjang.html', views.keranjang),
    path('pembayaran.html', views.pembayaran),
    path('profil.html', views.profil_user),
    path('artikel.html', views.artikel_list),
    path('login.html', views.login_page),

    path('admin_dashboard.html', views.admin_dashboard),
    path('admin_products.html', views.admin_products),
    path('admin_orders.html', views.admin_orders),
    path('admin_articles.html', views.admin_articles),
    path('admin_content.html', views.admin_content),
    path('admin_customers.html', views.admin_customers),
    path('admin_messages.html', views.admin_messages),
    path('admin_login.html', views.admin_login),
    path('login_admin.html', views.admin_login),
    path('register_admin.html', views.admin_register),
]
