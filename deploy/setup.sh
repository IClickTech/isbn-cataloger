#!/usr/bin/env bash
# One-time setup for a fresh Ubuntu VM. Run as root (sudo) from the project
# root AFTER the repo has already been copied/cloned to /opt/isbn-cataloger.
#
#   sudo bash deploy/setup.sh
set -euo pipefail

APP_DIR=/opt/isbn-cataloger

if [ "$(pwd)" != "$APP_DIR" ]; then
    echo "Run this from $APP_DIR (current dir: $(pwd))" >&2
    exit 1
fi

apt-get update
apt-get install -y python3-venv python3-pip nginx

id -u isbnapp &>/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin isbnapp

python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

mkdir -p "$APP_DIR/data"
chown -R isbnapp:isbnapp "$APP_DIR"

cp "$APP_DIR/deploy/isbn-cataloger.service" /etc/systemd/system/isbn-cataloger.service
systemctl daemon-reload
systemctl enable --now isbn-cataloger

cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/isbn-cataloger
ln -sf /etc/nginx/sites-available/isbn-cataloger /etc/nginx/sites-enabled/isbn-cataloger
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "Done. Check status with: systemctl status isbn-cataloger"
echo "App should now be reachable on http://<server-ip>/"
