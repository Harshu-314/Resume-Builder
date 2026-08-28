"""
One-off migration for the Google Sign-In changes.

The existing `users` table has `password_hash NOT NULL`, but Google-only
accounts have no local password, so that constraint needs to be relaxed.
SQLite can't ALTER a column's NOT NULL directly, so this recreates the table.

Usage:  python migrate_google_auth.py
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

    if column_exists(cur, "users", "google_id"):
        print("Migration already applied - nothing to do.")
        conn.close()
        return

    print("Migrating users table (adding google_id/auth_provider, relaxing password_hash)...")

    cur.executescript("""
        BEGIN TRANSACTION;

        CREATE TABLE users_new (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            email VARCHAR(180) NOT NULL,
            password_hash VARCHAR(255),
            auth_provider VARCHAR(20) NOT NULL DEFAULT 'password',
            google_id VARCHAR(64),
            plan VARCHAR(20) NOT NULL DEFAULT 'free',
            ats_checks_used INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME
        );

        INSERT INTO users_new (id, name, email, password_hash, plan, ats_checks_used, created_at, updated_at)
        SELECT id, name, email, password_hash, plan, ats_checks_used, created_at, updated_at FROM users;

        DROP TABLE users;
        ALTER TABLE users_new RENAME TO users;

        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);
        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_id ON users (google_id);

        COMMIT;
    """)

    conn.commit()
    conn.close()
    print("Done. Existing accounts are untouched and can still log in with their password.")


if __name__ == "__main__":
    main()
