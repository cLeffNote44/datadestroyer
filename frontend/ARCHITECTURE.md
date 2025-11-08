# Data Destroyer Frontend Architecture

## Tech Stack

### Core Framework
- **React 18+** with TypeScript
- **Vite** - Fast build tool and dev server
- **React Router v6** - Client-side routing

### State Management
- **Zustand** - Lightweight state management for global state
- **React Query (TanStack Query)** - Server state management, caching, and data fetching

### UI Framework & Styling
- **Tailwind CSS** - Utility-first CSS framework
- **Headless UI** - Unstyled, accessible UI components
- **Heroicons** - Icon library

### Data Visualization
- **Recharts** - Composable charting library for React

### API & Data
- **Axios** - HTTP client
- **Zod** - TypeScript-first schema validation

### Development Tools
- **ESLint** - Linting
- **Prettier** - Code formatting
- **TypeScript** - Type safety
- **Vitest** - Unit testing
- **Playwright** - E2E testing

---

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── api/            # API client and endpoint definitions
│   │   ├── client.ts   # Axios instance with interceptors
│   │   ├── auth.ts     # Authentication endpoints
│   │   ├── analytics.ts
│   │   ├── moderation.ts
│   │   ├── discovery.ts
│   │   └── documents.ts
│   ├── components/     # Reusable UI components
│   │   ├── common/    # Generic components (Button, Card, etc.)
│   │   ├── charts/    # Chart components
│   │   ├── layout/    # Layout components (Header, Sidebar)
│   │   └── forms/     # Form components
│   ├── pages/         # Page components
│   │   ├── Dashboard.tsx
│   │   ├── Discovery.tsx
│   │   ├── Moderation.tsx
│   │   ├── Compliance.tsx
│   │   ├── Documents.tsx
│   │   ├── Settings.tsx
│   │   └── Login.tsx
│   ├── hooks/         # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useAnalytics.ts
│   │   └── useTheme.ts
│   ├── stores/        # Zustand stores
│   │   ├── authStore.ts
│   │   └── uiStore.ts
│   ├── types/         # TypeScript type definitions
│   │   ├── api.ts     # API response types
│   │   └── models.ts  # Domain models
│   ├── utils/         # Utility functions
│   │   ├── formatters.ts
│   │   └── validators.ts
│   ├── App.tsx        # Root component
│   ├── main.tsx       # Entry point
│   └── routes.tsx     # Route definitions
├── .env.example       # Environment variables template
├── .eslintrc.js       # ESLint configuration
├── .prettierrc        # Prettier configuration
├── tsconfig.json      # TypeScript configuration
├── vite.config.ts     # Vite configuration
└── package.json       # Dependencies
```

---

## Key Design Decisions

### 1. Authentication Flow
- **Login**: POST to `/api/auth/login/` (we'll create this endpoint)
- **JWT Storage**: Store tokens in `httpOnly` cookies (secure) or localStorage (simpler)
- **Token Refresh**: Implement automatic token refresh logic
- **Protected Routes**: Wrapper component that checks auth state

### 2. State Management Strategy
- **Server State**: React Query for all API data (caching, refetching, optimistic updates)
- **Client State**: Zustand for auth state, UI preferences, theme
- **Form State**: React Hook Form for complex forms

### 3. API Integration
- **Base URL**: Environment variable (`VITE_API_URL`)
- **Interceptors**:
  - Request: Add auth token to headers
  - Response: Handle 401 (redirect to login), error messages
- **Error Handling**: Centralized error boundary + toast notifications

### 4. Component Architecture
- **Atomic Design**: atoms → molecules → organisms → pages
- **Composition over inheritance**
- **TypeScript strict mode**: Full type safety

### 5. Performance Optimization
- **Code Splitting**: Lazy load routes with React.lazy()
- **React Query caching**: Reduce API calls
- **Virtualization**: For large lists (react-window)
- **Image optimization**: Lazy loading, WebP format

---

## Page Breakdown

### 1. Dashboard (Homepage)
**Route**: `/`

**Features**:
- Privacy Score gauge (0-100)
- Quick stats cards (documents, violations, discoveries)
- Recent activity timeline
- Privacy insights carousel
- Trends charts (7-day, 30-day)

**API Calls**:
- GET `/api/analytics/dashboard/`
- GET `/api/analytics/insights/?limit=5`
- GET `/api/moderation/dashboard/`

### 2. Data Discovery
**Route**: `/discovery`

**Features**:
- Discovered assets table (filterable, searchable)
- Classification breakdown pie chart
- Data lineage visualization
- Real-time monitoring status
- Compliance validation results

**API Calls**:
- GET `/api/discovery/dashboard/`
- GET `/api/discovery/governance-dashboard/`

### 3. Moderation Center
**Route**: `/moderation`

**Features**:
- Violation queue (pending, acknowledged, resolved)
- Risk score distribution chart
- Content scan history
- Bulk actions (acknowledge, quarantine)
- False positive reporting

**API Calls**:
- GET `/api/moderation/violations/`
- GET `/api/moderation/scans/`
- POST `/api/moderation/violations/{id}/acknowledge/`

### 4. Compliance Reports
**Route**: `/compliance`

**Features**:
- GDPR/HIPAA/PCI-DSS/SOC2 status cards
- Compliance score trends
- Retention policy overview
- Audit log viewer
- Export reports (PDF, CSV)

**API Calls**:
- GET `/api/discovery/governance-dashboard/`
- GET `/api/analytics/retention/`

### 5. Document Manager
**Route**: `/documents`

**Features**:
- File upload with drag-and-drop
- Document table with filters
- Encryption status indicators
- Download/share controls
- Retention scheduling

**API Calls**:
- GET `/api/documents/`
- POST `/api/documents/`
- DELETE `/api/documents/{id}/`

### 6. Settings
**Route**: `/settings`

**Features**:
- Profile settings
- Privacy preferences
- Security settings (2FA, IP restrictions)
- Notification preferences
- Auto-delete settings

**API Calls**:
- GET `/api/moderation/settings/`
- PATCH `/api/moderation/settings/{id}/`

---

## API Client Design

### Axios Instance Configuration

```typescript
// src/api/client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: Add auth token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: Handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

---

## Environment Variables

```env
# .env.example
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=Data Destroyer
VITE_ENABLE_ANALYTICS=true
```

---

## Development Workflow

1. **Setup**: `npm install`
2. **Dev Server**: `npm run dev` (runs on http://localhost:5173)
3. **Lint**: `npm run lint`
4. **Format**: `npm run format`
5. **Test**: `npm run test`
6. **Build**: `npm run build`
7. **Preview**: `npm run preview`

---

## Integration with Django Backend

### CORS Configuration
Django is already configured to allow all origins in development mode. For production, we'll add the frontend URL to `DJANGO_CORS_ALLOWED_ORIGINS`.

### Authentication Endpoints (To Be Created)
We need to add these endpoints to the Django backend:
- `POST /api/auth/login/` - Login with username/password, return JWT
- `POST /api/auth/register/` - User registration
- `POST /api/auth/logout/` - Logout
- `POST /api/auth/refresh/` - Refresh JWT token
- `GET /api/auth/me/` - Get current user info

### Static File Serving
In production, the built React app will be served by Django:
- Build files → `/frontend/dist/`
- Django collectstatic includes frontend build
- Nginx serves static files

---

## Deployment Strategy

### Development
- Frontend: Vite dev server on port 5173
- Backend: Django dev server on port 8000
- Proxy API requests from frontend to backend

### Production
- Frontend: Built static files served by Django/Nginx
- Single domain: `https://datadestroyer.com`
- Frontend at `/`, API at `/api/`

---

## Next Steps

1. ✅ Initialize Vite + React + TypeScript project
2. ✅ Set up Tailwind CSS
3. ✅ Create API client and auth endpoints
4. ✅ Build authentication flow (login, protected routes)
5. ✅ Implement layout (header, sidebar, navigation)
6. ✅ Build dashboard page
7. ✅ Build discovery, moderation, compliance pages
8. ✅ Add charts and visualizations
9. ✅ Testing and optimization
10. ✅ Production build configuration
