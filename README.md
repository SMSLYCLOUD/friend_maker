# SocialGrowthAI

A hybrid monorepo consisting of:

1. **Web**: A web-hosted application built with a Next.js frontend, Python (FastAPI) backend, and Rust auxiliary service. Features campaign building, analytics, robust social automation, and more.
2. **Desktop**: A desktop application built with Tauri (Rust) and React, designed for native execution.

## Road Map

**Phase 3: Web App Refinement & True Platform Integrations**
- [ ] Connect the Next.js frontend directly to the Python FastAPI backend via authenticated API calls.
- [ ] Complete robust error handling and proxy support for the Playwright automation in `app/automation/executor.py`.
- [ ] Update platform adapters (Instagram, Twitter, LinkedIn, Facebook) to use resilient scraping logic (e.g. computer vision fallbacks, fuzzy matching) rather than brittle, hardcoded HTML selectors.
- [ ] Finalize the Rust Microservice logic for true optimization logic (currently mocked).

**Phase 4: Desktop Architecture & Core MVP**
- [ ] Initialize the React frontend for the Tauri desktop application.
- [ ] Translate core database logic and anti-detection mechanisms into the Rust Tauri backend.
- [ ] Build a robust IPC (Inter-Process Communication) layer between the React UI and the Rust backend.
- [ ] Package the desktop application for multi-OS deployment (macOS, Windows, Linux).

**Phase 5: Production Hardening & Global AI**
- [ ] Container orchestration (Kubernetes) and load-balancing strategy for the web stack.
- [ ] Integrate local AI models (via Ollama or similar) directly into the desktop client for fully local, privacy-first data processing.
- [ ] Implement robust user authentication (JWT/OAuth) in the Web version.

## Monorepo Structure

*   `/web/`: The web application project. Includes backend logic, the web interface, and related auxiliary services. Uses Docker and Docker Compose.
*   `/desktop/`: The desktop application project, powered by Tauri.

## Running the Web Application

The easiest way to run the web application is using Docker Compose. Make sure you are inside the `web` directory:

```bash
cd web
docker-compose up --build
```

This will start:
- The Python FastAPI backend on port 8000
- The Next.js frontend on port 3000

For development details, refer to the files in the `/web` directory.

To run only the frontend in a separate container:

```bash
cd web/frontend
docker-compose up --build
```

### Frontend ↔ Backend Connection

The frontend calls the backend using `NEXT_PUBLIC_API_URL`.

- Local Docker compose (`/web/docker-compose.yml`) sets:
  - `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Frontend-only compose (`/web/frontend/docker-compose.yml`) also expects backend on `http://localhost:8000`.
- In production, set `NEXT_PUBLIC_API_URL` to your deployed backend URL (for example `https://api.your-domain.com`).

Also ensure backend CORS allows your frontend origin via `CORS_ALLOWED_ORIGINS`.

## Running the Desktop Application

The desktop application is a Tauri project. Please refer to the documentation inside the `/desktop` folder for instructions on installing Rust, Tauri dependencies, and node modules to build and run it.

```bash
cd desktop
# Follow standard Tauri run instructions, e.g.:
npm install
npm run tauri dev
```
