# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-27

### Added
- **Scaling Behavior Configuration**: Optional advanced scaling policies for scale-up and scale-down
  - Stabilization window configuration
  - Select policy (Max, Min, Disabled)
  - Multiple scaling policies per direction (Percent or Pods based)
  - Independent configuration for scale-up and scale-down
- **Namespace Filter**: Namespace selector now uses dropdown with available namespaces
- **Deployment Filter**: Target deployment selector with automatic filtering by namespace
- **Trigger Type Selector**: Dropdown to select trigger type before adding (cron, prometheus, rabbitmq, kafka, cpu, memory, redis, postgresql, mysql, external)
- **Database Migration System**: Automatic migration on startup with manual migration scripts available
- **API Endpoint**: `/api/deployments` to list available deployments (with optional namespace filter)

### Changed
- Namespace field changed from text input to dropdown selector
- Target deployment field changed from text input to dropdown selector (filtered by namespace)
- Scaling tab reorganized with "Basic Parameters" and "Scaling Behavior" sections
- Chart version bumped to 0.2.0
- App version bumped to 1.1.0

### Fixed
- Trigger type selection bug when creating new ScaledObjects
- Database schema compatibility with PostgreSQL and SQLite

### Technical
- Added `scaling_behavior_json` column to `scaled_objects` table
- Added `list_deployments()` method to K8s service
- Automatic database migration on application startup
- Migration scripts in `backend/migrations/` directory

## [0.1.0] - Initial Release

### Added
- Initial release of KEDA Dashboard
- ScaledObject CRUD operations
- Support for multiple scaler types (cron, prometheus, rabbitmq, kafka, cpu, memory, redis, postgresql, mysql, external)
- Cron calendar view for scheduled scaling events
- Authentication system with JWT
- Mock mode for development without Kubernetes cluster
- In-cluster mode for production Kubernetes deployment
- PostgreSQL and SQLite database support
- Helm chart for Kubernetes deployment
- Docker Compose for local development
