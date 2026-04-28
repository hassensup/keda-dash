# Implementation Plan: Okta Authentication and RBAC

## Overview

This implementation plan breaks down the Okta authentication and RBAC feature into discrete, actionable coding tasks. The implementation follows a phased approach: database schema changes, backend authentication and authorization, frontend UI updates, testing, and DevOps configuration. Each task builds incrementally to ensure the system remains functional throughout development.

## Tasks

- [x] 1. Database schema migrations and ORM model updates
  - [x] 1.1 Create database migration script for users table extensions
    - Add `auth_provider` column (VARCHAR(50), default 'local')
    - Add `okta_subject` column (VARCHAR(255), nullable, indexed)
    - Modify `password_hash` column to be nullable
    - Add index on `okta_subject`
    - Backfill existing users with `auth_provider='local'`
    - _Requirements: 4.5, 4.6, 4.7, 11.5_
  
  - [x] 1.2 Create database migration script for permissions table
    - Create `permissions` table with columns: id, user_id, action, scope, namespace, object_name, created_at, created_by
    - Add foreign key constraint to users table with CASCADE delete
    - Add indexes: idx_user_id, idx_namespace, idx_user_namespace
    - Add unique constraint on (user_id, action, scope, namespace, object_name)
    - _Requirements: 5.5, 5.6, 5.7, 5.8_
  
  - [x] 1.3 Update SQLAlchemy UserModel with new fields
    - Add `auth_provider` field with default 'local'
    - Add `okta_subject` field (nullable, indexed)
    - Change `password_hash` to nullable
    - Add `permissions` relationship to PermissionModel
    - _Requirements: 4.5, 4.6, 4.7_
  
  - [x] 1.4 Create SQLAlchemy PermissionModel
    - Define all columns matching database schema
    - Add relationship back to UserModel
    - Add table constraints and indexes
    - _Requirements: 5.5, 5.6, 5.7, 5.8_
  
  - [x] 1.5 Create Pydantic schemas for permissions
    - Create `PermissionAction` enum (READ, WRITE)
    - Create `PermissionScope` enum (NAMESPACE, OBJECT)
    - Create `Permission` schema
    - Create `PermissionCreate` schema with validation
    - Create `UserWithPermissions` schema
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [ ]* 1.6 Write unit tests for permission schema validation
    - Test object scope requires object_name
    - Test namespace scope rejects object_name
    - Test enum validation
    - _Requirements: 5.5, 5.6_

- [ ] 2. Checkpoint - Verify database migrations
  - Run migrations in development environment
  - Verify existing users still authenticate
  - Ensure all tests pass, ask the user if questions arise

- [ ] 3. Backend authentication infrastructure
  - [x] 3.1 Create configuration module for authentication settings
    - Load Okta configuration from environment variables (OKTA_DOMAIN, OKTA_CLIENT_ID, OKTA_CLIENT_SECRET, OKTA_REDIRECT_URI)
    - Load feature flags (OKTA_ENABLED, LOCAL_AUTH_ENABLED)
    - Validate required configuration when Okta is enabled
    - Create `OktaConfig` and `AuthConfig` Pydantic models
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_
  
  - [x] 3.2 Implement LocalAuthHandler class
    - Implement `authenticate(email, password)` method
    - Implement `create_user(email, password, name)` method
    - Implement `hash_password(password)` using bcrypt
    - Implement `verify_password(plain, hashed)` using bcrypt
    - Update JWT token generation to include auth_provider
    - _Requirements: 1.1, 1.3, 1.6, 11.1, 11.2_
  
  - [ ]* 3.3 Write unit tests for LocalAuthHandler
    - Test password hashing and verification
    - Test authentication with valid credentials
    - Test authentication with invalid credentials
    - Test JWT token generation
    - _Requirements: 1.3, 1.6_
  
  - [x] 3.4 Implement OktaAuthHandler class
    - Implement `get_authorization_url(state)` method
    - Implement `exchange_code_for_tokens(code)` method using OAuth2
    - Implement `validate_id_token(id_token)` with JWKS verification
    - Implement `get_user_info(access_token)` method
    - Implement `sync_user_profile(okta_claims)` method
    - Handle token refresh logic
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_
  
  - [ ]* 3.5 Write property test for Okta profile synchronization
    - **Property 9: Okta Profile Synchronization Correctness**
    - **Validates: Requirements 1.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7**
    - Generate random Okta ID token claims
    - Verify user profile has correct email, name, auth_provider='okta', okta_subject, and no password_hash
  
  - [ ]* 3.6 Write unit tests for OktaAuthHandler
    - Test authorization URL generation
    - Test token exchange (mocked Okta API)
    - Test ID token validation (mocked JWKS)
    - Test user profile synchronization
    - Test error handling for invalid tokens
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [ ] 4. Backend authentication router and endpoints
  - [x] 4.1 Create authentication router module
    - Create FastAPI router with `/api/auth` prefix
    - Set up dependency injection for auth handlers
    - _Requirements: 1.1, 1.2_
  
  - [x] 4.2 Implement local login endpoint (POST /api/auth/login)
    - Accept email and password
    - Call LocalAuthHandler.authenticate()
    - Generate JWT token with user ID, email, and permissions
    - Set httpOnly cookie and return token in response
    - _Requirements: 1.1, 1.3, 1.6, 1.7, 11.2, 11.3_
  
  - [x] 4.3 Implement Okta login initiation endpoint (GET /api/auth/okta/login)
    - Generate secure random state parameter
    - Store state in session/cache
    - Return redirect URL to Okta authorization endpoint
    - _Requirements: 1.2, 1.4, 2.1, 2.3_
  
  - [x] 4.4 Implement Okta callback endpoint (GET /api/auth/okta/callback)
    - Validate state parameter
    - Exchange authorization code for tokens
    - Validate ID token
    - Sync user profile to database
    - Generate JWT token with user ID, email, and permissions
    - Set httpOnly cookie and return token in response
    - _Requirements: 1.4, 1.5, 1.6, 1.7, 2.4, 2.5, 2.6, 4.1, 4.2_
  
  - [x] 4.5 Implement auth configuration endpoint (GET /api/auth/config)
    - Return `okta_enabled` and `local_auth_enabled` flags
    - _Requirements: 3.5, 3.6, 9.7_
  
  - [x] 4.6 Update existing /api/auth/me endpoint
    - Include user permissions in response
    - _Requirements: 1.7, 10.5_
  
  - [x] 4.7 Update JWT token generation to include permissions
    - Add permissions array to JWT payload
    - _Requirements: 1.7_
  
  - [ ]* 4.8 Write property test for JWT token round-trip preservation
    - **Property 1: JWT Token Round-Trip Preservation**
    - **Validates: Requirements 1.6, 2.5, 2.6**
    - Generate random user profiles with permissions
    - Encode to JWT and decode back
    - Verify user identity and permissions are preserved
  
  - [ ]* 4.9 Write property test for JWT token contains permissions
    - **Property 2: JWT Token Contains User Permissions**
    - **Validates: Requirements 1.7**
    - Generate random users with non-empty permission sets
    - Encode to JWT
    - Verify all permissions are in token payload
  
  - [ ]* 4.10 Write integration tests for authentication flows
    - Test local login end-to-end
    - Test Okta login flow (mocked)
    - Test logout
    - Test token refresh
    - _Requirements: 1.1, 1.2, 1.4, 14.1, 14.2, 14.3, 14.4, 14.7_

- [x] 5. Checkpoint - Verify authentication endpoints
  - Test local login with existing users
  - Test auth config endpoint returns correct flags
  - Ensure all tests pass, ask the user if questions arise

- [ ] 6. Backend RBAC engine implementation
  - [x] 6.1 Create RBACEngine class
    - Implement `check_permission(user_id, action, resource_type, namespace, object_name)` method
    - Implement admin role bypass logic
    - Implement namespace-scoped permission evaluation
    - Implement object-scoped permission evaluation
    - Implement default deny logic
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_
  
  - [x] 6.2 Implement permission filtering method
    - Implement `filter_objects_by_permission(user_id, objects, action)` method
    - Filter ScaledObjects list based on user permissions
    - _Requirements: 6.1_
  
  - [x] 6.3 Implement permission management methods
    - Implement `get_user_permissions(user_id)` method
    - Implement `grant_permission(user_id, action, scope, namespace, object_name)` method
    - Implement `revoke_permission(permission_id)` method
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [ ]* 6.4 Write property test for permission filtering correctness
    - **Property 3: Permission Filtering Correctness**
    - **Validates: Requirements 6.1**
    - Generate random ScaledObjects and user permissions
    - Filter objects by user permissions
    - Verify only objects with read or write permission are returned
  
  - [ ]* 6.5 Write property test for read permission check correctness
    - **Property 4: Read Permission Check Correctness**
    - **Validates: Requirements 6.2, 7.1, 7.2, 7.7**
    - Generate random ScaledObjects and user permissions
    - Check read access for each object
    - Verify access granted only when user has admin role, object-scoped read/write, or namespace-scoped read/write
  
  - [ ]* 6.6 Write property test for write permission check correctness
    - **Property 5: Write Permission Check Correctness**
    - **Validates: Requirements 6.4, 6.5, 7.3, 7.4**
    - Generate random ScaledObjects and user permissions
    - Check write access for each object
    - Verify access granted only when user has admin role, object-scoped write, or namespace-scoped write
  
  - [ ]* 6.7 Write property test for namespace write permission check correctness
    - **Property 6: Namespace Write Permission Check Correctness**
    - **Validates: Requirements 6.3, 7.5**
    - Generate random namespaces and user permissions
    - Check write access for namespace-level operations
    - Verify access granted only when user has admin role or namespace-scoped write permission
  
  - [ ]* 6.8 Write property test for default deny rule
    - **Property 7: Default Deny Rule**
    - **Validates: Requirements 7.6**
    - Generate random resources and users without matching permissions
    - Verify access is denied for all resources
  
  - [ ]* 6.9 Write property test for admin bypass rule
    - **Property 8: Admin Bypass Rule**
    - **Validates: Requirements 7.7**
    - Generate random resources and admin users
    - Verify access is granted for all resources regardless of explicit permissions
  
  - [ ]* 6.10 Write unit tests for RBAC engine
    - Test specific permission scenarios
    - Test edge cases (empty permissions, null values)
    - Test error conditions
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

- [ ] 7. Backend permission middleware
  - [x] 7.1 Create permission middleware module
    - Implement `get_current_user_with_permissions(request)` dependency
    - Extract JWT token from request
    - Decode token and load user permissions
    - _Requirements: 1.6, 1.7_
  
  - [x] 7.2 Create permission decorator
    - Implement `require_permission(action, resource_type, namespace_param, object_param)` decorator
    - Extract namespace and object name from route parameters
    - Call RBACEngine.check_permission()
    - Raise 403 Forbidden if permission denied
    - _Requirements: 6.6_
  
  - [ ]* 7.3 Write unit tests for permission middleware
    - Test token extraction and validation
    - Test permission decorator with various scenarios
    - Test 403 error responses
    - _Requirements: 6.6_

- [ ] 8. Backend API endpoint updates with permission checks
  - [x] 8.1 Update GET /api/scaled-objects endpoint
    - Add permission filtering using RBACEngine.filter_objects_by_permission()
    - Return only objects user has read permission for
    - _Requirements: 6.1_
  
  - [x] 8.2 Update GET /api/scaled-objects/{id} endpoint
    - Add @require_permission decorator for read access
    - _Requirements: 6.2_
  
  - [x] 8.3 Update POST /api/scaled-objects endpoint
    - Add @require_permission decorator for namespace write access
    - _Requirements: 6.3_
  
  - [x] 8.4 Update PUT /api/scaled-objects/{id} endpoint
    - Add @require_permission decorator for write access
    - _Requirements: 6.4_
  
  - [x] 8.5 Update DELETE /api/scaled-objects/{id} endpoint
    - Add @require_permission decorator for write access
    - _Requirements: 6.5_
  
  - [ ]* 8.6 Write integration tests for permission enforcement
    - Test list filtering with various permission sets
    - Test read access with and without permissions
    - Test write access with and without permissions
    - Test 403 responses for unauthorized actions
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ] 9. Backend permission management API
  - [x] 9.1 Create permission management router
    - Create FastAPI router with `/api/permissions` prefix
    - Require admin role for all endpoints
    - _Requirements: 8.7_
  
  - [x] 9.2 Implement GET /api/permissions/users endpoint
    - List all users with their permission counts
    - _Requirements: 8.4_
  
  - [x] 9.3 Implement GET /api/permissions/users/{user_id} endpoint
    - Get all permissions for a specific user
    - _Requirements: 8.1_
  
  - [x] 9.4 Implement POST /api/permissions endpoint
    - Create new permission for a user
    - Validate namespace exists
    - Validate object exists (for object-scoped permissions)
    - _Requirements: 8.2, 8.5, 8.6_
  
  - [x] 9.5 Implement DELETE /api/permissions/{permission_id} endpoint
    - Delete a permission
    - _Requirements: 8.3_
  
  - [ ]* 9.6 Write unit tests for permission management API
    - Test permission creation with validation
    - Test permission deletion
    - Test admin-only access enforcement
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

- [ ] 10. Checkpoint - Verify backend RBAC implementation
  - Test permission checks on all endpoints
  - Test permission management API
  - Verify admin bypass works
  - Ensure all tests pass, ask the user if questions arise

- [ ] 11. Backend audit logging
  - [ ] 11.1 Create audit logging module
    - Define structured log format (JSON)
    - Create logging functions for auth events, permission checks, permission changes
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7_
  
  - [ ] 11.2 Add audit logging to authentication endpoints
    - Log successful authentication with user, provider, timestamp
    - Log failed authentication with email, reason
    - Log Okta token validation failures
    - _Requirements: 13.1, 13.2, 13.5_
  
  - [ ] 11.3 Add audit logging to RBAC engine
    - Log permission denials with user, resource, required permission
    - _Requirements: 13.3_
  
  - [ ] 11.4 Add audit logging to permission management
    - Log permission grants and revocations with admin user, target user, permission details
    - _Requirements: 13.4_
  
  - [ ]* 11.5 Write unit tests for audit logging
    - Test log format and content
    - Test sensitive data is not logged
    - _Requirements: 13.7_

- [ ] 12. Frontend authentication UI updates
  - [ ] 12.1 Update AuthContext to fetch and store permissions
    - Add `permissions` state
    - Update `checkAuth()` to fetch permissions from /api/auth/me
    - Add `hasPermission(action, namespace, objectName)` helper method
    - Update login methods to fetch permissions
    - _Requirements: 1.7, 10.5, 10.6_
  
  - [ ] 12.2 Update AuthContext to support Okta login
    - Add `loginWithOkta()` method that redirects to /api/auth/okta/login
    - Handle Okta callback on return
    - _Requirements: 1.2, 1.4, 9.3_
  
  - [ ] 12.3 Update LoginPage to fetch auth configuration
    - Fetch /api/auth/config on component mount
    - Store `oktaEnabled` in component state
    - _Requirements: 9.7_
  
  - [ ] 12.4 Update LoginPage to display Okta button
    - Conditionally render "Sign in with Okta" button when `oktaEnabled` is true
    - Style button to match design system
    - Wire button to AuthContext.loginWithOkta()
    - _Requirements: 9.1, 9.2, 9.3_
  
  - [ ] 12.5 Update LoginPage error handling
    - Display authentication errors from both providers
    - _Requirements: 9.5_
  
  - [ ]* 12.6 Write unit tests for AuthContext
    - Test permission loading
    - Test hasPermission() logic
    - Test Okta login flow
    - _Requirements: 1.7, 10.5_
  
  - [ ]* 12.7 Write unit tests for LoginPage
    - Test Okta button visibility based on config
    - Test form submission
    - Test error display
    - _Requirements: 9.1, 9.2, 9.3, 9.5, 9.7_

- [ ] 13. Frontend permission-aware UI components
  - [ ] 13.1 Create PermissionGate component
    - Accept props: action, namespace, objectName, children, fallback
    - Use AuthContext.hasPermission() to check permission
    - Conditionally render children or fallback
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  
  - [ ] 13.2 Update ScaledObject list page with permission filtering
    - Wrap create button in PermissionGate with write permission for namespace
    - Wrap edit/delete buttons in PermissionGate with write permission for object
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  
  - [ ] 13.3 Update ScaledObject detail page with permission checks
    - Wrap edit button in PermissionGate with write permission
    - Wrap delete button in PermissionGate with write permission
    - _Requirements: 10.1, 10.2_
  
  - [ ] 13.4 Add permission denied error handling
    - Display user-friendly message when 403 error received
    - _Requirements: 10.7_
  
  - [ ]* 13.5 Write unit tests for PermissionGate
    - Test conditional rendering based on permissions
    - Test fallback rendering
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  
  - [ ]* 13.6 Write integration tests for permission-aware UI
    - Test UI visibility with various permission sets
    - Test 403 error handling
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.7_

- [ ] 14. Frontend admin permission management UI
  - [ ] 14.1 Create AdminPermissionsPage component
    - Create page layout with user list and permission detail sections
    - _Requirements: 12.1, 12.2_
  
  - [ ] 14.2 Create UserList component
    - Fetch and display all users from /api/permissions/users
    - Show user email, name, and permission count
    - Handle user selection
    - _Requirements: 12.1_
  
  - [ ] 14.3 Create UserPermissionDetail component
    - Fetch and display permissions for selected user from /api/permissions/users/{user_id}
    - Group permissions by namespace
    - Display action, scope, and object name for each permission
    - _Requirements: 12.2, 12.3_
  
  - [ ] 14.4 Create PermissionForm component
    - Form to add new permission with fields: action, scope, namespace, object_name
    - Validate inputs (object_name required for object scope)
    - Submit to POST /api/permissions
    - _Requirements: 12.4, 12.6_
  
  - [ ] 14.5 Create PermissionList component
    - Display existing permissions with delete button
    - Call DELETE /api/permissions/{permission_id} on delete
    - _Requirements: 12.5_
  
  - [ ] 14.6 Add admin-only route protection
    - Wrap AdminPermissionsPage route with admin role check
    - _Requirements: 12.7_
  
  - [ ]* 14.7 Write unit tests for admin UI components
    - Test user list rendering
    - Test permission form validation
    - Test permission deletion
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 15. Checkpoint - Verify frontend implementation
  - Test login page with Okta button
  - Test permission-aware UI elements
  - Test admin permission management page
  - Ensure all tests pass, ask the user if questions arise

- [ ] 16. DevOps configuration and deployment preparation
  - [ ] 16.1 Update environment variable documentation
    - Document all new environment variables (OKTA_DOMAIN, OKTA_CLIENT_ID, OKTA_CLIENT_SECRET, OKTA_REDIRECT_URI, OKTA_ENABLED, LOCAL_AUTH_ENABLED)
    - Document default values and required vs optional
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_
  
  - [ ] 16.2 Update Helm chart values.yaml
    - Add Okta configuration parameters
    - Add feature flag parameters
    - Set secure defaults (Okta disabled by default)
    - _Requirements: 3.5, 3.6_
  
  - [ ] 16.3 Update Helm chart secret template
    - Add Okta client secret to secret template
    - _Requirements: 3.3_
  
  - [ ] 16.4 Update Helm chart configmap template
    - Add Okta domain, client ID, redirect URI to configmap
    - Add feature flags to configmap
    - _Requirements: 3.1, 3.2, 3.4, 3.5, 3.6_
  
  - [ ] 16.5 Update Helm chart deployment template
    - Mount new environment variables from configmap and secret
    - _Requirements: 3.7_
  
  - [ ] 16.6 Create database migration runbook
    - Document migration steps
    - Document rollback procedure
    - Document validation steps
    - _Requirements: 11.5_

- [ ] 17. Documentation
  - [ ] 17.1 Create Okta setup guide
    - Document how to create Okta application
    - Document required Okta configuration
    - Document how to assign users/groups
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [ ] 17.2 Create permission model documentation
    - Document permission actions and scopes
    - Document permission evaluation logic
    - Provide examples of common permission patterns
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_
  
  - [ ] 17.3 Create admin guide for permission management
    - Document how to grant and revoke permissions
    - Document how to use admin UI
    - Document how to use API endpoints
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  
  - [ ] 17.4 Update API documentation
    - Document new authentication endpoints
    - Document new permission management endpoints
    - Document updated ScaledObject endpoints with permission requirements
    - _Requirements: 1.1, 1.2, 1.4, 8.1, 8.2, 8.3, 8.4_
  
  - [ ] 17.5 Create troubleshooting guide
    - Document common authentication issues
    - Document common permission issues
    - Document how to check audit logs
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7_
  
  - [ ] 17.6 Update README with feature overview
    - Document dual authentication support
    - Document RBAC feature
    - Link to detailed guides
    - _Requirements: 1.1, 1.2, 5.1, 5.2_

- [ ] 18. Final integration and validation
  - [ ] 18.1 Run full test suite
    - Run all unit tests
    - Run all property-based tests
    - Run all integration tests
    - Verify 100% pass rate
  
  - [ ] 18.2 Perform end-to-end testing
    - Test local authentication flow
    - Test Okta authentication flow (with real Okta dev account)
    - Test permission enforcement on all endpoints
    - Test admin permission management
    - Test account linking for existing users
    - _Requirements: 1.1, 1.2, 1.4, 6.1, 6.2, 6.3, 6.4, 6.5, 8.1, 8.2, 8.3, 15.1, 15.2, 15.3_
  
  - [ ] 18.3 Verify backward compatibility
    - Test existing users can still log in with local credentials
    - Test existing API calls work unchanged
    - Test existing JWT tokens remain valid
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.6, 11.7_
  
  - [ ] 18.4 Perform security review
    - Review password storage (bcrypt)
    - Review JWT token security
    - Review Okta token validation
    - Review permission checks on all endpoints
    - Review audit logging for sensitive data
    - _Requirements: 13.7_
  
  - [ ] 18.5 Prepare deployment checklist
    - List all deployment steps
    - List all validation steps
    - List rollback procedure
    - _Requirements: 11.5_

- [ ] 19. Final checkpoint - Ready for deployment
  - All tests passing
  - Documentation complete
  - Deployment artifacts ready
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Property-based tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows and external service integration
- Checkpoints ensure incremental validation throughout implementation
- The implementation maintains backward compatibility with existing authentication
- Okta authentication is disabled by default and must be explicitly enabled
- Admin users bypass all permission checks via role-based logic
