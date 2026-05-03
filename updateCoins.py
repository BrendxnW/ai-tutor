#!/usr/bin/env python3
"""
Script to edit a specific user's coins in the AI Tutor database.
"""

import sys
import sqlite3
from pathlib import Path
from src.config import AUTH_DATABASE_PATH


def get_connection():
    """Get a connection to the database."""
    return sqlite3.connect(AUTH_DATABASE_PATH)


def get_user_balance(username):
    """Get the current balance for a user."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
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
    
    username = input("Enter username: ").strip()
    if not username:
        print("Error: Username cannot be empty")
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
        
        if command == "get" and len(sys.argv) == 3:
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
            print("    python updateCoins.py")
            print("\n  Command line mode:")
            print("    python updateCoins.py get <username>")
            print("    python updateCoins.py set <username> <balance>")
            print("    python updateCoins.py add <username> <amount>")
            print("    python updateCoins.py subtract <username> <amount>")
            sys.exit(1)


if __name__ == "__main__":
    main()
