#!/bin/bash
cd /www/wwwroot/squarecloudsmc.com/backend
source /www/server/pyporject_evn/backend_venv/bin/activate
export PYTHONPATH=/www/wwwroot/squarecloudsmc.com/backend
exec uvicorn main:app --host 127.0.0.1 --port 8000
