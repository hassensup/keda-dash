# KEDA Dashboard - PRD

## Problem Statement
Interface graphique pour KEDA permettant :
- Afficher et modifier tous les ScaledObjects
- Calendrier interactif pour les scalers cron avec gestion des events
- Application monolithique en Docker, deploiement via Helm chart
- Authentification login/password (JWT)

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + SQLAlchemy (SQLite dev / PostgreSQL prod)
- **Auth**: JWT custom (bcrypt password hashing)
- **K8s Access**: Mock mode (dev) / In-cluster (prod)
- **Deployment**: Dockerfile monolithique + Helm chart avec PostgreSQL

## User Personas
- **Platform Engineer**: Manages KEDA ScaledObjects across namespaces
- **DevOps**: Schedules cron-based autoscaling events
- **Admin**: Manages user access and configurations

## Core Requirements
- [x] Login/logout with JWT authentication
- [x] Dashboard with ScaledObjects table (filter by namespace, type, search)
- [x] CRUD operations on ScaledObjects (create, read, update, delete)
- [x] Support for all KEDA scaler types (cron, prometheus, kafka, rabbitmq, cpu, memory, redis, postgresql, mysql, external)
- [x] Cron Calendar with monthly view and event management
- [x] Add/edit/delete cron events via interactive dialogs
- [x] Sidebar navigation
- [x] Helm chart with PostgreSQL, RBAC, ServiceAccount, Ingress, ConfigMap, Secret
- [x] Dockerfile for monolithic deployment

## What's Been Implemented (2026-04-16)
- Full backend API with SQLAlchemy ORM (6 ScaledObjects + 4 cron events seeded)
- JWT authentication with admin seeding
- React frontend with professional enterprise design (IBM Plex Sans, slate tones)
- Dashboard with table, filters, search, CRUD
- ScaledObject detail editor with tabs (General, Scaling, Triggers)
- Dynamic trigger configuration per scaler type
- Cron Calendar with monthly grid view and event management
- Complete Helm chart with PostgreSQL StatefulSet, RBAC, Ingress

## Prioritized Backlog
### P0
- (done) All core features implemented

### P1
- Real Kubernetes API integration (in-cluster mode)
- User management (register, role-based access)
- Password reset functionality

### P2
- YAML editor for ScaledObjects
- Metrics/monitoring integration (Prometheus)
- Multi-cluster support
- Audit logging
- Dark mode theme

## Next Tasks
1. Connect to real Kubernetes cluster API for ScaledObject management
2. Add user registration and role-based access control
3. YAML editor view for advanced ScaledObject configuration
4. Metrics dashboard with Recharts
