# /deploy — Production Deployment

Build and deploy the full GDF-AutoMon stack.

## Steps

1. **Build frontend:**
   ```bash
   cd frontend && npm run build
   ```
   Output goes to `frontend/dist/` which Nginx serves.

2. **Build Docker images:**
   ```bash
   cd infra
   docker compose build backend realtime
   ```

3. **Deploy stack:**
   ```bash
   docker compose up -d
   ```

4. **Wait for health checks:**
   ```bash
   docker compose ps
   # All services should show "healthy"
   ```

5. **Run DB migrations:**
   ```bash
   docker exec -it gdf-backend alembic upgrade head
   ```

6. **Verify endpoints:**
   ```bash
   curl -s https://localhost/api/health          # FastAPI health
   curl -s https://localhost/api/sensors/types   # Sensor type registry
   ```

7. **Check EMQX broker:**
   Open http://localhost:18083 (admin / see .env EMQX_DASHBOARD_PASSWORD)

## Rolling Update (no downtime)
```bash
docker compose build backend realtime
docker compose up -d --no-deps backend realtime
```

## SSL Certificate (Let's Encrypt)
```bash
docker run --rm -v "$(pwd)/nginx/ssl:/etc/letsencrypt" certbot/certbot certonly \
  --standalone -d yourdomain.com --email admin@yourdomain.com --agree-tos
cp nginx/ssl/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
cp nginx/ssl/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
docker compose restart nginx
```
