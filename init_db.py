import sqlite3

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
        system_prompt TEXT
    )
    ''')
    
    conn.commit()
    print("Database initialized successfully!")
    conn.close()

if __name__ == "__main__":
    init_db()