# Waffen Tactics Web

Web client and backend for Waffen Tactics. Discord is used for OAuth login only.

## Setup

```bash
cd waffen-tactics-web
npm install
cp .env.example .env
cp backend/.env.example backend/.env
```

Fill in the environment values:

Frontend `.env`
```env
VITE_DISCORD_CLIENT_ID=your_client_id_here
VITE_DISCORD_REDIRECT_URI=http://localhost:3000/auth/callback
VITE_API_URL=http://localhost:8000
```

Backend `backend/.env`
```env
DISCORD_CLIENT_ID=your_client_id_here
DISCORD_CLIENT_SECRET=your_client_secret_here
DISCORD_REDIRECT_URI=http://localhost:3000/auth/callback
JWT_SECRET=your-random-secret-key-here
```

## Run locally

```bash
# backend
cd waffen-tactics-web/backend
python api.py

# frontend
cd waffen-tactics-web
npm run dev
```

The frontend is available at `http://localhost:3000` or the Vite fallback port if 3000 is busy.

## VPS workflow

- Keep the repository on the VPS as the runtime source of truth.
- Edit locally, push or sync to the VPS, then restart with `./start-all.sh`.
- Use `./setup.sh` only to install or refresh dependencies.
- Do not add Discord bot gameplay back into the runtime.

## Main paths

- Frontend app: `src/`
- Backend API: `backend/`
- Shared game core: `../waffen-tactics/`
- Startup script: `../start-all.sh`
- Setup script: `../setup.sh`

## Troubleshooting

- If login fails, verify the Discord OAuth redirect URI and both client IDs.
- If the backend refuses to start, check `backend/.env` for missing secrets.
- If the frontend build fails, install dependencies again with `npm install`.

