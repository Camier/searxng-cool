#!/usr/bin/env python3
"""
Setup user authentication system
Creates users table and initial admin user
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
from sqlalchemy import inspect

def setup_user_auth():
    """Setup user authentication system"""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Check if users table exists
        if 'users' not in inspector.get_table_names():
            print("📊 Creating users table...")
            db.create_all()
            print("✅ Users table created successfully!")
        else:
            print("ℹ️  Users table already exists")
        
        # Check if admin user exists
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count > 0:
            print(f"ℹ️  {admin_count} admin user(s) already exist")
            return
        
        print("\n🔐 Create Initial Admin User")
        print("-" * 40)
        
        # Get admin credentials
        username = input("Admin username: ").strip()
        email = input("Admin email: ").strip()
        
        while True:
            password = getpass.getpass("Admin password (min 8 chars): ")
            if len(password) < 8:
                print("❌ Password must be at least 8 characters")
                continue
            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                print("❌ Passwords do not match")
                continue
            break
        
        # Create admin user
        admin = User(
            username=username,
            email=email,
            is_active=True,
            is_admin=True
        )
        admin.set_password(password)
        
        try:
            db.session.add(admin)
            db.session.commit()
            print(f"\n✅ Admin user '{username}' created successfully!")
            print("\n🚀 User authentication system is ready!")
            print("\nYou can now login with:")
            print(f"   Username: {username}")
            print(f"   Password: [hidden]")
        except Exception as e:
            print(f"❌ Error creating admin user: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    setup_user_auth()