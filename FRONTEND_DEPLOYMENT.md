# Frontend Deployment Guide

This guide covers deploying the Data Destroyer frontend dashboard in various environments.

## Table of Contents

1. [Development Setup](#development-setup)
2. [Production Build](#production-build)
3. [Deployment Options](#deployment-options)
4. [Integration with Django](#integration-with-django)
5. [Docker Deployment](#docker-deployment)
6. [Troubleshooting](#troubleshooting)

---

## Development Setup

### Prerequisites

- Node.js 16+ and npm
- Django backend running on `http://localhost:8000`

### Quick Start

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create environment file
cp .env.example .env

# Start development server
npm run dev
```

The frontend will be available at http://localhost:5173 with hot module replacement.

### Backend Proxy

The dev server is configured to proxy API requests to Django:

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

This allows the frontend to call `/api/...` which gets proxied to `http://localhost:8000/api/...`.

---

## Production Build

### 1. Build the Frontend

```bash
cd frontend
npm run build
```

This creates optimized static files in `frontend/dist/`:

```
dist/
├── index.html
├── assets/
│   ├── index-abc123.js
│   ├── index-def456.css
│   └── ...
└── vite.svg
```

### 2. Preview the Build

```bash
npm run preview
```

Test the production build locally at http://localhost:4173

---

## Deployment Options

### Option 1: Static Hosting (Recommended for Testing)

Deploy to Netlify, Vercel, or AWS S3/CloudFront.

#### Netlify

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
cd frontend
npm run build
netlify deploy --prod --dir=dist
```

Configure environment variables in Netlify dashboard:
- `VITE_API_URL`: Your Django API URL (e.g., `https://api.yourdomain.com/api`)

#### Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
npm run build
vercel --prod
```

### Option 2: Serve with Django + Nginx (Recommended for Production)

Integrate the frontend build into Django and serve via Nginx.

#### Step 1: Update Django Settings

```python
# settings.py

# Add frontend build directory to static files
STATICFILES_DIRS = [
    BASE_DIR / 'frontend' / 'dist',
]

# Template directory for React app
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'frontend' / 'dist'],  # Add this
        ...
    }
]
```

#### Step 2: Create Django View for SPA

```python
# destroyer/views.py

from django.views.generic import TemplateView

class SPAView(TemplateView):
    template_name = 'index.html'
```

#### Step 3: Update URL Configuration

```python
# destroyer/urls.py

from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', ...),
    # Serve React app for all other routes
    path('', TemplateView.as_view(template_name='index.html'), name='spa'),
    # Catch-all for client-side routing
    re_path(r'^(?!api|admin|static|media).*$',
            TemplateView.as_view(template_name='index.html')),
]
```

#### Step 4: Build and Collect Static Files

```bash
# Build frontend
cd frontend
npm run build

# Collect static files
cd ..
python manage.py collectstatic --noinput
```

#### Step 5: Configure Nginx

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Serve static files
    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /app/media/;
    }

    # API requests to Django
    location /api/ {
        proxy_pass http://django:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Admin to Django
    location /admin/ {
        proxy_pass http://django:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # React SPA (all other routes)
    location / {
        proxy_pass http://django:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Docker Deployment

### Multi-Stage Dockerfile for Frontend

Create `frontend/Dockerfile`:

```dockerfile
# Build stage
FROM node:18-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage (Nginx)
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration for Frontend

`frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API proxy
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker Compose with Frontend

Update `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL database
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: destroyer
      POSTGRES_USER: destroyer
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Redis cache
  redis:
    image: redis:7-alpine

  # Django backend
  backend:
    build:
      context: .
      dockerfile: Dockerfile.prod
    command: gunicorn destroyer.wsgi:application --bind 0.0.0.0:8000
    environment:
      DATABASE_URL: postgres://destroyer:${DB_PASSWORD}@db:5432/destroyer
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - static_files:/app/staticfiles
      - media_files:/app/media

  # React frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    depends_on:
      - backend
    ports:
      - "80:80"

volumes:
  postgres_data:
  static_files:
  media_files:
```

### Build and Run

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Run containers
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

---

## Integration with Django

### Environment Variables

Production `.env` for frontend:

```env
VITE_API_URL=/api
VITE_APP_NAME=Data Destroyer
VITE_ENABLE_ANALYTICS=true
```

Note: Use relative paths (`/api`) when serving from same domain.

### CORS Configuration

Update Django CORS settings:

```python
# settings.py

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = [
        'https://yourdomain.com',
        'https://www.yourdomain.com',
    ]

# Allow credentials for JWT auth
CORS_ALLOW_CREDENTIALS = True
```

### JWT Configuration

```python
# settings.py

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

---

## Automated Deployment

### GitHub Actions Workflow

`.github/workflows/deploy-frontend.yml`:

```yaml
name: Deploy Frontend

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci

      - name: Build
        working-directory: ./frontend
        run: npm run build
        env:
          VITE_API_URL: ${{ secrets.API_URL }}

      - name: Deploy to S3
        uses: jakejarvis/s3-sync-action@master
        with:
          args: --delete
        env:
          AWS_S3_BUCKET: ${{ secrets.AWS_S3_BUCKET }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          SOURCE_DIR: 'frontend/dist'
```

---

## Performance Optimization

### 1. Code Splitting

React Router already implements route-based code splitting with lazy loading:

```typescript
const Dashboard = lazy(() => import('./pages/Dashboard'))
```

### 2. Build Optimization

Configure Vite for production:

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.logs
      },
    },
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
        },
      },
    },
  },
})
```

### 3. Image Optimization

- Use WebP format
- Implement lazy loading
- Add srcset for responsive images

### 4. Caching Strategy

Configure Nginx caching:

```nginx
# Cache static assets for 1 year
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Never cache index.html
location = /index.html {
    expires -1;
    add_header Cache-Control "no-store, no-cache, must-revalidate";
}
```

---

## Troubleshooting

### Build Fails

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
```

### API Calls Fail in Production

1. Check `VITE_API_URL` is correct
2. Verify CORS settings in Django
3. Check browser console for errors
4. Verify JWT tokens are being sent

### Routing Issues (404 on Refresh)

Ensure server is configured for SPA routing:

**Nginx:**
```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

**Apache:**
```apache
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteBase /
    RewriteRule ^index\.html$ - [L]
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteRule . /index.html [L]
</IfModule>
```

### Slow Initial Load

1. Enable gzip compression
2. Implement code splitting
3. Use CDN for static assets
4. Enable HTTP/2

---

## Security Checklist

- [ ] Set appropriate CORS headers
- [ ] Use HTTPS in production
- [ ] Set secure cookie flags for JWT
- [ ] Implement Content Security Policy (CSP)
- [ ] Enable HSTS headers
- [ ] Sanitize user inputs
- [ ] Implement rate limiting on API
- [ ] Regular dependency updates

---

## Monitoring

### Error Tracking

Integrate Sentry:

```typescript
// main.tsx
import * as Sentry from '@sentry/react'

if (import.meta.env.PROD) {
  Sentry.init({
    dsn: 'YOUR_SENTRY_DSN',
    environment: 'production',
  })
}
```

### Analytics

Add Google Analytics or Plausible:

```typescript
// utils/analytics.ts
export const trackPageView = (url: string) => {
  if (window.gtag) {
    window.gtag('config', 'GA_MEASUREMENT_ID', {
      page_path: url,
    })
  }
}
```

---

## Support

For issues and questions:
- Check the [Frontend README](frontend/README.md)
- Review Django backend logs
- Check browser console for errors
- Verify API responses in Network tab
