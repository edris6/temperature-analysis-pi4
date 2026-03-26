#!/bin/bash
# ThermalWatch installer for Raspberry Pi 4B
# Run as root: sudo bash install.sh

set -e
echo "=== ThermalWatch Installer ==="

APP_DIR="/opt/tempmonitor"
DATA_DIR="/var/lib/tempmonitor"

# Detect the real user who invoked sudo (falls back to current user)
REAL_USER="${SUDO_USER:-$(whoami)}"

# 1. Copy files
echo "[1/5] Installing files to $APP_DIR..."
mkdir -p "$APP_DIR"
cp temp_service.py "$APP_DIR/"
cp dashboard.html  "$APP_DIR/"

# 2. Create data directory
echo "[2/5] Creating data directory (owner: $REAL_USER)..."
mkdir -p "$DATA_DIR"
chown "$REAL_USER:$REAL_USER" "$DATA_DIR"

# 3. Install systemd service (inject real username)
echo "[3/5] Installing systemd service (user: $REAL_USER)..."
sed "s/YOUR_USER/$REAL_USER/" tempmonitor.service > /etc/systemd/system/tempmonitor.service
systemctl daemon-reload

# 4. Enable & start
echo "[4/5] Enabling service (starts on every boot)..."
systemctl enable tempmonitor
systemctl start  tempmonitor

# 5. Check status
echo "[5/5] Checking status..."
sleep 2
systemctl status tempmonitor --no-pager

# Get Pi's IP
IP=$(hostname -I | awk '{print $1}')
echo ""
echo "======================================"
echo "  ThermalWatch is running!"
echo "  Open in your browser:"
echo "    http://${IP}:8765"
echo "======================================"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status  tempmonitor   # check status"
echo "  sudo journalctl -u tempmonitor -f    # live logs"
echo "  sudo systemctl stop    tempmonitor   # stop"
echo "  sudo systemctl disable tempmonitor   # remove from startup"
