#!/usr/bin/env python
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from django.contrib.auth.models import User
from django.db.utils import IntegrityError

def create_superuser(username, email, password):
    try:
        user = User.objects.create_superuser(username, email, password)
        print(f"Superuser '{username}' created successfully!")
        return user
    except IntegrityError:
        print(f"Superuser '{username}' already exists.")
        return None

if __name__ == "__main__":
    if len(sys.argv) == 4:
        username = sys.argv[1]
        email = sys.argv[2]
        password = sys.argv[3]
        create_superuser(username, email, password)
    else:
        print("Usage: python create_superuser.py <username> <email> <password>")
        # Interactive mode if no arguments provided
        try:
            username = input("Enter username: ")
            email = input("Enter email: ")
            password = input("Enter password: ")
            if username and password:
                create_superuser(username, email, password)
            else:
                print("Username and password are required.")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(0) 