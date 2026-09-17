# NexaWork

**Connect. Collaborate. Work Smarter.**

NexaWork is a scalable **Workplace Communication & Collaboration Platform** designed to give organizations a centralized digital workplace for communication, collaboration, meetings, file sharing, workplace information, and AI-assisted productivity.

NexaWork is being built as a **secure modular monolith** for the initial MVP, with clear boundaries that allow individual modules to scale or evolve independently as the platform grows.

---

## Vision

NexaWork is more than a chat application.

The platform is designed to connect employees, managers, employers, and administrators across multiple:

* Organizations
* Regions
* Branches
* Departments
* Teams

Users will be able to communicate, collaborate, attend meetings, share files, receive announcements, search authorized workplace information, and interact with the **NexaWork Assistant**.

---

## Core Features

Planned capabilities include:

* Employee and administrator authentication
* Multi-tenant organizations
* Regions, branches, departments, and teams
* Role-Based Access Control (RBAC)
* Personalized employee dashboards
* Employee profiles and profile pictures
* Direct and group messaging
* Workplace channels
* Real-time communication with WebSockets
* Online/offline presence
* Audio/video meetings with WebRTC
* Meeting participant management
* Meeting chat
* Workplace announcements
* Notifications
* Secure file sharing
* Authorization-aware global search
* NexaWork AI Assistant
* Administrative dashboard
* Audit logging

---

## Technology Stack

### Backend

* **Python**
* **FastAPI**
* **Pydantic / Pydantic Settings**

### Database

* **PostgreSQL**
* **SQLAlchemy 2.x**
* **Alembic**

### Real-Time

* **FastAPI WebSockets**
* **Redis**

### Audio/Video

* **WebRTC**
* SFU infrastructure such as LiveKit, mediasoup, or Janus

### Frontend

* **React**
* **Next.js**

### Infrastructure

* Docker
* Docker Compose
* Object storage (S3-compatible)
* Redis
* PostgreSQL

---

## Architecture

NexaWork follows a modular architecture with clear separation of concerns:

```text
Frontend
   │
   ▼
FastAPI API
   │
   ├── Authentication
   ├── Organizations
   ├── Employees
   ├── Messaging
   ├── Channels
   ├── Meetings
   ├── Notifications
   ├── Files
   ├── AI
   ├── Search
   └── Administration
   │
   ▼
Services
   │
   ▼
Data Access
   │
   ▼
PostgreSQL
```

Real-time functionality will use WebSockets and Redis where distributed coordination is required.

Audio/video media will use WebRTC and dedicated media infrastructure rather than routing media traffic through ordinary REST APIs.

External providers such as AI, storage, email, and media services will be accessed through abstractions where appropriate.

---

## Security

Security is a first-class requirement.

NexaWork is designed around:

* Secure password hashing
* Authentication and authorization
* Role-Based Access Control
* Multi-tenant isolation
* Backend-enforced permissions
* Secure file access
* WebSocket authentication
* Rate limiting and brute-force protection
* Environment-based secrets
* Input validation
* Audit logging
* Secure API design

Users must never gain access to resources simply by manipulating IDs or frontend requests.

---

## Development Roadmap

NexaWork is being developed incrementally.

### Phase 1 — Foundation

**Current phase**

* FastAPI foundation
* PostgreSQL
* SQLAlchemy
* Alembic
* Authentication
* Users
* Organizations
* Regions
* Branches
* Departments
* Employees
* RBAC
* Multi-tenancy

### Phase 2 — Communication

* Direct messaging
* Group messaging
* Channels
* WebSockets
* Presence
* Notifications

### Phase 3 — Meetings

* Meeting creation
* Scheduling
* WebRTC
* Audio/video
* Participant management
* Participant removal/blocking
* Meeting chat

### Phase 4 — AI

* NexaWork Assistant
* AI conversations
* Knowledge sources
* Permission-aware retrieval
* AI provider abstraction

### Phase 5 — Files & Search

* File uploads
* Profile-picture uploads
* Secure storage
* File permissions
* Global search

### Phase 6 — Administration

* Admin dashboard
* Employee management
* Branch management
* Department management
* Permissions
* Announcements
* Audit logs
* Analytics

### Phase 7 — Hardening

* Security improvements
* Comprehensive testing
* Performance optimization
* Monitoring
* Deployment
* Production readiness

---

## Current Progress

**Status:** Active Development

**Current Phase:** Phase 1 — Foundation

Completed foundation work includes:

* FastAPI application setup
* Configuration management
* PostgreSQL integration
* SQLAlchemy ORM
* Alembic migrations
* User model
* Argon2 password hashing
* User registration
* User login
* JWT authentication
* Protected routes
* Database-backed authentication
* Authenticated user profile endpoint

The next major foundation work is focused on **organizations, multi-tenancy, employees, administrators, roles, and permissions**.

---

## Development Principles

NexaWork is being built with the following principles:

* Keep modules clearly separated
* Keep route handlers thin
* Keep business logic in services
* Keep database access appropriately separated
* Validate external input
* Never trust the frontend
* Enforce authorization on the backend
* Protect tenant boundaries
* Avoid unnecessary microservices
* Abstract external providers
* Write meaningful tests
* Keep the application extensible
* Commit meaningful milestones to Git

---

## Project Status

NexaWork is an **active development project**.

The MVP is being built incrementally, with each major milestone implemented, tested, verified, and committed to version control before moving to the next stage.

---

**NexaWork**

*Connect. Collaborate. Work Smarter.*
