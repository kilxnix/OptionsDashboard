#!/usr/bin/env python3
"""
Fix database schema by adding missing columns to the plans table
"""
import os
import psycopg2
from psycopg2 import sql

def fix_database_schema():
    """Add missing columns to the plans table"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found in environment")
        return False
    
    try:
        # Connect to the database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("Connected to database. Adding missing columns...")
        
        # List of columns to add with their types
        columns_to_add = [
            ('price_weekly', 'INTEGER DEFAULT 0'),
            ('stripe_price_weekly_id', 'VARCHAR(255)'),
            ('stripe_price_eur_id', 'VARCHAR(255)'),
            ('stripe_price_gbp_id', 'VARCHAR(255)'),
            ('stripe_price_usdc_id', 'VARCHAR(255)'),
            ('stripe_price_weekly_eur_id', 'VARCHAR(255)'),
            ('stripe_price_weekly_gbp_id', 'VARCHAR(255)'),
            ('stripe_price_weekly_usdc_id', 'VARCHAR(255)')
        ]
        
        # Add each column if it doesn't exist
        for column_name, column_type in columns_to_add:
            try:
                query = f"ALTER TABLE plans ADD COLUMN IF NOT EXISTS {column_name} {column_type};"
                cursor.execute(query)
                print(f"✓ Added column: {column_name}")
            except Exception as e:
                print(f"✗ Error adding column {column_name}: {e}")
                # Continue with other columns even if one fails
        
        # Commit the changes
        conn.commit()
        print("\n✓ Database schema updated successfully!")
        
        # Verify the columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'plans'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print("\nCurrent columns in plans table:")
        for col in columns:
            print(f"  - {col[0]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to fix database schema: {e}")
        return False

if __name__ == "__main__":
    success = fix_database_schema()
    if success:
        print("\n✅ Database schema fix completed successfully!")
    else:
        print("\n❌ Database schema fix failed!")