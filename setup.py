#!/usr/bin/env python
import os
import subprocess
import sys


def run_command(command):
    """Run a command and return its output"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(result.stdout)
    return True


def setup_project():
    """Setup the project"""
    print("=== Instagram Uploader with Playwright Setup ===")
    
    # Create necessary directories
    print("\n[1/7] Creating necessary directories...")
    os.makedirs("media", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    os.makedirs("bot/videos", exist_ok=True)
    os.makedirs("bot/cookies", exist_ok=True)
    os.makedirs("prepared_videos", exist_ok=True)
    
    # Install dependencies
    print("\n[2/7] Installing Python dependencies...")
    install_deps = run_command("pip install -r requirements.txt")
    if not install_deps:
        print("Failed to install Python dependencies. Please check your Python environment.")
        return False
    
    # Install Playwright browsers
    print("\n[3/7] Installing Playwright browsers...")
    install_pw = run_command("playwright install")
    if not install_pw:
        print("Failed to install Playwright browsers. You may need to install them manually.")
        print("Run: 'playwright install' after the setup is complete.")
    
    # Run migrations
    print("\n[4/7] Running Django migrations...")
    run_migrations = run_command("python manage.py makemigrations")
    run_migrations = run_command("python manage.py migrate") and run_migrations
    if not run_migrations:
        print("Failed to run Django migrations.")
        return False
    
    # Collect static files
    print("\n[5/7] Collecting static files...")
    collect_static = run_command("python manage.py collectstatic --noinput")
    if not collect_static:
        print("Failed to collect static files.")
        return False
    
    # Create superuser
    print("\n[6/7] Creating a superuser...")
    print("You'll need to create a superuser to access the admin interface.")
    create_su = run_command("python create_superuser.py")
    
    # Setup complete
    print("\n[7/7] Setup complete!")
    print("\nYou can now run the server with:")
    print("python manage.py runserver")
    print("\nAccess the application at: http://localhost:8000")
    print("Admin interface at: http://localhost:8000/admin")
    
    return True


if __name__ == "__main__":
    setup_project() 