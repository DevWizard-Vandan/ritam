# Deploying RITAM

## Local (Docker)
docker-compose up --build
# API at http://localhost:8000
# Health: http://localhost:8000/health

## Fly.io (Production API)
flyctl auth login
flyctl launch --no-deploy
flyctl secrets set GEMINI_API_KEY_1=... (all 7 keys)
flyctl secrets set DB_MODE=postgres
flyctl secrets set DATABASE_URL=postgres://...
flyctl secrets set SENTRY_DSN=...
flyctl secrets set ENVIRONMENT=production
flyctl deploy

## Frontend (Vercel)
cd frontend
vercel --prod
# Set VITE_API_BASE_URL=https://ritam-api.fly.dev

## PostgreSQL
Recommended: Fly.io Postgres (fly postgres create)
Or: Supabase free tier (same Supabase project as landing page)
