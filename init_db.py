import sqlite3
import hashlib

def init_db():
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    
    # Create conversations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        user_message TEXT,
        assistant_message TEXT,
        model TEXT,
        system_prompt TEXT,
        username TEXT
    )
    ''')
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT
    )
    ''')
    
    conn.commit()
    print("Database initialized successfully!")
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                      (username, hash_password(password)))
        conn.commit()
        return True, "Registration successful!"
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()

def check_login(username, password):
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] == hash_password(password):
        return True
    return False

if __name__ == "__main__":
    init_db()