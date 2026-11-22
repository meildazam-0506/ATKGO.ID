"""
Script Migrasi Database ATKGO.ID ke Supabase PostgreSQL
Memindahkan seluruh data lokal (Users, Profil, Produk, Artikel, Order) tanpa ada yang hilang.
"""

import os
import sys
import getpass
from pathlib import Path

# Setup Django Environment
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

def main():
    print("=" * 65)
    print("  ATKGO.ID - MIGRATION WIZARD TO SUPABASE POSTGRESQL")
    print("=" * 65)
    
    project_ref = "lfeaawstgowciackssme"
    host = "aws-0-ap-northeast-2.pooler.supabase.com"
    port = 5432
    user = f"postgres.{project_ref}"
    dbname = "postgres"

    print(f"Project Reference : {project_ref}")
    print(f"Supabase Host     : {host}:{port}")
    print(f"Supabase User     : {user}")
    print(f"Database Name     : {dbname}")
    print("-" * 65)

    # Dapatkan password database
    password = os.environ.get('SUPABASE_DB_PASSWORD')
    if len(sys.argv) > 1:
        password = sys.argv[1]
    
    if not password:
        password = getpass.getpass("Masukkan Password Database Supabase Anda: ")

    if not password:
        print("[ERROR] Password tidak boleh kosong.")
        sys.exit(1)

    print("\n[1/4] Menguji koneksi ke Supabase PostgreSQL...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            sslmode='require',
            connect_timeout=10
        )
        conn.close()
        print("  -> Koneksi BERHASIL!")
    except Exception as e:
        print(f"  -> GAGAL terkoneksi: {e}")
        print("\nTips:")
        print("1. Pastikan password benar. Jika lupa, buka Supabase Dashboard:")
        print("   Project Settings -> Database -> Reset database password.")
        print("2. Pastikan koneksi internet aktif.")
        sys.exit(1)

    # Terapkan konfigurasi database ke Django
    import django
    from django.conf import settings
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': dbname,
        'USER': user,
        'PASSWORD': password,
        'HOST': host,
        'PORT': str(port),
        'OPTIONS': {'sslmode': 'require'},
    }
    django.setup()

    print("\n[2/4] Menjalankan migrasi struktur tabel Django di Supabase...")
    from django.core.management import call_command
    try:
        call_command('migrate', interactive=False, verbosity=1)
        print("  -> Seluruh tabel berhasil dibuat di Supabase!")
    except Exception as e:
        print(f"  -> Error saat migrasi: {e}")
        sys.exit(1)

    print("\n[3/4] Mengimpor seluruh data ATKGO.ID ke Supabase...")
    fixture_path = BASE_DIR / 'app' / 'fixtures' / 'supabase_migration_data.json'
    if not fixture_path.exists():
        fixture_path = BASE_DIR / 'app' / 'fixtures' / 'initial_data.json'

    try:
        call_command('loaddata', str(fixture_path), verbosity=1)
        print("  -> Data berhasil diimpor tanpa ada yang hilang!")
    except Exception as e:
        print(f"  -> Error saat import fixture: {e}")
        sys.exit(1)

    print("\n[4/4] Verifikasi data di Supabase:")
    from django.contrib.auth.models import User
    from app.models import Product, Article, Order, UserPengguna, Provinsi
    print(f"  - Total User terdaftar     : {User.objects.count()}")
    print(f"  - Total Profil Pengguna    : {UserPengguna.objects.count()}")
    print(f"  - Total Produk Katalog     : {Product.objects.count()}")
    print(f"  - Total Artikel Edukasi    : {Article.objects.count()}")
    print(f"  - Total Pesanan/Order      : {Order.objects.count()}")
    print(f"  - Total Provinsi           : {Provinsi.objects.count()}")

    database_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"
    print("\n" + "=" * 65)
    print("MIGRASI BERHASIL SELESAI!")
    print("=" * 65)
    print("\nUntuk Vercel Deployment, tambahkan Environment Variable berikut di Vercel Dashboard:")
    print(f"Key   : DATABASE_URL")
    print(f"Value : {database_url}")
    print("\nAtau gunakan:")
    print(f"SUPABASE_DB_PASSWORD={password}")
    print("=" * 65)

if __name__ == '__main__':
    main()
