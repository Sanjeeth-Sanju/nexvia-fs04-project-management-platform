
# NEXVIA - Multi-Tenant SaaS Project Management Platform

> **One platform. Multiple workspaces. Secure project collaboration.**

NEXVIA is a full-stack, multi-tenant SaaS project management application designed to help organizations manage their teams, projects, tasks, sprints and workflows through isolated workspaces.

The platform provides a Jira-like project management experience where organizations can collaborate through customizable Kanban boards, issue tracking, sprint planning and workspace-level administration.

Built with React, Django REST Framework and PostgreSQL, NEXVIA combines multi-tenant architecture, role-based authorization, collaboration tools, background processing and subscription billing into a production-deployed application.

**Internship Project:** FS-04 - Multi-Tenant SaaS Project Management Platform  
**Organization:** Nexvia Technologies  
**Intern:** Sanjeeth Balan  
**Internship ID:** NEX-INT-2026-1827

---

# ✨ Features

- 🏢 **Multi-Tenant Workspaces** - Create isolated company workspaces within a shared SaaS application.
- 🔐 **Authentication** - Secure registration, login, JWT authentication, token refresh and session management.
- 👥 **Role-Based Access Control** - Workspace Owner, Admin and Member roles with permission enforcement.
- 📩 **Workspace Invitations** - Invite users, manage invitations, accept invitations and revoke pending invitations.
- 📁 **Project Management** - Create, organize, update and manage projects within workspaces.
- 📋 **Kanban Boards** - Organize tasks through visual workflow columns.
- 🏃 **Sprint Management** - Organize issues into sprints with goals, dates and lifecycle management.
- 📝 **Issue Tracking** - Create, assign, prioritize, update and manage project issues.
- 💬 **Comments** - Collaborate through issue-level discussions.
- 📎 **File Attachments** - Upload and manage files associated with issues.
- 🔔 **Notifications** - Receive updates about relevant workspace and project activities.
- 📜 **Audit Logs** - Maintain workspace-level activity history.
- 💳 **Subscription Billing** - Integrate Stripe checkout, customer portal and webhook processing.
- 📊 **Plan Enforcement** - Enforce subscription-based feature and usage limits through backend logic.
- 👤 **Profile Management** - Manage user profile information and account settings.
- 🔑 **Password Security** - Password-change verification and confirmation workflow.
- 📦 **Data Export** - Export accessible workspace data.
- 🗑️ **Account Management** - Account deletion impact review and confirmation.
- ⚙️ **Background Processing** - Use Celery and Redis for asynchronous background tasks.

---

# 🏛️ Architecture

NEXVIA follows a client-server architecture with a React frontend and a Django REST Framework backend.

The frontend is deployed on Vercel, while the backend API is deployed on Render.

PostgreSQL provides persistent relational storage, and Redis acts as the message broker and result backend for Celery background tasks.

```text
                      ┌──────────────────────┐
                      │        User          │
                      └──────────┬───────────┘
                                 │
                                 ▼
                      ┌──────────────────────┐
                      │     React + Vite     │
                      │                      │
                      │  Authentication      │
                      │  Dashboard           │
                      │  Workspaces          │
                      │  Projects            │
                      │  Kanban Boards       │
                      │  Sprints             │
                      │  Issues              │
                      │  Notifications       │
                      │  Billing             │
                      └──────────┬───────────┘
                                 │
                         REST API Requests
                                 │
                                 ▼
                  ┌─────────────────────────────┐
                  │       Django REST API       │
                  │                             │
                  │    JWT Authentication       │
                  │    Authorization            │
                  │    Tenant Isolation         │
                  │    Workspace Management     │
                  │    Project Management       │
                  │    Issue Management         │
                  │    Workflow Management      │
                  │    Billing Integration      │
                  └──────┬──────────┬───────────┘
                         │          │
                         ▼          ▼
                ┌─────────────┐  ┌──────────────┐
                │ PostgreSQL  │  │    Celery    │
                │             │  │              │
                │ Users       │  │ Background   │
                │ Workspaces  │  │ Tasks        │
                │ Projects    │  └──────┬───────┘
                │ Boards      │         │
                │ Sprints     │         ▼
                │ Issues      │  ┌──────────────┐
                │ Memberships │  │    Redis     │
                │ Audit Logs  │  │              │
                │ Billing     │  │ Task Broker  │
                └─────────────┘  └──────────────┘

                         │
                         ▼
                  ┌──────────────┐
                  │ Stripe API   │
                  │              │
                  │ Checkout     │
                  │ Customer     │
                  │ Portal       │
                  │ Webhooks     │
                  └──────────────┘
```

## ☁️ Production Infrastructure

```text
                 ┌──────────────────────┐
                 │      GitHub          │
                 │   Source Repository  │
                 └──────────┬───────────┘
                            │
                 ┌──────────┴───────────┐
                 │                      │
                 ▼                      ▼
        ┌─────────────────┐   ┌──────────────────┐
        │     Vercel      │   │      Render      │
        │                 │   │                  │
        │  React + Vite   │   │  Django REST API │
        │  Frontend       │   │  Docker          │
        └────────┬────────┘   └────────┬─────────┘
                 │                     │
                 │ API Requests        ├──────────────┐
                 │                     │              │
                 └─────────────────────┤              │
                                       ▼              ▼
                                ┌────────────┐  ┌───────────┐
                                │ PostgreSQL │  │   Redis   │
                                │            │  │           │
                                │ Database   │  │   Celery  │
                                └────────────┘  └───────────┘
```

---

# 🏢 Multi-Tenant Architecture

NEXVIA uses a workspace-based multi-tenant architecture.

Each workspace represents an organization and acts as the primary tenant boundary.

Multiple organizations can use the same application infrastructure while maintaining logically isolated workspace data.

## Workspace Membership

Users can belong to multiple workspaces.

Each workspace membership has an associated role:

| Role | Responsibilities |
|---|---|
| Owner | Workspace ownership and administrative privileges |
| Admin | Workspace administration and management |
| Member | Access to assigned projects and collaboration features |

## Project-Level Access

In addition to workspace roles, NEXVIA supports project-level member assignments.

Workspace owners and administrators can access projects within their workspace according to their permissions.

Members are restricted to projects assigned to them through project membership.

## Tenant Isolation

Tenant isolation is enforced at the backend level.

The application uses:

- Authenticated user identity.
- Workspace membership relationships.
- Project membership relationships.
- Permission checks.
- Membership-aware querysets.
- Serializer validation of related resources.

The backend does not rely solely on frontend visibility restrictions to protect tenant data.

---

# 🔐 Authentication & Authorization

NEXVIA uses Django REST Framework with Simple JWT authentication.

The authentication system supports:

- User registration.
- User login.
- Access token generation.
- Refresh token rotation.
- Token invalidation during logout.
- Authenticated user profile retrieval.
- Protected API operations.

The configured JWT lifetimes are:

| Token | Lifetime |
|---|---|
| Access Token | 5 minutes |
| Refresh Token | 7 days |

Refresh token rotation and blacklist-after-rotation are enabled.

Authenticated API requests use:

```http
Authorization: Bearer <access_token>
```

The frontend API service also handles CSRF initialization, automatic token refreshing and session expiration.

## Authorization Flow

```text
             User Request
                  │
                  ▼
          JWT Authentication
                  │
                  ▼
        Identify Authenticated User
                  │
                  ▼
         Workspace Membership
                  │
                  ▼
         Check Assigned Role
                  │
                  ▼
          Project Permission
                  │
                  ▼
         Resource Validation
                  │
             ┌────┴────┐
             │         │
             ▼         ▼
           Allow     Reject
```

---

# 📋 Project Management

Projects belong to individual workspaces.

The project management module supports:

- Project creation.
- Project listing.
- Project updates.
- Project deletion.
- Project membership assignments.
- Project lifecycle management.
- Project completion tracking.

Completed projects have lifecycle safeguards to prevent inappropriate modifications.

## Kanban Board

The Kanban board provides a visual representation of project work.

Issues are organized into workflow columns and can be moved between statuses.

```text
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    TO DO     │  │ IN PROGRESS  │  │     DONE     │
├──────────────┤  ├──────────────┤  ├──────────────┤
│              │  │              │  │              │
│   Issue 01   │  │   Issue 03   │  │   Issue 05   │
│              │  │              │  │              │
│   Issue 02   │  │   Issue 04   │  │              │
│              │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

The default workflow statuses are created for new workspaces.


## Sprint Management

Sprints provide a way to organize project issues into development cycles.

Each sprint can include:

- Sprint name.
- Sprint goal.
- Start date.
- End date.
- Sprint status.
- Associated issues.

Issues can be associated with sprints to organize project work.

---

# 📝 Issue Management

Issues represent individual units of work within projects.

The issue management module supports:

- Issue titles and descriptions.
- Issue types.
- Priority levels.
- Workflow status.
- Assignee selection.
- Board positioning.
- Sprint association.
- Issue comments.
- File attachments.

Issue relationships are validated by the backend to ensure that related boards, sprints and project members belong to the appropriate project or workspace context.

---


# 💬 Collaboration & Notifications

NEXVIA includes collaboration features designed to support project teams.

## Issue Comments

Team members can add comments to issues and participate in issue-level discussions.

## File Attachments

Users can upload attachments associated with project issues.

Attachments are managed through backend APIs and stored using Django's media storage configuration.

## Notifications

The notification system supports:

- Notification listing.
- Unread notification counts.
- Marking individual notifications as read.
- Marking all notifications as read.
- Clearing notifications.
- Deleting individual notifications.

## Audit Logs

Workspace-level audit logs maintain records of important actions.

Audit entries include information such as:

- Workspace.
- Actor.
- Action.
- Entity type.
- Entity identifier.
- Additional event details.
- Timestamp.

---

# 💳 Subscription & Billing

NEXVIA integrates Stripe for subscription billing.

The billing module supports:

- Available subscription plans.
- Subscription overview.
- Stripe checkout session creation.
- Stripe customer portal sessions.
- Stripe webhook processing.

Subscription-related feature and usage limits are enforced through backend logic.

Stripe webhook event identifiers are stored to support idempotent event processing.

Billing functionality should be configured using Stripe test credentials during local development.

---

# 📊 Database Architecture

NEXVIA uses PostgreSQL as its relational database.

The backend contains two main Django applications:

- `accounts` - User profiles, password-change challenges and account-related functionality.
- `core` - Workspaces, projects, memberships, boards, sprints, issues, workflows, billing and collaboration.

## Principal Data Models

| Model | Purpose |
|---|---|
| User | Authenticated application user |
| Profile | User profile information |
| PasswordChangeChallenge | Password-change verification state |
| Workspace | Tenant/company boundary |
| WorkspaceMembership | User membership and workspace role |
| Project | Workspace-level project |
| ProjectMembership | Project-level user assignment |
| Board | Project board |
| Sprint | Project development cycle |
| Issue | Individual work item |
| IssueComment | Issue discussion |
| IssueAttachment | Issue file attachment |
| WorkflowStatus | Workspace-specific workflow stage |
| AuditLog | Workspace activity history |
| WorkspaceInvitation | Workspace invitation lifecycle |
| Subscription | User subscription information |
| StripeWebhookEvent | Processed Stripe webhook event |
| Notification | User notification |

## Relationship Overview

```text
User
 │
 ├────────────── Profile
 │
 ├────────────── WorkspaceMembership
 │                       │
 │                       ▼
 │                    Workspace
 │                       │
 │             ┌─────────┼──────────┐
 │             │         │          │
 │             ▼         ▼          ▼
 │          Project   Workflow    Invitation
 │             │      Status
 │       ┌─────┼──────────┐
 │       │     │          │
 │       ▼     ▼          ▼
 │     Board  Sprint     ProjectMembership
 │       │     │
 │       └──┬──┘
 │          ▼
 │         Issue
 │          │
 │      ┌───┴────────┐
 │      │            │
 │      ▼            ▼
 │   Comments    Attachments
 │
 ├────────────── Subscription
 │
 └────────────── Notifications
```

---

# ⚙️ Background Processing

NEXVIA uses Celery for background task execution and Redis as the message broker and result backend.

The backend Celery application is configured in:

```text
backend/config/celery.py
```

Celery tasks are defined in:

```text
backend/core/tasks.py
```

Redis configuration is loaded through:

```env
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
```

The production startup script starts a Celery worker and the Gunicorn application process.

For local development, the Celery worker can be started separately.

---

# 🛡️ Security Design

NEXVIA implements multiple backend security mechanisms.

| Security Area | Implementation |
|---|---|
| Authentication | Django REST Framework JWT |
| Password Hashing | Argon2 preferred password hasher |
| Authorization | Workspace role and project membership checks |
| Tenant Isolation | Membership-aware queryset filtering |
| API Protection | Authenticated DRF endpoints |
| CSRF | CSRF token initialization and validation |
| Token Security | Access/refresh token rotation |
| Billing | Stripe webhook event verification |
| Account Security | Password-change verification workflow |
| Data Access | Backend resource validation |

The application uses backend permission checks and serializer validation to prevent unauthorized access to workspace and project resources.

---

# 🧱 Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 |
| Frontend Build Tool | Vite 8 |
| Routing | React Router 7 |
| Icons | Lucide React |
| Backend Language | Python |
| Backend Framework | Django 6.1 |
| API Framework | Django REST Framework |
| Database | PostgreSQL |
| Database Driver | Psycopg 3 |
| Authentication | Simple JWT |
| Password Hashing | Argon2 |
| Background Processing | Celery |
| Message Broker | Redis |
| Payment Integration | Stripe |
| Email Integration | Resend |
| Application Server | Gunicorn |
| Static File Serving | WhiteNoise |
| Containerization | Docker |
| Frontend Hosting | Vercel |
| Backend Hosting | Render |
| Version Control | Git and GitHub |

---

# 📁 Project Structure

The repository is organized into separate frontend and backend applications.

```text
nexvia-fs04-project-management-platform/
│
├── backend/
│   ├── accounts/
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── csrf.py
│   │   ├── data_export.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── tests.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── celery.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── core/
│   │   ├── migrations/
│   │   ├── billing.py
│   │   ├── billing_views.py
│   │   ├── email_service.py
│   │   ├── models.py
│   │   ├── notification_service.py
│   │   ├── notification_views.py
│   │   ├── permissions.py
│   │   ├── serializers.py
│   │   ├── tasks.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── tests.py
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   └── start.sh
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── context/
│   │   ├── constants/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── styles/
│   │   ├── utils/
│   │   └── main.jsx
│   │
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── vercel.json
│
├── render.yaml
└── README.md
```

---

# 🚀 Local Development Setup

This section explains how to clone, configure, install, run and verify NEXVIA locally.

## 1. Prerequisites

Install the following software before starting.

| Software | Purpose |
|---|---|
| Git | Clone the repository |
| Python 3.14 | Backend runtime |
| Node.js | Frontend runtime |
| npm | Frontend package management |
| PostgreSQL | Relational database |
| Redis | Celery message broker |

Use a Node.js release supported by Vite 8. Node.js 22 LTS is a suitable development choice.

Verify the installations:

```bash
git --version
python3 --version
node --version
npm --version
psql --version
redis-server --version
```

## 2. Clone the Repository

```bash
git clone https://github.com/Sanjeeth-Sanju/nexvia-fs04-project-management-platform.git
```

Navigate into the project:

```bash
cd nexvia-fs04-project-management-platform
```

The repository contains two main application directories:

```text
backend/
frontend/
```

The backend and frontend are installed and started independently.

## 3. PostgreSQL Database Setup

NEXVIA uses PostgreSQL for persistent application data.

Make sure the PostgreSQL service is running.

Create a development database:

```sql
CREATE DATABASE nexvia_fs04;
```

Create a development user:

```sql
CREATE USER nexvia_user WITH PASSWORD 'your_local_password';

GRANT ALL PRIVILEGES ON DATABASE nexvia_fs04 TO nexvia_user;
```

Connect to the database and configure schema privileges:

```sql
\c nexvia_fs04

GRANT ALL ON SCHEMA public TO nexvia_user;
```

The database credentials will be supplied to Django through environment variables.

**Important:** Use your own local database credentials. Never use production credentials in a development environment.

## 4. Backend Setup - Django REST Framework

Navigate to the backend:

```bash
cd backend
```

### Create a Python Virtual Environment

```bash
python3 -m venv .venv
```

Activate the virtual environment.

**macOS / Linux:**

```bash
source .venv/bin/activate
```

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

### Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### Configure Backend Environment Variables

Create a `.env` file inside `backend/`:

```bash
touch .env
```

Add your local configuration:

```env
# Django Configuration
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=replace-with-a-local-development-secret
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
DB_NAME=nexvia_fs04
DB_USER=nexvia_user
DB_PASSWORD=your_local_password
DB_HOST=127.0.0.1
DB_PORT=5432

# Frontend Configuration
FRONTEND_URL=http://localhost:5173

# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# CSRF Configuration
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Celery / Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email Integration
RESEND_API_KEY=
EMAIL_FROM=Nexvia <onboarding@resend.dev>

# Stripe Configuration
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=

STRIPE_PRICE_PRO=
STRIPE_PRICE_BUSINESS=
```

Replace the local database credentials and development secret with your own values.

The backend supports two database configuration approaches.

**Option A - Individual PostgreSQL variables**

```env
DB_NAME=nexvia_fs04
DB_USER=nexvia_user
DB_PASSWORD=your_local_password
DB_HOST=127.0.0.1
DB_PORT=5432
```

**Option B - PostgreSQL connection URL**

```env
DATABASE_URL=postgresql://nexvia_user:your_local_password@127.0.0.1:5432/nexvia_fs04
```

When `DATABASE_URL` is provided, the Django settings use it instead of the individual database variables.

Do not configure both approaches with conflicting database credentials.

### Run Database Migrations

```bash
python manage.py migrate
```

### Create an Administrator Account

```bash
python manage.py createsuperuser
```

Follow the terminal prompts to configure the administrator username, email and password.

### Start the Django Development Server

```bash
python manage.py runserver
```

The backend API will normally be available at:

```text
http://127.0.0.1:8000/
```

The authentication API is available under:

```text
http://127.0.0.1:8000/api/auth/
```

The core application API is available under:

```text
http://127.0.0.1:8000/api/
```

Keep the backend terminal running.

## 5. Redis Setup

NEXVIA uses Redis for Celery background task processing.

Start the local Redis server:

```bash
redis-server
```

Verify that Redis is responding:

```bash
redis-cli ping
```

Expected response:

```text
PONG
```

The default local Redis connection is:

```text
redis://localhost:6379/0
```

## 6. Start the Celery Worker

Open another terminal.

Navigate to the backend:

```bash
cd nexvia-fs04-project-management-platform/backend
```

Activate the Python virtual environment:

```bash
source .venv/bin/activate
```

Start the Celery worker:

```bash
celery -A config worker --loglevel=info
```

Keep this terminal running while testing background tasks.

## 7. Frontend Setup - React + Vite

Open another terminal from the repository root.

Navigate to the frontend:

```bash
cd frontend
```

### Install Frontend Dependencies

```bash
npm ci
```

### Configure Frontend Environment Variables

Create a `.env.local` file inside `frontend/`:

```bash
touch .env.local
```

Add:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

The frontend API service reads this variable to determine the backend API base URL.

When the variable is not provided, the frontend service defaults to:

```text
http://localhost:8000/api
```

Only expose values that are safe to include in browser-side code through `VITE_*` variables.

Never place Django secrets, database passwords, Redis credentials or Stripe secret keys in frontend environment files.

### Start the Frontend Development Server

```bash
npm run dev
```

Vite will start the React application.

The default local development URL is:

```text
http://localhost:5173/
```

Open this URL in your browser.

Make sure the Django backend, PostgreSQL and Redis services are running when testing the complete application.

---

# 🔗 API Structure

The backend exposes REST API endpoints through Django REST Framework.

The primary API prefixes are:

```text
/api/auth/
/api/
```

## Authentication APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/auth/csrf/` | Initialize CSRF protection |
| POST | `/api/auth/register/` | Register a user |
| POST | `/api/auth/login/` | User login |
| POST | `/api/auth/refresh/` | Refresh access token |
| POST | `/api/auth/logout/` | Logout |
| GET | `/api/auth/me/` | Retrieve current user |
| PATCH/PUT | `/api/auth/profile/` | Update profile |
| POST | `/api/auth/password-change/request/` | Request password-change verification |
| POST | `/api/auth/password-change/verify/` | Verify password-change code |
| POST | `/api/auth/password-change/confirm/` | Confirm password change |
| GET | `/api/auth/account-deletion/impact/` | Preview deletion impact |
| POST | `/api/auth/account-deletion/confirm/` | Confirm account deletion |
| GET | `/api/auth/data-export/` | Export accessible workspace data |

## Workspace APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET, POST | `/api/workspaces/` | List and create workspaces |
| DELETE | `/api/workspaces/{id}/` | Delete workspace |
| GET, POST | `/api/workspaces/{id}/members/` | Manage workspace members |
| PATCH | `/api/workspaces/{id}/members/{user_id}/role/` | Change member role |
| DELETE | `/api/workspaces/{id}/members/{user_id}/` | Remove member |
| GET, POST | `/api/workspaces/{id}/invitations/` | Manage invitations |
| POST | `/api/invitations/{token}/accept/` | Accept invitation |
| POST | `/api/invitations/{id}/revoke/` | Revoke invitation |

## Project and Issue APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET, POST | `/api/projects/` | List and create projects |
| PATCH | `/api/projects/{id}/edit/` | Update project |
| PATCH | `/api/projects/{id}/lifecycle/` | Update project lifecycle |
| DELETE | `/api/projects/{id}/` | Delete project |
| GET, POST | `/api/boards/` | List and create boards |
| GET, POST | `/api/sprints/` | List and create sprints |
| GET, PUT/PATCH, DELETE | `/api/sprints/{id}/` | Manage sprint |
| GET, POST | `/api/issues/` | List and create issues |
| GET, PUT/PATCH, DELETE | `/api/issues/{id}/` | Manage issue |
| PATCH | `/api/issues/{id}/move/` | Move issue on board |
| GET, POST | `/api/issues/{id}/comments/` | Manage issue comments |
| GET, POST | `/api/issues/{id}/attachments/` | Manage issue attachments |

## Workflow APIs

```text
/api/workspaces/{workspace_id}/workflow-statuses/
/api/workspaces/{workspace_id}/workflow-statuses/{status_id}/
/api/workspaces/{workspace_id}/workflow-statuses/reorder/
```

## Notifications APIs

```text
/api/notifications/
/api/notifications/unread-count/
/api/notifications/read-all/
/api/notifications/clear-all/
/api/notifications/{notification_id}/read/
/api/notifications/{notification_id}/
```

## Billing APIs

```text
/api/billing/plans/
/api/billing/overview/
/api/billing/checkout/
/api/billing/portal/
/api/billing/webhook/
```

The endpoint inventory should be checked against the current backend URL configuration before treating it as a complete API contract.

---

# 🧪 Testing & Verification

NEXVIA includes automated Django test suites covering important backend functionality.

Testing areas include:

- Workspace creation and access.
- Workspace role permissions.
- Tenant isolation.
- Project-level access restrictions.
- Board and sprint operations.
- Issue management.
- Workflow statuses.
- Invitations.
- Notifications.
- Billing and Stripe webhook handling.
- Authentication.
- Password-change security.
- Account deletion.
- Data export.

## Run Backend Tests

From the repository root:

```bash
cd backend
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Run the full Django test suite:

```bash
python manage.py test
```

For detailed test output:

```bash
python manage.py test --verbosity 2
```

## Frontend Linting

Navigate to the frontend:

```bash
cd frontend
```

Run ESLint:

```bash
npm run lint
```

## Frontend Production Build

```bash
npm run build
```

Vite generates the optimized production build inside:

```text
frontend/dist/
```

To preview the production build locally:

```bash
npm run preview
```

Record the actual results of the final test execution rather than assuming all tests pass.

---

# 🐳 Docker Configuration

The backend includes a Dockerfile:

```text
backend/Dockerfile
```

Build the backend image from the repository root:

```bash
docker build -t nexvia-fs04-backend ./backend
```

Run the container with the appropriate environment variables and database/Redis connectivity configured:

```bash
docker run --env-file backend/.env \
  -p 10000:10000 \
  nexvia-fs04-backend
```

The production startup script:

```text
backend/start.sh
```

performs the following operations:

1. Runs database migrations.
2. Collects static files.
3. Starts a Celery worker.
4. Starts the Gunicorn application server.
5. Handles process cleanup when the container stops.

The container requires access to its configured PostgreSQL and Redis services.

---

# ☁️ Production Deployment

NEXVIA is deployed using Vercel and Render.

## Frontend - Vercel

The React application is hosted on Vercel.

Deployment configuration:

```text
frontend/vercel.json
```

The Vercel configuration handles:

- API request rewrites to the Render backend.
- Media request rewrites to the Render backend.
- React single-page application fallback routing.

API requests use the backend production domain:

```text
https://nexvia-fs04-api.onrender.com
```

## Backend - Render

The Django backend is deployed on Render using Docker.

The repository includes:

```text
render.yaml
backend/Dockerfile
backend/start.sh
```

The Render infrastructure includes:

- Django REST API service.
- PostgreSQL database.
- Redis service.

The backend deployment uses Gunicorn and WhiteNoise.

## Production Environment Configuration

Production environment variables must be configured through Render's environment settings.

Important configuration variables include:

```env
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<protected-secret>

DATABASE_URL=<postgresql-connection-url>

ALLOWED_HOSTS=<backend-hostname>
FRONTEND_URL=<production-frontend-origin>

CORS_ALLOWED_ORIGINS=<production-frontend-origin>
CSRF_TRUSTED_ORIGINS=<production-frontend-origin>

CELERY_BROKER_URL=<redis-connection-url>
CELERY_RESULT_BACKEND=<redis-connection-url>

RESEND_API_KEY=<protected-email-api-key>
EMAIL_FROM=<configured-sender>

STRIPE_SECRET_KEY=<protected-stripe-secret>
STRIPE_PUBLISHABLE_KEY=<stripe-publishable-key>
STRIPE_WEBHOOK_SECRET=<protected-webhook-secret>

STRIPE_PRICE_PRO=<stripe-price-id>
STRIPE_PRICE_BUSINESS=<stripe-price-id>
```

The values above are configuration placeholders, not actual credentials.

Do not publish production environment values.

---

# 🔑 Secrets Management

Sensitive credentials must remain outside the public source repository.

Never commit:

```text
.env
.env.local
Database passwords
Django production secret keys
Redis credentials
Stripe secret keys
Stripe webhook secrets
Resend API keys
```

Use environment variables for local development and protected environment configuration for production.

---

# 🌐 Production Application

**Frontend Application**

https://nexvia-fs04-96400s9a6-sanjeeth-sanjus-projects.vercel.app

**Backend API**

https://nexvia-fs04-api.onrender.com

**GitHub Repository**

https://github.com/Sanjeeth-Sanju/nexvia-fs04-project-management-platform

---

# 📌 Project Scope

This repository contains the completed implementation of FS-04 - Multi-Tenant SaaS Project Management Platform.

The internship portal also listed FS-01 - Multi-Vendor E-Commerce Marketplace. FS-01 was not developed as part of this submission.

This repository therefore documents and delivers the completed FS-04 project only.

---

# 🏁 Conclusion

NEXVIA demonstrates the design, development and deployment of a full-stack multi-tenant SaaS application.

The project combines React frontend development, Django REST API engineering, PostgreSQL data modeling, workspace-based tenant isolation, role-based authorization, project collaboration, background processing and Stripe billing integration.

The completed application is deployed using Vercel and Render and provides a production environment for demonstrating the implemented project management functionality.

---

**NEXVIA - Multi-Tenant SaaS Project Management Platform**

Developed by **Sanjeeth**

Internship ID: **NEX-INT-2026-1827**

Nexvia Technologies | Full-Stack Development | FS-04
