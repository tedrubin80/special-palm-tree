#!/usr/bin/env bash
# Deploy MediaSearch to mediasearch.online
# Usage: sudo bash /var/www/media/deploy.sh

set -euo pipefail

echo "=== MediaSearch Deployment ==="

# 1. Nginx config
echo "[1/5] Creating nginx config..."
cat > /etc/nginx/sites-available/mediasearch <<'NGINX'
server {
    listen 80;
    listen [::]:80;
    server_name mediasearch.online www.mediasearch.online;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 1000;

    location ~ /\. { deny all; }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    access_log /var/log/nginx/mediasearch-access.log;
    error_log /var/log/nginx/mediasearch-error.log;
}
NGINX
ln -sf /etc/nginx/sites-available/mediasearch /etc/nginx/sites-enabled/

# 2. Systemd service
echo "[2/5] Installing systemd service..."
cp /var/www/media/mediasearch.service /etc/systemd/system/
systemctl daemon-reload

# 3. Fix permissions so www-data can read the app
echo "[3/5] Setting permissions..."
chown -R www-data:www-data /var/www/media

# 4. Start services
echo "[4/5] Starting gunicorn and reloading nginx..."
nginx -t
systemctl enable --now mediasearch
systemctl reload nginx

# 5. SSL
echo "[5/5] Setting up SSL with Certbot..."
certbot --nginx -d mediasearch.online -d www.mediasearch.online --non-interactive --agree-tos --redirect

echo ""
echo "=== Done! mediasearch.online is live ==="
