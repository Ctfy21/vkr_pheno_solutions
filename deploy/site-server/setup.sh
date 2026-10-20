#!/usr/bin/env bash
# Prepares the site server before each upload (run over SSH by .github/workflows/site-server.yml):
# installs nginx, rsync and certbot if they are missing, gets a Let's Encrypt certificate for
# SITE_DOMAIN and writes the PhenoPlant server block. Other nginx sites on the server are left alone.
set -euo pipefail

SITE_DIR="${SITE_DIR:-/var/www/phenoplant}"
SITE_DOMAIN="${SITE_DOMAIN:-}"   # empty: plain HTTP on the server's address
CERT_EMAIL="${CERT_EMAIL:-}"     # Let's Encrypt writes here before a certificate expires
ACME_DIR=/var/www/letsencrypt    # outside SITE_DIR, which rsync --delete keeps equal to site/
SUDO=""
[ "$(id -u)" -eq 0 ] || SUDO="sudo"

missing=()
command -v nginx >/dev/null || missing+=(nginx)
command -v rsync >/dev/null || missing+=(rsync)
[ -z "$SITE_DOMAIN" ] || command -v certbot >/dev/null || missing+=(certbot)
if [ ${#missing[@]} -gt 0 ]; then
  if command -v apt-get >/dev/null; then
    $SUDO apt-get update -q
    # a fresh VM may still be running unattended-upgrades, which holds the dpkg lock for a while
    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -q -o DPkg::Lock::Timeout=300 "${missing[@]}"
  elif command -v dnf >/dev/null; then
    $SUDO dnf install -y -q "${missing[@]}"
  else
    echo "Install ${missing[*]} on the server by hand: no apt-get or dnf found" >&2
    exit 1
  fi
fi

$SUDO mkdir -p "$SITE_DIR" "$ACME_DIR"
$SUDO chown "$(id -un)" "$SITE_DIR"  # the upload runs as the SSH user

# Debian/Ubuntu keep sites in sites-available, RHEL-like systems in conf.d
if [ -d /etc/nginx/sites-available ]; then
  CONF=/etc/nginx/sites-available/phenoplant
  LINK=/etc/nginx/sites-enabled/phenoplant
else
  CONF=/etc/nginx/conf.d/phenoplant.conf
  LINK=""
fi
CERT_DIR="/etc/letsencrypt/live/$SITE_DOMAIN"
V6=""
[ -f /proc/net/if_inet6 ] && V6=1  # listen on IPv6 too, unless the kernel has it switched off

site_body() {
  cat <<NGINX
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
NGINX
}

# Port 80 serves the site until a certificate exists, then redirects to https://SITE_DOMAIN.
# Let's Encrypt checks /.well-known/acme-challenge/ on port 80 in both cases.
render_conf() {
  local https=$1 names=""
  [ -z "$SITE_DOMAIN" ] || names="$SITE_DOMAIN www.$SITE_DOMAIN "
  echo "# PhenoPlant startup website, uploaded from GitHub by the \"Site to server\" workflow"
  echo "server {"
  echo "    listen 80 default_server;"
  [ -z "$V6" ] || echo "    listen [::]:80 default_server;"
  echo "    server_name ${names}_;"
  echo
  echo "    location /.well-known/acme-challenge/ {"
  echo "        root $ACME_DIR;"
  echo "    }"
  if [ "$https" = 1 ]; then
    echo
    echo "    location / {"
    echo "        return 301 https://$SITE_DOMAIN\$request_uri;"
    echo "    }"
  else
    echo
    site_body
  fi
  echo "}"
  [ "$https" = 1 ] || return 0
  cat <<NGINX

server {
    listen 443 ssl http2;
${V6:+    listen [::]:443 ssl http2;
}    server_name $SITE_DOMAIN;
    ssl_certificate $CERT_DIR/fullchain.pem;
    ssl_certificate_key $CERT_DIR/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:PhenoPlant:10m;

$(site_body)
}

# www.$SITE_DOMAIN leads to the main name
server {
    listen 443 ssl http2;
${V6:+    listen [::]:443 ssl http2;
}    server_name www.$SITE_DOMAIN;
    ssl_certificate $CERT_DIR/fullchain.pem;
    ssl_certificate_key $CERT_DIR/privkey.pem;
    return 301 https://$SITE_DOMAIN\$request_uri;
}
NGINX
}

# Writes the server block and reloads nginx; on a config nginx rejects, puts the previous one back
install_conf() {
  local new old removed_default=""
  new=$(render_conf "$1")
  old=$($SUDO cat "$CONF" 2>/dev/null || true)
  [ "$new" != "$old" ] || return 0
  printf '%s\n' "$new" | $SUDO tee "$CONF" >/dev/null
  if [ -n "$LINK" ]; then
    $SUDO ln -sf "$CONF" "$LINK"
    # the stock welcome page also claims default_server on port 80
    if [ -L /etc/nginx/sites-enabled/default ]; then
      $SUDO rm /etc/nginx/sites-enabled/default
      removed_default=1
    fi
  fi
  if ! $SUDO nginx -t; then
    if [ -n "$old" ]; then
      printf '%s\n' "$old" | $SUDO tee "$CONF" >/dev/null
    else
      $SUDO rm -f "$CONF" ${LINK:+"$LINK"}
    fi
    [ -z "$removed_default" ] || $SUDO ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
    echo "nginx rejected the PhenoPlant server block (another site may already be default_server on port 80)" >&2
    exit 1
  fi
  $SUDO systemctl enable --now nginx >/dev/null
  $SUDO systemctl reload nginx
}

have_cert() { [ -n "$SITE_DOMAIN" ] && $SUDO test -f "$CERT_DIR/fullchain.pem"; }

# A certificate already on the server keeps https working even if this run cannot renew it
install_conf "$(have_cert && echo 1 || echo 0)"
$SUDO systemctl is-active --quiet nginx || $SUDO systemctl start nginx

[ -n "$SITE_DOMAIN" ] || exit 0

# www goes into the certificate only when its DNS record points where the main name does
names=(-d "$SITE_DOMAIN")
main_ip=$(getent ahostsv4 "$SITE_DOMAIN" | awk 'NR==1{print $1}' || true)
www_ip=$(getent ahostsv4 "www.$SITE_DOMAIN" | awk 'NR==1{print $1}' || true)
if [ -n "$main_ip" ] && [ "$main_ip" = "$www_ip" ]; then
  names+=(-d "www.$SITE_DOMAIN")
else
  echo "www.$SITE_DOMAIN does not point to $SITE_DOMAIN yet, so the certificate covers $SITE_DOMAIN only"
fi
contact=(--register-unsafely-without-email)
[ -z "$CERT_EMAIL" ] || contact=(-m "$CERT_EMAIL")

# Does nothing while the certificate is valid for the same names; renewals run from certbot's own timer
if $SUDO certbot certonly --webroot -w "$ACME_DIR" --cert-name "$SITE_DOMAIN" "${names[@]}" \
     --non-interactive --agree-tos "${contact[@]}" --keep-until-expiring --expand; then
  # reload nginx after each automatic renewal so it serves the new certificate
  $SUDO mkdir -p /etc/letsencrypt/renewal-hooks/deploy
  printf '#!/bin/sh\nsystemctl reload nginx\n' | $SUDO tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx >/dev/null
  $SUDO chmod 755 /etc/letsencrypt/renewal-hooks/deploy/reload-nginx
  $SUDO systemctl enable --now certbot.timer >/dev/null 2>&1 || true
fi

if have_cert; then
  install_conf 1
  $SUDO systemctl reload nginx  # picks up a certificate certbot has just issued or extended to www
else
  echo "::warning::No certificate for $SITE_DOMAIN yet: the site stays on plain http. Check that $SITE_DOMAIN points to this server and port 80 is open, then run the workflow again."
fi
