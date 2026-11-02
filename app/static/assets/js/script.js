/* ==========================================================
   ATKGO.ID — JavaScript
   Isi file:
   1. PENGATURAN  → email tujuan, nama penyimpanan keranjang
   2. Menu mobile
   3. Keranjang belanja
   4. Pencarian & filter produk
   5. Formulir kontak
   ========================================================== */

/* ---------- 1. PENGATURAN (edit di sini) ---------- */
const CONFIG = {
  contactEmail: 'hello@atkgo.id',   // ganti dengan email resmi
  cartStorageKey: 'atkgo_cart',
  toastDuration: 1800               // milidetik
};

/* ---------- Fungsi bantu ---------- */
function readCart() {

  try {

    return JSON.parse(

      localStorage.getItem(CONFIG.cartStorageKey) || '[]'

    );

  } catch (error) {

    return [];

  }

}
function saveCart(cart) {

  try {

    localStorage.setItem(

      CONFIG.cartStorageKey,

      JSON.stringify(cart)

    );

  } catch (error) {

    console.error('Keranjang gagal disimpan.', error);

  }

}
/* ---------- 2. Menu mobile ---------- */
function initMobileMenu() {
  const menuBtn = document.getElementById('menuBtn');
  const mainNav = document.getElementById('mainNav');
  if (!menuBtn || !mainNav) return;

  function setOpen(isOpen) {
    mainNav.classList.toggle('open', isOpen);
    menuBtn.setAttribute('aria-expanded', String(isOpen));
    menuBtn.textContent = isOpen ? '✕' : '☰';
  }

  menuBtn.addEventListener('click', function () {
    setOpen(!mainNav.classList.contains('open'));
  });

  // Tutup menu setelah salah satu link diklik
  mainNav.addEventListener('click', function (event) {
    if (event.target.closest('a')) setOpen(false);
  });

  // Tutup menu dengan tombol Esc
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') setOpen(false);
  });

  // Reset saat layar diperbesar kembali ke desktop
  window.addEventListener('resize', function () {
    if (window.innerWidth > 850) setOpen(false);
  });
}

/* ---------- 3. Keranjang ---------- */
function updateCartCount() {

  const counter = document.getElementById('cart-count');

  if (!counter) return;

  const total = readCart().reduce(function (sum, item) {

    return sum + Number(item.qty || 0);

  }, 0);

  counter.textContent = total;

}
}
function showToast(message) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(function () {
    toast.classList.remove('show');
  }, CONFIG.toastDuration);
}

function addToCart(name, price, quantity) {

    const cart = readCart();

    const qty = Math.max(1, Number(quantity) || 1);

    const harga = Number(price) || 0;

    const existing = cart.find(function (item) {

        return item.name === name;

    });

    if (existing) {

        existing.qty = Number(existing.qty || 0) + qty;

    } else {

        cart.push({

            name: name,

            price: harga,

            qty: qty

        });

    }

    saveCart(cart);

    updateCartCount();

    showToast(name + ' berhasil ditambahkan!');

}

  const cart = readCart();

  const qty = Math.max(1, Number(quantity) || 1);

  const harga = Number(price);

  const existing = cart.find(function (item) {

    return item.name === name;

  });

  if (existing) {

    existing.qty = (Number(existing.qty) || 0) + qty;

    existing.price = harga;

  } else {

    cart.push({

      name: name,

      price: harga,

      qty: qty

    });

  }

  saveCart(cart);

  updateCartCount();

  showToast(name + ' berhasil ditambahkan!');

}

function initCart() {

    updateCartCount();

    document.addEventListener('click', function (event) {

        const button = event.target.closest('.add');

        if (!button) return;

        addToCart(

            button.dataset.name,

            button.dataset.price,

            button.dataset.qty

        );

    });
    const cart = readCart();

    const existing = cart.find(function (item) {

      return item.name === name;

    });

    if (existing) {

      existing.qty += quantity;

    } else {

      cart.push({

        name: name,

        price: price,

        qty: quantity

      });

    }

    saveCart(cart);

    updateCartCount();

    showToast(name + ' berhasil ditambahkan!');

  });

}

/* ---------- 4. Pencarian & filter produk ---------- */
function initProductFilter() {
  const search = document.getElementById('searchProducts');
  const filter = document.getElementById('filter');
  const products = document.querySelectorAll('#products .product');
  if (!search || !filter) return;

  function applyFilter() {
    const query = search.value.trim().toLowerCase();
    const category = filter.value;

    products.forEach(function (product) {
      // Pencarian mengecek nama produk dan kategorinya
      const searchable = (product.dataset.name + ' ' + product.dataset.category).toLowerCase();
      const nameMatch = searchable.includes(query);
      const categoryMatch = category === 'all' || product.dataset.category === category;
      const show = nameMatch && categoryMatch;
      product.hidden = !show;
    });
  }

  search.addEventListener('input', applyFilter);
  filter.addEventListener('change', applyFilter);
}

/* ---------- 5. Formulir kontak ---------- */
function initContactForm() {
  const form = document.getElementById('contactForm');
  if (!form) return;

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    const body =
      'Nama: ' + document.getElementById('nama').value + '\n' +
      'Email: ' + document.getElementById('email').value + '\n' +
      'Keperluan: ' + document.getElementById('keperluan').value + '\n' +
      'Pesan: ' + document.getElementById('pesan').value;

    window.location.href =
      'mailto:' + CONFIG.contactEmail +
      '?subject=' + encodeURIComponent('Pesan dari website ATKGO.ID') +
      '&body=' + encodeURIComponent(body);
  });
}

/* ---------- Jalankan semua ---------- */
document.addEventListener('DOMContentLoaded', function () {
  initMobileMenu();
  initCart();
  initProductFilter();
  initContactForm();
});

function formatRupiah(angka) {

  return new Intl.NumberFormat('id-ID', {

    style: 'currency',

    currency: 'IDR',

    maximumFractionDigits: 0

  }).format(Number(angka) || 0);

}
function tampilkanRingkasanPesanan() {

    const daftar = document.getElementById('daftar-layanan');

    const totalElement = document.getElementById('total-harga');

    if (!daftar || !totalElement) return;

    const keranjang = readCart();

    let total = 0;

    if (!keranjang.length) {

        daftar.textContent = 'Belum ada layanan yang dipilih.';

        totalElement.textContent = 'Rp0';

        return;

    }

    daftar.innerHTML = '';

    keranjang.forEach(function(item) {

        const nama = item.name || item.nama || 'Layanan';

        const harga = Number(item.price ?? item.harga ?? 0);

        const jumlah = Number(item.qty ?? item.quantity ?? item.jumlah ?? 1);

        const subtotal = harga * jumlah;

        total += subtotal;

        const baris = document.createElement('div');

        baris.className = 'order-item';

        const namaElement = document.createElement('span');

        namaElement.textContent = nama + ' × ' + jumlah;

        const hargaElement = document.createElement('span');

        hargaElement.textContent = formatRupiah(subtotal);

        baris.appendChild(namaElement);

        baris.appendChild(hargaElement);

        daftar.appendChild(baris);

    });

    totalElement.textContent = formatRupiah(total);

}

function buatNomorPesanan() {

  const waktu = new Date();

  const tanggal = waktu.getFullYear().toString() +

    String(waktu.getMonth() + 1).padStart(2, '0') +

    String(waktu.getDate()).padStart(2, '0');

  const acak = Math.random().toString(36).slice(2, 8).toUpperCase();

  return 'ATK-' + tanggal + '-' + acak;

}

document.addEventListener('DOMContentLoaded', function () {

  tampilkanRingkasanPesanan();

  const form = document.getElementById('form-pembayaran');

  if (!form) return;

  form.addEventListener('submit', function (event) {

    event.preventDefault();

    const layanan = readCart();

    if (layanan.length === 0) {

      alert('Silakan pilih layanan terlebih dahulu.');

      return;

    }

    const namaInput = document.getElementById('nama');

    const emailInput = document.getElementById('email');

    const teleponInput = document.getElementById('telepon');

    const metodeInput = document.getElementById('metode');

    if (!namaInput || !emailInput || !metodeInput) {

      alert('Pastikan kolom nama, email, dan metode pembayaran tersedia.');

      return;

    }

    const nama = namaInput.value.trim();

    const email = emailInput.value.trim();

    const telepon = teleponInput ? teleponInput.value.trim() : '';

    const metode = metodeInput.value;

    if (!nama || !email || !metode) {

      alert('Mohon lengkapi informasi pesanan.');

      return;

    }

    const daftarLayanan = layanan.map(function (item) {

    const namaLayanan = item.name || item.nama || 'Layanan';

    const harga = Number(item.price || item.harga) || 0;

    const jumlah = Number(item.qty || item.quantity || item.jumlah) || 1;

    return - ${namaLayanan} (${jumlah}): ${formatRupiah(harga * jumlah)};

}).join('\n');

        name: namaLayanan,

        price: harga,

        qty: jumlah

    };

});

    const total = rincian.reduce(function (sum, item) {

      return sum + item.price * item.qty;

    }, 0);

    const pesanan = {

      nomor: buatNomorPesanan(),

      tanggal: new Date().toLocaleString('id-ID'),

      nama: nama,

      email: email,

      telepon: telepon,

      metode: metode,

      layanan: rincian,

      total: total,

      status: 'Menunggu pembayaran'

    };

    try {

      localStorage.setItem(

        'atkgo_pesanan_terakhir',

        JSON.stringify(pesanan)

      );

      window.location.href = 'bukti-pesanan.html';

    } catch (error) {

      alert('Pesanan tidak dapat disimpan. Periksa penyimpanan browser.');

    }

  });
