
(function () {
    'use strict';

    const KEY = 'atkgo_cart';

    function cartRead() {
        try {
            return JSON.parse(localStorage.getItem(KEY) || '[]');
        } catch (error) {
            return [];
        }
    }

    function cartCount() {
        const el = document.getElementById('cart-count');

        if (el) {
            el.textContent = cartRead().reduce(
                (total, item) => total + (Number(item.qty) || 0),
                0
            );
        }
    }

    function menuInit() {
        const button = document.getElementById('menuBtn');
        const nav = document.getElementById('mainNav');

        if (!button || !nav) return;

        button.addEventListener('click', function () {
            const opened = nav.classList.toggle('open');
            button.setAttribute('aria-expanded', String(opened));
        });

        nav.addEventListener('click', function (event) {
            if (event.target.closest('a')) {
                nav.classList.remove('open');
                button.setAttribute('aria-expanded', 'false');
            }
        });
    }

    function cartInit() {
        cartCount();

        document.addEventListener('click', function (event) {
            const button = event.target.closest('.add');

            if (!button) return;

            const cart = cartRead();
            const name = button.dataset.name || 'Layanan';
            const price = Number(button.dataset.price) || 0;
            const qty = Math.max(1, Number(button.dataset.qty) || 1);

            const existing = cart.find(item => item.name === name);

            if (existing) {
                existing.qty = (Number(existing.qty) || 0) + qty;
            } else {
                cart.push({
                    name: name,
                    price: price,
                    qty: qty
                });
            }

            try {
                localStorage.setItem(KEY, JSON.stringify(cart));
                cartCount();

                const cartUrl = document.body.dataset.cartUrl;

                if (cartUrl) {
                    window.location.href = cartUrl;
                }
            } catch (error) {
                alert('Layanan gagal ditambahkan. Silakan coba kembali.');
            }
        });
    }

    function filterInit() {
        const search = document.getElementById('searchProducts');
        const filter = document.getElementById('filter');
        const items = document.querySelectorAll('#products .product');

        if (!search || !filter) return;

        function filterProducts() {
            const keyword = search.value.toLowerCase().trim();
            const category = filter.value.toLowerCase().trim();

            items.forEach(function (item) {
                const name = (item.dataset.name || '').toLowerCase();
                const itemCategory = (item.dataset.category || '').toLowerCase();

                const matchesName = name.includes(keyword);
                const matchesCategory =
                    category === 'all' || itemCategory === category;

                item.hidden = !(matchesName && matchesCategory);
            });
        }

        search.addEventListener('input', filterProducts);
        filter.addEventListener('change', filterProducts);
    }

    document.addEventListener('DOMContentLoaded', function () {
        menuInit();
        cartInit();
        filterInit();
    });

})();
