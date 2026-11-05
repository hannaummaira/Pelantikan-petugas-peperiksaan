#!/bin/bash
# Deploy SPM JPN Selangor - Hostinger VPS (Ubuntu 22.04 / 24.04)
# Guna:  cd /opt/spm && bash deploy.sh
set -e
echo "=== Deploy SPM JPN Selangor ==="

apt-get update -y
apt-get install -y ca-certificates curl unzip ufw

# Docker (rasmi) jika belum ada
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

# Swap 2GB (VPS 4GB)
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Firewall: SSH + web sahaja
ufw allow OpenSSH >/dev/null || true
ufw allow 8501/tcp >/dev/null || true
ufw --force enable >/dev/null || true

# Jana .env jika belum ada (kata laluan JPN rawak, matikan kata laluan induk 'a')
if [ ! -f .env ]; then
  PW=$(head -c 12 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 12)
  printf "JPN_PASSWORD=%s\nDISABLE_MASTER_PASSWORD=true\n" "$PW" > .env
  chmod 600 .env
  echo ">>> Kata laluan JPN baharu: $PW   (disimpan dalam /opt/spm/.env - SIMPAN!)"
fi

# docker compose v2 (fallback ke v1)
if docker compose version >/dev/null 2>&1; then DC="docker compose"; else DC="docker-compose"; fi
$DC down || true
$DC up -d --build

IP=$(curl -fsS ifconfig.me 2>/dev/null || echo "IP_VPS")
echo "=== SIAP === Buka: http://$IP:8501"
echo "Log: docker logs -f spm_jpn --tail 50"
