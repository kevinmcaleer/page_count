# PostgreSQL Migration Guide

This guide explains how to migrate your page_count app from SQLite to PostgreSQL.

## Prerequisites

1. PostgreSQL database server must be running and accessible
2. Database credentials must be configured in `.env` file
3. Python dependencies must be installed

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install `psycopg2-binary` which is required for PostgreSQL connectivity.

## Step 2: Verify Database Configuration

Ensure your `.env` file contains the correct PostgreSQL connection details:

```
DATABASE_URL=postgresql://username:password@host:port/database_name
```

The `.env` file is already in `.gitignore` to prevent committing secrets to git.

## Step 3: Run Migration (Dry Run First)

It's recommended to do a dry run first to see what will be migrated:

```bash
python migrate_to_postgres.py --dry-run
```

This will show:
- How many records will be migrated
- Sample records
- No actual changes will be made

## Step 4: Run Migration

Once you're satisfied with the dry run, execute the migration:

```bash
python migrate_to_postgres.py
```

The migration script will:
1. Read all records from SQLite (`./data/visits.db` by default)
2. Create the PostgreSQL schema if it doesn't exist
3. Transfer all records while preserving original timestamps
4. Show progress updates every 1,000 records
5. Verify the migration was successful

### Custom SQLite Path

If your SQLite database is in a different location:

```bash
python migrate_to_postgres.py --sqlite-db /path/to/your/visits.db
```

## Step 5: Verify Migration

The migration script automatically verifies:
- Record count matches
- Timestamp range is preserved

You can also manually verify by starting the app and checking:
- `/health` endpoint
- `/stats` endpoint
- `/all-visits` endpoint

## Step 6: Start Using PostgreSQL

Once migration is complete, the app will automatically use PostgreSQL for all operations. The SQLite database files are kept as backup but are no longer used.

## Rollback

If you need to rollback to SQLite:
1. Keep your SQLite database files as backup
2. Update `page_count.py` to use SQLite again
3. Or restore from your SQLite backup

## Troubleshooting

### Connection Errors

If you see connection errors:
- Verify PostgreSQL is running
- Check DATABASE_URL is correct in `.env`
- Ensure firewall allows connections on the PostgreSQL port

### Migration Errors

If migration fails:
- The script will rollback automatically
- Check error messages for specific issues
- Verify both databases are accessible

### Performance

For large databases (>100k records):
- Migration commits every 1,000 records for performance
- You can monitor progress in real-time
- Estimated time: ~1,000-5,000 records per second

## Security Notes

- **NEVER** commit `.env` file to git (already in `.gitignore`)
- **NEVER** share database credentials
- Use strong passwords for production databases
- Consider using environment variables in production instead of `.env` files
