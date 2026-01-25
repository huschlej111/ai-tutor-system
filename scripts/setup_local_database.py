#!/usr/bin/env python3
"""
Setup local database for Know-It-All Tutor System
Uses existing PostgreSQL installation instead of Docker
"""
import os
import sys
import subprocess
from pathlib import Path


def check_postgresql_running():
    """Check if PostgreSQL is running"""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "postgresql"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0 and result.stdout.strip() == "active"
    except FileNotFoundError:
        # Try alternative check
        try:
            result = subprocess.run(
                ["pg_isready", "-h", "localhost", "-p", "5432"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False


def get_postgres_user():
    """Get the PostgreSQL superuser (usually postgres)"""
    # Try common usernames
    for user in ["postgres", "postgresql"]:
        try:
            result = subprocess.run(
                ["sudo", "-u", user, "psql", "-c", "SELECT 1;"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return user
        except FileNotFoundError:
            continue
    return None


def create_database_and_user():
    """Create database and user for the tutor system"""
    postgres_user = get_postgres_user()
    if not postgres_user:
        print("❌ Could not find PostgreSQL superuser")
        return False
    
    print(f"📝 Using PostgreSQL superuser: {postgres_user}")
    
    # SQL commands to set up database
    setup_sql = """
-- Create user if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'tutor_user') THEN
        CREATE USER tutor_user WITH PASSWORD 'tutor_password';
    END IF;
END
$$;

-- Create database if not exists
SELECT 'CREATE DATABASE tutor_system OWNER tutor_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'tutor_system')\\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE tutor_system TO tutor_user;
ALTER USER tutor_user CREATEDB;
"""
    
    try:
        # Execute setup SQL
        result = subprocess.run(
            ["sudo", "-u", postgres_user, "psql"],
            input=setup_sql,
            text=True,
            capture_output=True
        )
        
        if result.returncode != 0:
            print(f"❌ Failed to create database: {result.stderr}")
            return False
        
        print("✅ Database and user created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False


def initialize_schema():
    """Initialize database schema"""
    init_sql_path = Path("scripts/sql/init.sql")
    
    if not init_sql_path.exists():
        print(f"❌ Schema file not found: {init_sql_path}")
        return False
    
    try:
        # Set environment for psql
        env = os.environ.copy()
        env.update({
            "PGHOST": "localhost",
            "PGPORT": "5432",
            "PGDATABASE": "tutor_system",
            "PGUSER": "tutor_user",
            "PGPASSWORD": "tutor_password"
        })
        
        # Execute schema initialization
        result = subprocess.run(
            ["psql", "-f", str(init_sql_path)],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Failed to initialize schema: {result.stderr}")
            return False
        
        print("✅ Database schema initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing schema: {e}")
        return False


def test_connection():
    """Test database connection"""
    try:
        env = os.environ.copy()
        env.update({
            "PGHOST": "localhost",
            "PGPORT": "5432", 
            "PGDATABASE": "tutor_system",
            "PGUSER": "tutor_user",
            "PGPASSWORD": "tutor_password"
        })
        
        result = subprocess.run(
            ["psql", "-c", "SELECT COUNT(*) FROM users;"],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Database connection test successful")
            print(f"   {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Database connection test failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        return False


def main():
    """Main setup function"""
    print("🗄️  Setting up local PostgreSQL database for Tutor System")
    print("=" * 60)
    
    # Check if PostgreSQL is running
    if not check_postgresql_running():
        print("❌ PostgreSQL is not running")
        print("   Try: sudo systemctl start postgresql")
        sys.exit(1)
    
    print("✅ PostgreSQL is running")
    
    # Create database and user
    if not create_database_and_user():
        sys.exit(1)
    
    # Initialize schema
    if not initialize_schema():
        sys.exit(1)
    
    # Test connection
    if not test_connection():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 Database setup completed successfully!")
    print("\nConnection details:")
    print("  Host: localhost")
    print("  Port: 5432")
    print("  Database: tutor_system")
    print("  User: tutor_user")
    print("  Password: tutor_password")
    print("\nNext steps:")
    print("  1. Start LocalStack: make localstack-start")
    print("  2. Setup LocalStack resources: make localstack-setup")
    print("  3. Run tests: make local-test")


if __name__ == "__main__":
    main()