"""
One-off migration: adds github_id and linkedin_id to the users table for
GitHub and LinkedIn social sign-in, alongside the existing google_id.

Unlike the earlier Google migration, this one doesn't need to touch any
NOT NULL constraints - both new columns are plain nullable string columns,
so a simple ALTER TABLE ADD COLUMN is enough (no table rebuild needed).

Usage:  python migrate_social_auth.py
Safe to run multiple times - it checks the current schema first and skips
if the migration was already applied.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "resume_builder.sqlite")


def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def main():
    if not os.path.exists(DB_PATH):
        print(f"No existing database at {DB_PATH} - nothing to migrate. "
              "It will be created fresh with the correct schema on next run.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if column_exists(cur, "users", "github_id") and column_exists(cur, "users", "linkedin_id"):
        print("Migration already applied - nothing to do.")
        conn.close()
        return

    print("Migrating users table (adding github_id, linkedin_id)...")

    if not column_exists(cur, "users", "github_id"):
        cur.execute("ALTER TABLE users ADD COLUMN github_id VARCHAR(64)")
    if not column_exists(cur, "users", "linkedin_id"):
        cur.execute("ALTER TABLE users ADD COLUMN linkedin_id VARCHAR(64)")

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_github_id ON users (github_id)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_linkedin_id ON users (linkedin_id)")

    conn.commit()
    conn.close()
    print("Done. Existing accounts are untouched; GitHub/LinkedIn sign-in is ready to use.")


if __name__ == "__main__":
    main()
