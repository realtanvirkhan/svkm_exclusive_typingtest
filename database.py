import sqlite3

def initialize_database():
    connection = sqlite3.connect('svkm_typing.db')
    cursor = connection.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            sap_id TEXT NOT NULL UNIQUE,
            college TEXT NOT NULL
        )
    ''')

    # Create test_results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            wpm INTEGER NOT NULL,
            accuracy FLOAT NOT NULL,
            raw_wpm INTEGER NOT NULL,
            test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    connection.commit()
    connection.close()

if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")