# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KEDA Dashboard is a full-stack web application for managing Kubernetes Event-driven Autoscaling (KEDA) ScaledObjects. It provides a UI to create, view, edit, and delete ScaledObjects, schedule cron-based scaling events, and monitor KEDA scaler status.

**Tech Stack**:
- **Backend**: FastAPI (Python 3.11+) with SQLAlchemy, SQLite (default), JWT authentication
- **Frontend**: React 19 with Create React App, Tailwind CSS, Shadcn/ui components
- **Database**: SQLite (development), PostgreSQL via DATABASE_URL environment variable
- **Container**: Multi-stage Docker build (Node + Python)

## Architecture

### Backend (`backend/`)
- `server.py` - Main FastAPI application with authentication, ScaledObject CRUD, cron events, and Kubernetes integration
- `k8s_service.py` - Abstract service layer with two implementations:
  - `MockK8sService`: Uses SQLite database (default development mode)
  - `RealK8sService`: Uses Kubernetes Python client for actual K8s cluster interaction
- `requirements.txt` - Python dependencies including FastAPI, SQLAlchemy, kubernetes client, AI/ML libraries

**Kubernetes Integration**: Controlled by `K8S_MODE` environment variable:
- `mock` (default): Uses SQLite database, no actual K8s cluster required
- `in-cluster`: Connects to real Kubernetes cluster using in-cluster config or kubeconfig

**Authentication**: JWT tokens stored in HTTP-only cookies. Default admin credentials:
- Email: `admin@example.com`
- Password: `admin123`

**Database Models**:
- `UserModel` - User accounts for authentication
- `ScaledObjectModel` - Stores ScaledObject configurations
- `CronEventModel` - Scheduled scaling events linked to ScaledObjects

### Frontend (`frontend/`)
- React single-page application with React Router for navigation
- **Pages**: Login, Dashboard (ScaledObjects list), ScaledObject detail, Cron Calendar
- **Context**: `AuthContext` manages authentication state and token
- **Styling**: Tailwind CSS with Shadcn/ui components, following design guidelines in `design_guidelines.json`
- **Build Tool**: Create React App configured with CRACO for Tailwind

**Design Guidelines**: See `design_guidelines.json` for comprehensive UI specifications including:
- Typography (IBM Plex Sans + JetBrains Mono)
- Color palette (sober slate/zinc tones)
- Component styling (Shadcn overrides)
- Layout principles (data-dense "control room" grid)

### Testing
- `backend_test.py` - Comprehensive API test suite (run with `python backend_test.py`)
- Frontend tests via `yarn test` (Create React App Jest setup)

### Containerization
- `Dockerfile` - Multi-stage build: Node for frontend, Python for backend
- Frontend static files served from FastAPI at `/frontend/build`
- Health check at `/api/health`

## Development Commands

### Backend Development
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Environment Variables** (set in `.env` file or shell):
```bash
DATABASE_URL=sqlite+aiosqlite:///./keda_dashboard.db  # SQLite default
JWT_SECRET=your-secret-key-here
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123
K8S_MODE=mock  # or "in-cluster" for real K8s
CORS_ORIGINS=http://localhost:3000,http://localhost:8001
```

### Frontend Development
```bash
cd frontend
yarn install
yarn start  # Runs on http://localhost:3000
```

### Running Tests
- **Backend API tests**: `python backend_test.py`
- **Frontend tests**: `cd frontend && yarn test`

### Docker Build & Run
```bash
# Build image
docker build -t keda-dash .

# Run container
docker run -p 8001:8001 -e JWT_SECRET=your-secret keda-dash

# With environment file
docker run -p 8001:8001 --env-file .env keda-dash
```

### GitHub Actions
- Automatically builds and pushes Docker image to GitHub Container Registry on push to `main` or `develop` branches
- Image tags: `latest` for main branch, `dev` for develop branch

## Important Files & Conventions

### Backend
- `backend/server.py` - Main application with routes, models, and authentication
- `backend/k8s_service.py` - Kubernetes service abstraction with mock/real implementations
- `backend/requirements.txt` - Python dependencies (freeze with `pip freeze > requirements.txt`)
- `backend/k8s_service.py:create_k8s_service()` - Factory function determining K8s mode

### Frontend
- `frontend/src/App.js` - Root component with routing and auth provider
- `frontend/src/contexts/AuthContext.js` - Authentication state management
- `frontend/src/components/` - Reusable UI components (mostly Shadcn/ui)
- `frontend/src/pages/` - Page components for each route
- `frontend/craco.config.js` - CRACO configuration for Tailwind
- `frontend/tailwind.config.js` - Tailwind configuration (check for Shadcn overrides)

### Design System
- `design_guidelines.json` - Comprehensive design specifications that MUST be followed:
  - Color palette (slate/zinc tones, high contrast)
  - Typography rules (IBM Plex Sans, JetBrains Mono)
  - Component styling (sharp radii, grid borders)
  - Motion guidelines (fast, functional transitions)
  - Icon usage (@phosphor-icons/react)

### Configuration
- `.gitignore` - Standard ignores including environment files
- `.github/workflows/docker-build-push.yml` - CI/CD pipeline
- `.emergent/emergent.yml` - Emergent integration metadata

## Key Implementation Notes

1. **K8S_MODE**: Defaults to `mock` for development. Set to `in-cluster` and ensure Kubernetes config is available for production.

2. **Authentication**: JWT tokens are stored in HTTP-only cookies. The frontend automatically includes them in API requests.

3. **ScaledObject IDs**: In mock mode, IDs are UUIDs. In real K8s mode, IDs follow `namespace/name` format.

4. **Cron Events**: Linked to ScaledObjects via `scaled_object_id`. Events can be filtered by month (`YYYY-MM` format).

5. **API Endpoints**:
   - `GET /api/health` - Health check
   - `POST /api/auth/login` - Login with email/password
   - `GET /api/auth/me` - Get current user
   - `GET /api/scaled-objects` - List ScaledObjects (filter by namespace, scaler_type)
   - `POST /api/scaled-objects` - Create ScaledObject
   - `GET /api/scaled-objects/{id}` - Get ScaledObject
   - `PUT /api/scaled-objects/{id}` - Update ScaledObject
   - `DELETE /api/scaled-objects/{id}` - Delete ScaledObject
   - `GET /api/cron-events` - List cron events
   - `POST /api/cron-events` - Create cron event
   - `GET /api/namespaces` - List namespaces (real K8s) or distinct namespaces from DB (mock)
   - `GET /api/scaler-types` - List scaler types
   - `GET /api/k8s-status` - Get Kubernetes connection status

6. **Frontend Data-testid**: Follow kebab-case role-based names per design guidelines (e.g., `data-testid="login-submit-btn"`).

## Development Workflow

1. **Local Development**: Run backend and frontend separately for hot reload
   ```bash
   # Terminal 1: backend
   cd backend && uvicorn server:app --host 0.0.0.0 --port 8001 --reload
   
   # Terminal 2: frontend  
   cd frontend && yarn start
   ```

2. **Testing**: Backend tests require a running server (default `https://keda-dashboard.preview.emergentagent.com`). Update `KEDADashboardTester.base_url` in `backend_test.py` for local testing.

3. **Database Changes**: Modify SQLAlchemy models in `server.py`, then restart backend. Tables are auto-created on startup via `Base.metadata.create_all`.

4. **Adding New Scaler Types**: The system supports arbitrary scaler types. Frontend displays scaler types from `/api/scaler-types` endpoint.

5. **Styling Changes**: Update `design_guidelines.json` and ensure Tailwind classes match. Use Shadcn/ui components with overridden styles.

## Deployment Considerations

- **Production Database**: Change `DATABASE_URL` to PostgreSQL or other supported SQLAlchemy database
- **Kubernetes Mode**: Set `K8S_MODE=in-cluster` and ensure service account has proper RBAC permissions
- **CORS**: Configure `CORS_ORIGINS` with production frontend URLs
- **Security**: Change default JWT secret and admin credentials
- **Health Checks**: Docker healthcheck runs every 30s on `/api/health`

## Common Issues & Solutions

- **Backend fails to start**: Check SQLite database file permissions in `backend/keda_dashboard.db`
- **Frontend can't connect to backend**: Ensure CORS origins include frontend URL (default `http://localhost:3000`)
- **Kubernetes connection fails**: Verify kubeconfig or service account credentials when using `in-cluster` mode
- **Authentication errors**: Verify JWT_SECRET matches between backend restarts