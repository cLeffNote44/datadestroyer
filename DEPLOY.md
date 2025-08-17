# Deployment guide (GHCR + Docker Compose)

This document explains how to deploy the app to a Linux VM using the published container image at GHCR, and how to keep it running with systemd.

Prerequisites
- Linux VM (Ubuntu 22.04+ recommended)
- Docker Engine + Compose plugin installed
- Port 80 (and 443 if using TLS) open in firewall/security group
- If your GHCR package is private: a GitHub Personal Access Token (PAT) with `read:packages`

1) Install Docker (Ubuntu)
```
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release; echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
# Re-log or `newgrp docker` to apply group membership
```

2) Fetch deployment files
- Copy these from the repo to the VM (same directory structure):
  - `docker-compose.prod.yml`
  - `nginx/nginx.conf`
  - `.env` (create this on the server; see next step)

3) Create `.env` on the server
```
DJANGO_SECRET_KEY=<strong-random-secret>
DJANGO_ALLOWED_HOSTS=<your.domain>,<www.your.domain>,<server-ip>
DJANGO_CSRF_TRUSTED_ORIGINS=https://<your.domain>,https://<www.your.domain>
DEBUG=false
```

4) Log in to GHCR (if private)
```
export CR_PAT=<your_pat_with_read_packages>
echo $CR_PAT | docker login ghcr.io -u <your_github_username> --password-stdin
```

5) Start the stack
```
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

6) Validate
```
curl -I http://<server-ip-or-domain>/health/
docker compose -f docker-compose.prod.yml logs --tail 100 web
```

7) Optional: systemd service
Create `/etc/systemd/system/datadestroyer.service`:
```
[Unit]
Description=Data Destroyer (Docker Compose)
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
WorkingDirectory=/opt/datadestroyer
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
RemainAfterExit=yes
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Then enable:
```
sudo systemctl daemon-reload
sudo systemctl enable --now datadestroyer
```

Notes
- TLS: provide an `nginx/nginx.tls.conf` and mount certs under `nginx/certs`, then use `docker-compose.prod.tls.yml`.
- Updating:
  - `docker compose -f docker-compose.prod.yml pull`
  - `docker compose -f docker-compose.prod.yml up -d`
- Logs:
  - `docker compose -f docker-compose.prod.yml logs -f web`
- Database persistence is handled by the named volume `pgdata`.
