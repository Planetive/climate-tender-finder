# Deploy: Vercel (frontend) + AWS EC2 (backend)

This repo is a **monorepo**:
- **Backend** = repo root (`main.py`, `services/`, `Dockerfile`)
- **Frontend** = `frontend/` (Vite + React)

---

## 1) Backend on AWS EC2 (Docker)

### Prerequisites
- EC2 with Docker installed
- Security Group: open **TCP 3001** (or 80/443 if you put nginx in front)
- Optional: domain pointing to the EC2 public IP

### Build & run
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

Check health:
```bash
curl http://YOUR_EC2_IP:3001/api/health
curl "http://YOUR_EC2_IP:3001/api/sources"
```

First `/api/feeds?refresh=true` can take several minutes (RSS + scrapers including Playwright for SECP).

### Without Docker (bare metal)
```bash
sudo apt update && sudo apt install -y python3.13 python3.13-venv
python3.13 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium
export ENABLE_AI_FILTERING=false
export CORS_ORIGINS=https://YOUR-APP.vercel.app
python main.py
```

---

## 2) Frontend on Vercel

1. Import repo: `Planetive/climate-tender-finder`
2. **Root Directory** = `frontend`  ← required
3. Framework: Vite (auto)
4. Build: `npm run build` / Output: `dist`
5. Environment variables:

| Name | Value |
|------|--------|
| `VITE_API_URL` | `http://YOUR_EC2_IP:3001/api` **or** `https://api.yourdomain.com/api` |
| `VITE_SUPABASE_URL` | optional (from `frontend/.env.example`) |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | optional |
| `VITE_SUPABASE_PROJECT_ID` | optional |

6. Deploy

**Important:** `VITE_*` vars are baked in at **build time**. After changing `VITE_API_URL`, redeploy Vercel.

### HTTPS tip
Browsers block `https://vercel.app` → `http://EC2` (mixed content). Prefer:
- nginx + Let’s Encrypt on EC2 → `https://api.yourdomain.com`
- or Cloudflare Tunnel / ALB with TLS

---

## 3) CORS

Backend reads `CORS_ORIGINS` (comma-separated). Example:
```bash
-e CORS_ORIGINS=https://climate-tender-finder.vercel.app,http://localhost:8080
```
Default is `*` (fine for early testing).

---

## 4) What gets fetched

All sources in `config/feeds.py` are active (10 RSS + 5 scrapers including UNDP Pakistan & SECP).

`ENABLE_AI_FILTERING=false` (default in Docker) returns everything after keyword filters — no Gemini drop. Set `true` + `GEMINI_API_KEY` only if you want stricter climate filtering.

Auth is open (guest mode) — no login wall on Vercel.

---

## 5) Quick checklist

- [ ] EC2 `/api/health` returns ok
- [ ] EC2 `/api/sources` shows ~15 sources
- [ ] Vercel Root Directory = `frontend`
- [ ] `VITE_API_URL` points to EC2 `/api`
- [ ] CORS includes your Vercel URL
- [ ] Prefer HTTPS API if frontend is HTTPS
