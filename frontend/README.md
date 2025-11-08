# Data Destroyer Frontend

Modern React dashboard for the Data Destroyer privacy-first data governance platform.

## Features

- 🔐 **JWT Authentication** - Secure login with token-based auth
- 📊 **Privacy Dashboard** - Real-time privacy score and insights
- 🔍 **Data Discovery** - Automatic sensitive data classification
- 🛡️ **Moderation Center** - Review and manage policy violations
- ✅ **Compliance Reports** - GDPR, HIPAA, PCI-DSS, SOC2 tracking
- 📁 **Document Manager** - Secure file upload and management
- ⚙️ **Settings** - Privacy preferences and security settings

## Tech Stack

- **React 18** with TypeScript
- **Vite** - Fast build tool
- **Tailwind CSS** - Utility-first styling
- **React Query** - Server state management
- **Zustand** - Client state management
- **Axios** - HTTP client
- **React Router** - Navigation
- **Headless UI** - Accessible components
- **Heroicons** - Icon library

## Prerequisites

- Node.js 16+ and npm
- Backend API running on `http://localhost:8000`

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Environment Setup

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` if needed:

```env
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=Data Destroyer
```

### 3. Start Development Server

```bash
npm run dev
```

The app will be available at http://localhost:5173

### 4. Login

Use these demo credentials:
- **Username**: admin
- **Password**: admin

(Or create a user via Django admin or registration)

## Available Scripts

### Development

```bash
npm run dev          # Start dev server (http://localhost:5173)
npm run build        # Build for production
npm run preview      # Preview production build
npm run lint         # Run ESLint
npm run format       # Format code with Prettier
```

## Project Structure

```
frontend/
├── src/
│   ├── api/                 # API client and endpoints
│   │   ├── client.ts        # Axios instance with interceptors
│   │   ├── auth.ts          # Authentication API
│   │   ├── analytics.ts     # Analytics API
│   │   ├── moderation.ts    # Moderation API
│   │   ├── discovery.ts     # Discovery API
│   │   └── documents.ts     # Documents API
│   ├── components/          # Reusable components
│   │   ├── common/          # Generic components
│   │   ├── charts/          # Chart components
│   │   ├── layout/          # Layout components
│   │   └── forms/           # Form components
│   ├── pages/               # Page components
│   │   ├── Login.tsx        # Login page
│   │   ├── Dashboard.tsx    # Main dashboard
│   │   ├── Discovery.tsx    # Data discovery
│   │   ├── Moderation.tsx   # Moderation center
│   │   ├── Compliance.tsx   # Compliance reports
│   │   ├── Documents.tsx    # Document manager
│   │   └── Settings.tsx     # User settings
│   ├── stores/              # Zustand stores
│   │   ├── authStore.ts     # Auth state
│   │   └── uiStore.ts       # UI state
│   ├── types/               # TypeScript types
│   │   └── api.ts           # API types
│   ├── App.tsx              # Root component
│   ├── routes.tsx           # Route definitions
│   └── main.tsx             # Entry point
├── public/                  # Static assets
├── index.html               # HTML template
├── package.json             # Dependencies
├── vite.config.ts           # Vite configuration
├── tailwind.config.js       # Tailwind configuration
└── tsconfig.json            # TypeScript configuration
```

## Key Features

### Authentication

The app uses JWT authentication with automatic token refresh:

```typescript
// Login
const login = useAuthStore((state) => state.login)
await login(username, password)

// Logout
const logout = useAuthStore((state) => state.logout)
await logout()

// Get current user
const user = useAuthStore((state) => state.user)
```

### API Calls with React Query

```typescript
// Fetch data with caching
const { data, isLoading, error } = useQuery({
  queryKey: ['analytics', 'dashboard'],
  queryFn: () => analyticsApi.getDashboard(),
})

// Mutations
const mutation = useMutation({
  mutationFn: (data) => api.create(data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['data'] })
  },
})
```

### Notifications

```typescript
const addNotification = useUIStore((state) => state.addNotification)

addNotification({
  type: 'success',
  title: 'Success!',
  message: 'Operation completed successfully',
})
```

## API Integration

The frontend expects these backend endpoints:

### Authentication
- `POST /api/auth/login/` - Login with username/password
- `POST /api/auth/register/` - User registration
- `POST /api/auth/logout/` - Logout
- `POST /api/auth/refresh/` - Refresh JWT token
- `GET /api/auth/me/` - Get current user

### Analytics
- `GET /api/analytics/snapshots/` - Analytics snapshots
- `GET /api/analytics/insights/` - Privacy insights
- `GET /api/analytics/metrics/` - Usage metrics
- `GET /api/analytics/retention/` - Retention timeline
- `GET /api/analytics/dashboard/` - Dashboard data

### Moderation
- `GET /api/moderation/violations/` - Policy violations
- `GET /api/moderation/scans/` - Content scans
- `POST /api/moderation/violations/{id}/acknowledge/` - Acknowledge violation
- `POST /api/moderation/violations/{id}/resolve/` - Resolve violation
- `GET /api/moderation/dashboard/` - Moderation dashboard

### Discovery
- `GET /api/discovery/dashboard/` - Discovery dashboard
- `GET /api/discovery/governance-dashboard/` - Governance dashboard

### Documents
- `GET /api/documents/` - List documents
- `POST /api/documents/` - Upload document
- `DELETE /api/documents/{id}/` - Delete document

## Customization

### Theming

Edit `tailwind.config.js` to customize colors:

```javascript
theme: {
  extend: {
    colors: {
      primary: {
        // Your brand colors
      },
    },
  },
}
```

### API Base URL

Change in `.env`:

```env
VITE_API_URL=https://api.yourcompany.com/api
```

## Production Build

### 1. Build

```bash
npm run build
```

### 2. Preview

```bash
npm run preview
```

### 3. Deploy

The `dist/` folder contains static files ready for deployment:

- **Static Hosting**: Deploy to Netlify, Vercel, or AWS S3
- **With Django**: Copy to Django static files and serve via Nginx
- **Docker**: Use multi-stage build with Nginx

## Troubleshooting

### CORS Errors

Make sure Django has CORS configured:

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
]
```

### API Connection Failed

1. Check backend is running on port 8000
2. Verify `VITE_API_URL` in `.env`
3. Check browser console for errors

### Authentication Issues

1. Clear localStorage: `localStorage.clear()`
2. Check JWT token is being sent in headers
3. Verify backend JWT settings

## Contributing

1. Follow the existing code style
2. Use TypeScript for type safety
3. Add proper error handling
4. Write descriptive commit messages

## License

Proprietary - Data Destroyer Platform
