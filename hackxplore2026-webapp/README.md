# HackXplore 2026 — Karlsruhe Tree Sensor Dashboard

A public-facing dashboard for Karlsruhe's IoT tree-humidity sensor network. Built with React 18, MapLibre GL JS, and Supabase.

## Features

- **Interactive map** — dark Stadia Maps tile style, zoomable, filterable
- **Tree & sensor markers** — color-coded by humidity status with pulsing alerts for dry trees
- **Detail panels** — slide-in panels for tree/sensor data with 30-day history charts and AI recommendations
- **Stats panel** — desktop sidebar / mobile bottom drawer with live network metrics
- **Search** — instant client-side search across trees, sensors, and districts
- **Statistics page** — full network analytics with leaderboard and charts
- **Weather widget** — 5-day forecast with moisture impact analysis

## Tech Stack

| Concern | Library |
| --- | --- |
| Framework | React 18 + Vite + TypeScript |
| Map | react-map-gl v8 + MapLibre GL JS v5 |
| Map tiles | Stadia Maps "Alidade Smooth Dark" |
| Charts | Recharts v2 |
| Animation | Framer Motion |
| Styling | Tailwind CSS v3 |
| Data | Supabase (mock data by default) |
| Deployment | Netlify + GitHub Actions |

## Getting Started

```bash
cp .env.example .env
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Environment Variables

| Variable | Description |
| --- | --- |
| `VITE_USE_MOCK_DATA` | `true` to use local mock data (default), `false` for Supabase |
| `VITE_SUPABASE_URL` | Your Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Your Supabase anon key |
| `VITE_STADIA_API_KEY` | Stadia Maps API key (optional for localhost) |

## Connecting to Supabase

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Run `docs/schema.sql` in the Supabase SQL editor
3. Set `VITE_USE_MOCK_DATA=false` and add your `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`

## Deployment (Netlify)

**Quick deploy (drag & drop):**

```bash
npm run build
# Drag the dist/ folder to app.netlify.com/drop
```

**CLI deploy:**

```bash
npm install -g netlify-cli
netlify login
netlify init        # link to your Netlify site
netlify deploy --prod
```

**GitHub auto-deploy:**

1. Connect your repo at [app.netlify.com](https://app.netlify.com/start)
2. Build command: `npm run build` · Publish dir: `dist`
3. Add environment variables in Netlify dashboard → Site settings → Environment variables:
   - `VITE_USE_MOCK_DATA` = `true`
   - `VITE_STADIA_API_KEY` = your key
   - `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` (when connecting Supabase)

**GitHub Actions CI/CD** — add these GitHub Secrets:

- `NETLIFY_AUTH_TOKEN` — from [app.netlify.com/user/applications](https://app.netlify.com/user/applications)
- `NETLIFY_SITE_ID` — from Netlify site settings → General → Site ID
- `STADIA_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`

PRs get automatic preview deployments. Merging to `main` triggers production deploy.

## Design Reference

Visual design inspired by [world.helium.com](https://world.helium.com/en/network/mobile). Reference implementation cloned at `/tmp/helium-reference` (Apache-2.0). Not forked — built independently.
