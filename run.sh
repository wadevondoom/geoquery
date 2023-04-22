#!/bin/bash

source /path/to/venv/bin/activate
export PYTHONPATH=/path/to/geoquery
exec gunicorn --workers 3 --bind unix:/path/to/gunicorn_socks/geoquery.sock wsgi:app
