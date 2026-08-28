"""
One-off migration: adds forgot-password (OTP) fields to the users table.

Usage:  python migrate_password_reset.py
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

    if column_exists(cur, "users", "reset_otp_hash"):
        print("Migration already applied - nothing to do.")
        conn.close()
        return

    print("Migrating users table (adding password-reset fields)...")
    cur.executescript("""
        ALTER TABLE users ADD COLUMN reset_otp_hash VARCHAR(255);
        ALTER TABLE users ADD COLUMN reset_otp_expires_at DATETIME;
        ALTER TABLE users ADD COLUMN reset_otp_attempts INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN reset_otp_last_sent_at DATETIME;
    """)

    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
