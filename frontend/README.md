# RITAM Dashboard — Frontend

A premium, dark-themed React dashboard for the RITAM market perception engine.
Built with Vite + React + TypeScript + Tailwind CSS.

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:5173` and proxies API requests to `http://localhost:8000` (the FastAPI backend).

## Panels

| Panel | Endpoint | Refresh |
| --- | --- | --- |
| Signal (BUY/SELL/HOLD) | `GET /api/candles` | 60s |
| Accuracy | `GET /api/feedback/accuracy` | 60s |
| Historical Analogs | `GET /api/analogs` | 60s |
| Gemma Explanation | `GET /api/explanation/latest` | 60s |

## Running with the backend

Make sure the RITAM FastAPI server is running:

```bash
# From the project root
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

The Vite dev server will proxy `/api/*` and `/ws/*` to the backend automatically.

## Tech Stack

- **Vite** — fast dev server and build
- **React 19** + TypeScript
- **Tailwind CSS v4** — utility-first styling with custom design tokens
- **Custom design system** — glassmorphism, signal glows, micro-animations
