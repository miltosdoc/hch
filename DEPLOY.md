# HCH Deployment Guide

## Prerequisites

- Docker & Docker Compose
- Domain name (optional, for HTTPS)
- SSL certificate (optional, for HTTPS)

## Setup

### 1. Copy and configure .env

```bash
cp .env.example .env
```

Edit `.env` with your values:

- `SECRET_KEY` — Generate a random key: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- `ADMIN_USERNAME` — Default admin username (default: admin)
- `ADMIN_PASSWORD` — Default admin password (REQUIRED — no default)
- `WEBDOC_CLIENT_ID` — WebDoc API client ID (optional)
- `WEBDOC_CLIENT_SECRET` — WebDoc API client secret (optional)

### 2. Build and start

```bash
docker compose up -d --build
```

### 3. Verify

Check all services are running:
```bash
docker compose ps
```

Check health endpoints:
```bash
curl http://localhost:8081/health  # Nginx
curl http://localhost:5001/health  # Portal
curl http://localhost:5002/health  # Holter Review
curl http://localhost:5003/health  # Holter Tracker
curl http://localhost:5004/health  # ECG Archive
```

### 4. First login

Visit `http://<server-ip>:8080` and login with the admin credentials from `.env`.

## HTTPS Setup (Optional)

### Using Let's Encrypt

1. Install certbot:
```bash
sudo apt install certbot
```

2. Get certificate:
```bash
sudo certbot certonly --standalone -d your-domain.com
```

3. Update nginx config to use the certificate (add to `default.conf`):
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    # ... your proxy locations ...
}
```

4. Update `SESSION_COOKIE_SECURE = True` in `app/app.py` if using HTTPS

## Maintenance

### View logs

```bash
docker compose logs -f
```

### Restart

```bash
docker compose restart
```

### Update

```bash
git pull && docker compose up -d --build
```

### Backup

```bash
docker compose exec db pg_dump -U hch_user hch > backup.sql
```

### Restore

```bash
docker compose exec -T db psql -U hch_user hch < backup.sql
```

## Security Notes

- **Never commit `.env` to git** — it's in `.gitignore`
- **Change the default admin password** after first login
- **Use HTTPS** in production (see HTTPS setup above)
- **Rotate SECRET_KEY** if you suspect a leak
- **Regular backups** of the PostgreSQL database
- **Update Docker images** regularly: `docker compose pull && docker compose up -d`
