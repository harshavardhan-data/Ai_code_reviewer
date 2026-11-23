#!/bin/sh
set -e
python -m app.init_db
exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 1 -b 0.0.0.0:8000