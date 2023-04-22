#!/bin/bash

source /home/appuser/venv/bin/activate
export PYTHONPATH=/path/to/geoquery
exec gunicorn --workers 3 --bind unix:/home/appuser/gunicorn_socks/geoquery.sock wsgi:app
