#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to PostgreSQL.

This script:
1. Reads all records from the existing SQLite database
2. Transfers them to PostgreSQL while preserving all original data including timestamps
3. Provides progress updates and error handling
4. Verifies the migration was successful

Usage:
    python migrate_to_postgres.py [--sqlite-db PATH] [--dry-run]

Options:
    --sqlite-db PATH    Path to SQLite database (default: ./data/visits.db)
    --dry-run          Show what would be migrated without actually doing it
"""

import sqlite3
import psycopg2
import os
import sys
import argparse
from datetime import datetime
from urllib.parse import urlparse

def get_postgres_connection():
    """Get PostgreSQL connection from environment"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set. Please check your .env file.")
    return psycopg2.connect(database_url)

def verify_postgres_schema(pg_conn):
    """Verify PostgreSQL schema exists and create if needed"""
    cursor = pg_conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id SERIAL PRIMARY KEY,
            url TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_url ON visits(url)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON visits(timestamp)")

    pg_conn.commit()
    cursor.close()
    print("✓ PostgreSQL schema verified")

def get_sqlite_records(sqlite_path):
    """Read all records from SQLite database"""
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    # Get all records
    cursor.execute("SELECT id, url, ip_address, user_agent, timestamp FROM visits ORDER BY id")
    records = cursor.fetchall()

    # Get count
    cursor.execute("SELECT COUNT(*) FROM visits")
    count = cursor.fetchone()[0]

    conn.close()

    return records, count

def check_existing_records(pg_conn):
    """Check if PostgreSQL already has records"""
    cursor = pg_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM visits")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def migrate_records(sqlite_path, dry_run=False):
    """Migrate records from SQLite to PostgreSQL"""
    print(f"Starting migration from {sqlite_path}")
    print("=" * 60)

    # Read SQLite records
    print(f"\n1. Reading records from SQLite database...")
    records, sqlite_count = get_sqlite_records(sqlite_path)
    print(f"   Found {sqlite_count:,} records in SQLite")

    if sqlite_count == 0:
        print("\n⚠ No records to migrate.")
        return

    # Connect to PostgreSQL
    print(f"\n2. Connecting to PostgreSQL...")
    pg_conn = get_postgres_connection()
    print("   ✓ Connected to PostgreSQL")

    # Verify schema
    print(f"\n3. Verifying PostgreSQL schema...")
    verify_postgres_schema(pg_conn)

    # Check existing records
    existing_count = check_existing_records(pg_conn)
    if existing_count > 0:
        print(f"\n⚠ Warning: PostgreSQL database already contains {existing_count:,} records")
        response = input("Do you want to continue? This will add more records (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            pg_conn.close()
            return

    if dry_run:
        print(f"\n🔍 DRY RUN MODE - Would migrate {sqlite_count:,} records")
        print("\nSample records to be migrated:")
        for i, record in enumerate(records[:5], 1):
            print(f"  {i}. ID={record[0]}, URL={record[1][:50]}, TS={record[4]}")
        if len(records) > 5:
            print(f"  ... and {len(records) - 5} more records")
        pg_conn.close()
        return

    # Migrate records
    print(f"\n4. Migrating records to PostgreSQL...")
    cursor = pg_conn.cursor()

    migrated = 0
    errors = 0

    try:
        for i, record in enumerate(records, 1):
            sqlite_id, url, ip_address, user_agent, timestamp = record

            try:
                # Insert record preserving the original timestamp
                cursor.execute(
                    """
                    INSERT INTO visits (url, ip_address, user_agent, timestamp)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (url, ip_address, user_agent, timestamp)
                )
                migrated += 1

                # Progress indicator
                if i % 1000 == 0:
                    print(f"   Migrated {i:,} / {sqlite_count:,} records...")
                    pg_conn.commit()  # Commit every 1000 records

            except Exception as e:
                errors += 1
                print(f"   ✗ Error migrating record ID {sqlite_id}: {e}")
                if errors > 10:
                    print("   Too many errors, stopping migration.")
                    raise

        # Final commit
        pg_conn.commit()
        print(f"   ✓ Migrated {migrated:,} records")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        pg_conn.rollback()
        cursor.close()
        pg_conn.close()
        sys.exit(1)

    cursor.close()

    # Verify migration
    print(f"\n5. Verifying migration...")
    final_count = check_existing_records(pg_conn)
    print(f"   PostgreSQL now contains {final_count:,} records")

    # Get timestamp range
    cursor = pg_conn.cursor()
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM visits")
    min_ts, max_ts = cursor.fetchone()
    cursor.close()

    print(f"   Timestamp range: {min_ts} to {max_ts}")

    pg_conn.close()

    print("\n" + "=" * 60)
    print("✓ Migration completed successfully!")
    print(f"  Total records migrated: {migrated:,}")
    if errors > 0:
        print(f"  Errors encountered: {errors}")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(
        description="Migrate data from SQLite to PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--sqlite-db",
        default="./data/visits.db",
        help="Path to SQLite database (default: ./data/visits.db)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually doing it"
    )

    args = parser.parse_args()

    try:
        migrate_records(args.sqlite_db, dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
