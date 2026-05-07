#!/usr/bin/env bash
# scripts/bootstrap.sh — One-time setup on a fresh Amazon Linux 2023 Lightsail instance.
#
# Usage (after SSHing into the server):
#   curl -fsSL https://raw.githubusercontent.com/siesto-rivera/PrivateMemo-backend/main/scripts/bootstrap.sh -o bootstrap.sh
#   bash bootstrap.sh
#
# This script is idempotent — re-run safely. It will fail with a clear message
# if the .env file is missing; place it via SCP, then re-run.

set -euo pipefail

REPO_URL="https://github.com/siesto-rivera/PrivateMemo-backend.git"
APP_DIR="$HOME/github/memo-app"
SERVICE_NAME="memo-app"

log() { printf '\n==> %s\n' "$*"; }

log "Updating system packages"
sudo dnf update -y

log "Installing Python 3.12, MariaDB headers, build tools, nginx, git, cronie"
sudo dnf install -y \
  python3.12 python3.12-pip python3.12-devel \
  gcc git pkgconf \
  mariadb-connector-c-devel \
  nginx cronie

log "Cloning repo into $APP_DIR (skip if exists)"
mkdir -p "$(dirname "$APP_DIR")"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

if [ ! -f .env ]; then
  cat <<EOF

ERROR: $APP_DIR/.env not found.

From your laptop, copy your prepared .env to the server:
  scp -i ~/nodong1987.pem .env ec2-user@54.116.131.130:$APP_DIR/.env

Then re-run this script.
EOF
  exit 1
fi

log "Creating venv and installing dependencies"
[ -d venv ] || python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

log "Running migrations"
python manage.py migrate --noinput

log "Collecting static files"
python manage.py collectstatic --noinput

log "Installing systemd service ($SERVICE_NAME)"
sudo cp scripts/memo-app.service "/etc/systemd/system/${SERVICE_NAME}.service"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

log "Configuring Nginx"
sudo cp scripts/nginx-memo-app.conf /etc/nginx/conf.d/memo-app.conf
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

log "Allowing nginx to traverse \$HOME so it can serve /static/ files"
# AL2023's /home/ec2-user is mode 700 by default, blocking nginx from entering.
chmod 755 "$HOME"

log "Granting passwordless sudo for systemctl restart (used by GitHub Actions deploys)"
sudo tee /etc/sudoers.d/memo-app >/dev/null <<EOF
ec2-user ALL=(ALL) NOPASSWD: /bin/systemctl restart ${SERVICE_NAME}
ec2-user ALL=(ALL) NOPASSWD: /bin/systemctl status ${SERVICE_NAME}
EOF
sudo chmod 0440 /etc/sudoers.d/memo-app

log "Enabling cron daemon and registering daily cleanup_trash job (04:00 UTC)"
sudo systemctl enable --now crond
CRON_LINE="0 4 * * * cd $APP_DIR && $APP_DIR/venv/bin/python manage.py cleanup_trash >> $HOME/memo-cleanup.log 2>&1"
EXISTING_CRON=$(crontab -l 2>/dev/null || true)
if echo "$EXISTING_CRON" | grep -qF "manage.py cleanup_trash"; then
  echo "    cron already registered — skipping"
else
  printf '%s\n%s\n' "$EXISTING_CRON" "$CRON_LINE" | grep -v "^$" | crontab -
  echo "    cron registered"
fi

log "Done"
echo "    App health: sudo systemctl status $SERVICE_NAME"
echo "    Service URL: http://54.116.131.130/"
echo "    Admin: http://54.116.131.130/admin/  (run 'python manage.py createsuperuser' inside venv to create an admin)"
