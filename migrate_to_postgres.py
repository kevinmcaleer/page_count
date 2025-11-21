#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to PostgreSQL with incremental sync support.

This script supports incremental syncing - you can run it multiple times and it will only
copy new records that don't already exist in PostgreSQL. This is perfect for:
- Running initial migration before switching to new service
- Running again after the switch to catch any gap records
- Repeatedly syncing during a gradual cutover period

The script uses a composite unique constraint (url, ip_address, user_agent, timestamp)
to detect and skip duplicate records.

Usage:
    python migrate_to_postgres.py [--sqlite-db PATH] [--dry-run] [--force]

Options:
    --sqlite-db PATH    Path to SQLite database (default: ./data/visits.db)
    --dry-run          Show what would be migrated without actually doing it
    --force            Skip confirmation prompts
"""

import sqlite3
import psycopg2
import os
import sys
import argparse
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env_file()

def get_postgres_connection():
    """Get PostgreSQL connection from environment"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set. Please check your .env file.")
    return psycopg2.connect(database_url)

def ensure_database_exists():
    """Create the database if it doesn't exist"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set.")

    # Parse the database URL to extract connection details
    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip('/')

    # Build connection string to 'postgres' database (default database)
    admin_url = f"{parsed.scheme}://{parsed.netloc}/postgres"

    try:
        # Connect to the default 'postgres' database
        conn = psycopg2.connect(admin_url)
        conn.autocommit = True  # Required for CREATE DATABASE
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()

        if not exists:
            print(f"   Creating database '{db_name}'...")
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"   ✓ Database '{db_name}' created successfully")
        else:
            print(f"   ✓ Database '{db_name}' already exists")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"   ⚠ Could not create database: {e}")
        print(f"   Please create the database manually: CREATE DATABASE {db_name};")
        raise

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

    # Create unique constraint for duplicate detection (idempotent - won't fail if exists)
    cursor.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'visits_unique_record'
            ) THEN
                ALTER TABLE visits
                ADD CONSTRAINT visits_unique_record
                UNIQUE (url, ip_address, user_agent, timestamp);
            END IF;
        END $$;
    """)

    pg_conn.commit()
    cursor.close()
    print("✓ PostgreSQL schema verified with unique constraint for deduplication")

def get_sqlite_records(sqlite_path, since_timestamp=None):
    """Read records from SQLite database, optionally filtering by timestamp"""
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    # Build query with optional timestamp filter
    if since_timestamp:
        query = "SELECT id, url, ip_address, user_agent, timestamp FROM visits WHERE timestamp > ? ORDER BY timestamp"
        cursor.execute(query, (since_timestamp,))
    else:
        query = "SELECT id, url, ip_address, user_agent, timestamp FROM visits ORDER BY timestamp"
        cursor.execute(query)

    records = cursor.fetchall()

    # Get total count
    if since_timestamp:
        cursor.execute("SELECT COUNT(*) FROM visits WHERE timestamp > ?", (since_timestamp,))
    else:
        cursor.execute("SELECT COUNT(*) FROM visits")
    count = cursor.fetchone()[0]

    conn.close()

    return records, count

def check_existing_records(pg_conn):
    """Check if PostgreSQL already has records and return count + latest timestamp"""
    cursor = pg_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM visits")
    count = cursor.fetchone()[0]

    latest_timestamp = None
    if count > 0:
        cursor.execute("SELECT MAX(timestamp) FROM visits")
        latest_timestamp = cursor.fetchone()[0]

    cursor.close()
    return count, latest_timestamp

def migrate_records(sqlite_path, dry_run=False, force=False):
    """Migrate records from SQLite to PostgreSQL with incremental sync support"""
    print(f"Starting incremental migration from {sqlite_path}")
    print("=" * 70)

    # Ensure database exists
    print(f"\n1. Ensuring database exists...")
    ensure_database_exists()

    # Connect to PostgreSQL
    print(f"\n2. Connecting to PostgreSQL...")
    pg_conn = get_postgres_connection()
    print("   ✓ Connected to PostgreSQL")

    # Verify schema (includes unique constraint for deduplication)
    print(f"\n3. Verifying PostgreSQL schema...")
    verify_postgres_schema(pg_conn)

    # Check existing records and get latest timestamp
    existing_count, latest_timestamp = check_existing_records(pg_conn)

    if existing_count > 0:
        print(f"\n   PostgreSQL already contains {existing_count:,} records")
        print(f"   Latest timestamp: {latest_timestamp}")
        print(f"   Will sync only records newer than this timestamp...")
    else:
        print(f"\n   PostgreSQL is empty - performing initial migration")

    # Read SQLite records (only newer than latest if incremental)
    print(f"\n4. Reading records from SQLite database...")
    records, sqlite_count = get_sqlite_records(sqlite_path, since_timestamp=latest_timestamp)

    if sqlite_count == 0:
        print(f"   ✓ No new records to migrate - databases are in sync!")
        pg_conn.close()
        return

    print(f"   Found {sqlite_count:,} new/updated records to migrate")

    if dry_run:
        print(f"\n🔍 DRY RUN MODE - Would migrate {sqlite_count:,} records")
        print("\nSample records to be migrated:")
        for i, record in enumerate(records[:5], 1):
            print(f"  {i}. ID={record[0]}, URL={record[1][:50]}, TS={record[4]}")
        if len(records) > 5:
            print(f"  ... and {len(records) - 5} more records")
        pg_conn.close()
        return

    # Migrate records with ON CONFLICT DO NOTHING for safety
    print(f"\n5. Migrating records to PostgreSQL (skipping duplicates)...")
    cursor = pg_conn.cursor()

    migrated = 0
    skipped = 0
    errors = 0

    try:
        for i, record in enumerate(records, 1):
            sqlite_id, url, ip_address, user_agent, timestamp = record

            try:
                # Insert record with ON CONFLICT DO NOTHING to skip duplicates
                cursor.execute(
                    """
                    INSERT INTO visits (url, ip_address, user_agent, timestamp)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT ON CONSTRAINT visits_unique_record DO NOTHING
                    """,
                    (url, ip_address, user_agent, timestamp)
                )

                # Check if row was actually inserted
                if cursor.rowcount > 0:
                    migrated += 1
                else:
                    skipped += 1

                # Progress indicator
                if i % 1000 == 0:
                    print(f"   Processed {i:,} / {sqlite_count:,} records (inserted: {migrated:,}, skipped: {skipped:,})...")
                    pg_conn.commit()  # Commit every 1000 records

            except Exception as e:
                errors += 1
                print(f"   ✗ Error migrating record ID {sqlite_id}: {e}")
                if errors > 10:
                    print("   Too many errors, stopping migration.")
                    raise

        # Final commit
        pg_conn.commit()
        print(f"   ✓ Processed {len(records):,} records")
        print(f"   ✓ Inserted {migrated:,} new records")
        print(f"   ✓ Skipped {skipped:,} duplicate records")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        pg_conn.rollback()
        cursor.close()
        pg_conn.close()
        sys.exit(1)

    cursor.close()

    # Verify migration
    print(f"\n6. Verifying migration...")
    final_count, final_latest = check_existing_records(pg_conn)
    print(f"   PostgreSQL now contains {final_count:,} total records")

    # Get timestamp range
    cursor = pg_conn.cursor()
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM visits")
    min_ts, max_ts = cursor.fetchone()
    cursor.close()

    print(f"   Timestamp range: {min_ts} to {max_ts}")

    pg_conn.close()

    print("\n" + "=" * 70)
    print("✓ Incremental migration completed successfully!")
    print(f"  New records inserted: {migrated:,}")
    print(f"  Duplicates skipped: {skipped:,}")
    if errors > 0:
        print(f"  Errors encountered: {errors}")
    print("\n  You can run this script again to sync any new records.")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(
        description="Migrate data from SQLite to PostgreSQL with incremental sync",
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
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts"
    )

    args = parser.parse_args()

    try:
        migrate_records(args.sqlite_db, dry_run=args.dry_run, force=args.force)
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
