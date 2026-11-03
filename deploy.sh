#!/bin/bash
# Pakai:  ./deploy.sh        -> git pull + build + reload
#         ./deploy.sh local  -> build + reload tanpa pull
set -euo pipefail
cd /var/www/squareclouds-studio
if [ "${1:-}" != "local" ]; then
  echo "==> git pull"
  git pull --ff-only origin main
fi
echo "==> backend deps"
backend/venv/bin/pip install -q -r backend/requirements.txt
echo "==> frontend build"
( cd frontend && npm ci --no-audit --no-fund && npm run build )
echo "==> reload pm2"
pm2 reload ecosystem.config.js --update-env
pm2 save
echo "==> health check"
sleep 4
curl -s -o /dev/null -w "api %{http_code}\n" https://api.squarecloudsmc.com/docs
curl -s -o /dev/null -w "web %{http_code}\n" https://squarecloudsmc.com
echo "==> selesai"
