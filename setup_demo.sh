#!/bin/bash

# Data Destroyer Demo Setup Script
# One command to set up a fully functional demo environment

set -e  # Exit on error

echo "🚀 Data Destroyer Demo Setup"
echo "================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

print_success "Python 3 found"

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV}" ]]; then
    print_info "Not in a virtual environment. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    print_success "Virtual environment created and activated"
else
    print_success "Virtual environment is active"
fi

# Install Python dependencies
print_info "Installing Python dependencies..."
if [ -f "requirements/dev.txt" ]; then
    pip install -q -r requirements/dev.txt
    print_success "Python dependencies installed"
else
    print_error "requirements/dev.txt not found"
    exit 1
fi

# Run migrations
print_info "Running database migrations..."
python manage.py migrate --noinput
print_success "Database migrations complete"

# Load moderation patterns
print_info "Loading moderation patterns..."
python manage.py load_moderation_patterns
print_success "Moderation patterns loaded"

# Generate demo data
print_info "Generating demo data (this may take a minute)..."
python manage.py generate_demo_data --users 5 --days 30
print_success "Demo data generated"

# Create demo superuser
print_info "Creating demo superuser..."
python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@datadestroyer.local', 'admin123')
    print('Superuser created')
else:
    print('Superuser already exists')
EOF
print_success "Superuser ready"

# Check if Node.js is installed
if command -v npm &> /dev/null; then
    print_info "Node.js found. Setting up frontend..."

    cd frontend

    # Install frontend dependencies
    print_info "Installing frontend dependencies..."
    npm install
    print_success "Frontend dependencies installed"

    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_success "Frontend .env file created"
    fi

    cd ..
else
    print_info "Node.js not found. Skipping frontend setup."
    print_info "Install Node.js 16+ to use the frontend dashboard."
fi

echo
echo "================================"
echo "🎉 Setup Complete!"
echo "================================"
echo
echo "Demo Users Created:"
echo "  • Username: admin"
echo "  • Password: admin123"
echo "  • Plus 5 demo users (password: demo123)"
echo
echo "To start the backend:"
echo "  python manage.py runserver"
echo
if command -v npm &> /dev/null; then
    echo "To start the frontend:"
    echo "  cd frontend && npm run dev"
    echo
fi
echo "Access the application:"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo "  Admin:    http://localhost:8000/admin"
echo "  API Docs: http://localhost:8000/api/docs/"
echo
echo "Happy coding! 🚀"
