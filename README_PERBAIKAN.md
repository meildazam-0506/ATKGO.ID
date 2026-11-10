# ATKGO.ID — Versi perapihan

## Yang diperbaiki
- URL `/` diarahkan ke halaman beranda.
- URL halaman utama, produk, kategori, tentang, kontak, login, logout, dan pembayaran disediakan.
- Konfigurasi Django menggunakan database `atkgo_db` pada MariaDB Docker port `3309`.
- PyMySQL disiapkan sebagai driver MySQL Django.
- Registrasi dan login menggunakan sistem autentikasi bawaan Django; akun tersimpan pada tabel `auth_user`.
- Pesan dari formulir kontak disimpan ke tabel `app_contactmessage`.
- Produk dapat dikelola melalui Django Admin dan disimpan di tabel `app_product`.
- Template login dan katalog produk dilengkapi; JavaScript yang sebelumnya memiliki sintaks rusak diganti dengan versi yang valid.
- File static memakai jalur `assets/...` yang sesuai dengan struktur folder proyek.

## Menjalankan di Windows PowerShell

Buka terminal VS Code pada folder proyek `atkgo2`, lalu jalankan:

```powershell
# Aktifkan virtual environment yang sudah ada
.\venv\Scripts\Activate.ps1

# Pasang dependensi
pip install -r requirements.txt

# Jalankan MariaDB dan phpMyAdmin
docker compose -f core/compose.yaml up -d

# Jalankan migrasi database
python manage.py migrate

# Buat akun admin
python manage.py createsuperuser

# Jalankan website
python manage.py runserver
```

Buka:
- Website: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/
- phpMyAdmin: http://127.0.0.1:8888/

## Login phpMyAdmin
- Server: `db` (jika login melalui phpMyAdmin yang disediakan Compose)
- Username: `root`
- Password: `rootpassword`
- Database: `atkgo_db`

Django dari Windows memakai host `127.0.0.1` dan port `3309`. Jangan mengubah port tersebut kecuali port mapping Docker juga diubah.

## Menambahkan produk
1. Masuk ke `/admin/` dengan akun superuser.
2. Buka bagian **Produk** lalu pilih **Add**.
3. Isi nama, deskripsi, kategori, harga, stok, lalu simpan.
4. Produk aktif akan tampil di halaman `/produk/`.

## Catatan penting
- Versi ini menggunakan login email + password standar. Pengiriman OTP email belum diaktifkan karena membutuhkan konfigurasi SMTP/email provider.
- Password database `rootpassword` ditujukan untuk pengembangan lokal. Ganti kredensial dan `SECRET_KEY`, serta matikan `DEBUG` sebelum website dipublikasikan.
- Data lama pada volume Docker tidak dihapus oleh perintah `docker compose up -d`. Jika sebelumnya sudah ada database/volume dengan konfigurasi berbeda, periksa isi database sebelum melakukan reset. Jangan menjalankan `docker compose down -v` karena dapat menghapus data database.
- Jalankan `python manage.py migrate` setelah mengganti file proyek.
