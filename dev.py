#!/usr/bin/env python
"""
Development convenience script for common tasks.
Run: python dev.py <command>
"""

import os
import subprocess
import sys


def run_cmd(cmd, **kwargs):
    """Run a shell command and return success status."""
    print(f"🔧 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, **kwargs)
    return result.returncode == 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python dev.py <command>")
        print("\nAvailable commands:")
        print("  server     - Start Django development server")
        print("  test       - Run tests with coverage")
        print("  test-fast  - Run tests without coverage")
        print("  lint       - Run linting and formatting")
        print("  check      - Run Django system checks")
        print("  docker     - Start Docker dev environment")
        print("  shell      - Start Django shell with extensions")
        print("  migrate    - Run database migrations")
        print("  reset-db   - Reset database and run migrations")
        sys.exit(1)

    command = sys.argv[1]

    # Ensure we're in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if command == "server":
        run_cmd("python manage.py runserver")

    elif command == "test":
        print("🧪 Running tests with coverage...")
        run_cmd("python -m pytest --cov --cov-report=term-missing")

    elif command == "test-fast":
        print("🏃 Running tests (fast)...")
        run_cmd("python -m pytest -x --tb=short")

    elif command == "lint":
        print("🔍 Running linting and formatting...")
        run_cmd("python -m ruff check . --fix")
        run_cmd("python -m black .")
        run_cmd("python -m mypy .")

    elif command == "check":
        print("✅ Running Django system checks...")
        run_cmd("python manage.py check")
        run_cmd("python manage.py check --deploy")

    elif command == "docker":
        print("🐳 Starting Docker development environment...")
        run_cmd("docker compose -f docker-compose.dev.yml up --build")

    elif command == "shell":
        print("🐍 Starting Django shell...")
        run_cmd("python manage.py shell_plus --ipython")

    elif command == "migrate":
        print("📊 Running database migrations...")
        run_cmd("python manage.py migrate")

    elif command == "reset-db":
        print("⚠️  Resetting database...")
        if input("Are you sure? This will delete all data! (y/N): ").lower() == "y":
            run_cmd("rm -f db.sqlite3 || del db.sqlite3")
            run_cmd("python manage.py migrate")
            print("✅ Database reset complete!")

    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
