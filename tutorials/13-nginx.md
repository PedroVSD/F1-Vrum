# Tutorial 13.6 — Nginx (Reverse Proxy + TLS)

## Passo 1 — `nginx.conf` na raiz

```nginx
upstream api { server api:8000; }

server {
    listen 80;
    server_name localhost;

    # API
    location / {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # rate limit opcional
        limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    }
    # Dashboard Streamlit se usar
    location /dashboard/ {
        proxy_pass http://dashboard:8501/;
    }
}
```

Para TLS (produção), adicione:
```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.pem;
    # ...
}
```

## Passo 2 — `docker-compose.yml` — adicione serviço

```yaml
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes: ["./nginx.conf:/etc/nginx/nginx.conf:ro"]
    depends_on: [api]
  # opcional dashboard
  dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dashboard
    ports: ["8501:8501"]
```

**`Dockerfile.dashboard`**:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY dashboard/ dashboard/
RUN pip install streamlit httpx pandas plotly
CMD ["streamlit","run","dashboard/app.py","--server.port","8501","--server.address","0.0.0.0"]
```

## Passo 3 — Teste

```bash
docker compose up --build
curl http://localhost:80/weekend/health | jq # via nginx
curl http://localhost:80/docs | head
# fora do docker, api ainda em :8000, mas produção só expõe :80
```

Remova `ports: ["8000:8000"]` do `api` em produção para só expor via Nginx.
