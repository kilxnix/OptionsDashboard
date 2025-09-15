#!/usr/bin/env python3
"""
Database migration script to add multi-currency columns to the plans table
"""

import os
from flask import Flask
from models import db
from sqlalchemy import text

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/options_scanner')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

def add_multicurrency_columns():
    """Add multi-currency price columns to plans table"""
    print("Starting database migration for multi-currency support...")
    
    with app.app_context():
        db.init_app(app)
        
        # Check if columns already exist
        check_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'plans' 
        AND column_name IN ('stripe_price_eur_id', 'stripe_price_gbp_id', 'stripe_price_usdc_id');
        """
        
        result = db.session.execute(text(check_query))
        existing_columns = [row[0] for row in result]
        
        # Add missing columns
        columns_to_add = {
            'stripe_price_eur_id': 'VARCHAR(255)',
            'stripe_price_gbp_id': 'VARCHAR(255)',
            'stripe_price_usdc_id': 'VARCHAR(255)'
        }
        
        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                try:
                    alter_query = f"ALTER TABLE plans ADD COLUMN {column_name} {column_type};"
                    db.session.execute(text(alter_query))
                    db.session.commit()
                    print(f"✓ Added column: {column_name}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"  Column {column_name} already exists")
                    else:
                        print(f"✗ Error adding column {column_name}: {e}")
                        db.session.rollback()
            else:
                print(f"  Column {column_name} already exists")
        
        print("\nMigration completed successfully!")
        return True

if __name__ == "__main__":
    try:
        add_multicurrency_columns()
        print("\n✅ Database migration successful!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        exit(1)