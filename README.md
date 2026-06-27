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
|---|---|
| Framework | React 18 + Vite + TypeScript |
| Map | react-map-gl v8 + MapLibre GL JS v5 |
| Map tiles | Stadia Maps "Alidade Smooth Dark" |
| Charts | Recharts v2 |
| Animation | Framer Motion |
| Styling | Tailwind CSS v3 |
| Data | Supabase (mock data by default) |
| Deployment | Vercel + GitHub Actions |

## Getting Started

```bash
cp .env.example .env
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Environment Variables

| Variable | Description |
|---|---|
| `VITE_USE_MOCK_DATA` | `true` to use local mock data (default), `false` for Supabase |
| `VITE_SUPABASE_URL` | Your Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Your Supabase anon key |
| `VITE_STADIA_API_KEY` | Stadia Maps API key (optional for localhost) |

## Connecting to Supabase

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Run `docs/schema.sql` in the Supabase SQL editor
3. Set `VITE_USE_MOCK_DATA=false` and add your `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`

## Deployment (Vercel)

```bash
npm install -g vercel
vercel link          # creates .vercel/project.json with org/project IDs
vercel env add VITE_USE_MOCK_DATA production
vercel env add VITE_STADIA_API_KEY production
# Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY as well
```

Then add these GitHub Secrets for the CI/CD pipeline:
- `VERCEL_TOKEN` — from [vercel.com/account/tokens](https://vercel.com/account/tokens)
- `VERCEL_ORG_ID` — from `.vercel/project.json`
- `VERCEL_PROJECT_ID` — from `.vercel/project.json`
- `STADIA_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`

PRs get automatic preview deployments. Merging to `main` triggers production deploy.

## Design Reference

Visual design inspired by [world.helium.com](https://world.helium.com/en/network/mobile). Reference implementation cloned at `/tmp/helium-reference` (Apache-2.0). Not forked — built independently.
