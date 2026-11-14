#!/usr/bin/env bash
# Script build untuk Vercel Deployment ATKGO.ID
python3 -m pip install -r requirements.txt
python3 manage.py collectstatic --noinput --clear
