# PostgreSQL Migration Guide with Incremental Sync

This guide explains how to migrate your page_count app from SQLite to PostgreSQL with support for incremental syncing during the cutover period.

## Key Feature: Incremental Sync

The migration script is **fully idempotent** and supports incremental syncing. This means:

- ✓ Run it multiple times safely - no duplicate records will be created
- ✓ Automatically detects and skips records that already exist in PostgreSQL
- ✓ Only copies new records created since the last sync
- ✓ Perfect for gradual cutover scenarios

**Use Case:** Run the migration before switching to PostgreSQL, then run it again afterward to catch any records created during the gap period.

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
- Whether it's an initial sync or incremental sync
- Sample records
- No actual changes will be made

## Step 4: Run Initial Migration

Execute the initial migration before switching services:

```bash
python migrate_to_postgres.py
```

The migration script will:
1. Create PostgreSQL schema with unique constraint for deduplication
2. Read all records from SQLite (`./data/visits.db` by default)
3. Transfer all records while preserving original timestamps
4. Show progress updates every 1,000 records
5. Verify the migration was successful

### Custom SQLite Path

If your SQLite database is in a different location:

```bash
python migrate_to_postgres.py --sqlite-db /path/to/your/visits.db
```

## Step 5: Incremental Sync (Run Multiple Times)

After the initial migration, you can run the script again to sync any new records:

```bash
python migrate_to_postgres.py
```

On subsequent runs, the script will:
1. Detect the latest timestamp in PostgreSQL
2. Only read records newer than that timestamp from SQLite
3. Skip any duplicates automatically using unique constraint
4. Report how many records were inserted vs. skipped

**Example Output:**
```
PostgreSQL already contains 42,168 records
Latest timestamp: 2025-01-20 15:30:45
Will sync only records newer than this timestamp...

Found 127 new/updated records to migrate
✓ Inserted 127 new records
✓ Skipped 0 duplicate records
```

## Step 6: Verify Migration

The migration script automatically verifies:
- Total record count
- Timestamp range is preserved
- Reports inserted vs. skipped records

You can also manually verify by starting the app and checking:
- `/health` endpoint
- `/stats` endpoint
- `/all-visits` endpoint

## Step 7: Start Using PostgreSQL

Once migration is complete, the app will automatically use PostgreSQL for all operations. The SQLite database files are kept as backup but are no longer used.

## Recommended Cutover Workflow

For a smooth transition with zero data loss:

1. **Before cutover:** Run initial migration while SQLite app is still running
   ```bash
   python migrate_to_postgres.py --dry-run  # Preview
   python migrate_to_postgres.py            # Execute
   ```

2. **Switch services:** Stop SQLite app, start PostgreSQL app

3. **After cutover:** Run incremental sync to catch any gap records
   ```bash
   python migrate_to_postgres.py            # Syncs only new records
   ```

4. **Optional:** Run sync again to confirm databases are identical
   ```bash
   python migrate_to_postgres.py            # Should report "No new records to migrate"
   ```

## How Duplicate Detection Works

The migration script uses a unique constraint on `(url, ip_address, user_agent, timestamp)` to prevent duplicates:

- If a record with the same values already exists, it's automatically skipped
- No errors are thrown for duplicates
- The script reports how many records were skipped
- Safe to run multiple times without any risk

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
- Incremental syncs are very fast (only reads new records)

## Security Notes

- **NEVER** commit `.env` file to git (already in `.gitignore`)
- **NEVER** share database credentials
- Use strong passwords for production databases
- Consider using environment variables in production instead of `.env` files
