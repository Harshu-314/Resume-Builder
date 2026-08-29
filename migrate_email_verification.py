"""
One-off migration: adds email-verification (OTP) fields to the users table.

Existing accounts (created before this feature existed) are grandfathered
in as already-verified so nobody who's already using the app gets locked
out - only new signups go through the OTP flow.

Usage:  python migrate_email_verification.py
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

    if column_exists(cur, "users", "email_verified"):
        print("Migration already applied - nothing to do.")
        conn.close()
        return

    print("Migrating users table (adding email verification fields)...")
    cur.executescript("""
        ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN otp_hash VARCHAR(255);
        ALTER TABLE users ADD COLUMN otp_expires_at DATETIME;
        ALTER TABLE users ADD COLUMN otp_attempts INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN otp_last_sent_at DATETIME;
    """)
    cur.execute("UPDATE users SET email_verified = 1")

    conn.commit()
    conn.close()
    print("Done. Existing accounts are marked as verified; new signups will need to verify.")


if __name__ == "__main__":
    main()
