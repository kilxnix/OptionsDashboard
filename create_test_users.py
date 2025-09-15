"""
Create test users for the Options Scanner SaaS
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, Plan, Subscription, db
from auth import hash_password
from datetime import datetime, timedelta

# Create database connection
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Get the free plan
    free_plan = session.query(Plan).filter_by(code='free').first()
    if not free_plan:
        print("Error: Free plan not found in database")
        exit(1)
    
    # Create test user
    test_email = 'test@example.com'
    existing_test = session.query(User).filter_by(email=test_email).first()
    if not existing_test:
        test_user = User(
            email=test_email,
            password_hash=hash_password('Test123!'),
            role='USER',
            created_at=datetime.utcnow(),
            status='active'
        )
        session.add(test_user)
        session.flush()
        
        # Create free subscription for test user
        test_sub = Subscription(
            user_id=test_user.id,
            plan_id=free_plan.id,
            status='active',
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow() + timedelta(days=365),
            created_at=datetime.utcnow()
        )
        session.add(test_sub)
        print(f"Created test user: {test_email} / Test123!")
    else:
        print(f"Test user already exists: {test_email}")
    
    # Create demo user
    demo_email = 'demo@example.com'
    existing_demo = session.query(User).filter_by(email=demo_email).first()
    if not existing_demo:
        demo_user = User(
            email=demo_email,
            password_hash=hash_password('Demo123!'),
            role='USER',
            created_at=datetime.utcnow(),
            status='active'
        )
        session.add(demo_user)
        session.flush()
        
        # Create free subscription for demo user
        demo_sub = Subscription(
            user_id=demo_user.id,
            plan_id=free_plan.id,
            status='active',
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow() + timedelta(days=365),
            created_at=datetime.utcnow()
        )
        session.add(demo_sub)
        print(f"Created demo user: {demo_email} / Demo123!")
    else:
        print(f"Demo user already exists: {demo_email}")
    
    # Commit all changes
    session.commit()
    print("\nTest users ready for login!")
    print("You can now login with:")
    print("  Email: test@example.com, Password: Test123!")
    print("  Email: demo@example.com, Password: Demo123!")
    
except Exception as e:
    session.rollback()
    print(f"Error creating users: {e}")
finally:
    session.close()