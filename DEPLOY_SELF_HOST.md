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
