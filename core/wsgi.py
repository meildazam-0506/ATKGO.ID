"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.
For Vercel deployment, ``app`` is also exposed as an alias.
"""

import os
from pathlib import Path
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_wsgi_application()
app = application

# Inisialisasi otomatis tabel dan akun produksi pada Vercel Serverless
if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
    try:
        from django.db import connection
        from django.core.management import call_command

        tables = connection.introspection.table_names()
        if 'auth_user' not in tables:
            call_command('migrate', interactive=False, verbosity=0)
            fixture_file = Path(__file__).resolve().parent.parent / 'app' / 'fixtures' / 'supabase_migration_data.json'
            if not fixture_file.exists():
                fixture_file = Path(__file__).resolve().parent.parent / 'app' / 'fixtures' / 'initial_data.json'
            if fixture_file.exists():
                try:
                    call_command('loaddata', str(fixture_file), verbosity=0)
                except Exception:
                    pass
    except Exception:
        pass
