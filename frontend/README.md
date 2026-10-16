# AgenticAim Dashboard

React + Vite + Tailwind frontend for the AgenticAim AI aim coach.

## Run
    npm install
    npm run dev        # http://localhost:5173

In a separate terminal, start the FastAPI backend from the `AgenticAim` folder:

    python main.py --serve    # http://127.0.0.1:8000

Vite forwards `/api/*` and `/analyze` to `http://127.0.0.1:8000`, so the browser
uses the frontend origin and does not need backend CORS configuration for local
development. To use another backend address, set `VITE_API_PROXY_TARGET` before
starting Vite. For deployments that call the API directly, set `VITE_API_BASE`
to the backend URL and configure that backend's CORS origins.

If the backend is offline the UI shows demo data (header shows "DEMO DATA").

## Endpoints used (polled every 3s)
GET /api/hardware · GET /api/latest-session · GET /api/rag/status · POST /api/chat · POST /analyze
