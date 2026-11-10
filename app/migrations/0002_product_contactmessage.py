from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('app', '0001_initial')]
    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama', models.CharField(max_length=150)),
                ('deskripsi', models.TextField(blank=True)),
                ('kategori', models.CharField(blank=True, max_length=100)),
                ('harga', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('stok', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('gambar', models.ImageField(blank=True, null=True, upload_to='produk/')),
                ('dibuat_pada', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Produk', 'verbose_name_plural': 'Produk', 'ordering': ['nama']},
        ),
        migrations.CreateModel(
            name='ContactMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama', models.CharField(max_length=120)),
                ('email', models.EmailField(max_length=254)),
                ('pesan', models.TextField()),
                ('dibuat_pada', models.DateTimeField(auto_now_add=True)),
                ('sudah_dibaca', models.BooleanField(default=False)),
            ],
            options={'verbose_name': 'Pesan Kontak', 'verbose_name_plural': 'Pesan Kontak', 'ordering': ['-dibuat_pada']},
        ),
    ]
