#!/usr/bin/env bash
# Prepares the site server before each upload (run over SSH by .github/workflows/site-server.yml):
# installs nginx and rsync if they are missing and adds the PhenoPlant server block once.
# Other nginx sites on the server are left alone.
set -euo pipefail

SITE_DIR="${SITE_DIR:-/var/www/phenoplant}"
SUDO=""
[ "$(id -u)" -eq 0 ] || SUDO="sudo"

missing=()
command -v nginx >/dev/null || missing+=(nginx)
command -v rsync >/dev/null || missing+=(rsync)
if [ ${#missing[@]} -gt 0 ]; then
  if command -v apt-get >/dev/null; then
    $SUDO apt-get update -q
    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -q "${missing[@]}"
  elif command -v dnf >/dev/null; then
    $SUDO dnf install -y -q "${missing[@]}"
  else
    echo "Install ${missing[*]} on the server by hand: no apt-get or dnf found" >&2
    exit 1
  fi
fi

$SUDO mkdir -p "$SITE_DIR"
$SUDO chown "$(id -un)" "$SITE_DIR"  # the upload runs as the SSH user

# Debian/Ubuntu keep sites in sites-available, RHEL-like systems in conf.d
if [ -d /etc/nginx/sites-available ]; then
  CONF=/etc/nginx/sites-available/phenoplant
  LINK=/etc/nginx/sites-enabled/phenoplant
else
  CONF=/etc/nginx/conf.d/phenoplant.conf
  LINK=""
fi

if [ ! -f "$CONF" ]; then
  $SUDO tee "$CONF" >/dev/null <<NGINX
# PhenoPlant startup website, uploaded from GitHub by the "Site to server" workflow
server {
    listen 80 default_server;
    server_name _;
    root $SITE_DIR;
    index index.html;
    charset utf-8;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location ~* \.(?:css|js|webp|jpg|png|svg|ico|mp4|webm)\$ {
        expires 1h;
        add_header Cache-Control "public";
    }

    gzip on;
    gzip_types text/css application/javascript image/svg+xml;
}
NGINX
  removed_default=""
  if [ -n "$LINK" ]; then
    $SUDO ln -sf "$CONF" "$LINK"
    # the stock welcome page also claims default_server on port 80
    if [ -L /etc/nginx/sites-enabled/default ]; then
      $SUDO rm /etc/nginx/sites-enabled/default
      removed_default=1
    fi
  fi
  if ! $SUDO nginx -t; then
    # put everything back so a later nginx restart does not fail because of us
    $SUDO rm -f "$CONF" ${LINK:+"$LINK"}
    [ -z "$removed_default" ] || $SUDO ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
    echo "nginx rejected the PhenoPlant server block (another site may already be default_server on port 80)" >&2
    exit 1
  fi
fi

$SUDO systemctl enable --now nginx >/dev/null
$SUDO systemctl reload nginx
