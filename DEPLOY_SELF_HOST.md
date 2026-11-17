# Self-Hosting VaultPDF Studio (Option 3: Permanent Link)

This guide sets up **VaultPDF Studio** on an always-on server (VPS) with a **permanent HTTPS URL** using Docker Compose + Caddy (automatic Let's Encrypt certificates).

> **Platform note:** `docx2pdf` (Word → PDF) requires **Microsoft Word on Windows**. On a typical Linux VPS this specific conversion will not work; all other tools (merge, split, compress, true redact, PDF→Word, PDF↔Images, protect/unlock, rotate, watermark) work if dependencies install correctly. If you need Word→PDF on the server, host on a Windows machine/server with Microsoft Word installed and adapt the reverse-proxy steps.

## Prerequisites

- A VPS/server that stays online (Ubuntu 22.04/24.04 recommended).
- A domain name you control (e.g. `pdf.example.com`).
- DNS **A record** (and AAAA if using IPv6) for your domain pointing to the server’s public IP.
- Ports **80** and **443** open in the server firewall/security group (Caddy needs them for HTTPS certificates and traffic).
- SSH access to the server.

## 1. Prepare the server (Ubuntu example)

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker Engine + Compose plugin (official convenience script or distro packages)
# See: https://docs.docker.com/engine/install/ubuntu/
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Log out and back in (or: newgrp docker) so docker runs without sudo
```

Verify:
```bash
docker --version
docker compose version
```

## 2. Copy the project to the server

From your local machine (PowerShell/scp/rsync) or by cloning your repo on the server. The server needs at least:
- `app/`, `static/`, `templates/`
- `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`
- `Caddyfile.example`

Do **not** copy `.venv/`, `.temp_workspace/`, or `cloudflared.exe`.

Example (from local machine):
```bash
scp -r ./vaultpdf user@YOUR_SERVER_IP:~/vaultpdf
# or use rsync/git clone on the server
```

## 3. Configure your domain in Caddy

On the server, inside the project directory:

```bash
cd ~/vaultpdf
cp Caddyfile.example Caddyfile
nano Caddyfile   # replace pdf.example.com with your real domain
```

`Caddyfile` should contain your domain, e.g.:
```caddy
pdf.yourdomain.com {
    encode gzip zstd
    reverse_proxy app:8000
}
```

> Caddy automatically obtains and renews TLS certificates from Let's Encrypt. This requires the domain to resolve to this server and ports 80/443 to be reachable.

## 4. Build and start

```bash
docker compose up -d --build
```

Check status and logs:
```bash
docker compose ps
docker compose logs -f app
docker compose logs -f caddy
```

Once Caddy has issued a certificate, your permanent link will be:
- `https://pdf.yourdomain.com` (your configured domain)

## 5. Verify

- Open `https://your-domain` in a browser — you should see VaultPDF Studio.
- Test a simple operation (e.g. merge or rotate) to confirm uploads/processing/downloads work through the proxy.
- Temp files are written to `.temp_workspace/` inside the container and auto-cleaned after each response.

## 6. Updates

After changing code:
```bash
git pull   # if using git
docker compose up -d --build
```

## 7. Firewall (if enabled)

Example with UFW:
```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## Alternative: without Docker (systemd + venv + Caddy/Nginx)

1. Install Python 3.10+ and Caddy (or Nginx + Certbot) on the server.
2. Create a venv and install deps: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
3. Run with a process manager. Example systemd unit (`/etc/systemd/system/vaultpdf.service`):
   ```ini
   [Unit]
   Description=VaultPDF Studio
   After=network.target

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/opt/vaultpdf
   ExecStart=/opt/vaultpdf/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
   Then: `sudo systemctl daemon-reload && sudo systemctl enable --now vaultpdf`
4. Configure Caddy/Nginx to reverse proxy `https://your-domain` → `127.0.0.1:8000` and enable TLS.

## Privacy & exposure note

This app is designed for local/offline processing. When you self-host it publicly:
- Anyone with the URL can access it unless you add authentication (not included by default). Consider restricting access (basic auth in Caddy, VPN/Tailscale, IP allowlist, or SSO) if it should not be public.
- Uploaded files are processed on your server and auto-deleted after responses, but traffic and handling occur on that infrastructure. Share the link only with intended users and use HTTPS.

## Troubleshooting

- **Certificate not issued:** confirm DNS points to the server, ports 80/443 are open, and no other service is using them (`docker compose logs caddy`).
- **502 Bad Gateway:** app container not ready or crashed (`docker compose logs app`).
- **Large PDFs/timeouts:** reverse proxies may have upload/body/time limits; Caddy defaults are generally permissive, but adjust if needed.
- **Word → PDF fails on Linux:** expected without Microsoft Word; use PDF→Word or run that feature on a Windows host.
