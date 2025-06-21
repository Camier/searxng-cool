#!/usr/bin/env python3
"""
Create admin user for SearXNG-Cool
"""
import os
import sys
import getpass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from orchestrator.app import create_app
from orchestrator.database import db
from orchestrator.models.user import User

def create_admin_user():
    """Create an admin user interactively"""
    app = create_app()
    
    with app.app_context():
        # Check if users table exists
        inspector = db.inspect(db.engine)
        if 'users' not in inspector.get_table_names():
            print("❌ Users table does not exist. Please run migrations first:")
            print("   cd migrations && alembic upgrade head")
            return
        
        print("🔐 Create Admin User for SearXNG-Cool")
        print("-" * 40)
        
        # Get username
        while True:
            username = input("Username: ").strip()
            if not username:
                print("❌ Username cannot be empty")
                continue
            if User.query.filter_by(username=username).first():
                print(f"❌ Username '{username}' already exists")
                continue
            break
        
        # Get email
        while True:
            email = input("Email: ").strip()
            if not email or '@' not in email:
                print("❌ Please enter a valid email")
                continue
            if User.query.filter_by(email=email).first():
                print(f"❌ Email '{email}' already registered")
                continue
            break
        
        # Get password
        while True:
            password = getpass.getpass("Password (min 8 chars): ")
            if len(password) < 8:
                print("❌ Password must be at least 8 characters")
                continue
            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                print("❌ Passwords do not match")
                continue
            break
        
        # Create admin user
        user = User(
            username=username,
            email=email,
            is_active=True,
            is_admin=True
        )
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            print(f"\n✅ Admin user '{username}' created successfully!")
            print(f"   Email: {email}")
            print(f"   Admin: Yes")
            print(f"   Active: Yes")
        except Exception as e:
            print(f"❌ Error creating user: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    create_admin_user()