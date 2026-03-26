# ThermalWatch 🌡️

A lightweight CPU temperature monitor for the **Raspberry Pi 4B**.  
Reads temperature every 30 seconds, stores it locally, and serves a live web dashboard accessible from any device on your network.

---

## Requirements

- Raspberry Pi 4B running Raspberry Pi OS (Bullseye or later)
- Python 3 (pre-installed on all Pi OS images)
- No extra Python packages needed — uses only the standard library

---

## Files

| File | Purpose |
|---|---|
| `temp_service.py` | Backend daemon — reads temp, stores to SQLite, serves web UI |
| `dashboard.html` | Web dashboard — graphs, stats, live readout |
| `tempmonitor.service` | Systemd unit — makes the service start on boot |
| `install.sh` | One-command installer |

---

## Installation

**1. SSH into your Raspberry Pi:**
```bash
ssh pi@<pi-ip-address>
```

**2. Make sure `git` is installed:**
```bash
sudo apt update && sudo apt install -y git
```

**3. Clone the repository:**
```bash
git clone https://github.com/edris6/temperature-analysis-pi4.git
cd temperature-analysis-pi4
```



**4. Run the installer as root:**
```bash
sudo bash install.sh
```

The installer will:
- Copy the app files to `/opt/tempmonitor/`
- Create the data directory at `/var/lib/tempmonitor/`
- Register and start the systemd service
- Enable it to run automatically on every boot

**5. Find your Pi's IP address (if you don't know it):**
```bash
hostname -I
```

**6. Open the dashboard in any browser on your network:**
```
http://<pi-ip-address>:8765
```

---

## Checking if it's Running

```bash
sudo systemctl status tempmonitor
```

You should see `Active: active (running)` in green. Example output:

```
● tempmonitor.service - ThermalWatch – CPU Temperature Monitor
     Loaded: loaded (/etc/systemd/system/tempmonitor.service; enabled)
     Active: active (running) since ...
```

---

## Live Logs

Stream logs in real time directly from the terminal:

```bash
sudo journalctl -u tempmonitor -f
```

Each line shows a timestamp and the temperature recorded at that moment:

```
[tempmonitor] 2026-03-26T14:32:10 → 47.2°C
[tempmonitor] 2026-03-26T14:32:40 → 47.8°C
```

Press `Ctrl + C` to stop following the log.

To view the last 100 lines without following:
```bash
sudo journalctl -u tempmonitor -n 100
```

---

## Restarting the Service

```bash
sudo systemctl restart tempmonitor
```

Use this after making any changes to `temp_service.py` or `dashboard.html`.

---

## Stopping the Service

Stops the service until next reboot (or until you start it again):

```bash
sudo systemctl stop tempmonitor
```

To start it again manually:
```bash
sudo systemctl start tempmonitor
```

---

## Disabling Auto-Start on Boot

This keeps the service installed but stops it from starting automatically when the Pi boots:

```bash
sudo systemctl disable tempmonitor
```

To re-enable auto-start:
```bash
sudo systemctl enable tempmonitor
```

---

## Uninstallation

Run these commands one by one to fully remove ThermalWatch:

```bash
# 1. Stop the running service
sudo systemctl stop tempmonitor

# 2. Disable it from starting on boot
sudo systemctl disable tempmonitor

# 3. Remove the systemd service file
sudo rm /etc/systemd/system/tempmonitor.service

# 4. Reload systemd so it forgets the unit
sudo systemctl daemon-reload

# 5. Delete the app files
sudo rm -rf /opt/tempmonitor

# 6. Delete the database and all stored readings
sudo rm -rf /var/lib/tempmonitor
```

> ⚠️ Step 6 permanently deletes all historical temperature data. Skip it if you want to keep your readings.

---

## File & Data Locations

| Path | Contents |
|---|---|
| `/opt/tempmonitor/` | App files (`temp_service.py`, `dashboard.html`) |
| `/var/lib/tempmonitor/temps.db` | SQLite database with all temperature readings |
| `/etc/systemd/system/tempmonitor.service` | Systemd service unit |

---

## API Endpoints

The service also exposes a simple JSON API if you want to build on top of it:

| Endpoint | Description |
|---|---|
| `GET /` | The web dashboard |
| `GET /api/current` | Latest temperature reading `{ts, temp_c}` |
| `GET /api/24h` | Last 24 hours, bucketed every 5 minutes `[{ts, min, avg, max}]` |
| `GET /api/7w` | Last 7 weeks, bucketed every hour `[{ts, min, avg, max}]` |
| `GET /api/info` | Service metadata `{total_readings, oldest_ts, db_path, interval_seconds}` |

---

## Troubleshooting

**Dashboard won't load**
- Check the service is running: `sudo systemctl status tempmonitor`
- Make sure port 8765 isn't blocked: `sudo ufw allow 8765` (if using a firewall)
- Confirm you're on the same network as the Pi

**Temperature shows `-1.0°C`**
- The thermal sensor file couldn't be read — check permissions or try rebooting the Pi

**Service fails to start**
- View the full error log: `sudo journalctl -u tempmonitor -n 50`
- Ensure Python 3 is available: `python3 --version`

**Changes to files aren't showing**
- After editing any file in `/opt/tempmonitor/`, restart the service: `sudo systemctl restart tempmonitor`

---

## Quick Reference

```bash
sudo systemctl start    tempmonitor   # start
sudo systemctl stop     tempmonitor   # stop
sudo systemctl restart  tempmonitor   # restart
sudo systemctl status   tempmonitor   # check status
sudo systemctl enable   tempmonitor   # enable on boot
sudo systemctl disable  tempmonitor   # disable on boot
sudo journalctl -u tempmonitor -f     # live logs
```
