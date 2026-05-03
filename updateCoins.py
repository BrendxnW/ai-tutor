#!/usr/bin/env python3
"""
Script to edit a specific user's coins in the AI Tutor database.
"""

import sys
import sqlite3
from pathlib import Path
from src.config import AUTH_DATABASE_PATH
from src.database import initialize_auth_database


def get_connection():
    """Get a connection to the database."""
    initialize_auth_database()
    conn = sqlite3.connect(AUTH_DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def list_usernames():
    """List account usernames that can actually log in."""
    with get_connection() as conn:
        rows = conn.execute("SELECT username FROM users ORDER BY username").fetchall()
    return [row["username"] for row in rows]


def require_existing_user(username):
    """Prevent editing a coin row for the wrong case or a non-login account."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT username FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if row:
        return row["username"]

    usernames = list_usernames()
    lower_username = username.lower()
    close_matches = [name for name in usernames if name.lower() == lower_username]
    message = f"User '{username}' does not exist in {AUTH_DATABASE_PATH}."
    if close_matches:
        message += f" Did you mean: {', '.join(close_matches)}?"
    elif usernames:
        message += f" Existing users: {', '.join(usernames)}"
    raise ValueError(message)


def get_user_balance(username):
    """Get the current balance for a user."""
    require_existing_user(username)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT username, balance, updated_at FROM user_coins WHERE username = ?",
            (username,),
        ).fetchone()
    
    if row:
        return dict(row)
    return None


def set_balance(username, balance):
    """Set a specific balance for a user."""
    import time
    require_existing_user(username)
    balance = int(balance)
    now = int(time.time())
    
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_coins (username, balance, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                balance = excluded.balance,
                updated_at = excluded.updated_at
            """,
            (username, balance, now),
        )
        conn.commit()
    
    return get_user_balance(username)


def add_coins(username, amount):
    """Add coins to a user's balance."""
    import time
    require_existing_user(username)
    amount = int(amount)
    now = int(time.time())
    
    with get_connection() as conn:
        # Get current balance
        current = conn.execute(
            "SELECT balance FROM user_coins WHERE username = ?",
            (username,),
        ).fetchone()
        
        current_balance = current[0] if current else 0
        new_balance = current_balance + amount
        
        # Update or insert
        conn.execute(
            """
            INSERT INTO user_coins (username, balance, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                balance = excluded.balance,
                updated_at = excluded.updated_at
            """,
            (username, new_balance, now),
        )
        conn.commit()
    
    return get_user_balance(username)


def subtract_coins(username, amount):
    """Subtract coins from a user's balance."""
    return add_coins(username, -int(amount))


def interactive_mode():
    """Run the script in interactive mode."""
    print("\n=== AI Tutor Coin Editor ===\n")
    print(f"Editing database: {AUTH_DATABASE_PATH}\n")
    
    username = input("Enter username: ").strip()
    if not username:
        print("Error: Username cannot be empty")
        return

    try:
        require_existing_user(username)
    except ValueError as error:
        print(f"Error: {error}")
        return
    
    # Check if user exists
    balance_info = get_user_balance(username)
    if balance_info:
        print(f"\nCurrent balance for '{username}': {balance_info['balance']} coins")
    else:
        print(f"\nNo existing coins found for '{username}'. Will create new entry.")
    
    print("\nOptions:")
    print("1. Set specific balance")
    print("2. Add coins")
    print("3. Subtract coins")
    print("4. View current balance")
    print("5. Exit")
    
    while True:
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == "1":
            amount = input("Enter new balance: ").strip()
            try:
                result = set_balance(username, amount)
                print(f"✓ Balance updated to {result['balance']} coins")
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == "2":
            amount = input("Enter amount to add: ").strip()
            try:
                result = add_coins(username, amount)
                print(f"✓ Added {amount} coins. New balance: {result['balance']} coins")
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == "3":
            amount = input("Enter amount to subtract: ").strip()
            try:
                result = subtract_coins(username, amount)
                print(f"✓ Subtracted {amount} coins. New balance: {result['balance']} coins")
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == "4":
            result = get_user_balance(username)
            if result:
                print(f"Current balance for '{username}': {result['balance']} coins")
            else:
                print(f"No coins found for '{username}'")
        
        elif choice == "5":
            print("Exiting...")
            break
        
        else:
            print("Invalid option. Please select 1-5.")


def main():
    """Main entry point."""
    if len(sys.argv) == 1:
        # Interactive mode
        interactive_mode()
    
    elif len(sys.argv) >= 2:
        # Command line mode
        command = sys.argv[1].lower()

        try:
            if command == "users" and len(sys.argv) == 2:
                print("Users:")
                for username in list_usernames():
                    print(f"  {username}")

            elif command == "get" and len(sys.argv) == 3:
                username = sys.argv[2]
                result = get_user_balance(username)
                if result:
                    print(f"{username}: {result['balance']} coins")
                else:
                    print(f"{username}: 0 coins (no entry)")

            elif command == "set" and len(sys.argv) == 4:
                username = sys.argv[2]
                balance = sys.argv[3]
                result = set_balance(username, balance)
                print(f"✓ {username}: {result['balance']} coins")

            elif command == "add" and len(sys.argv) == 4:
                username = sys.argv[2]
                amount = sys.argv[3]
                result = add_coins(username, amount)
                print(f"✓ {username}: {result['balance']} coins")

            elif command == "subtract" and len(sys.argv) == 4:
                username = sys.argv[2]
                amount = sys.argv[3]
                result = subtract_coins(username, amount)
                print(f"✓ {username}: {result['balance']} coins")

            else:
                print("Usage:")
                print("  Interactive mode:")
                print("    python3 updateCoins.py")
                print("\n  Command line mode:")
                print("    python3 updateCoins.py users")
                print("    python3 updateCoins.py get <username>")
                print("    python3 updateCoins.py set <username> <balance>")
                print("    python3 updateCoins.py add <username> <amount>")
                print("    python3 updateCoins.py subtract <username> <amount>")
                sys.exit(1)
        except ValueError as error:
            print(f"Error: {error}")
            sys.exit(1)


if __name__ == "__main__":
    main()
