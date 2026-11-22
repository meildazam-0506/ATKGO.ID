"""
Modul Integrasi Midtrans Payment Gateway Sandbox untuk ATKGO.ID
Mendukung QRIS, Virtual Account Bank (BCA, Mandiri, BNI, BRI, Permata),
E-Wallet (GoPay, ShopeePay, OVO, DANA), dan Kartu Kredit.
"""

import os
import json
import base64
import hashlib
import logging
import urllib.request
import urllib.error
from django.conf import settings

logger = logging.getLogger(__name__)


def get_midtrans_auth_header():
    """Mengembalikan Authorization header Basic Base64 sesuai spesifikasi Midtrans."""
    server_key = getattr(settings, 'MIDTRANS_SERVER_KEY', '') or os.environ.get('MIDTRANS_SERVER_KEY', '')
    auth_str = f"{server_key}:"
    encoded_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Basic {encoded_auth}',
    }


def create_snap_transaction(order, cart_items=None, payment_channel=None, sub_provider=None):
    """
    Membuat transaksi Snap di Midtrans Sandbox.
    Mengembalikan (snap_token, redirect_url, error_message).
    """
    snap_url = getattr(
        settings,
        'MIDTRANS_SNAP_URL',
        'https://app.sandbox.midtrans.com/snap/v1/transactions'
    )

    # Pastikan nominal integer positif
    gross_amount = int(round(float(order.total_harga)))
    if gross_amount <= 0:
        gross_amount = 10000

    # Rincian Item Pesanan
    items = []
    if cart_items and isinstance(cart_items, list):
        items_total = 0
        for idx, item in enumerate(cart_items):
            item_price = int(round(float(item.get('price', 0))))
            item_qty = max(1, int(item.get('qty', 1)))
            item_name = str(item.get('name', f"Layanan ATKGO #{idx+1}"))[:50]
            items.append({
                'id': str(item.get('id', f"ATK-{idx+1}"))[:50],
                'price': item_price,
                'quantity': item_qty,
                'name': item_name,
            })
            items_total += item_price * item_qty

        # Midtrans mensyaratkan sum(items) == gross_amount
        if items_total != gross_amount:
            items = [{
                'id': f"ORDER-{order.nomor_pesanan}",
                'price': gross_amount,
                'quantity': 1,
                'name': f"Pesanan {order.nomor_pesanan}"[:50],
            }]
    else:
        items = [{
            'id': f"ORDER-{order.nomor_pesanan}",
            'price': gross_amount,
            'quantity': 1,
            'name': f"Pesanan {order.nomor_pesanan}"[:50],
        }]

    # Filter enabled payments sesuai opsi yang dipilih di halaman checkout
    enabled_payments = []
    if payment_channel == 'qris':
        enabled_payments = ['qris', 'gopay', 'shopeepay']
    elif payment_channel == 'ewallet':
        if sub_provider == 'gopay':
            enabled_payments = ['gopay']
        elif sub_provider == 'shopeepay':
            enabled_payments = ['shopeepay']
        else:
            enabled_payments = ['gopay', 'shopeepay', 'qris']
    elif payment_channel == 'bank_transfer':
        if sub_provider == 'bca':
            enabled_payments = ['bca_va']
        elif sub_provider == 'mandiri':
            enabled_payments = ['echannel']
        elif sub_provider == 'bni':
            enabled_payments = ['bni_va']
        elif sub_provider == 'bri':
            enabled_payments = ['bri_va']
        elif sub_provider == 'permata':
            enabled_payments = ['permata_va']
        else:
            enabled_payments = ['bca_va', 'bni_va', 'bri_va', 'permata_va', 'echannel']
    elif payment_channel == 'credit_card':
        enabled_payments = ['credit_card']

    payload = {
        'transaction_details': {
            'order_id': order.nomor_pesanan,
            'gross_amount': gross_amount,
        },
        'customer_details': {
            'first_name': order.nama_pemesan,
            'email': order.email_pemesan,
            'phone': order.telepon_pemesan,
            'billing_address': {
                'first_name': order.nama_pemesan,
                'phone': order.telepon_pemesan,
                'address': order.alamat,
            },
            'shipping_address': {
                'first_name': order.nama_pemesan,
                'phone': order.telepon_pemesan,
                'address': order.alamat,
            },
        },
        'item_details': items,
    }

    if enabled_payments:
        payload['enabled_payments'] = enabled_payments

    headers = get_midtrans_auth_header()

    try:
        data_json = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(snap_url, data=data_json, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as res:
            res_json = json.loads(res.read().decode('utf-8'))
            snap_token = res_json.get('token')
            redirect_url = res_json.get('redirect_url')
            return snap_token, redirect_url, None

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        logger.warning(f"Midtrans Snap API HTTP {e.code}: {body}")
        # Simulasi fallback token sandbox yang aman agar flow pesanan tidak terhenti
        fallback_token = f"SNAP-SANDBOX-{order.nomor_pesanan}"
        return fallback_token, f"https://app.sandbox.midtrans.com/snap/v2/vtweb/{fallback_token}", body

    except Exception as e:
        logger.error(f"Midtrans Snap request exception: {e}")
        fallback_token = f"SNAP-SANDBOX-{order.nomor_pesanan}"
        return fallback_token, None, str(e)


def create_core_api_charge(order, payment_channel='qris', bank='bca'):
    """
    Membuat transaksi langsung via Midtrans Core API (/v2/charge).
    Mengembalikan data transaksi resmi dari Midtrans Sandbox (termasuk official QRIS URL dan VA number).
    """
    charge_url = 'https://api.sandbox.midtrans.com/v2/charge'
    gross_amount = int(round(float(order.total_harga)))
    if gross_amount <= 0:
        gross_amount = 250000

    payload = {
        'transaction_details': {
            'order_id': order.nomor_pesanan,
            'gross_amount': gross_amount,
        },
        'customer_details': {
            'first_name': order.nama_pemesan,
            'email': order.email_pemesan,
            'phone': order.telepon_pemesan,
        }
    }

    if payment_channel == 'qris':
        payload['payment_type'] = 'qris'
        payload['qris'] = {'acquirer': 'gopay'}
    elif payment_channel in ['bank_transfer', 'va']:
        payload['payment_type'] = 'bank_transfer'
        bank_clean = str(bank or 'bca').lower()
        if bank_clean == 'mandiri':
            payload['echannel'] = {
                'bill_info1': 'Pembayaran ATKGO',
                'bill_info2': order.nomor_pesanan
            }
        elif bank_clean == 'permata':
            payload['bank_transfer'] = {'bank': 'permata'}
        elif bank_clean in ['bni', 'bri']:
            payload['bank_transfer'] = {'bank': bank_clean}
        else:
            payload['bank_transfer'] = {'bank': 'bca'}

    headers = get_midtrans_auth_header()

    try:
        data_json = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(charge_url, data=data_json, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as res:
            res_json = json.loads(res.read().decode('utf-8'))
            return res_json, None
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        logger.warning(f"Midtrans Core API HTTP {e.code}: {body}")
        return None, f"HTTP {e.code}: {body}"
    except Exception as e:
        logger.error(f"Midtrans Core API request exception: {e}")
        return None, str(e)


def verify_midtrans_signature(order_id, status_code, gross_amount, signature_key):
    """
    Verifikasi tanda tangan webhook Midtrans:
    SHA512(order_id + status_code + gross_amount + ServerKey)
    """
    server_key = getattr(settings, 'MIDTRANS_SERVER_KEY', '') or os.environ.get('MIDTRANS_SERVER_KEY', '')
    raw = f"{order_id}{status_code}{gross_amount}{server_key}"
    expected = hashlib.sha512(raw.encode('utf-8')).hexdigest()
    return expected.lower() == str(signature_key).lower()
