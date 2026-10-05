# Deploy guide

This repo is a **monorepo**:
- **Backend (`app`)** = repo root (`main.py`, `services/`, `Dockerfile`)
- **Frontend** = `frontend/` (Vite + React)

---

## Option A — Everything on Vercel (multi-service)

Root `vercel.json` defines two services: `app` (FastAPI) and `frontend` (Vite).

1. Import `Planetive/climate-tender-finder` on Vercel
2. **Do not** set Root Directory to `frontend` — leave it at the **repo root** so `vercel.json` is used
3. Env vars on the project (optional):
   - `ENABLE_AI_FILTERING=false`
   - `GEMINI_API_KEY=` (only if AI filter is on)
   - Leave `VITE_API_URL` **unset** so the UI calls same-origin `/api`
4. Deploy

Routing:
- `/api/*` → FastAPI (`app`)
- everything else → Vite SPA (`frontend`)

**Limits to know:** Vercel Functions have a max duration (set to 300s here). Full scrapes (Playwright / SECP) can be slow or fail on the Python runtime because Chromium is heavy. If scrapers break on Vercel, use Option B for the backend.

---

## Option B — Vercel frontend + AWS EC2 backend (Docker)

### Backend on EC2
```bash
git clone https://github.com/Planetive/climate-tender-finder.git
cd climate-tender-finder
git checkout main

docker build -t climate-tender-api .

docker run -d --name climate-tender-api \
  -p 3001:3001 \
  -e PORT=3001 \
  -e ENABLE_AI_FILTERING=false \
  -e CORS_ORIGINS=https://YOUR-APP.vercel.app \
  -e GEMINI_API_KEY= \
  --restart unless-stopped \
  climate-tender-api
```

Health checks:
```bash
curl http://YOUR_EC2_IP:3001/api/health
curl "http://YOUR_EC2_IP:3001/api/sources"
```

### Frontend on Vercel (frontend-only)
1. Root Directory = `frontend`
2. Set `VITE_API_URL=https://YOUR_API_HOST/api` (must include `/api`)
3. Deploy

Browsers block `https://vercel.app` → `http://EC2` (mixed content). Prefer HTTPS on the API (nginx + Let’s Encrypt, Cloudflare Tunnel, or ALB).

---

## CORS

Backend reads `CORS_ORIGINS` (comma-separated). Same-origin Option A usually needs no special CORS. For Option B:
```bash
-e CORS_ORIGINS=https://your-app.vercel.app,http://localhost:8080
```

---

## Checklist

- [ ] `/api/health` returns ok
- [ ] `/api/sources` lists sources
- [ ] UI loads opportunities without CORS / mixed-content errors
- [ ] If using AI filter: `GEMINI_API_KEY` set and `ENABLE_AI_FILTERING=true`
